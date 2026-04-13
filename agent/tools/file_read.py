"""Read a file from the filesystem and return its contents."""
from pathlib import Path


def file_read(path: str) -> dict:
    """
    Read a file and return its text contents.

    Args:
        path: Absolute path to the file.

    Returns:
        {"status": "success", "content": str}
        {"status": "error", "error": str}
    """
    try:
        content = Path(path).read_text()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "error": str(e)}
