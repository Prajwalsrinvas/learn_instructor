import argparse
import os

from agent import Agent
from colorama import init
from dotenv import load_dotenv
from openai import OpenAI
from tools import search_on_internet


def main():
    parser = argparse.ArgumentParser(
        description="Run J.A.R.V.I.S. agent with a specified question."
    )
    parser.add_argument(
        "-q",
        "--question",
        type=str,
        required=True,
        help="The question to ask J.A.R.V.I.S.",
    )
    args = parser.parse_args()

    load_dotenv()
    init(autoreset=True)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    openai_client = OpenAI(api_key=openai_api_key)

    agent = Agent("J.A.R.V.I.S.", openai_client)
    agent.add_tool(search_on_internet)

    agent.run(args.question)


if __name__ == "__main__":
    main()
