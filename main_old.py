from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import shutil
from typing import List, Optional
from PIL import Image, ExifTags
from starlette.websockets import WebSocketState
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import json
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from dotenv import load_dotenv
import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# Load environment variables
load_dotenv()

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

# Authentication setup
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Google OAuth setup
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
if not GOOGLE_CLIENT_ID:
    raise ValueError("GOOGLE_CLIENT_ID environment variable is required")

# Apple OAuth setup
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY_PATH = os.getenv("APPLE_PRIVATE_KEY_PATH")

if not all([APPLE_CLIENT_ID, APPLE_TEAM_ID, APPLE_KEY_ID]):
    print("Warning: Apple Sign-In not configured. Set APPLE_CLIENT_ID, APPLE_TEAM_ID, and APPLE_KEY_ID environment variables.")

security = HTTPBearer()

# Pydantic models


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class GoogleToken(BaseModel):
    token: str

class AppleToken(BaseModel):
    token: str

# Simple in-memory user storage (in production, use a database)
users_db = {}

guest_count = 0
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

active_connections: List[WebSocket] = []
IP = os.getenv("SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("SERVER_PORT", "8000"))
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(5 * 1024 * 1024)))  # Default 5 MB

# Authentication helper functions

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        if username not in users_db:
            raise HTTPException(status_code=401, detail="User not found")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Authentication endpoints


@app.get("/verify-token")
async def verify_user_token(current_user: str = Depends(verify_token)):
    return {"username": current_user, "valid": True}

@app.post("/google-login", response_model=Token)
async def google_login(google_token: GoogleToken):
    try:
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            google_token.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        
        # Check if the token is valid
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(status_code=400, detail="Wrong issuer")
        
        # Extract user info from Google token
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', email)
        
        # Create or get existing user
        username = f"google_{google_id}"
        
        if username not in users_db:
            # Create new user from Google account
            users_db[username] = {
                "username": username,
                "email": email,
                "name": name,
                "google_id": google_id,
                "provider": "google"
            }
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": name  # Use the display name instead of internal username
        }
    
    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=400, detail="Invalid Google token")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.post("/apple-login", response_model=Token)
async def apple_login(apple_token: AppleToken):
    try:
        # Decode the Apple JWT token without verification first to get the header
        unverified_header = pyjwt.get_unverified_header(apple_token.token)
        
        # Get Apple's public keys
        import requests
        apple_keys_response = requests.get("https://appleid.apple.com/auth/keys")
        apple_keys = apple_keys_response.json()
        
        # Find the correct key
        key_id = unverified_header.get('kid')
        public_key = None
        
        for key in apple_keys['keys']:
            if key['kid'] == key_id:
                # Convert the JWK to PEM format
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import serialization
                import base64
                
                # Decode the key components
                n = base64.urlsafe_b64decode(key['n'] + '==')
                e = base64.urlsafe_b64decode(key['e'] + '==')
                
                # Convert to integers
                n_int = int.from_bytes(n, 'big')
                e_int = int.from_bytes(e, 'big')
                
                # Create RSA public key
                public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
                public_key = public_numbers.public_key()
                break
        
        if not public_key:
            raise HTTPException(status_code=400, detail="Invalid Apple token - key not found")
        
        # Verify and decode the token
        try:
            decoded_token = pyjwt.decode(
                apple_token.token,
                public_key,
                algorithms=['RS256'],
                audience=APPLE_CLIENT_ID,
                issuer='https://appleid.apple.com'
            )
        except pyjwt.InvalidTokenError as e:
            raise HTTPException(status_code=400, detail=f"Invalid Apple token: {str(e)}")
        
        # Extract user info from Apple token
        apple_id = decoded_token.get('sub')
        email = decoded_token.get('email', '')
        name = email.split('@')[0] if email else f"Apple User {apple_id[:8]}"
        
        # Create or get existing user
        username = f"apple_{apple_id}"
        
        if username not in users_db:
            # Create new user from Apple account
            users_db[username] = {
                "username": username,
                "email": email,
                "name": name,
                "apple_id": apple_id,
                "provider": "apple"
            }
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": name  # Use the display name instead of internal username
        }
    
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Failed to verify Apple token")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Apple authentication failed")

@app.post(
    "/upload",
    summary="Upload image files",
    description="Upload up to 10 image files (jpg, jpeg, png)."
)
async def upload_images(images: list[UploadFile] = File(..., description="List of image files")):

    for image in images:
        if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG files are allowed.")

        image.file.seek(0, os.SEEK_END)
        size = image.file.tell()
        image.file.seek(0)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Max size is 5MB.")

        safe_filename = os.path.basename(image.filename)
        save_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        img = Image.open(save_path)

        # Only try to extract EXIF for JPEG images
        if img.format in ["JPEG", "JPG"]:
            exif_data = getattr(img, "_getexif", lambda: None)()
            if exif_data is not None:
                exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items() if k in ExifTags.TAGS}
                print(exif)
            else:
                print("No EXIF data found.")
        else:
            print("EXIF extraction skipped (not a JPEG image).")

    return JSONResponse(content="The file upload successfully")

@app.get(
    "/get-images",
    summary="Get all image files",
    description="Get all image files (jpg, jpeg, png)."
)
async def get_images():
    try:
        files = os.listdir(UPLOAD_DIR)
        allowed_exts = ('.jpg', '.jpeg', '.png')
        image_files = [
            f"/api/uploads/{filename}"
            for filename in files
            if filename.lower().endswith(allowed_exts)
        ]
        return image_files
    except Exception as e:
        return {"error": str(e)}

@app.get("/guest")
async def get_guest_count():
    return {"count": guest_count}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global guest_count
    await websocket.accept()
    active_connections.append(websocket)
    guest_count = len(active_connections)
    await broadcast_guest_count()
    print("➕ connected", guest_count)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass  # Handle disconnect gracefully
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        if websocket in active_connections:
            active_connections.remove(websocket)
        guest_count = len(active_connections)
        await broadcast_guest_count()
        print("➖ disconnected", guest_count)

async def broadcast_guest_count() -> None:
    global guest_count
    stale = []
    for ws in list(active_connections):
        if ws.client_state != WebSocketState.CONNECTED:
            stale.append(ws)
            continue

        try:
            await ws.send_json({"guestCount": guest_count})
        except Exception as e:
            # Any send error means the connection is bad
            print(f"Failed to send to client: {e}")
            stale.append(ws)

    # Remove stale connections
    for ws in stale:
        if ws in active_connections:
            active_connections.remove(ws)
    
    # Update guest count after cleanup
    guest_count = len(active_connections)