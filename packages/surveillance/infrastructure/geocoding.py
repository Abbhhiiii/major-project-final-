from __future__ import annotations

import threading
import time
from typing import Any

import httpx


class GeocodingUnavailable(RuntimeError):
    pass


class NominatimGeocoder:
    """Rate-limited, cached location search behind a replaceable provider boundary."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        minimum_interval_seconds: float = 1.0,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.minimum_interval_seconds = minimum_interval_seconds
        self.timeout_seconds = timeout_seconds
        self._cache: dict[tuple[Any, ...], Any] = {}
        self._lock = threading.Lock()
        self._last_request_at = 0.0

    def search(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        normalized = " ".join(query.strip().split())
        key = ("search", normalized.casefold(), limit)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        payload = self._request(
            "/search",
            {"q": normalized, "format": "jsonv2", "addressdetails": 1, "limit": limit},
        )
        if not isinstance(payload, list):
            raise GeocodingUnavailable("Map provider returned an invalid search response")
        results = [self._place(item) for item in payload if isinstance(item, dict)]
        self._cache[key] = results
        return results

    def reverse(self, latitude: float, longitude: float) -> dict[str, object]:
        key = ("reverse", round(latitude, 5), round(longitude, 5))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        payload = self._request(
            "/reverse",
            {
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": 18,
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            raise GeocodingUnavailable("No named location was found for that map point")
        result = self._place(payload)
        self._cache[key] = result
        return result

    def _request(self, path: str, params: dict[str, object]) -> Any:
        with self._lock:
            remaining = self.minimum_interval_seconds - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
            try:
                response = httpx.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise GeocodingUnavailable("Map search is temporarily unavailable") from error
            finally:
                self._last_request_at = time.monotonic()

    @staticmethod
    def _place(item: dict[str, Any]) -> dict[str, object]:
        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])
        except (KeyError, TypeError, ValueError) as error:
            raise GeocodingUnavailable("Map provider returned invalid coordinates") from error
        return {
            "display_name": str(item.get("display_name") or f"{latitude:.5f}, {longitude:.5f}"),
            "latitude": latitude,
            "longitude": longitude,
            "category": str(item.get("category") or item.get("type") or "place"),
        }
