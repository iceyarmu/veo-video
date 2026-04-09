---
name: veo-video
description: Generate videos via Gemini Veo 3.1 API. Supports text-to-video, image-to-video (first/last frame), reference-image-to-video, and video extension. Model auto-selected based on input mode and aspect ratio.
metadata:
  openclaw:
    emoji: "\U0001F3AC"
    requires:
      bins: [python3]
      env: [GEMINI_API_KEY, GEMINI_BASE_URL]
      pip: [requests]
    primaryEnv: GEMINI_API_KEY
    envHelp:
      GEMINI_API_KEY:
        required: true
        description: Gemini API Key
        howToGet: |
          1. Visit https://aistudio.google.com/apikey
          2. Create an API Key
        url: https://aistudio.google.com/apikey
      GEMINI_BASE_URL:
        required: true
        description: Gemini API Base URL
---

# Veo Video

Generate videos using the Gemini Veo 3.1 API.

## Configuration

```bash
export GEMINI_BASE_URL="https://generativelanguage.googleapis.com"
export GEMINI_API_KEY="your-api-key"
```

## Command

```bash
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "description" --filename "output.mp4" \
  [--reference_image path1 path2] [--reference_video path] \
  [--first_frame path] [--last_frame path] \
  [--resolution 720p|1080p|4k] [--ratio 16:9|9:16] [--duration 8]
```

Always run from user's working directory, do NOT cd to skill directory.

## Model Auto-Selection

Model is automatically chosen based on input mode and aspect ratio:

| Mode | Trigger | 16:9 Model | 9:16 Model |
|------|---------|------------|------------|
| t2v (text-to-video) | No image/video inputs | `veo_3_1_t2v_fast_ultra_relaxed` | `veo_3_1_t2v_fast_portrait_ultra_relaxed` |
| i2v (image-to-video) | `--first_frame` or `--last_frame` | `veo_3_1_i2v_s_fast_ultra_relaxed` | `veo_3_1_i2v_s_fast_portrait_ultra_relaxed` |
| r2v (reference-to-video) | `--reference_image` | `veo_3_1_r2v_fast_ultra_relaxed` | `veo_3_1_r2v_fast_portrait_ultra_relaxed` |

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--prompt` | Yes | - | Video description prompt |
| `--filename` | Yes | - | Output file path (.mp4) |
| `--reference_image` | No | - | Reference image path(s)/URL(s), up to 3 |
| `--reference_video` | No | - | Video to extend (single path/URL) |
| `--first_frame` | No | - | First frame image (triggers i2v mode) |
| `--last_frame` | No | - | Last frame image (interpolation, use with first_frame) |
| `--resolution` | No | 720p | 720p, 1080p, or 4k |
| `--ratio` | No | 16:9 | 16:9 or 9:16 |
| `--duration` | No | 8 | Duration in seconds (4, 5, 6, or 8) |

## Constraints

- **Aspect ratio**: Only 16:9 (landscape) and 9:16 (portrait)
- **Duration**: 4, 5, 6, or 8 seconds. 8s required for 1080p/4k.
- **Reference images**: Up to 3 images
- **Audio**: Veo 3.x generates audio natively (no separate audio parameter)
- **Local files**: Auto base64-encoded. URLs downloaded then encoded.
- **Video retention**: 2 days on server; download immediately.

## Examples

```bash
# Text-to-video (landscape)
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "A cat walking on a beach at sunset" \
  --duration 8 --ratio 16:9 --filename output.mp4

# Image-to-video with first frame
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "The scene comes alive with gentle motion" \
  --first_frame photo.jpg --duration 8 --filename output.mp4

# Reference-image-to-video
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "Product showcase video" \
  --reference_image product1.jpg product2.jpg \
  --duration 8 --filename output.mp4
```

## Filename

Pattern: `yyyy-mm-dd-hh-mm-ss-descriptive-name.mp4`

## Output

- Progress and status printed to stderr
- Final saved file path printed to stdout
- Auto-polls every 10s until completion (timeout: 30 minutes)

## Preflight

- `command -v python3`
- `python3 -c "import requests"`
- Verify env vars: `[ -n "$GEMINI_API_KEY" ] && [ -n "$GEMINI_BASE_URL" ]`
