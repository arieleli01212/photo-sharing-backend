import os
from PIL import Image, ExifTags

def extract_image_metadata(image_path: str) -> dict:
    """Extract metadata from an image file."""
    try:
        img = Image.open(image_path)
        
        # Only try to extract EXIF for JPEG images
        if img.format in ["JPEG", "JPG"]:
            exif_data = getattr(img, "_getexif", lambda: None)()
            if exif_data is not None:
                exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items() if k in ExifTags.TAGS}
                return exif
            else:
                return {"message": "No EXIF data found."}
        else:
            return {"message": "EXIF extraction skipped (not a JPEG image)."}
    except Exception as e:
        return {"error": f"Failed to extract metadata: {str(e)}"}

def get_safe_filename(filename: str) -> str:
    """Get a safe filename by removing directory traversal attempts."""
    return os.path.basename(filename)

def is_allowed_file_type(filename: str, allowed_extensions: tuple = ('.jpg', '.jpeg', '.png')) -> bool:
    """Check if the file type is allowed."""
    return filename.lower().endswith(allowed_extensions)

def is_file_size_valid(file_size: int, max_size: int) -> bool:
    """Check if file size is within limits."""
    return file_size <= max_size

def validate_image_content(file_path: str) -> bool:
    """Validate that the file is actually an image by checking its content."""
    try:
        with Image.open(file_path) as img:
            # Verify the image by attempting to load it
            img.verify()
            return True
    except Exception:
        return False