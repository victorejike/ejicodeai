from types import SimpleNamespace

from agents.job_scout.job_scout_agent import GoogleMapsScraper


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": {"id": "run-1", "defaultDatasetId": "dataset-1"}},
        )

    async def get(self, url, **kwargs):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: [
                {
                    "title": "Acme Labs",
                    "name": "Acme Labs",
                    "url": "https://maps.google.com/example",
                    "address": "Remote",
                    "description": "Builds AI products",
                }
            ],
        )


def test_google_maps_scraper_returns_mapped_results(monkeypatch):
    monkeypatch.setattr("agents.job_scout.job_scout_agent.get_settings", lambda: SimpleNamespace(apify_api_token="token", apify_google_maps_actor_id="compass/crawler-google-places"))
    monkeypatch.setattr("httpx.AsyncClient", DummyAsyncClient)

    scraper = GoogleMapsScraper(query="ai startups", location="Remote")
    results = __import__("asyncio").run(scraper.scrape())

    assert len(results) == 1
    assert results[0]["title"] == "Acme Labs"
    assert results[0]["source_platform"] == "googlemaps"
    assert results[0]["location"] == "Remote"
