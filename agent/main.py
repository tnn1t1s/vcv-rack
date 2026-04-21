"""
Minimal async CLI runner for the current VCV Rack patch-builder agent.

Canonical entrypoints:
    uv run vcv-agent "Create a minimal patch"
    uv run vcv-agent-doctor
    uv run python -m agent
"""

from __future__ import annotations

import argparse
import asyncio

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .patch_builder.agent import root_agent

APP_NAME = "vcv_agent"


async def run_agent(prompt: str | None = None) -> None:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        state={}, app_name=APP_NAME, user_id="user"
    )
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )

    if prompt:
        content = types.Content(parts=[types.Part.from_text(text=prompt)])
        async for event in runner.run_async(
            session_id=session.id, user_id="user", new_message=content
        ):
            if event.is_final_response() and event.content:
                print(event.content.parts[0].text)
        return

    print("VCV Rack Patch Agent  (type 'quit' to exit)")
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        content = types.Content(parts=[types.Part.from_text(text=user_input)])
        async for event in runner.run_async(
            session_id=session.id,
            user_id="user",
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                print(f"\nAgent: {event.content.parts[0].text}")


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="vcv-agent",
        description="Run the VCV Rack patch-builder agent once or in interactive mode.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional one-shot prompt. If omitted, start the interactive REPL.",
    )
    args = parser.parse_args()
    prompt = " ".join(args.prompt).strip() or None
    asyncio.run(run_agent(prompt))


if __name__ == "__main__":
    run()
