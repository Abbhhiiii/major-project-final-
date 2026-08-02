import hashlib
import math
import re


class LocalHashEmbedding:
    """Small deterministic feature-hash embedding for reliable offline retrieval."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % self.dimensions
            vector[index] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector

    @staticmethod
    def similarity(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))
