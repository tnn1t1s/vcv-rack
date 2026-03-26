"""
Serialize a patch dict to the .vcv file format:
  zstd-compressed POSIX tar archive containing patch.json
"""

import io
import json
import tarfile
import zstandard


def save_vcv(patch_dict: dict, path: str):
    """Write patch_dict to a .vcv file at path."""
    json_bytes = json.dumps(patch_dict, indent=1).encode("utf-8")

    # Build tar archive in memory
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json")
        info.size = len(json_bytes)
        tar.addfile(info, io.BytesIO(json_bytes))
    tar_bytes = buf.getvalue()

    # Compress with zstd
    cctx = zstandard.ZstdCompressor(level=3)
    compressed = cctx.compress(tar_bytes)

    with open(path, "wb") as f:
        f.write(compressed)


def load_vcv(path: str) -> dict:
    """Load a .vcv file and return the patch dict."""
    with open(path, "rb") as f:
        data = f.read()

    dctx = zstandard.ZstdDecompressor()
    tar_bytes = dctx.decompress(data, max_output_size=64 * 1024 * 1024)

    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        member = tar.getmember("patch.json")
        f = tar.extractfile(member)
        return json.loads(f.read())
