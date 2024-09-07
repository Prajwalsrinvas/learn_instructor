import os

import requests


def search_on_internet(query: str) -> dict:
    search_url = "https://serpapi.com/search"
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable is not set")

    params = {"q": query, "api_key": api_key, "num": 3}
    response = requests.get(search_url, params=params)

    if response.status_code != 200:
        raise Exception(
            f"Search request failed with status code {response.status_code}"
        )

    data = response.json()

    if "error" in data:
        raise Exception(f"Search API returned an error: {data['error']}")

    if "organic_results" not in data or len(data["organic_results"]) == 0:
        return {"results": [], "text": "No results found"}

    return {
        "results": data["organic_results"],
        "text": data["organic_results"][0]["snippet"],
    }
