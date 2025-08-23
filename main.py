from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
from typing import List

from app.core.config import config
from app.models.models import Token, GoogleToken
from app.services.auth import AuthService, verify_token
from app.services.websocket_manager import websocket_manager
from app.core.utils import extract_image_metadata, get_safe_filename, is_allowed_file_type, is_file_size_valid, validate_image_content

# Create upload directory
os.makedirs(config.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Image Upload API",
    description="API for uploading image files with OAuth authentication",
    version="2.0.0"
)

# Configure CORS - restrict origins in production
allowed_origins = ["*"]  # For development - should be restricted in production
if config.SERVER_HOST != "127.0.0.1" and config.SERVER_HOST != "localhost" and config.SERVER_HOST != "0.0.0.0":
    # In production, specify actual frontend domains
    allowed_origins = [
        "https://wedding.open-spaces.xyz",
        "https://www.wedding.open-spaces.xyz"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)

# Mount static files
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

# Authentication endpoints
@app.post("/google-login", response_model=Token)
async def google_login(google_token: GoogleToken):
    return await AuthService.google_login(google_token)


@app.get("/verify-token")
async def verify_user_token(current_user: str = Depends(verify_token)):
    return {"username": current_user, "valid": True}

# File upload endpoints
@app.post(
    "/upload",
    summary="Upload image files",
    description="Upload up to 10 image files (jpg, jpeg, png)."
)
async def upload_images(images: list[UploadFile] = File(..., description="List of image files"), current_user: str = Depends(verify_token)):
    for image in images:
        # Validate file type
        if not is_allowed_file_type(image.filename):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG files are allowed.")

        # Validate file size
        image.file.seek(0, os.SEEK_END)
        size = image.file.tell()
        image.file.seek(0)
        
        if not is_file_size_valid(size, config.MAX_FILE_SIZE):
            raise HTTPException(status_code=413, detail="File too large. Max size is 5MB.")

        # Generate unique filename to prevent conflicts and improve security
        import uuid
        file_extension = os.path.splitext(get_safe_filename(image.filename))[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        save_path = os.path.join(config.UPLOAD_DIR, unique_filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Validate that the uploaded file is actually an image
        if not validate_image_content(save_path):
            os.remove(save_path)  # Remove invalid file
            raise HTTPException(status_code=400, detail=f"Invalid image file: {image.filename}")
        
        # Extract metadata and print (or store in database)
        metadata = extract_image_metadata(save_path)
        print(metadata)

    return JSONResponse(content={"message": "Files uploaded successfully", "count": len(images)})

@app.get(
    "/get-images",
    summary="Get all image files",
    description="Get all image files (jpg, jpeg, png)."
)
async def get_images(request: Request):  # accept Request
    try:
        files = os.listdir(config.UPLOAD_DIR)
        allowed_exts = ('.jpg', '.jpeg', '.png')
        base = str(request.base_url).rstrip("/")  # e.g., http://localhost:8000
        image_files = [
            f"{base}/uploads/{filename}"
            for filename in files
            if filename.lower().endswith(allowed_exts)
        ]
        return image_files
    except Exception as e:
        return {"error": str(e)}

# WebSocket endpoints
@app.get("/guest")
async def get_guest_count():
    return {"count": websocket_manager.guest_count}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.handle_websocket(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)