"""PixelLab CLI - Command line interface for PixelLab API."""

import json
import os
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .client import PixelLabClient, PixelLabError
from .utils import image_to_base64, get_image_size, save_images_from_response

load_dotenv()
console = Console()


def get_client() -> PixelLabClient:
    api_key = os.environ.get("PIXELLAB_API_KEY")
    if not api_key:
        console.print("[red]Error: PIXELLAB_API_KEY not set. Set it in .env or environment.[/red]")
        sys.exit(1)
    return PixelLabClient(api_key)


def handle_job_response(client: PixelLabClient, result: dict, output_dir: str, prefix: str, wait: bool):
    """Handle async job responses - optionally wait and save images."""
    job_id = result.get("background_job_id") or result.get("data", {}).get("background_job_id")
    if job_id:
        console.print(f"[yellow]Job started:[/yellow] {job_id}")
        if wait:
            console.print("[dim]Waiting for completion...[/dim]")
            result = client.wait_for_job(job_id)
            console.print("[green]Job completed![/green]")

    saved = save_images_from_response(result, output_dir, prefix)
    if saved:
        for p in saved:
            console.print(f"[green]Saved:[/green] {p}")
    else:
        # Print raw response if no images extracted
        console.print_json(json.dumps(result, indent=2, default=str))

    return result


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """PixelLab - Pixel art generation CLI tool."""
    pass


# ── Account ──

@cli.command()
def balance():
    """Check account balance and remaining credits."""
    client = get_client()
    result = client.get_balance()
    data = result.get("data", result)
    table = Table(title="Account Balance")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    for key, val in data.items():
        table.add_row(str(key), str(val))
    console.print(table)


# ── Image Generation ──

@cli.group()
def generate():
    """Generate pixel art images."""
    pass


@generate.command("image")
@click.argument("description")
@click.option("-w", "--width", default=128, help="Image width (px)")
@click.option("-h", "--height", default=128, help="Image height (px)")
@click.option("-o", "--output", default="output", help="Output directory")
@click.option("--seed", default=None, type=int, help="Seed for reproducibility")
@click.option("--no-bg", is_flag=True, help="Remove background")
@click.option("--wait/--no-wait", default=True, help="Wait for job completion")
@click.option("--model", type=click.Choice(["pro", "pixflux", "bitforge"]), default="pro", help="Model to use")
def generate_image(description, width, height, output, seed, no_bg, wait, model):
    """Generate a pixel art image from text description."""
    client = get_client()
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    if no_bg:
        kwargs["no_background"] = True

    if model == "pro":
        result = client.generate_image(description, width, height, **kwargs)
    elif model == "pixflux":
        result = client.generate_image_pixflux(description, width, height, **kwargs)
    else:
        result = client.generate_image_bitforge(description, width, height, **kwargs)

    handle_job_response(client, result, output, "image", wait)


@generate.command("ui")
@click.argument("description")
@click.option("-w", "--width", default=256, help="Image width (px)")
@click.option("-h", "--height", default=256, help="Image height (px)")
@click.option("-o", "--output", default="output", help="Output directory")
@click.option("--seed", default=None, type=int)
@click.option("--no-bg", is_flag=True)
@click.option("--wait/--no-wait", default=True)
def generate_ui(description, width, height, output, seed, no_bg, wait):
    """Generate pixel art UI elements."""
    client = get_client()
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    if no_bg:
        kwargs["no_background"] = True
    result = client.generate_ui(description, width, height, **kwargs)
    handle_job_response(client, result, output, "ui", wait)


@generate.command("style")
@click.argument("description")
@click.option("-s", "--style-image", required=True, multiple=True, help="Style reference image path(s)")
@click.option("-w", "--width", default=128)
@click.option("-h", "--height", default=128)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--no-bg", is_flag=True)
@click.option("--wait/--no-wait", default=True)
def generate_with_style(description, style_image, width, height, output, seed, no_bg, wait):
    """Generate pixel art matching a style reference."""
    client = get_client()
    style_images = []
    for path in style_image:
        img = image_to_base64(path)
        size = get_image_size(path)
        style_images.append({"image": img, "size": size})

    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    if no_bg:
        kwargs["no_background"] = True
    result = client.generate_with_style(description, style_images, width, height, **kwargs)
    handle_job_response(client, result, output, "style", wait)


