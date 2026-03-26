"""
Minimal async CLI runner for the VCV Rack patch agent.

Usage:
    python3 agent/main.py

The ADK web UI is also supported:
    adk web --port 8000
"""

import asyncio
import sys

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import root_agent

APP_NAME = "vcv_agent"


async def main() -> None:
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

    # Single-shot mode: prompt passed as CLI argument
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        content = types.Content(parts=[types.Part.from_text(text=user_input)])
        async for event in runner.run_async(
            session_id=session.id, user_id="user", new_message=content
        ):
            if event.is_final_response() and event.content:
                print(event.content.parts[0].text)
        return

    # Interactive REPL
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


if __name__ == "__main__":
    asyncio.run(main())
