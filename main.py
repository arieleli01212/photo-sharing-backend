from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
#from fastapi.staticfiles import StaticFiles
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

#app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

IP = "127.0.0.1"
PORT = 8000


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
