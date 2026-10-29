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

## Requirements

| Requirement | Why |
|---|---|
| Python 3.9+ | `requires-python` in `pyproject.toml` |
| [pipx](https://pipx.pypa.io/) or `python3-venv` | Debian 12+, Ubuntu 23.04+ and other distributions mark the system Python as externally managed ([PEP 668](https://peps.python.org/pep-0668/)), so `pip install --user` fails with `externally-managed-environment` |
| Access to the serial port | On Linux the display is `/dev/ttyACM*`, owned by the `dialout` group: `sudo usermod -aG dialout $USER`, then log in again |
| A valid locale | `library/log.py` calls `locale.setlocale(LC_ALL, '')`, which fails if `LANG`/`LC_*` name a locale that is not generated (`locale -a` lists the available ones) |

Python packages (`pyserial`, `Pillow`, `numpy`) are installed automatically. On Linux x86_64/arm64 they come as prebuilt wheels that already include freetype, libjpeg and zlib. On platforms without wheels (e.g. 32-bit ARM), pip builds Pillow and needs `libjpeg-dev`, `zlib1g-dev` and `libfreetype-dev`. Fonts are bundled, no system fonts are needed.

## Installation

Install as a command with [pipx](https://pipx.pypa.io/) (isolated environment, `turing-smart-picture-frame` placed in `~/.local/bin`):

```bash
sudo apt install pipx    # Debian/Ubuntu; other systems: see pipx docs
pipx ensurepath          # adds ~/.local/bin to PATH if needed (open a new terminal afterwards)
pipx install .
turing-smart-picture-frame --font-list
```

Update after `git pull` or after changing the defaults in the code: `pipx install --force .`

Or run from the repository without installing, in a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python turing-smart-picture-frame.py --images ~/Pictures
```

## Usage

```bash
turing-smart-picture-frame [--images PATH] [--recursive] [--preload-images N] [--interval SEC]
                           [--font NAME|PATH] [--font-list] [--time-size N] [--date-size N] [--day-size N]
                           [--revision {A,B,C,D,SIMU}] [--port PORT] [--brightness 0-100]
                           [--text-contrast MODE] [--scale-mode MODE] [--max-crop PCT]
                           [--min-coverage PCT] [--cache-size MB] [--debug]
```

| Option | Description |
|---|---|
| `--images PATH` | Images directory (default: `images` in the current directory) |
| `--recursive` | Search images in subdirectories |
| `--preload-images N` | Use only N random images of the discovered ones; a new random sample is taken once all of them have been shown. Only the sampled images are opened, so startup stays fast with thousands of images (default: `0` = no limit) |
| `--interval SEC` | Seconds between image changes (default: `30`) |
| `--font NAME\|PATH` | Font for the time/date overlay: a bundled font name (see [Fonts](#fonts), case-insensitive) or the path to a custom `.ttf`/`.otf` file (default: `dejavu`) |
| `--font-list` | List the bundled fonts usable as `--font NAME` and exit |
| `--time-size N` / `--date-size N` / `--day-size N` | Overlay font sizes (default: `34` / `22` / `24`) |
| `--revision REV` | Display hardware revision, see table above (default: `A`) |
| `--port PORT` | Serial port, e.g. `/dev/ttyACM0`, or `AUTO` (default: `AUTO`) |
| `--brightness N` | Display brightness 0-100 (default: `50`) |
| `--text-contrast MODE` | Keep the time/date readable on any background: `auto+outline`, `auto`, `outline`, `box` or `off` (default: `auto+outline`, see [Text contrast](#text-contrast)) |
| `--scale-mode MODE` | How images are fitted to the screen: `auto`, `fill`, `fit` or `blur` (default: `auto`, see [Image scaling](#image-scaling)) |
| `--max-crop PCT` | Percent of the width or height `auto` may crop (default: `15`) |
| `--min-coverage PCT` | Skip images that would cover less than PCT percent of the screen, e.g. very wide panoramas; `0` = never, not used by `fill` (default: `40`) |
| `--cache-size MB` | Max size of the processed images cache; least recently used images are deleted first (default: `100`) |
| `--debug` | Debug logging |

Image extensions are matched case-insensitively (`.jpg`, `.JPG`, `.Jpg`, ...). Hidden files and directories are skipped.

Example:

```bash
turing-smart-picture-frame --images ~/Pictures --recursive --preload-images 100 --interval 60 \
    --font dancingscript --brightness 30

# custom font: give its path
turing-smart-picture-frame --images ~/Pictures --font ~/fonts/MyFont.ttf
```

Supported formats: PNG, JPG/JPEG, BMP, GIF. Press Ctrl+C to exit.

Defaults are set at the top of `turing_smart_picture_frame.py`: `COM_PORT`, `REVISION`, `IMAGE_ROTATION_INTERVAL`, `PRELOAD_IMAGES`, `BRIGHTNESS`, `CACHE_DIR`, `CACHE_SIZE_MB`, `TIME_STYLE`/`DATE_STYLE`/`DAY_STYLE` (size, color on dark and on light backgrounds), `TEXT_CONTRAST`, `OUTLINE_WIDTH`, `BOX_ALPHA`, `SCALE_MODE`, `MAX_CROP`, `MIN_COVERAGE`, `BLUR_RADIUS`, `BLUR_BRIGHTNESS`, `OVERLAY_MARGIN`, `OVERLAY_LINE_GAP`, `WIDTH`/`HEIGHT`. When installed, re-run `pipx install --force .` after changing them.

### Image scaling

The screen is 3:2 (480x320); most images are not. `--scale-mode` decides what to do with the difference:

| Mode | Behavior |
|---|---|
| `auto` (default) | Crop at most `--max-crop` percent of the width or height; if the image still does not fill the screen, show it whole over a blurred, darkened copy of itself. Images close to 3:2 (e.g. 16:9 screenshots) look as in `fill` |
| `fill` | Crop to fill the screen (previous behavior; a square image loses 33%, a 16:9 one 16%) |
| `fit` | Whole image, black bars |
| `blur` | Whole image over a blurred, darkened copy of itself (no crop) |

Portrait images are shown in pairs, each one in half of the screen with the same mode. Images that would cover less than `--min-coverage` percent of their area (very wide panoramas, tall strips) are skipped; the log shows how many.

### Image cache

Each image is resized/cropped for the screen the first time it is shown and stored in `$XDG_CACHE_HOME/tspf/` (default `~/.cache/tspf/`). Files are named by the SHA-256 of the source image content plus the processing parameters, so:

- they survive restarts and are reused instead of processing the image again
- identical images in different directories (or with different names) share one cache file
- an edited image gets a new hash and is processed again

When the cache exceeds `--cache-size` MB, the least recently used files are deleted. The cache can also be removed manually at any time.

Files created in the current directory: `log.log`, and with `SIMU` also `screencap.png` and `tmp`.

## Fonts

Bundled in `res/fonts/<name>/`, usable as `--font <name>` (also listed by `--font-list`):

| Name | File | Style |
|---|---|---|
| `dejavu` | `DejaVuSans-Bold.ttf` | Sans serif bold (default) |
| `dancingscript` | `DancingScript.ttf` | Script, similar to Brush Script |
| `pacifico` | `Pacifico-Regular.ttf` | Brush script, bold |
| `greatvibes` | `GreatVibes-Regular.ttf` | Elegant calligraphy |
| `kaushanscript` | `KaushanScript-Regular.ttf` | Brush script, slanted |
| `caveat` | `Caveat.ttf` | Handwriting |
| `lobster` | `Lobster-Regular.ttf` | Retro bold script |
| `bebasneue` | `BebasNeue-Regular.ttf` | Condensed display, uppercase |
| `orbitron` | `Orbitron.ttf` | Futuristic / digital |
| `sharetechmono` | `ShareTechMono-Regular.ttf` | Monospace tech |
| `pressstart2p` | `PressStart2P-Regular.ttf` | 8-bit pixel |

Any other font can be used by giving its path: values containing `/`, starting with `~` or ending in `.ttf`/`.otf` are treated as paths.

`DancingScript.ttf`, `Caveat.ttf` and `Orbitron.ttf` are variable fonts, rendered at their default weight.
The overlay is right-aligned to the screen edge and its lines are stacked using the real glyph size of the selected font, so any font fits. Sizes and colors are set in `TIME_STYLE`, `DATE_STYLE` and `DAY_STYLE`.

### Text contrast

`--text-contrast` keeps the time/date readable on light, dark or busy backgrounds:

| Mode | Behavior |
|---|---|
| `auto+outline` (default) | Color chosen per background + 2 px outline in the opposite color |
| `auto` | For each line, the color with the best [WCAG contrast](https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio) against the mean color of the background behind it: white/cyan on dark backgrounds, black/dark teal on light ones |
| `outline` | White/cyan with a black outline |
| `box` | White/cyan over a translucent dark box (`BOX_ALPHA`) |
| `off` | White/cyan only (original behavior) |

`auto` alone can fail on busy backgrounds (half dark, half light behind the same line); the outline covers that case.

## Licenses

- Code: GPL-3.0 (`LICENSE`), same as turing-smart-screen-python
- Font `res/fonts/dejavu/DejaVuSans-Bold.ttf`: Bitstream Vera license, DejaVu changes in public domain (`res/fonts/dejavu/LICENSE.txt`)
- All other fonts in `res/fonts/`: SIL Open Font License 1.1 (`OFL.txt` in each folder), from [google/fonts](https://github.com/google/fonts) commit `9862abc`
