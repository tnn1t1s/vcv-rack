"""Write text content to a file, creating parent directories as needed."""
from pathlib import Path


def write_file(path: str, content: str) -> dict:
    """
    Write text content to a file.

    Args:
        path: Absolute path to write.
        content: Text content to write.

    Returns:
        {"status": "success", "path": str}
        {"status": "error", "error": str}
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"status": "success", "path": str(p)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