# ── Character ──

@cli.group()
def character():
    """Character creation and management."""
    pass


@character.command("create")
@click.argument("description")
@click.option("-d", "--directions", type=click.Choice(["4", "8"]), default="4", help="Number of directions")
@click.option("-w", "--width", default=64)
@click.option("-h", "--height", default=64)
@click.option("-o", "--output", default="output")
@click.option("--outline", type=click.Choice(["thin", "medium", "thick", "none"]), default=None)
@click.option("--shading", type=click.Choice(["soft", "hard", "flat", "none"]), default=None)
@click.option("--detail", type=click.Choice(["low", "medium", "high"]), default=None)
@click.option("--template", default=None, help="Template ID (mannequin, bear, cat, dog, horse, lion)")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def character_create(description, directions, width, height, output, outline, shading, detail, template, seed, wait):
    """Create a character with directional views."""
    client = get_client()
    kwargs = {}
    if outline:
        kwargs["outline"] = outline
    if shading:
        kwargs["shading"] = shading
    if detail:
        kwargs["detail"] = detail
    if template:
        kwargs["template_id"] = template
    if seed is not None:
        kwargs["seed"] = seed

    if directions == "4":
        result = client.create_character_4dir(description, width, height, **kwargs)
    else:
        result = client.create_character_8dir(description, width, height, **kwargs)

    console.print(f"[cyan]Character ID:[/cyan] {result.get('character_id', 'N/A')}")
    handle_job_response(client, result, output, "character", wait)


@character.command("animate")
@click.argument("character_id")
@click.argument("animation")
@click.option("-o", "--output", default="output")
@click.option("--wait/--no-wait", default=True)
@click.option("--seed", default=None, type=int)
def character_animate(character_id, animation, output, wait, seed):
    """Animate a character with a template animation.

    ANIMATION: Template ID (e.g. walking, running, jumping, breathing-idle, attack, etc.)
    """
    client = get_client()
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.animate_character(character_id, animation, **kwargs)
    handle_job_response(client, result, output, "anim", wait)


@character.command("list")
@click.option("--limit", default=20)
@click.option("--offset", default=0)
def character_list(limit, offset):
    """List your characters."""
    client = get_client()
    result = client.list_characters(limit, offset)
    data = result.get("data", result)
    characters = data if isinstance(data, list) else data.get("characters", [])
    table = Table(title="Characters")
    table.add_column("ID", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="yellow")
    for ch in characters:
        table.add_row(
            str(ch.get("id", "")),
            str(ch.get("description", ""))[:60],
            ", ".join(ch.get("tags", [])),
        )
    console.print(table)


@character.command("get")
@click.argument("character_id")
def character_get(character_id):
    """Get character details."""
    client = get_client()
    result = client.get_character(character_id)
    console.print_json(json.dumps(result, indent=2, default=str))


@character.command("delete")
@click.argument("character_id")
@click.confirmation_option(prompt="Are you sure you want to delete this character?")
def character_delete(character_id):
    """Delete a character."""
    client = get_client()
    client.delete_character(character_id)
    console.print(f"[green]Character {character_id} deleted.[/green]")


@character.command("export")
@click.argument("character_id")
@click.option("-o", "--output", default="output", help="Output directory")
def character_export(character_id, output):
    """Export character as ZIP file."""
    client = get_client()
    data = client.export_character_zip(character_id)
    os.makedirs(output, exist_ok=True)
    path = os.path.join(output, f"character_{character_id}.zip")
    with open(path, "wb") as f:
        f.write(data)
    console.print(f"[green]Exported:[/green] {path}")


# ── Animation ──

@cli.group()
def animate():
    """Animation tools."""
    pass


