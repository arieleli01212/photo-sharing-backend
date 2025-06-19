from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
import psycopg2
from typing import List
from PIL import Image, ExifTags
from starlette.websockets import WebSocketState
from worker import add_image
from fastapi import BackgroundTasks

app = FastAPI(
    title="Image Upload API",
    description="API for uploading image files",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
guest_count = 0
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

active_connections: List[WebSocket] = []
IP = "172.20.10.6"
PORT = 5000
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
DB  = psycopg2.connect("postgresql://postgres:admin@localhost:5432/metadata")

@app.post(
    "/upload",
    summary="Upload image files",
    description="Upload up to 10 image files (jpg, jpeg, png)."
)
async def upload_images(bg: BackgroundTasks, images: list[UploadFile] = File(..., description="List of image files")):
    for image in images:
        if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG files are allowed.")

        save_path = os.path.join(UPLOAD_DIR, image.filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            img = Image.open(save_path)

            raw_exif = img._getexif()          # may be None
            if raw_exif:
                exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}
            else:
                exif = {}
            print(exif)

        # enqueue the face job
        bg.add_task(add_image, save_path) 

    return JSONResponse(content="The file upload successfully")

@app.get(
    "/get-images",
    summary="Get all image files",
    description="Get all image files (jpg, jpeg, png)."
)
async def get_images():
    try:
        files = os.listdir(UPLOAD_DIR)
        image_files = [
            f"http://{IP}:{PORT}/uploads/{filename}"
            for filename in files
            if filename.lower()
        ]
        return image_files
    except Exception as e:
        return {"error": str(e)}

@app.get("/people", summary="List known people")
async def list_people(limit: int = 100):
    cur = DB.cursor()
    cur.execute("""
        SELECT person_id, COUNT(*) AS shots
          FROM faces
      GROUP BY person_id
      ORDER BY shots DESC
      LIMIT %s
    """, (limit,))
    return cur.fetchall()

@app.get("/people/{person_id}")
async def photos_of_person(person_id: int, limit: int = 100):
    cur = DB.cursor()
    cur.execute(
        "SELECT image_path, bbox FROM faces WHERE person_id = %s LIMIT %s",
        (person_id, limit),
    )
    return [
        {
            "url": f"/{row[0]}",   # → /uploads/face1.jpeg
            "bbox": row[1],
        }
        for row in cur.fetchall()
    ]

@app.get("/guest")
async def get_guest_count():
    return {"count": guest_count}



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global guest_count
    await websocket.accept()
    active_connections.append(websocket)
    guest_count = len(active_connections)            # simpler
    await broadcast_guest_count()
    print("➕ connected", guest_count)
    try:
        while True:
            await websocket.receive_text()           # keep the task alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        guest_count = len(active_connections)
        await broadcast_guest_count()
        print("➖ disconnected", guest_count)

async def broadcast_guest_count() -> None:
    stale = []                                       # sockets we can’t use any more
    for ws in list(active_connections):             # iterate over a copy – we may edit the set
        if ws.client_state != WebSocketState.CONNECTED:
            stale.append(ws)
            continue

        try:
            await ws.send_json({"guestCount": guest_count})
        except RuntimeError:
            # close already started – mark as stale
            stale.append(ws)

    for ws in stale:
        active_connections.remove(ws)