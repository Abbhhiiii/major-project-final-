from collections.abc import Iterator
from pathlib import Path

import cv2

from .models import VideoFrame


class VideoReadError(RuntimeError):
    pass


class OpenCVFrameReader:
    def frames(self, path: Path, sample_fps: float) -> tuple[int, Iterator[VideoFrame]]:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise VideoReadError("OpenCV could not open the uploaded video")
        source_fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        total_source_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, round(source_fps / sample_fps))
        expected = max(1, (total_source_frames + interval - 1) // interval)

        def read_frames() -> Iterator[VideoFrame]:
            source_index = 0
            try:
                while True:
                    ok, image = capture.read()
                    if not ok:
                        break
                    if source_index % interval == 0:
                        timestamp_ms = round(source_index / source_fps * 1000)
                        yield VideoFrame(source_index, timestamp_ms, image)
                    source_index += 1
            finally:
                capture.release()

        return expected, read_frames()
