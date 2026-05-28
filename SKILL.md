---
name: veo-video
description: Generate videos via the Veo 3.1 video API. Supports text-to-video, image-to-video with first/last frames, and reference-image-to-video. Uses a configured model.
metadata:
  openclaw:
    emoji: "\U0001F3AC"
    requires:
      bins: [python3]
      pip: [requests]
---

# Veo Video

Generate videos using the Veo 3.1 video API.

## Command

```bash
python3 ~/.hermes/skills/veo-video/scripts/generate_video.py \
  --prompt "description" --filename "output.mp4" \
  [--reference_image path1 path2 path3] \
  [--first_frame path] [--last_frame path] \
  [--ratio 16:9|9:16]
```

Always run from user's working directory, do NOT cd to skill directory.

## Request Modes

| Mode | Trigger | Request image field |
|------|---------|---------------------|
| t2v (text-to-video) | No image inputs | None |
| i2v (image-to-video) | `--first_frame`, optional `--last_frame` | `images` |
| r2v (reference-to-video) | `--reference_image` | `Ingredients_images` |

All requests use:

- A configured model value
- `aspect_ratio`: `16:9` or `9:16`

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--prompt` | Yes | - | Video description prompt |
| `--filename` | Yes | - | Output file path (.mp4) |
| `--reference_image` | No | - | Reference image path(s), URL(s), or data URI(s), up to 3 |
| `--first_frame` | No | - | First frame image path, URL, or data URI |
| `--last_frame` | No | - | Last frame image path, URL, or data URI; requires `--first_frame` |
| `--ratio` | No | 16:9 | 16:9 or 9:16 |

## Constraints

- **Model**: Supplied by runtime configuration
- **Aspect ratio**: Only 16:9 (landscape) and 9:16 (portrait)
- **First/last frame**: First frame can be used alone; last frame requires first frame
- **Reference images**: Up to 3 images
- **Local files**: Auto base64-encoded into `data:image/...;base64,...`
- **URLs**: Downloaded first, then encoded into data URIs
- **Data URIs**: Existing `data:image/...;base64,...` inputs are passed through
- **Video retention**: Download generated videos immediately

## Examples

```bash
# Text-to-video (landscape)
python3 ~/.hermes/skills/veo-video/scripts/generate_video.py \
  --prompt "A cat walking on a beach at sunset" \
  --ratio 16:9 --filename output.mp4

# Image-to-video with first frame
python3 ~/.hermes/skills/veo-video/scripts/generate_video.py \
  --prompt "The scene comes alive with gentle motion" \
  --first_frame photo.jpg --filename output.mp4

# First and last frame video
python3 ~/.hermes/skills/veo-video/scripts/generate_video.py \
  --prompt "A smooth transition between these moments" \
  --first_frame start.jpg --last_frame end.png --filename output.mp4

# Reference-image-to-video
python3 ~/.hermes/skills/veo-video/scripts/generate_video.py \
  --prompt "Product showcase video" \
  --reference_image product1.jpg product2.jpg product3.jpg \
  --filename output.mp4
```

## Filename

Pattern: `yyyy-mm-dd-hh-mm-ss-descriptive-name.mp4`

## Output

- Progress and status printed to stderr
- Final saved file path printed to stdout
- Auto-polls every 10s until completion (timeout: 30 minutes)
- Downloads from `video_url`, `url`, or `metadata.result_urls[0]`

## Preflight

- `command -v python3`
- `python3 -c "import requests"`
