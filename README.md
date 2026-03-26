# PixelLab Tool

GUI & CLI tool for the [PixelLab](https://pixellab.ai) pixel art generation API.

## Setup

```bash
pip install -e .
```

Create a `.env` file with your API key:

```
PIXELLAB_API_KEY=your_api_key_here
```

Get your API key at: https://pixellab.ai/account

## GUI (Recommended)

```bash
pixellab-gui
```

Features:
- **Dashboard** - Balance check, quick actions
- **Generate** - Text-to-pixel-art (Pro/PixFlux/BitForge), UI elements, style transfer
- **Character** - Create 4/8 direction characters, animate, manage & export
- **Animation** - Text-based animation, frame interpolation
- **Tileset** - Top-down, sidescroller, isometric, pro tiles
- **Edit** - Image editing, inpainting, resize, convert to pixel art
- **Rotate** - 8 rotations, single rotation with direction control
- **Settings** - API key, output directory, appearance theme

## CLI

```bash
# Check balance
pixellab balance

# Generate pixel art
pixellab generate image "brave knight" -w 128 -h 128
pixellab generate image "forest cabin" --model pixflux
pixellab generate ui "medieval stone button"
pixellab generate style "wooden barrel" -s style_ref.png

# Characters
pixellab character create "brave knight" -d 4 -w 64 -h 64
pixellab character animate <character_id> walking
pixellab character list

# Animation
pixellab animate text "knight" "walking" -r reference.png --pro

# Tilesets
pixellab tileset create "ocean" "sand" --tile-size 16
pixellab tileset sidescroller "stone bricks"
pixellab tileset isometric "grass field" --shape block

# Edit & Inpaint
pixellab edit sprite.png "add a red cape"
pixellab inpaint image.png mask.png "stone wall" --pro

# Rotation
pixellab rotate 8rot -r character.png -w 64 -h 64
pixellab rotate single character.png --to-direction north

# Image operations
pixellab to-pixelart photo.jpg --out-width 64 --out-height 64
pixellab resize sprite.png "knight" --target-width 128 --target-height 128

# Job management
pixellab job <job_id> --wait -o output/
```

### Common Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory (default: `output/`) |
| `-w, --width` | Image width in pixels |
| `-h, --height` | Image height in pixels |
| `--seed` | Seed for reproducible generation |
| `--no-bg` | Remove background |
| `--wait/--no-wait` | Wait for async jobs (default: wait) |

## API Documentation

- API Docs: https://api.pixellab.ai/v2/docs
- Python SDK: https://github.com/pixellab-code/pixellab-python

## License

MIT
