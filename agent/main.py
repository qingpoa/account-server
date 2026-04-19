from __future__ import annotations

import os
from argparse import ArgumentParser
from dotenv import load_dotenv

load_dotenv()


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Accounting agent CLI")
    parser.add_argument(
        "--thread-id",
        default=os.getenv("ACCOUNT_AGENT_THREAD_ID", "demo-thread"),
        help="Conversation thread id used by LangGraph memory.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        from account_agent.service.agent_service import AccountingAgentService
        from account_agent.config import get_settings
    except ModuleNotFoundError as exc:
        print(
            "Missing dependency or package: "
            f"{exc.name}. Run `pip install -e .` inside the agent directory first."
        )
        return 1

    if not get_settings().api_key:
        print("ACCOUNT_AGENT_API_KEY is not set. Copy `.env.example` to `.env` and fill it first.")
        return 1

    service = AccountingAgentService()

    print("Accounting agent is ready. Type `exit` or `quit` to stop.")
    print(f"Thread id: {args.thread_id}")
    print("Image accounting is available through LangSmith / Studio / API message attachments.")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("bye")
            return 0

        try:
            reply = service.chat(user_input=user_input, thread_id=args.thread_id)
        except Exception as exc:  # pragma: no cover
            print(f"agent error> {exc}")
            continue

        print(f"agent> {reply}")


if __name__ == "__main__":
    raise SystemExit(main())
