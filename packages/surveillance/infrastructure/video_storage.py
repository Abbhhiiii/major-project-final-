from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, ClassVar
from uuid import uuid4

from ..perception.models import VideoAsset


class InvalidVideoError(ValueError):
    pass


class LocalVideoStorage:
    allowed_types: ClassVar[dict[str, str]] = {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/webm": ".webm",
    }

    def __init__(self, root: Path, max_size_bytes: int) -> None:
        self.root = root.resolve()
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, filename: str, content_type: str, source: BinaryIO) -> VideoAsset:
        suffix = self.allowed_types.get(content_type)
        if suffix is None:
            raise InvalidVideoError("Supported formats are MP4, MOV, AVI, and WebM")
        safe_original = Path(filename or "video").name
        video_id = str(uuid4())
        stored_name = f"{video_id}{suffix}"
        target = self.resolve(stored_name)
        size = 0
        try:
            with target.open("xb") as destination:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_size_bytes:
                        raise InvalidVideoError(
                            f"Video exceeds the {self.max_size_bytes // (1024 * 1024)} MB limit"
                        )
                    destination.write(chunk)
            if size == 0:
                raise InvalidVideoError("Uploaded video is empty")
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return VideoAsset(video_id, safe_original, stored_name, content_type, size)

    def resolve(self, stored_name: str) -> Path:
        candidate = (self.root / Path(stored_name).name).resolve()
        if candidate.parent != self.root:
            raise InvalidVideoError("Invalid stored video path")
        return candidate
