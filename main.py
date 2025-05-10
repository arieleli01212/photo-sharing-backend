from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil

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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

IP = "172.20.10.6"
PORT = 8000
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post(
    "/upload",
    summary="Upload image files",
    description="Upload up to 10 image files (jpg, jpeg, png)."
)
async def upload_images(images: list[UploadFile] = File(..., description="List of image files")):
    for image in images:
        if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG files are allowed.")

        save_path = os.path.join(UPLOAD_DIR, image.filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

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
