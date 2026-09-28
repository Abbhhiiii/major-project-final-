import httpx

from packages.surveillance.infrastructure.geocoding import NominatimGeocoder


def test_geocoder_normalizes_and_caches_user_triggered_search(monkeypatch) -> None:
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            json=[
                {
                    "display_name": "Airport Road, Bengaluru",
                    "lat": "12.9716",
                    "lon": "77.5946",
                    "category": "highway",
                }
            ],
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    geocoder = NominatimGeocoder(
        "https://nominatim.example", "Sentrix-Test/1.0", minimum_interval_seconds=0
    )

    first = geocoder.search("  Airport   Road ")
    second = geocoder.search("airport road")

    assert first == second
    assert first[0]["latitude"] == 12.9716
    assert first[0]["longitude"] == 77.5946
    assert len(calls) == 1
    assert calls[0][1]["headers"]["User-Agent"] == "Sentrix-Test/1.0"
