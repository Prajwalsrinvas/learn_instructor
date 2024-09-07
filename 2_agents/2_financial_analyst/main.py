import argparse
import os

from agent import Agent
from colorama import init
from dotenv import load_dotenv
from openai import OpenAI
from tools import (get_company_name_and_ticker, get_company_news,
                   get_financial_statements, search_on_internet)

# Initialize colorama
init(autoreset=True)


def main():
    parser = argparse.ArgumentParser(
        description="Run Financial Analyst agent with a specified company."
    )
    parser.add_argument(
        "-c",
        "--company",
        type=str,
        required=True,
        help="The company to analyze",
    )
    args = parser.parse_args()

    load_dotenv()
    init(autoreset=True)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    openai_client = OpenAI(api_key=openai_api_key)

    agent = Agent("Financial Analyst", openai_client)
    agent.add_tool(search_on_internet)
    agent.add_tool(get_company_news)
    agent.add_tool(get_company_name_and_ticker)
    agent.add_tool(get_financial_statements)

    directive = f"Write a detailed investment thesis for {args.company} based on the latest news and financial statements"
    agent.run(directive)


if __name__ == "__main__":
    main()
