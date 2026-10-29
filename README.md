# turing-smart-picture-frame

Image slideshow (picture frame) with time/date overlay for Turing Smart Screen and compatible USB-C displays.

The display communication code in `library/` comes from [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) by Matthieu Houdebine. Only the modules needed by the picture frame are included.

## Features

- Landscape images are cropped to fill the screen; portrait images are shown in pairs side by side
- Random rotation every `IMAGE_ROTATION_INTERVAL` seconds (default 30)
- Time (refreshed every second), date and day of week overlay in the bottom right corner
- Optional recursive search of the images directory
- Gradient default background when no images are found

## Supported hardware

| `REVISION` | Display |
|---|---|
| `A` | Turing Smart Screen 3.5" & UsbPCMonitor 3.5"/5" |
| `B` | XuanFang screen 3.5" version B / flagship |
| `C` | Turing Smart Screen 5" |
| `D` | Kipye Qiye Smart Display 3.5" |
| `SIMU` | Simulated display, served at `http://localhost:5678` |

## Installation

Requires Python 3.9+.

Install as a command (`turing-smart-picture-frame` is placed in `~/.local/bin`, which must be in `PATH`):

```bash
pip install --user .
```

Or run from the repository without installing:

```bash
pip install -r requirements.txt
python3 turing-smart-picture-frame.py
```

## Usage

```bash
turing-smart-picture-frame [--images PATH] [--recursive] [--preload-images N] [--interval SEC]
                           [--font PATH] [--time-size N] [--date-size N] [--day-size N]
                           [--revision {A,B,C,D,SIMU}] [--port PORT] [--brightness 0-100]
                           [--cache-size MB] [--debug]
```

| Option | Description |
|---|---|
| `--images PATH` | Images directory (default: `images` in the current directory) |
| `--recursive` | Search images in subdirectories |
| `--preload-images N` | Use only N random images of the discovered ones; a new random sample is taken once all of them have been shown. Only the sampled images are opened, so startup stays fast with thousands of images (default: `0` = no limit) |
| `--interval SEC` | Seconds between image changes (default: `30`) |
| `--font PATH` | TrueType/OpenType font for the time/date overlay (default: bundled `res/fonts/dejavu/DejaVuSans-Bold.ttf`) |
| `--time-size N` / `--date-size N` / `--day-size N` | Overlay font sizes (default: `34` / `22` / `24`) |
| `--revision REV` | Display hardware revision, see table above (default: `A`) |
| `--port PORT` | Serial port, e.g. `/dev/ttyACM0`, or `AUTO` (default: `AUTO`) |
| `--brightness N` | Display brightness 0-100 (default: `50`) |
| `--cache-size MB` | Max size of the processed images cache; least recently used images are deleted first (default: `100`) |
| `--debug` | Debug logging |

Image extensions are matched case-insensitively (`.jpg`, `.JPG`, `.Jpg`, ...). Hidden files and directories are skipped.

Example:

```bash
turing-smart-picture-frame --images ~/Pictures --recursive --preload-images 100 --interval 60 \
    --font res/fonts/dancingscript/DancingScript.ttf --brightness 30
```

Supported formats: PNG, JPG/JPEG, BMP, GIF. Press Ctrl+C to exit.

Defaults are set at the top of `turing_smart_picture_frame.py`: `COM_PORT`, `REVISION`, `IMAGE_ROTATION_INTERVAL`, `PRELOAD_IMAGES`, `BRIGHTNESS`, `CACHE_DIR`, `CACHE_SIZE_MB`, `TIME_STYLE`/`DATE_STYLE`/`DAY_STYLE` (size and color), `OVERLAY_MARGIN`, `OVERLAY_LINE_GAP`, `WIDTH`/`HEIGHT`. When installed, re-run `pip install --user .` after changing them.

### Image cache

Each image is resized/cropped for the screen the first time it is shown and stored in `$XDG_CACHE_HOME/tspf/` (default `~/.cache/tspf/`). Files are named by the SHA-256 of the source image content plus the processing parameters, so:

- they survive restarts and are reused instead of processing the image again
- identical images in different directories (or with different names) share one cache file
- an edited image gets a new hash and is processed again

When the cache exceeds `--cache-size` MB, the least recently used files are deleted. The cache can also be removed manually at any time.

Files created in the current directory: `log.log`, and with `SIMU` also `screencap.png` and `tmp`.

## Fonts

Bundled in `res/fonts/`, usable with `--font`:

| File | Style |
|---|---|
| `dejavu/DejaVuSans-Bold.ttf` | Sans serif bold (default) |
| `dancingscript/DancingScript.ttf` | Script, similar to Brush Script |
| `pacifico/Pacifico-Regular.ttf` | Brush script, bold |
| `greatvibes/GreatVibes-Regular.ttf` | Elegant calligraphy |
| `kaushanscript/KaushanScript-Regular.ttf` | Brush script, slanted |
| `caveat/Caveat.ttf` | Handwriting |
| `lobster/Lobster-Regular.ttf` | Retro bold script |
| `bebasneue/BebasNeue-Regular.ttf` | Condensed display, uppercase |
| `orbitron/Orbitron.ttf` | Futuristic / digital |
| `sharetechmono/ShareTechMono-Regular.ttf` | Monospace tech |
| `pressstart2p/PressStart2P-Regular.ttf` | 8-bit pixel |

`DancingScript.ttf`, `Caveat.ttf` and `Orbitron.ttf` are variable fonts, rendered at their default weight.
The overlay is right-aligned to the screen edge and its lines are stacked using the real glyph size of the selected font, so any font fits. Sizes and colors are set in `TIME_STYLE`, `DATE_STYLE` and `DAY_STYLE`.

## Licenses

- Code: GPL-3.0 (`LICENSE`), same as turing-smart-screen-python
- Font `res/fonts/dejavu/DejaVuSans-Bold.ttf`: Bitstream Vera license, DejaVu changes in public domain (`res/fonts/dejavu/LICENSE.txt`)
- All other fonts in `res/fonts/`: SIL Open Font License 1.1 (`OFL.txt` in each folder), from [google/fonts](https://github.com/google/fonts) commit `9862abc`
