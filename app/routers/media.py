"""
Media router for handling media file uploads, serving, and management.
"""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(prefix="/media", tags=["media"])

# Media storage configuration
MEDIA_ROOT = Path("static/media")
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".webm",
    ".mp3",
    ".wav",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    """Upload a media file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Ensure media directory exists
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = MEDIA_ROOT / file.filename
    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        with file_path.open("wb") as f:
            f.write(content)

        return {"filename": file.filename, "size": len(content), "path": str(file_path)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save file: {str(e)}"
        ) from e


@router.get("/files")
async def list_media_files():
    """List all uploaded media files."""
    if not MEDIA_ROOT.exists():
        return {"files": []}

    files = []
    for file_path in MEDIA_ROOT.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                {
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

    return {"files": files}


@router.get("/serve/{filename}")
async def serve_media(filename: str):
    """Serve a media file."""
    file_path = MEDIA_ROOT / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        content_type = "application/octet-stream"

    return FileResponse(path=str(file_path), media_type=content_type, filename=filename)


@router.delete("/files/{filename}")
async def delete_media_file(filename: str):
    """Delete a media file."""
    file_path = MEDIA_ROOT / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.unlink()
        return {"message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete file: {str(e)}"
        ) from e
