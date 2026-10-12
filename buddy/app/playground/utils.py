from typing import Optional

from fastapi import HTTPException, UploadFile

from buddy.media import Audio
from buddy.media import File as FileMedia
from buddy.media import Image, Video
from buddy.utils.log import logger


def process_image(file: UploadFile) -> Image:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    return Image(content=content)


def process_audio(file: UploadFile) -> Audio:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    media_format = None
    if file.filename and "." in file.filename:
        media_format = file.filename.rsplit(".", 1)[-1].lower()
    elif file.content_type:
        media_format = file.content_type.split("/", 1)[-1].lower()

    return Audio(content=content, format=media_format)


def process_video(file: UploadFile) -> Video:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    media_format = None
    if file.filename and "." in file.filename:
        media_format = file.filename.rsplit(".", 1)[-1].lower()
    elif file.content_type:
        media_format = file.content_type.split("/", 1)[-1].lower()
    return Video(content=content, format=media_format)


def process_document(file: UploadFile) -> FileMedia:
    try:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")

        return FileMedia(content=content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Could not process document {file.filename}") from e