@animate.command("text")
@click.argument("description")
@click.argument("action")
@click.option("-r", "--reference", required=True, help="Reference image path")
@click.option("-w", "--width", default=64)
@click.option("-h", "--height", default=64)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
@click.option("--pro", is_flag=True, help="Use Pro (v2) model")
def animate_text(description, action, reference, width, height, output, seed, wait, pro):
    """Animate from text description and reference image."""
    client = get_client()
    ref_img = image_to_base64(reference)
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed

    if pro:
        result = client.animate_with_text_v2(ref_img, action, width, height, description=description, **kwargs)
    else:
        result = client.animate_with_text(ref_img, description, action, **kwargs)
    handle_job_response(client, result, output, "anim", wait)


@animate.command("skeleton")
@click.option("-r", "--reference", required=True, help="Reference image path")
@click.option("-w", "--width", default=64)
@click.option("-h", "--height", default=64)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
def animate_skeleton(reference, width, height, output, seed):
    """Animate using skeleton keypoints."""
    client = get_client()
    ref_img = image_to_base64(reference)
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.animate_with_skeleton(ref_img, width, height, **kwargs)
    save_images_from_response(result, output, "skeleton")
    console.print_json(json.dumps(result, indent=2, default=str))


@animate.command("estimate-skeleton")
@click.argument("image_path")
def estimate_skeleton(image_path):
    """Estimate skeleton keypoints from a character image."""
    client = get_client()
    img = image_to_base64(image_path)
    result = client.estimate_skeleton(img)
    console.print_json(json.dumps(result, indent=2, default=str))


# ── Edit ──

@cli.command()
@click.argument("image_path")
@click.argument("description")
@click.option("-w", "--width", default=None, type=int, help="Output width (auto from image if omitted)")
@click.option("-h", "--height", default=None, type=int, help="Output height (auto from image if omitted)")
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--no-bg", is_flag=True)
@click.option("--wait/--no-wait", default=True)
def edit(image_path, description, width, height, output, seed, no_bg, wait):
    """Edit an existing pixel art image with text description."""
    client = get_client()
    img = image_to_base64(image_path)
    size = get_image_size(image_path)
    w = width or size["width"]
    h = height or size["height"]
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    if no_bg:
        kwargs["no_background"] = True
    result = client.edit_image(img, description, w, h, **kwargs)
    handle_job_response(client, result, output, "edit", wait)


# ── Inpaint ──

@cli.command()
@click.argument("image_path")
@click.argument("mask_path")
@click.argument("description")
@click.option("-w", "--width", default=None, type=int)
@click.option("-h", "--height", default=None, type=int)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
@click.option("--pro", is_flag=True, help="Use Pro (v3) model")
def inpaint(image_path, mask_path, description, width, height, output, seed, wait, pro):
    """Inpaint masked region of an image."""
    client = get_client()
    img = image_to_base64(image_path)
    mask = image_to_base64(mask_path)
    size = get_image_size(image_path)
    w = width or size["width"]
    h = height or size["height"]
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed

    if pro:
        inp_img = {"image": img, "size": {"width": w, "height": h}}
        mask_img = {"image": mask, "size": {"width": w, "height": h}}
        result = client.inpaint_v3(description, inp_img, mask_img, **kwargs)
    else:
        result = client.inpaint(description, img, mask, w, h, **kwargs)
    handle_job_response(client, result, output, "inpaint", wait)


# ── Tileset ──

@cli.group()
def tileset():
    """Tileset and map generation."""
    pass


@tileset.command("create")
@click.argument("lower_description")
@click.argument("upper_description")
@click.option("--tile-size", default=16, type=click.Choice(["16", "32"]))
@click.option("--view", type=click.Choice(["low top-down", "high top-down"]), default=None)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def tileset_create(lower_description, upper_description, tile_size, view, output, seed, wait):
    """Create a Wang tileset for top-down games.

    LOWER_DESCRIPTION: Base terrain (e.g. 'ocean', 'grass')
    UPPER_DESCRIPTION: Elevated terrain (e.g. 'sand', 'stone')
    """
    client = get_client()
    kwargs = {"tile_size": {"width": int(tile_size), "height": int(tile_size)}}
    if view:
        kwargs["view"] = view
    if seed is not None:
        kwargs["seed"] = seed
    result = client.create_tileset(lower_description, upper_description, **kwargs)
    handle_job_response(client, result, output, "tileset", wait)


