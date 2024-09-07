import os
from typing import Dict

import requests
from yahooquery import Ticker


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


def get_company_news(company_name: str) -> str:
    params = {
        "engine": "google",
        "tbm": "nws",
        "q": company_name,
        "api_key": os.environ["SERPAPI_API_KEY"],
    }
    response = search_on_internet(params["q"])
    return f"news: {response['results']}"


def get_company_name_and_ticker(input: str) -> Dict[str, str]:
    # This function would typically use the brain to extract information,
    # but for simplicity, we'll just return a dummy result
    return {"company_name": input, "ticker": input.upper()}


def get_financial_statements(ticker: str) -> str:
    company = Ticker(ticker)

    balance_sheet = company.balance_sheet().to_string()
    cash_flow = company.cash_flow(trailing=False).to_string()
    income_statement = company.income_statement().to_string()
    valuation_measures = str(company.valuation_measures)

    return (
        f"Balance Sheet: {balance_sheet}\n"
        f"Cash Flow: {cash_flow}\n"
        f"Income Statement: {income_statement}\n"
        f"Valuation Measures: {valuation_measures}"
    )
