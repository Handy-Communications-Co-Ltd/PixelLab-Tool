"""Image and file utility helpers."""

import base64
import io
import os
from pathlib import Path

from PIL import Image


def image_to_base64(path: str) -> dict:
    """Convert an image file to PixelLab base64 format."""
    path = Path(path)
    fmt = path.suffix.lstrip(".").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return {"type": "base64", "base64": data, "format": fmt}


def get_image_size(path: str) -> dict:
    """Get width and height of an image file."""
    with Image.open(path) as img:
        return {"width": img.width, "height": img.height}


def save_base64_image(data: str, output_path: str, fmt: str = "png"):
    """Decode a base64 string and save as image file."""
    raw = base64.b64decode(data)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(raw)


def save_images_from_response(data: dict, output_dir: str, prefix: str = "output") -> list[str]:
    """Extract and save images from an API response. Returns list of saved paths."""
    os.makedirs(output_dir, exist_ok=True)
    saved = []

    # Handle different response shapes
    images = []
    if isinstance(data, dict):
        # Single image in data
        if "base64" in data:
            images = [data]
        # List of images in data.images
        elif "images" in data:
            images = data["images"]
        # Frames from animation
        elif "frames" in data:
            images = data["frames"]
        # Nested data
        elif "data" in data:
            return save_images_from_response(data["data"], output_dir, prefix)
    elif isinstance(data, list):
        images = data

    for i, img in enumerate(images):
        if isinstance(img, dict) and "base64" in img:
            fmt = img.get("format", "png")
            ext = fmt if fmt != "jpeg" else "jpg"
            path = os.path.join(output_dir, f"{prefix}_{i}.{ext}")
            save_base64_image(img["base64"], path, fmt)
            saved.append(path)
        elif isinstance(img, str):
            # Raw base64 string
            path = os.path.join(output_dir, f"{prefix}_{i}.png")
            save_base64_image(img, path)
            saved.append(path)

    return saved
