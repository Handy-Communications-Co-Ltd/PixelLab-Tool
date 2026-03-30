"""PixelLab API v2 client."""

import time
from typing import Any, Optional

import requests

BASE_URL = "https://api.pixellab.ai/v2"


class PixelLabError(Exception):
    """API error with status code and message."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"[{status_code}] {message}")


class PixelLabClient:
    """Client for PixelLab pixel art generation API."""

    def __init__(self, api_key: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code in (200, 202):
            return resp.json()
        try:
            err = resp.json()
            msg = err.get("error") or err.get("detail") or str(err)
        except Exception:
            msg = resp.text
        raise PixelLabError(resp.status_code, msg)

    def _post(self, path: str, payload: dict) -> dict:
        return self._request("POST", path, json=payload)

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def _patch(self, path: str, payload: dict) -> dict:
        return self._request("PATCH", path, json=payload)

    # ── Account ──

    def get_balance(self) -> dict:
        return self._get("/balance")

    # ── Background Jobs ──

    def get_job(self, job_id: str) -> dict:
        return self._get(f"/background-jobs/{job_id}")

    def wait_for_job(self, job_id: str, poll_interval: float = 2.0) -> dict:
        """Poll a background job until completion."""
        job_id = job_id.strip()
        retries_on_not_found = 3
        # Initial delay to let the job register on the server
        time.sleep(1.0)
        while True:
            try:
                result = self.get_job(job_id)
            except PixelLabError as e:
                # Retry on 403/404 (job may not be registered yet)
                if e.status_code in (403, 404) and retries_on_not_found > 0:
                    retries_on_not_found -= 1
                    time.sleep(poll_interval)
                    continue
                raise
            data = result.get("data", {})
            status = result.get("status") or data.get("status", "")
            status_lower = status.lower() if isinstance(status, str) else ""

            # Check explicit completion status
            if status_lower in ("completed", "complete", "done", "success", "finished"):
                return result
            if status_lower in ("failed", "error", "cancelled"):
                # Extract readable error from last_response
                last_resp = result.get("last_response") or data.get("last_response") or {}
                detail = last_resp.get("detail") or last_resp.get("error") or ""
                if "429" in str(detail) or "job limits" in str(detail).lower():
                    msg = (
                        "작업 한도 초과!\n\n"
                        "PixelLab 구독 플랜의 동시 작업 또는 일일 한도에 도달했습니다.\n"
                        "대시보드에서 잔여 크레딧을 확인하거나 잠시 후 다시 시도해주세요."
                    )
                else:
                    msg = detail or f"작업 실패 (status: {status})"
                raise PixelLabError(500, msg)

            # Check if last_response contains completed data (API sometimes
            # keeps status as "processing" but has results in last_response)
            last_resp = result.get("last_response") or data.get("last_response")
            if isinstance(last_resp, dict):
                resp_type = last_resp.get("type", "")
                if resp_type in ("message_done", "done", "completed"):
                    return result

            time.sleep(poll_interval)

    # ── Character Creation ──

    def create_character_4dir(self, description: str, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/create-character-with-4-directions", payload)

    def create_character_8dir(self, description: str, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/create-character-with-8-directions", payload)

    def animate_character(self, character_id: str, template_animation_id: str, **kwargs) -> dict:
        payload = {
            "character_id": character_id,
            "template_animation_id": template_animation_id,
            **kwargs,
        }
        return self._post("/animate-character", payload)

    def create_character_animation(self, character_id: str, template_animation_id: str, **kwargs) -> dict:
        payload = {
            "character_id": character_id,
            "template_animation_id": template_animation_id,
            **kwargs,
        }
        return self._post("/characters/animations", payload)

    # ── Character Management ──

    def list_characters(self, limit: int = 20, offset: int = 0) -> dict:
        return self._get("/characters", {"limit": limit, "offset": offset})

    def get_character(self, character_id: str) -> dict:
        return self._get(f"/characters/{character_id}")

    def delete_character(self, character_id: str) -> dict:
        return self._delete(f"/characters/{character_id}")

    def export_character_zip(self, character_id: str) -> bytes:
        url = f"{self.base_url}/characters/{character_id}/zip"
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.content
        raise PixelLabError(resp.status_code, resp.text)

    def update_character_tags(self, character_id: str, tags: list[str]) -> dict:
        return self._patch(f"/characters/{character_id}/tags", {"tags": tags})

    # ── Image Generation ──

    def generate_image(self, description: str, width: int = 128, height: int = 128, **kwargs) -> dict:
        """Generate image using Pro model (v2)."""
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/generate-image-v2", payload)

    def generate_image_pixflux(self, description: str, width: int = 128, height: int = 128, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/create-image-pixflux", payload)

    def generate_image_bitforge(self, description: str, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/create-image-bitforge", payload)

    def generate_with_style(self, description: str, style_images: list[dict],
                            width: int = 128, height: int = 128, **kwargs) -> dict:
        payload = {
            "description": description,
            "style_images": style_images,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/generate-with-style-v2", payload)

    def generate_ui(self, description: str, width: int = 256, height: int = 256, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/generate-ui-v2", payload)

    # ── Edit ──

    def edit_image(self, image: dict, description: str, width: int, height: int, **kwargs) -> dict:
        payload = {
            "image": image,
            "description": description,
            "image_size": {"width": width, "height": height},
            "width": width,
            "height": height,
            **kwargs,
        }
        return self._post("/edit-image", payload)

    def edit_images_v2(self, edit_images: list[dict], width: int, height: int, **kwargs) -> dict:
        payload = {
            "edit_images": edit_images,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/edit-images-v2", payload)

    # ── Animation ──

    def animate_with_text(self, reference_image: dict, description: str, action: str, **kwargs) -> dict:
        payload = {
            "reference_image": reference_image,
            "description": description,
            "action": action,
            "image_size": {"width": 64, "height": 64},
            **kwargs,
        }
        return self._post("/animate-with-text", payload)

    def animate_with_text_v2(self, reference_image: dict, action: str,
                             width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "reference_image": reference_image,
            "action": action,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        if "reference_image_size" not in payload:
            payload["reference_image_size"] = {"width": width, "height": height}
        return self._post("/animate-with-text-v2", payload)

    def animate_with_skeleton(self, reference_image: dict, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "reference_image": reference_image,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/animate-with-skeleton", payload)

    def edit_animation(self, description: str, frames: list[dict],
                       width: int, height: int, **kwargs) -> dict:
        payload = {
            "description": description,
            "frames": frames,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/edit-animation-v2", payload)

    def interpolate(self, start_image: dict, end_image: dict, action: str,
                    width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "start_image": start_image,
            "end_image": end_image,
            "action": action,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/interpolation-v2", payload)

    def transfer_outfit(self, reference_image: dict, frames: list[dict],
                        width: int, height: int, **kwargs) -> dict:
        payload = {
            "reference_image": reference_image,
            "frames": frames,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/transfer-outfit-v2", payload)

    def estimate_skeleton(self, image: dict) -> dict:
        return self._post("/estimate-skeleton", {"image": image})

    # ── Image Operations ──

    def image_to_pixelart(self, image: dict, input_width: int, input_height: int,
                          output_width: int, output_height: int, **kwargs) -> dict:
        payload = {
            "image": image,
            "image_size": {"width": input_width, "height": input_height},
            "output_size": {"width": output_width, "height": output_height},
            **kwargs,
        }
        return self._post("/image-to-pixelart", payload)

    def resize(self, description: str, reference_image: dict,
               ref_width: int, ref_height: int,
               target_width: int, target_height: int, **kwargs) -> dict:
        payload = {
            "description": description,
            "reference_image": reference_image,
            "reference_image_size": {"width": ref_width, "height": ref_height},
            "target_size": {"width": target_width, "height": target_height},
            **kwargs,
        }
        return self._post("/resize", payload)

    # ── Inpaint ──

    def inpaint(self, description: str, inpainting_image: dict, mask_image: dict,
                width: int, height: int, **kwargs) -> dict:
        payload = {
            "description": description,
            "inpainting_image": inpainting_image,
            "mask_image": mask_image,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/inpaint", payload)

    def inpaint_v3(self, description: str, inpainting_image: dict, mask_image: dict, **kwargs) -> dict:
        payload = {
            "description": description,
            "inpainting_image": inpainting_image,
            "mask_image": mask_image,
            **kwargs,
        }
        return self._post("/inpaint-v3", payload)

    # ── Tilesets ──

    def create_tileset(self, lower_description: str, upper_description: str, **kwargs) -> dict:
        payload = {
            "lower_description": lower_description,
            "upper_description": upper_description,
            **kwargs,
        }
        return self._post("/tilesets", payload)

    def create_tileset_topdown(self, lower_description: str, upper_description: str, **kwargs) -> dict:
        payload = {
            "lower_description": lower_description,
            "upper_description": upper_description,
            **kwargs,
        }
        return self._post("/create-tileset", payload)

    def get_tileset(self, tileset_id: str) -> dict:
        return self._get(f"/tilesets/{tileset_id}")

    def create_tileset_sidescroller(self, lower_description: str, **kwargs) -> dict:
        payload = {"lower_description": lower_description, **kwargs}
        return self._post("/tilesets-sidescroller", payload)

    def create_isometric_tile(self, description: str, width: int = 32, height: int = 32, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/create-isometric-tile", payload)

    def get_isometric_tile(self, tile_id: str) -> dict:
        return self._get(f"/isometric-tiles/{tile_id}")

    def create_tiles_pro(self, description: str, **kwargs) -> dict:
        payload = {"description": description, **kwargs}
        return self._post("/create-tiles-pro", payload)

    def get_tiles_pro(self, tile_id: str) -> dict:
        return self._get(f"/tiles-pro/{tile_id}")

    # ── Map Objects ──

    def create_map_object(self, description: str, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/map-objects", payload)

    # ── Object Management ──

    def list_objects(self, limit: int = 20, offset: int = 0) -> dict:
        return self._get("/objects", {"limit": limit, "offset": offset})

    def get_object(self, object_id: str) -> dict:
        return self._get(f"/objects/{object_id}")

    def delete_object(self, object_id: str) -> dict:
        return self._delete(f"/objects/{object_id}")

    def update_object_tags(self, object_id: str, tags: list[str]) -> dict:
        return self._patch(f"/objects/{object_id}/tags", {"tags": tags})

    # ── Objects (directions) ──

    def create_object_4dir(self, description: str, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {
            "description": description,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/create-object-with-4-directions", payload)

    # ── Rotate ──

    def generate_8_rotations(self, width: int = 64, height: int = 64, **kwargs) -> dict:
        payload = {"image_size": {"width": width, "height": height}, **kwargs}
        return self._post("/generate-8-rotations-v2", payload)

    def rotate(self, from_image: dict, width: int, height: int, **kwargs) -> dict:
        payload = {
            "from_image": from_image,
            "image_size": {"width": width, "height": height},
            **kwargs,
        }
        return self._post("/rotate", payload)
