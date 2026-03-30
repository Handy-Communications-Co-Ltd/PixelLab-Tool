"""Image and file utility helpers."""

import base64
import io
import os
from datetime import datetime
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


def _save_rgba_image(b64_data: str, width: int, height: int, output_path: str):
    """Decode rgba_bytes base64 and save as PNG."""
    raw = base64.b64decode(b64_data)
    img = Image.frombytes("RGBA", (width, height), raw)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")


def save_images_from_response(data: dict, output_dir: str, prefix: str = "output") -> list[str]:
    """Extract and save images from an API response. Returns list of saved paths."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{prefix}_{timestamp}"
    saved = []

    # Check for last_response with images (background job result)
    if isinstance(data, dict) and "last_response" in data:
        last_resp = data["last_response"]
        if isinstance(last_resp, dict) and "images" in last_resp:
            result = _extract_images(last_resp["images"], output_dir, prefix)
            if result:
                return result
        # Single image in last_response (e.g. /create-isometric-tile)
        if isinstance(last_resp, dict) and "image" in last_resp and isinstance(last_resp["image"], dict):
            img = last_resp["image"]
            if "base64" in img:
                img_type = img.get("type", "")
                path = os.path.join(output_dir, f"{prefix}_0.png")
                if img_type == "rgba_bytes" and "width" in img:
                    w = img["width"]
                    h = img.get("height", w)
                    _save_rgba_image(img["base64"], w, h, path)
                else:
                    save_base64_image(img["base64"], path)
                return [path]

    # Handle different response shapes
    images = []
    if isinstance(data, dict):
        # Single image in data
        if "base64" in data:
            images = [data]
        # Single image field (pixflux/bitforge sync response)
        elif "image" in data and isinstance(data["image"], dict):
            images = [data["image"]]
        # List of images in data.images
        elif "images" in data:
            result = _extract_images(data["images"], output_dir, prefix)
            if result:
                return result
            images = data["images"] if isinstance(data["images"], list) else []
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
            img_type = img.get("type", "")
            if img_type == "rgba_bytes" and "width" in img:
                w = img["width"]
                h = img.get("height", w)
                path = os.path.join(output_dir, f"{prefix}_{i}.png")
                _save_rgba_image(img["base64"], w, h, path)
                saved.append(path)
            else:
                fmt = img.get("format", "png")
                ext = fmt if fmt != "jpeg" else "jpg"
                path = os.path.join(output_dir, f"{prefix}_{i}.{ext}")
                save_base64_image(img["base64"], path, fmt)
                saved.append(path)
        elif isinstance(img, str):
            path = os.path.join(output_dir, f"{prefix}_{i}.png")
            save_base64_image(img, path)
            saved.append(path)

    return saved


def _extract_images(images_data, output_dir: str, prefix: str) -> list[str]:
    """Extract images from dict (direction-keyed) or list format."""
    saved = []
    if isinstance(images_data, dict):
        # Direction-keyed images: {"south": {"type": "rgba_bytes", "width": 64, "base64": "..."}, ...}
        for direction, img in images_data.items():
            if isinstance(img, dict) and "base64" in img:
                img_type = img.get("type", "")
                path = os.path.join(output_dir, f"{prefix}_{direction}.png")
                if img_type == "rgba_bytes" and "width" in img:
                    w = img["width"]
                    h = img.get("height", w)
                    _save_rgba_image(img["base64"], w, h, path)
                else:
                    save_base64_image(img["base64"], path)
                saved.append(path)
    elif isinstance(images_data, list):
        for i, img in enumerate(images_data):
            if isinstance(img, dict) and "base64" in img:
                img_type = img.get("type", "")
                path = os.path.join(output_dir, f"{prefix}_{i}.png")
                if img_type == "rgba_bytes" and "width" in img:
                    w = img["width"]
                    h = img.get("height", w)
                    _save_rgba_image(img["base64"], w, h, path)
                else:
                    save_base64_image(img["base64"], path)
                saved.append(path)
    return saved
