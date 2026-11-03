"""CLI composition root for policy publication operations."""

import argparse
from pathlib import Path

from src.composition import build_chat_runtime, build_policy_runtime
from src.config import PolicyRuntimeSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Empório da Música service agent")
    parser.add_argument("command", choices=("chat", "publish", "rollback", "active"))
    parser.add_argument("version", nargs="?")
    parser.add_argument("--phone", help="Customer channel phone number, required for chat")
    args = parser.parse_args()
    project_root = Path(__file__).parents[1]
    settings = PolicyRuntimeSettings.from_environment(project_root)
    if args.command == "chat":
        if not args.phone:
            parser.error("chat requires --phone")
        chat = build_chat_runtime(settings, project_root / "data")
        session = chat.authenticator.get_or_create_session(args.phone, chat.policy_version)
        print("Empório da Música: olá! Digite 'sair' para encerrar.")
        while True:
            try:
                message = input("Você: ").strip()
            except EOFError:
                break
            if message.casefold() in {"sair", "exit", "quit"}:
                break
            if message:
                print(f"Empório da Música: {chat.orchestrator.reply(message, session).response}")
        return
    runtime = build_policy_runtime(settings)
    if args.command == "publish":
        if not args.version:
            parser.error("publish requires a policy version")
        print(f"indexed_chunks={runtime.publisher.publish(args.version)}")
    elif args.command == "rollback":
        print(runtime.publisher.rollback() or "no_previous_version")
    else:
        active = runtime.registry.active()
        print(active.version if active else "no_active_version")


if __name__ == "__main__":
    main()
