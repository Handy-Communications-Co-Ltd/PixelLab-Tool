# PixelLab Tool

CLI tool for the [PixelLab](https://pixellab.ai) pixel art generation API.

## Setup

```bash
pip install -e .
```

Create a `.env` file with your API key:

```
PIXELLAB_API_KEY=your_api_key_here
```

Get your API key at: https://pixellab.ai/account

## Usage

### Check Balance

```bash
pixellab balance
```

### Generate Pixel Art

```bash
# Pro model (default)
pixellab generate image "brave knight with shining armor" -w 128 -h 128

# Choose model
pixellab generate image "forest cabin" --model pixflux -w 64 -h 64
pixellab generate image "tiny slime" --model bitforge -w 32 -h 32

# Generate UI elements
pixellab generate ui "medieval stone button"

# Generate with style reference
pixellab generate style "wooden barrel" -s style_ref.png
```

### Characters

```bash
# Create character (4 or 8 directions)
pixellab character create "brave knight" -d 4 -w 64 -h 64
pixellab character create "wizard" -d 8 --outline thin --shading soft

# Animate character
pixellab character animate <character_id> walking
pixellab character animate <character_id> attack

# List / Get / Delete / Export
pixellab character list
pixellab character get <character_id>
pixellab character delete <character_id>
pixellab character export <character_id>
```

### Animation

```bash
# Text-based animation
pixellab animate text "knight" "walking" -r reference.png

# Pro text animation
pixellab animate text "knight" "walking" -r reference.png --pro

# Estimate skeleton
pixellab animate estimate-skeleton character.png
```

### Tilesets

```bash
# Top-down tileset
pixellab tileset create "ocean" "sand" --tile-size 16

# Sidescroller tileset
pixellab tileset sidescroller "stone bricks" --transition "moss"

# Isometric tile
pixellab tileset isometric "grass field" --shape block

# Pro tiles (hex, isometric, etc.)
pixellab tileset tiles-pro "1). grass 2). stone 3). lava" --type isometric --n-tiles 3
```

### Map Objects

```bash
pixellab map-object create "wooden barrel" -w 64 -h 64
pixellab map-object create "stone fountain" --view "high top-down"
```

### Edit & Inpaint

```bash
# Edit image
pixellab edit sprite.png "add a red cape"

# Inpaint
pixellab inpaint image.png mask.png "stone wall"
pixellab inpaint image.png mask.png "stone wall" --pro
```

### Rotation

```bash
# 8 rotations from reference
pixellab rotate 8rot -r character.png -w 64 -h 64

# Single rotation
pixellab rotate single character.png --to-direction north
```

### Image Operations

```bash
# Convert to pixel art
pixellab to-pixelart photo.jpg --out-width 64 --out-height 64

# Resize pixel art
pixellab resize sprite.png "knight character" --target-width 128 --target-height 128
```

### Job Management

```bash
# Check job status
pixellab job <job_id>

# Wait for job and download results
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
- Python Client: https://github.com/pixellab-code/pixellab-python

## License

MIT