@tileset.command("sidescroller")
@click.argument("lower_description")
@click.option("--transition", default=None, help="Transition description")
@click.option("--tile-size", default=16, type=click.Choice(["16", "32"]))
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def tileset_sidescroller(lower_description, transition, tile_size, output, seed, wait):
    """Create a sidescroller platform tileset."""
    client = get_client()
    kwargs = {"tile_size": {"width": int(tile_size), "height": int(tile_size)}}
    if transition:
        kwargs["transition_description"] = transition
    if seed is not None:
        kwargs["seed"] = seed
    result = client.create_tileset_sidescroller(lower_description, **kwargs)
    handle_job_response(client, result, output, "sidescroller", wait)


@tileset.command("isometric")
@click.argument("description")
@click.option("-w", "--width", default=32)
@click.option("-h", "--height", default=32)
@click.option("--shape", type=click.Choice(["thin tile", "thick tile", "block"]), default="block")
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def tileset_isometric(description, width, height, shape, output, seed, wait):
    """Create an isometric tile."""
    client = get_client()
    kwargs = {"isometric_tile_shape": shape}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.create_isometric_tile(description, width, height, **kwargs)
    handle_job_response(client, result, output, "iso", wait)


@tileset.command("tiles-pro")
@click.argument("description")
@click.option("--type", "tile_type", type=click.Choice(["hex", "hex_pointy", "isometric", "octagon", "square_topdown"]),
              default="isometric")
@click.option("--tile-size", default=32, type=int)
@click.option("--n-tiles", default=None, type=int)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def tileset_tiles_pro(description, tile_type, tile_size, n_tiles, output, seed, wait):
    """Create pro tiles with various shapes."""
    client = get_client()
    kwargs = {"tile_type": tile_type, "tile_size": tile_size}
    if n_tiles:
        kwargs["n_tiles"] = n_tiles
    if seed is not None:
        kwargs["seed"] = seed
    result = client.create_tiles_pro(description, **kwargs)
    handle_job_response(client, result, output, "tiles", wait)


@tileset.command("get")
@click.argument("tileset_id")
@click.option("-o", "--output", default="output")
def tileset_get(tileset_id, output):
    """Get a tileset by ID."""
    client = get_client()
    result = client.get_tileset(tileset_id)
    saved = save_images_from_response(result, output, "tileset")
    if saved:
        for p in saved:
            console.print(f"[green]Saved:[/green] {p}")
    else:
        console.print_json(json.dumps(result, indent=2, default=str))


# ── Map Objects ──

@cli.group(name="map-object")
def map_object():
    """Map object generation."""
    pass


@map_object.command("create")
@click.argument("description")
@click.option("-w", "--width", default=64)
@click.option("-h", "--height", default=64)
@click.option("--view", type=click.Choice(["low top-down", "high top-down", "side"]), default="high top-down")
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def map_object_create(description, width, height, view, output, seed, wait):
    """Create a pixel art map object."""
    client = get_client()
    kwargs = {"view": view}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.create_map_object(description, width, height, **kwargs)
    handle_job_response(client, result, output, "object", wait)


# ── Object Management ──

@cli.group(name="object")
def object_mgmt():
    """Object management."""
    pass


@object_mgmt.command("list")
@click.option("--limit", default=20)
@click.option("--offset", default=0)
def object_list(limit, offset):
    """List your objects."""
    client = get_client()
    result = client.list_objects(limit, offset)
    console.print_json(json.dumps(result, indent=2, default=str))


@object_mgmt.command("create-4dir")
@click.argument("description")
@click.option("-w", "--width", default=64)
@click.option("-h", "--height", default=64)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--wait/--no-wait", default=True)
def object_create_4dir(description, width, height, output, seed, wait):
    """Create an object with 4 directional views."""
    client = get_client()
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.create_object_4dir(description, width, height, **kwargs)
    handle_job_response(client, result, output, "obj4dir", wait)


