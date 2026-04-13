"""
build_patch -- execute PatchBuilder code in-process, capture output, save files.

Since the agent runs inside the uv-managed Python process, there is no need to
shell out. We exec() the patch code directly, redirect stdout to capture the
status line, and write both patch.py and patch.vcv to the output directory.
"""
import io
import sys
import contextlib
from pathlib import Path


def build_patch(code: str, output_dir: str) -> dict:
    """
    Execute PatchBuilder Python code, save patch.py + patch.vcv, return status.

    The code should use PatchBuilder normally but call pb.save() with a path
    under output_dir. The tool captures stdout (status, warnings) and returns
    whether the patch was proven.

    Args:
        code:       Complete Python source using PatchBuilder API.
        output_dir: Absolute path to directory for patch.py and patch.vcv.

    Returns:
        {
            "status":   "success" | "error",
            "proven":   bool,
            "stdout":   str,   # captured print output (pb.status, warnings)
            "error":    str,   # only on exception
        }
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Capture stdout so pb.status and warnings are returned, not printed
    stdout_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(code, {"__name__": "__main__"})  # noqa: S102

        captured = stdout_buf.getvalue()
        proven = "proven=True" in captured

        # Save the Python source alongside the compiled patch
        (out_dir / "patch.py").write_text(code)

        return {
            "status": "success",
            "proven": proven,
            "stdout": captured,
        }

    except Exception as e:
        captured = stdout_buf.getvalue()
        return {
            "status": "error",
            "proven": False,
            "stdout": captured,
            "error": str(e),
        }
