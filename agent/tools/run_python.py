"""Execute a Python script via `uv run python`, ensuring the correct venv and
project dependencies are available. Never calls system python3.
"""
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent  # vcv-rack/


def run_python(script_path: str) -> dict:
    """
    Execute a Python script using `uv run python` from the project root.

    This guarantees the script runs inside the project's uv-managed venv with
    all dependencies available -- identical to how agents themselves are launched.

    Args:
        script_path: Absolute path to the .py script to run.

    Returns:
        {"status": "success", "stdout": str, "stderr": str}
        {"status": "error", "returncode": int, "stdout": str, "stderr": str}
    """
    try:
        result = subprocess.run(
            ["uv", "run", "python", script_path],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        status = "success" if result.returncode == 0 else "error"
        return {
            "status": status,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "returncode": -1, "stdout": "", "stderr": "Timeout after 30s"}
    except Exception as e:
        return {"status": "error", "returncode": -1, "stdout": "", "stderr": str(e)}