# ── Rotate ──

@cli.group()
def rotate():
    """Rotation tools."""
    pass


@rotate.command("8rot")
@click.option("-r", "--reference", required=True, help="Reference image path")
@click.option("-w", "--width", default=64)
@click.option("-h", "--height", default=64)
@click.option("--view", type=click.Choice(["low top-down", "high top-down", "side"]), default="low top-down")
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
@click.option("--no-bg", is_flag=True)
@click.option("--wait/--no-wait", default=True)
def rotate_8(reference, width, height, view, output, seed, no_bg, wait):
    """Generate 8 rotational views of a character/object."""
    client = get_client()
    ref_img = image_to_base64(reference)
    ref_size = get_image_size(reference)
    kwargs = {
        "reference_image": {"image": ref_img, "size": ref_size},
        "view": view,
    }
    if seed is not None:
        kwargs["seed"] = seed
    if no_bg:
        kwargs["no_background"] = True
    result = client.generate_8_rotations(width, height, **kwargs)
    handle_job_response(client, result, output, "rot8", wait)


@rotate.command("single")
@click.argument("image_path")
@click.option("--to-direction", default=None, help="Target direction (e.g. north, south-east)")
@click.option("--direction-change", default=None, type=int, help="Degrees to rotate")
@click.option("-w", "--width", default=None, type=int)
@click.option("-h", "--height", default=None, type=int)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
def rotate_single(image_path, to_direction, direction_change, width, height, output, seed):
    """Rotate a single character/object."""
    client = get_client()
    img = image_to_base64(image_path)
    size = get_image_size(image_path)
    w = width or size["width"]
    h = height or size["height"]
    kwargs = {}
    if to_direction:
        kwargs["to_direction"] = to_direction
    if direction_change is not None:
        kwargs["direction_change"] = direction_change
    if seed is not None:
        kwargs["seed"] = seed
    result = client.rotate(img, w, h, **kwargs)
    saved = save_images_from_response(result, output, "rotated")
    for p in saved:
        console.print(f"[green]Saved:[/green] {p}")


# ── Image Operations ──

@cli.command("to-pixelart")
@click.argument("image_path")
@click.option("--out-width", required=True, type=int, help="Output width")
@click.option("--out-height", required=True, type=int, help="Output height")
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
def to_pixelart(image_path, out_width, out_height, output, seed):
    """Convert a regular image to pixel art."""
    client = get_client()
    img = image_to_base64(image_path)
    size = get_image_size(image_path)
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.image_to_pixelart(img, size["width"], size["height"], out_width, out_height, **kwargs)
    saved = save_images_from_response(result, output, "pixelart")
    for p in saved:
        console.print(f"[green]Saved:[/green] {p}")


@cli.command("resize")
@click.argument("image_path")
@click.argument("description")
@click.option("--target-width", required=True, type=int)
@click.option("--target-height", required=True, type=int)
@click.option("-o", "--output", default="output")
@click.option("--seed", default=None, type=int)
def resize_image(image_path, description, target_width, target_height, output, seed):
    """Intelligently resize pixel art."""
    client = get_client()
    img = image_to_base64(image_path)
    size = get_image_size(image_path)
    kwargs = {}
    if seed is not None:
        kwargs["seed"] = seed
    result = client.resize(description, img, size["width"], size["height"], target_width, target_height, **kwargs)
    saved = save_images_from_response(result, output, "resized")
    for p in saved:
        console.print(f"[green]Saved:[/green] {p}")


# ── Job Status ──

@cli.command("job")
@click.argument("job_id")
@click.option("--wait/--no-wait", default=False, help="Wait for completion")
@click.option("-o", "--output", default="output")
def job_status(job_id, wait, output):
    """Check or wait for a background job."""
    client = get_client()
    if wait:
        result = client.wait_for_job(job_id)
        console.print("[green]Job completed![/green]")
        saved = save_images_from_response(result, output, "job")
        for p in saved:
            console.print(f"[green]Saved:[/green] {p}")
    else:
        result = client.get_job(job_id)
    console.print_json(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    cli()
