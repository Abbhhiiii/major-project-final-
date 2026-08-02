from dataclasses import replace
from typing import BinaryIO

from ..perception.models import VideoAsset
from ..ports import VideoRepository, VideoStorage


class VideoIngestionService:
    def __init__(self, storage: VideoStorage, repository: VideoRepository) -> None:
        self.storage = storage
        self.repository = repository

    def ingest(
        self, filename: str, content_type: str, source: BinaryIO, organization_id: str
    ) -> VideoAsset:
        asset = replace(
            self.storage.store(filename, content_type, source),
            organization_id=organization_id,
        )
        self.repository.save(asset)
        return asset
