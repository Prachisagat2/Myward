"""Image validation by file signature (not just the client-sent content type)."""


def detect_image_type(data: bytes) -> str | None:
    """Return the file extension for JPEG/PNG/WEBP data, else None."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None
