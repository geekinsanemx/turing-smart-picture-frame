#!/usr/bin/env python3
# Simple Image Slideshow for Turing Smart Screen
# Based on turing-smart-screen-python library
#
# Changelog:
# 1.0.10 - Image scaling modes: --scale-mode {auto, fill, fit, blur} (default auto). auto crops at most
#          --max-crop percent per side (default 15) and shows the rest whole over a blurred, darkened copy
#          of the image; fill keeps the previous crop-to-fill. Portrait pairs and lone portraits use the
#          same mode. --min-coverage PCT (default 40) skips images that would cover less than PCT of
#          the screen (very wide panoramas). Scale settings are part of the cache key
# 1.0.9 - Overlay text contrast: --text-contrast {auto+outline, auto, outline, box, off}
#         (default auto+outline). auto picks, per background, the color with the best WCAG contrast
#         between the dark-bg and light-bg colors of TIME_STYLE/DATE_STYLE/DAY_STYLE; outline adds a
#         2 px outline (OUTLINE_WIDTH) in the opposite color; box draws a translucent box (BOX_ALPHA)
# 1.0.8 - --font accepts a bundled font name (folder in res/fonts, case-insensitive, e.g. pacifico)
#         or a path to a custom .ttf/.otf; --font-list prints the bundled fonts and exits
# 1.0.7 - Processed images moved from ./.images to a persistent cache in $XDG_CACHE_HOME/tspf
#         (default ~/.cache/tspf): files named by SHA-256 of the source image content + processing
#         parameters, so they are reused across runs and for identical images in different directories;
#         --cache-size MB (default 100) deletes least recently used files when exceeded;
#         background kept in memory as a single PIL image (no longer every displayed path in
#         lcd_comm.image_cache, which grew without limit and could show stale content for reused names)
# 1.0.6 - Renamed --max-images to --preload-images (MAX_IMAGES -> PRELOAD_IMAGES);
#         image discovery matches extensions case-insensitively (.jpg, .JPG, .Jpg, ...) using os.walk,
#         hidden files and directories are skipped as before
# 1.0.5 - Command line options for the hardcoded settings: --interval, --revision, --port, --brightness,
#         --time-size, --date-size, --day-size (defaults = previous values);
#         --max-images N: only N random images of the discovered ones are opened/categorized,
#         a new random sample is taken once every image of the current sample has been shown;
#         a lone portrait image next to landscape images is now shown (as landscape) instead of never
# 1.0.4 - Time/date/day overlay right-aligned to the screen edge and stacked from the bottom using the
#         real glyph extents of the selected font (any --font fits; no clipping, no leftover pixels);
#         overlay sizes/colors in TIME_STYLE, DATE_STYLE, DAY_STYLE
# 1.0.3 - Bundled 10 SIL OFL fonts in res/fonts/ (from google/fonts) for use with --font
# 1.0.2 - Renamed to turing_smart_picture_frame.py (module) + turing-smart-picture-frame.py (launcher);
#         installed command is now 'turing-smart-picture-frame';
#         added --font option (default: bundled DejaVuSans-Bold.ttf);
#         larger overlay text: time 34 (y = height - 35), date 22, day 24
# 1.0.1 - Bundle DejaVuSans-Bold.ttf in res/fonts/dejavu and resolve FONT_PATH with importlib.resources
#         (no longer depends on system fonts or on the current working directory);
#         installable with pyproject.toml, provides the 'picture_frame' command
# 1.0.0 - Initial version (turing-smart-screen-python branch picture-frame-and-demo)

"""
Turing Smart Screen Image Slideshow

Description:
This script displays an automated slideshow of images on a Turing Smart Screen display.
It supports both portrait and landscape images, automatically resizing and formatting them
to fit the display. Portrait images are displayed in pairs side-by-side.

Features:
- Automatic image rotation at configurable intervals
- Support for multiple display hardware revisions (A, B, C, D, SIMU)
- Time and date overlay on displayed images
- Recursive directory searching for images
- Automatic creation of default image if none found

Configuration:
1. Command Line Arguments:
   --debug       : Enable debug output (more verbose logging)
   --images PATH : Specify directory containing images (default: './images')
   --recursive   : Search for images recursively in subdirectories
   --font NAME|PATH: Font for the time/date overlay: bundled font name (folder name in
                   res/fonts, e.g. pacifico) or path to a custom .ttf/.otf (default: dejavu)
   --font-list   : List the bundled fonts usable as --font NAME and exit
   --interval SEC: Seconds between image changes (default: 30)
   --preload-images N: Use only N random images of the discovered ones, re-sampled after
                   all of them have been shown (default: 0 = no limit)
   --revision REV: Display hardware revision: A, B, C, D or SIMU (default: A)
   --port PORT   : Serial port, e.g. /dev/ttyACM0, or AUTO for auto-detection (default: AUTO)
   --brightness N: Display brightness 0-100 (default: 50)
   --time-size N, --date-size N, --day-size N : Overlay font sizes (default: 34, 22, 24)
   --cache-size MB: Max size of the processed images cache (default: 100)
   --text-contrast MODE: auto+outline, auto, outline, box or off (default: auto+outline)
   --scale-mode MODE: auto, fill, fit or blur (default: auto)
   --max-crop PCT: Percent of width/height auto may crop (default: 15)
   --min-coverage PCT: Skip images covering less than PCT of the screen, 0 = never (default: 40)

2. Hardcoded Configuration (modify in code; defaults of the options above):
   - COM_PORT, REVISION, IMAGE_ROTATION_INTERVAL, PRELOAD_IMAGES, BRIGHTNESS, CACHE_SIZE_MB
   - CACHE_DIR: processed images cache ($XDG_CACHE_HOME/tspf, default ~/.cache/tspf)
   - TIME_STYLE, DATE_STYLE, DAY_STYLE: overlay (font size, color on dark bg, color on light bg)
   - TEXT_CONTRAST, OUTLINE_WIDTH, BOX_ALPHA: overlay contrast mode, outline px, box opacity
   - SCALE_MODE, MAX_CROP, MIN_COVERAGE, BLUR_RADIUS, BLUR_BRIGHTNESS: image scaling
   - OVERLAY_MARGIN, OVERLAY_LINE_GAP: overlay spacing in pixels
   - WIDTH, HEIGHT: Display dimensions in portrait mode (default: 320x480)

Usage:
1. Place images in the 'images' directory (or specify custom path with --images)
2. Run script: python3 turing-smart-picture-frame.py [options]
   or, once installed with 'pip install --user .': turing-smart-picture-frame [options]
3. Press Ctrl+C to exit gracefully

Image Requirements:
- Supported formats: PNG, JPG/JPEG, BMP, GIF
- Any orientation (portrait or landscape)
- Will be automatically resized and formatted for display (see --scale-mode)

Notes:
- To run from any folder, install the project with 'pip install --user .' instead of copying
  library/ into site-packages; the 'turing-smart-picture-frame' command is installed into ~/.local/bin
- Text overlay uses the bundled font res/fonts/dejavu/DejaVuSans-Bold.ttf (see LICENSE.txt there)
  unless --font is given (bundled name, see --font-list, or path to a custom font)
- Processed images are cached in $XDG_CACHE_HOME/tspf (default ~/.cache/tspf), named by the hash of
  the source image content; they survive restarts and are shared by identical images in different
  directories. The least recently used files are deleted when the cache exceeds --cache-size MB.
- An image is processed the first time it is shown; later it is read from the cache.
"""

import os
import signal
import sys
import time
import random
import argparse
import calendar
import hashlib
import logging
from datetime import datetime
from importlib.resources import files
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat
from threading import Thread, Event

# Import LCD communication modules
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_comm_rev_c import LcdCommRevC
from library.lcd.lcd_comm_rev_d import LcdCommRevD
from library.lcd.lcd_simulated import LcdSimulated
from library.log import logger

__version__ = "1.0.10"

# Configuration (defaults of the command line options)
COM_PORT = "AUTO"  # Set your COM port or "AUTO" for auto-discovery
REVISION = "A"     # Display revision (A, B, C, D, or SIMU)
REVISIONS = ("A", "B", "C", "D", "SIMU")
WIDTH, HEIGHT = 320, 480  # Display dimensions in portrait mode
IMAGE_ROTATION_INTERVAL = 30  # Seconds between background changes
PRELOAD_IMAGES = 0  # Random sample size of discovered images, 0 = no limit
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
BRIGHTNESS = 50    # Display brightness 0-100
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "tspf")
CACHE_SIZE_MB = 100  # Max size of CACHE_DIR, least recently used images are deleted first
CACHE_FORMAT = 1     # Part of every cache key: bump when image processing changes to invalidate old files

# Verbosity configuration - will be set by command line args
VERBOSE_LEVEL = "INFO"  # Default to INFO level

# Set your font file style to use
FONT_PATH = str(files("res").joinpath("fonts", "dejavu", "DejaVuSans-Bold.ttf"))
DEFAULT_FONT = "dejavu"  # Bundled font name (res/fonts/<name>/) used when --font is not given
FONT_EXTENSIONS = (".ttf", ".otf")

# Time/date overlay, stacked from the bottom-right corner (font size, color on dark bg, color on light bg)
TIME_STYLE = (34, (255, 255, 255), (0, 0, 0))
DATE_STYLE = (22, (0, 255, 255), (0, 70, 90))
DAY_STYLE = (24, (0, 255, 255), (0, 70, 90))
OVERLAY_MARGIN = 6    # Pixels between overlay text and the right/bottom screen edges
OVERLAY_LINE_GAP = 2  # Pixels between overlay lines

# Text contrast against the background:
#   auto+outline: auto color + outline   auto: pick the color with the best WCAG contrast
#   outline: dark-bg color + outline     box: translucent dark box behind the text   off: dark-bg color only
TEXT_CONTRAST = "auto+outline"
TEXT_CONTRAST_MODES = ("auto+outline", "auto", "outline", "box", "off")
OUTLINE_WIDTH = 2   # Outline thickness in pixels (outline modes)
BOX_ALPHA = 120     # Opacity 0-255 of the box behind the text (box mode)

# Image scaling:
#   auto: crop at most MAX_CROP % per side, show the rest whole over a blurred copy (= fill when that is enough)
#   fill: crop to fill the screen   fit: whole image over black   blur: whole image over a blurred copy
SCALE_MODE = "auto"
SCALE_MODES = ("auto", "fill", "fit", "blur")
MAX_CROP = 15         # Percent of width/height auto may crop
MIN_COVERAGE = 40     # Skip images covering less than this percent of their area (not in fill), 0 = never
BLUR_RADIUS = 18      # Gaussian blur radius of the background (blur/auto)
BLUR_BRIGHTNESS = 0.55  # Brightness factor of the blurred background (blur/auto)

def configure_logging(verbose_level):
    """Configure both custom and library logging levels"""
    # Configure the library's logger
    library_logger = logging.getLogger('library')

    if verbose_level == "DEBUG":
        library_logger.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    else:
        library_logger.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    # Also configure the root logger to be safe
    if verbose_level == "DEBUG":
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

def log_info(message):
    """Log info message if verbosity allows"""
    logger.info(message)

def log_debug(message):
    """Log debug message if verbosity allows"""
    if VERBOSE_LEVEL == "DEBUG":
        logger.debug(message)

def log_warning(message):
    """Log warning message (always shown)"""
    logger.warning(message)

def log_error(message):
    """Log error message (always shown)"""
    logger.error(message)

# Global variables
stop_event = Event()
lcd_comm = None
current_background = None
last_background = None
background_frame = None
overlay = None

class ImageCache:
    """Processed images on disk, named by a hash of the source image content and processing parameters.

    Files are kept between runs and reused for identical images found in any directory.
    Least recently used files (by mtime, refreshed on every hit) are deleted when the total
    size exceeds max_bytes."""

    def __init__(self, directory, max_bytes):
        self.directory = directory
        self.max_bytes = max_bytes
        self.content_hashes = {}
        os.makedirs(directory, exist_ok=True)
        for name in os.listdir(directory):
            if name.endswith(".tmp"):
                os.remove(os.path.join(directory, name))
        self.enforce_limit()

    def content_hash(self, image_path):
        """SHA-256 of the file content, computed once per (path, mtime, size)"""
        stat = os.stat(image_path)
        memo_key = (os.path.abspath(image_path), stat.st_mtime_ns, stat.st_size)
        if memo_key not in self.content_hashes:
            digest = hashlib.sha256()
            with open(image_path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    digest.update(chunk)
            self.content_hashes[memo_key] = digest.hexdigest()
        return self.content_hashes[memo_key]

    def path_for(self, *parts):
        """Cache file path for a processing request (kind, display size, source content hashes)"""
        key = hashlib.sha256("|".join(str(part) for part in (CACHE_FORMAT,) + parts).encode()).hexdigest()
        return os.path.join(self.directory, f"{key}.png")

    def get(self, path):
        """True if path is cached; marks it as recently used"""
        try:
            os.utime(path)
        except FileNotFoundError:
            return False
        return True

    def put(self, path, image):
        """Store image atomically at path, then enforce the size limit"""
        tmp_path = f"{path}.tmp"
        image.save(tmp_path, format="PNG")
        os.replace(tmp_path, path)
        self.enforce_limit(keep=path)

    def enforce_limit(self, keep=None):
        """Delete least recently used files until the cache fits in max_bytes"""
        with os.scandir(self.directory) as scan:
            entries = [(entry.stat().st_mtime, entry.stat().st_size, entry.path)
                       for entry in scan if entry.is_file() and entry.name.endswith(".png")]
        total = sum(size for _, size, _ in entries)
        removed = 0
        for _, size, path in sorted(entries):
            if total <= self.max_bytes:
                break
            if path == keep:
                continue
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            total -= size
            removed += 1
        if removed:
            log_debug(f"Cache limit: removed {removed} least recently used images, {total / 1048576:.1f} MB left")

class ImageManager:
    """Handles image loading, resizing, and rotation with orientation detection"""

    def __init__(self, source_images_dir, cache, recursive_search=False, display_width=320, display_height=480,
                 preload_images=0):
        self.source_images_dir = source_images_dir
        self.cache = cache
        self.recursive_search = recursive_search
        self.display_width = display_width
        self.display_height = display_height
        self.preload_images = preload_images

        self.discovered_images = []
        self.image_list = []
        self.portrait_images = []
        self.landscape_images = []
        self.shown_images = set()
        self.current_index = 0
        self.load_images()

    def load_images(self):
        """Scan directory for supported image files and categorize by orientation"""
        if not os.path.exists(self.source_images_dir):
            os.makedirs(self.source_images_dir)
            log_warning(f"Created source images directory: {self.source_images_dir}")
            log_info("Please add some images (PNG, JPG, JPEG, BMP, GIF) to the source images directory")
            return

        log_info(f"Scanning for images in: {os.path.abspath(self.source_images_dir)}")
        log_info(f"Recursive search: {'enabled' if self.recursive_search else 'disabled'}")

        self.discovered_images = list(self.find_images())

        if not self.discovered_images:
            log_warning(f"No images found in {self.source_images_dir} directory")
            # Create a default image if none found
            self.create_default_image()
        else:
            log_info(f"Found {len(self.discovered_images)} images in {self.source_images_dir}")
            if self.recursive_search:
                # Show which subdirectories contain images
                subdirs = set()
                for img_path in self.discovered_images:
                    subdir = os.path.dirname(os.path.relpath(img_path, self.source_images_dir))
                    if subdir and subdir != '.':
                        subdirs.add(subdir)
                if subdirs:
                    log_info(f"Images found in subdirectories: {', '.join(sorted(subdirs))}")

            self.select_sample()

    def find_images(self):
        """Yield supported image files (extension matched case-insensitively), skipping hidden files/dirs"""
        for root, dirs, filenames in os.walk(self.source_images_dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.')) if self.recursive_search else []
            for name in sorted(filenames):
                if not name.startswith('.') and os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                    yield os.path.join(root, name)

    def is_sampled(self):
        """True when --preload-images limits the discovered images to a random sample"""
        return 0 < self.preload_images < len(self.discovered_images)

    def select_sample(self):
        """Pick the images to rotate (a random sample of preload_images, or all) and categorize them"""
        if self.is_sampled():
            self.image_list = random.sample(self.discovered_images, self.preload_images)
            log_info(f"Selected random sample of {self.preload_images} of {len(self.discovered_images)} images")
        else:
            self.image_list = list(self.discovered_images)
        self.shown_images = set()

        # Categorize images by orientation
        self.categorize_images_by_orientation()
        # A lone portrait can never form a pair: show it full screen like get_next_image does
        if len(self.portrait_images) == 1 and self.landscape_images:
            self.landscape_images.append(self.portrait_images.pop())
        # Shuffle both lists for random order
        random.shuffle(self.portrait_images)
        random.shuffle(self.landscape_images)

    def sample_exhausted(self):
        """True when every image of the current random sample has been shown"""
        if not self.is_sampled():
            return False
        return self.shown_images.issuperset(self.portrait_images + self.landscape_images)

    def categorize_images_by_orientation(self):
        """Categorize images into portrait and landscape lists"""
        self.portrait_images = []
        self.landscape_images = []

        skipped = 0
        for image_path in self.image_list:
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    portrait = height > width
                    # Portraits are shown in pairs, each one in half of the screen
                    target_width = self.display_width // 2 if portrait else self.display_width
                    coverage = self.coverage(width, height, target_width, self.display_height)
                    if coverage < MIN_COVERAGE / 100:
                        skipped += 1
                        log_debug(f"Skipped: {os.path.basename(image_path)} ({width}x{height}) would cover "
                                  f"{coverage:.0%} of its area, below --min-coverage {MIN_COVERAGE}%")
                    elif portrait:
                        self.portrait_images.append(image_path)
                        log_debug(f"Portrait: {os.path.basename(image_path)} ({width}x{height})")
                    else:
                        self.landscape_images.append(image_path)
                        log_debug(f"Landscape: {os.path.basename(image_path)} ({width}x{height})")
            except Exception as e:
                log_error(f"Error reading image {image_path}: {e}")
                continue

        log_info(f"Categorized images: {len(self.portrait_images)} portrait, {len(self.landscape_images)} landscape"
                 + (f", {skipped} skipped (below --min-coverage {MIN_COVERAGE}%)" if skipped else ""))

    def create_default_image(self):
        """Create a default gradient background if no images are found"""
        default_path = self.cache.path_for("default", self.display_width, self.display_height, FONT_PATH)
        self.landscape_images = [default_path]  # Treat default as landscape
        if self.cache.get(default_path):
            log_info(f"Using cached default background: {default_path}")
            return

        # Create a gradient background
        img = Image.new('RGB', (self.display_width, self.display_height))
        draw = ImageDraw.Draw(img)

        # Create vertical gradient from blue to purple
        for y in range(self.display_height):
            ratio = y / self.display_height
            r = int(50 + (150 * ratio))
            g = int(100 - (50 * ratio))
            b = int(200 + (55 * ratio))
            draw.line([(0, y), (self.display_width, y)], fill=(r, g, b))

        # Add some text
        try:
            font = ImageFont.truetype(FONT_PATH, 40)
        except:
            font = ImageFont.load_default()

        text = "Image Slideshow"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.display_width - text_width) // 2
        y = (self.display_height - text_height) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        self.cache.put(default_path, img)
        log_info(f"Created default background: {default_path}")

    def resize_portrait_pair(self, image_path1, image_path2):
        """Resize two portrait images to fit side by side on screen"""
        try:
            processed_path = self.cache.path_for("pair", self.display_width, self.display_height,
                                                 SCALE_MODE, MAX_CROP, BLUR_RADIUS, BLUR_BRIGHTNESS,
                                                 self.cache.content_hash(image_path1),
                                                 self.cache.content_hash(image_path2))
            if self.cache.get(processed_path):
                log_info(f"Cached portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")
                return processed_path

            log_debug(f"Processing portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")

            # Load both images
            with Image.open(image_path1) as img1, Image.open(image_path2) as img2:
                # Convert to RGB if necessary
                if img1.mode != 'RGB':
                    img1 = img1.convert('RGB')
                if img2.mode != 'RGB':
                    img2 = img2.convert('RGB')

                # Each image gets half the screen width, scaled according to SCALE_MODE
                half_width = self.display_width // 2
                final_img = Image.new('RGB', (self.display_width, self.display_height), (0, 0, 0))
                final_img.paste(self.compose(img1, half_width, self.display_height), (0, 0))
                final_img.paste(self.compose(img2, self.display_width - half_width, self.display_height),
                                (half_width, 0))

                self.cache.put(processed_path, final_img)

                log_info(f"Created portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")
                log_debug(f"Saved to: {processed_path}")

                return processed_path

        except Exception as e:
            log_error(f"Error processing portrait pair {image_path1}, {image_path2}: {e}")
            return None

    def resize_landscape_single(self, image_path):
        """Scale a single image to the full screen according to SCALE_MODE"""
        try:
            processed_path = self.cache.path_for("landscape", self.display_width, self.display_height,
                                                 SCALE_MODE, MAX_CROP, BLUR_RADIUS, BLUR_BRIGHTNESS,
                                                 self.cache.content_hash(image_path))
            if self.cache.get(processed_path):
                log_info(f"Cached landscape ({SCALE_MODE}): {os.path.basename(image_path)}")
                return processed_path

            log_debug(f"Processing landscape image: {os.path.basename(image_path)}")
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                final_img = self.compose(img, self.display_width, self.display_height)

                self.cache.put(processed_path, final_img)

                log_info(f"Processed landscape ({SCALE_MODE}): {os.path.basename(image_path)}")
                log_debug(f"Saved to: {processed_path}")

                return processed_path

        except Exception as e:
            log_error(f"Error processing landscape image {image_path}: {e}")
            return None

    @staticmethod
    def crop_box(width, height, aspect, max_crop):
        """Centered crop box moving width x height toward aspect, removing at most max_crop (0-1) of a side"""
        if width / height > aspect:
            new_width = max(height * aspect, width * (1 - max_crop))
            left = (width - new_width) / 2
            return left, 0, left + new_width, height
        new_height = max(width / aspect, height * (1 - max_crop))
        top = (height - new_height) / 2
        return 0, top, width, top + new_height

    @staticmethod
    def fitted_size(width, height, target_width, target_height):
        """Largest size with the aspect ratio of width x height that fits in target_width x target_height"""
        scale = min(target_width / width, target_height / height)
        return max(1, round(width * scale)), max(1, round(height * scale))

    @staticmethod
    def mode_max_crop():
        """Fraction of a side SCALE_MODE may crop: fill = all needed, auto = MAX_CROP, fit/blur = none"""
        return {"fill": 1.0, "auto": MAX_CROP / 100}.get(SCALE_MODE, 0.0)

    def coverage(self, width, height, target_width, target_height):
        """Fraction of the target area the image covers in the current SCALE_MODE (1.0 for fill)"""
        left, top, right, bottom = self.crop_box(width, height, target_width / target_height, self.mode_max_crop())
        fitted_width, fitted_height = self.fitted_size(right - left, bottom - top, target_width, target_height)
        return fitted_width * fitted_height / (target_width * target_height)

    def compose(self, img, target_width, target_height):
        """Scale img to target_width x target_height according to SCALE_MODE.

        fill: crop to fill the target; fit: whole image over black; blur: whole image over a blurred,
        darkened copy of itself; auto: crop at most MAX_CROP percent per side, rest as in blur
        (identical to fill when that crop is enough)."""
        aspect = target_width / target_height
        if SCALE_MODE == "fit":
            canvas = Image.new("RGB", (target_width, target_height))
        else:
            canvas = img.crop(self.crop_box(img.width, img.height, aspect, 1.0))
            canvas = canvas.resize((target_width, target_height), Image.Resampling.LANCZOS)
            if SCALE_MODE == "fill":
                return canvas
            canvas = canvas.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
            canvas = ImageEnhance.Brightness(canvas).enhance(BLUR_BRIGHTNESS)
        source = img.crop(self.crop_box(img.width, img.height, aspect, self.mode_max_crop()))
        fitted = source.resize(self.fitted_size(source.width, source.height, target_width, target_height),
                               Image.Resampling.LANCZOS)
        canvas.paste(fitted, ((target_width - fitted.width) // 2, (target_height - fitted.height) // 2))
        return canvas

    def get_next_image(self):
        """Get the next processed image for display with 50/50 probability between portrait pairs and landscape"""
        if self.sample_exhausted():
            log_info("All images of the current sample have been shown, selecting a new sample")
            self.select_sample()

        if not self.portrait_images and not self.landscape_images:
            return None

        # Check what's available
        can_show_portrait_pair = len(self.portrait_images) >= 2
        can_show_landscape = len(self.landscape_images) > 0
        can_show_single_portrait = len(self.portrait_images) > 0

        # If both portrait pairs and landscape are available, randomly choose (50/50)
        if can_show_portrait_pair and can_show_landscape:
            show_portrait_pair = random.choice([True, False])
            log_debug(f"Random choice: {'Portrait pair' if show_portrait_pair else 'Landscape'}")

            if show_portrait_pair:
                return self._get_portrait_pair()
            else:
                return self._get_landscape_single()

        # If only portrait pairs are available
        elif can_show_portrait_pair:
            log_debug("Only portrait pairs available")
            return self._get_portrait_pair()

        # If only landscape images are available
        elif can_show_landscape:
            log_debug("Only landscape images available")
            return self._get_landscape_single()

        # If only single portrait images are left, treat as landscape
        elif can_show_single_portrait:
            log_debug("Only single portrait images left, treating as landscape")
            img = self.portrait_images.pop(0)
            self.portrait_images.append(img)
            self.shown_images.add(img)
            return self.resize_landscape_single(img)

        return None

    def _get_portrait_pair(self):
        """Helper method to get a portrait pair"""
        # Get two random portrait images
        img1 = self.portrait_images.pop(0)
        img2 = self.portrait_images.pop(0)

        # Add them back to the end for rotation
        self.portrait_images.extend([img1, img2])
        self.shown_images.update([img1, img2])

        return self.resize_portrait_pair(img1, img2)

    def _get_landscape_single(self):
        """Helper method to get a landscape image"""
        # Get one landscape image
        img = self.landscape_images.pop(0)

        # Add it back to the end for rotation
        self.landscape_images.append(img)
        self.shown_images.add(img)

        return self.resize_landscape_single(img)

def initialize_display():
    """Initialize the LCD communication"""
    global lcd_comm

    # Build LcdComm object based on hardware revision
    if REVISION == "A":
        log_info("Selected Hardware Revision A (Turing Smart Screen 3.5\" & UsbPCMonitor 3.5\"/5\")")
        lcd_comm = LcdCommRevA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "B":
        log_info("Selected Hardware Revision B (XuanFang screen 3.5\" version B / flagship)")
        lcd_comm = LcdCommRevB(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "C":
        log_info("Selected Hardware Revision C (Turing Smart Screen 5\")")
        lcd_comm = LcdCommRevC(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "D":
        log_info("Selected Hardware Revision D (Kipye Qiye Smart Display 3.5\")")
        lcd_comm = LcdCommRevD(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "SIMU":
        log_info("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=WIDTH, display_height=HEIGHT)
    else:
        log_error("Unknown revision")
        sys.exit(1)

    # Initialize display
    lcd_comm.Reset()
    lcd_comm.InitializeComm()
    lcd_comm.SetBrightness(level=BRIGHTNESS)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))
    lcd_comm.SetOrientation(orientation=Orientation.LANDSCAPE)

def relative_luminance(color):
    """WCAG 2.x relative luminance of an sRGB color (0-255 channels)"""
    channels = [value / 255 for value in color[:3]]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

def contrast_ratio(luminance1, luminance2):
    """WCAG 2.x contrast ratio between two relative luminances (1-21)"""
    lighter, darker = max(luminance1, luminance2), min(luminance1, luminance2)
    return (lighter + 0.05) / (darker + 0.05)

class OverlayLine:
    """Right-aligned overlay text line drawn inside a fixed screen region over the background.

    Depending on TEXT_CONTRAST the text color is chosen per background (best WCAG contrast between
    the dark-bg and light-bg colors against the region's mean color), outlined with the opposite
    color, or drawn over a translucent box."""

    def __init__(self, font, light_color, dark_color, region, baseline, stroke_width):
        self.font = font
        self.light_color = light_color
        self.dark_color = dark_color
        self.region = region
        self.baseline = baseline
        self.stroke_width = stroke_width

    def text_color(self, image):
        if TEXT_CONTRAST not in ("auto", "auto+outline"):
            return self.light_color
        background = relative_luminance(ImageStat.Stat(image).mean)
        light = contrast_ratio(relative_luminance(self.light_color), background)
        dark = contrast_ratio(relative_luminance(self.dark_color), background)
        return self.light_color if light >= dark else self.dark_color

    def draw(self, text, background):
        left, top, right, bottom = self.region
        image = background.crop(self.region)
        color = self.text_color(image)
        if TEXT_CONTRAST == "box":
            shade = Image.new("RGB", image.size, (0, 0, 0))
            image = Image.blend(image, shade, BOX_ALPHA / 255)
        outline = (0, 0, 0) if relative_luminance(color) > 0.4 else (255, 255, 255)
        ImageDraw.Draw(image).text((lcd_comm.get_width() - OVERLAY_MARGIN - left, self.baseline - top),
                                   text, font=self.font, fill=color, anchor="rs",
                                   stroke_width=self.stroke_width, stroke_fill=outline)
        lcd_comm.DisplayPILImage(image, left, top)

def build_overlay():
    """Stack time, date and day lines from the bottom-right corner using the real glyph extents of FONT_PATH.

    Each line region covers every text it can show (all digits, all locale day names), so a redraw
    fully replaces the previous text and never overlaps the other lines."""
    digits = "0123456789"
    lines = [
        (TIME_STYLE, [f"{d}{d}:{d}{d}:{d}{d}" for d in digits]),
        (DATE_STYLE, [f"{d * 4}-{d * 2}-{d * 2}" for d in digits]),
        (DAY_STYLE, list(calendar.day_name)),
    ]
    width, height = lcd_comm.get_width(), lcd_comm.get_height()
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    stroke_width = OUTLINE_WIDTH if TEXT_CONTRAST in ("auto+outline", "outline") else 0
    result = []
    next_bottom = height - OVERLAY_MARGIN
    for (font_size, light_color, dark_color), samples in lines:
        font = lcd_comm.open_font(FONT_PATH, font_size)
        boxes = [measure.textbbox((0, 0), sample, font=font, anchor="rs", stroke_width=stroke_width)
                 for sample in samples]
        ink_left = min(box[0] for box in boxes)
        ink_top = min(box[1] for box in boxes)
        ink_bottom = max(box[3] for box in boxes)
        baseline = next_bottom - ink_bottom
        region = (max(0, width - OVERLAY_MARGIN + ink_left - OVERLAY_MARGIN),
                  max(0, baseline + ink_top),
                  width,
                  min(height, baseline + ink_bottom + 1))
        result.append(OverlayLine(font, light_color, dark_color, region, baseline, stroke_width))
        next_bottom = region[1] - OVERLAY_LINE_GAP
    log_debug(f"Overlay regions (time, date, day): {[line.region for line in result]}")
    return result

def display_slideshow_content(background_image, force_background_refresh=False):
    """Display slideshow content with time and date.

    The background is loaded from the cache file once per change and kept in memory as the only
    frame used by the overlay, so cache eviction never affects the image on screen."""
    global last_background, background_frame

    if not background_image:
        logger.warning(f"Background image not found or invalid: {background_image}")
        return

    try:
        # Only refresh background if it changed or forced
        background_changed = last_background != background_image
        if background_changed or force_background_refresh:
            last_background = background_image
            try:
                with Image.open(background_image) as img:
                    frame = img.convert("RGB")
            except OSError as e:
                logger.warning(f"Background image not found or invalid: {background_image}: {e}")
                if background_frame is None:
                    return
            else:
                logger.info(f"Displaying background: {os.path.basename(background_image)}")
                start_bg = time.perf_counter()
                background_frame = frame
                lcd_comm.DisplayPILImage(background_frame)
                end_bg = time.perf_counter()
                logger.debug(f"Background display took: {end_bg - start_bg:.3f}s")

        time_line, date_line, day_line = overlay
        now = datetime.now()

        # Current time (updates every second) - bottom right corner
        time_line.draw(now.strftime("%H:%M:%S"), background_frame)

        # Only redraw static content when background changes
        if background_changed or force_background_refresh:
            logger.debug("Redrawing static content due to background change")
            date_line.draw(now.strftime("%Y-%m-%d"), background_frame)
            day_line.draw(now.strftime("%A"), background_frame)

        logger.debug("Slideshow content display completed successfully")

    except Exception as e:
        logger.error(f"Error displaying slideshow content: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")

def background_rotation_thread(image_manager):
    """Thread function for rotating background images"""
    global current_background

    log_debug("Background rotation thread started")

    while not stop_event.is_set():
        try:
            log_debug("Getting next background image...")
            new_background = image_manager.get_next_image()
            if new_background:
                current_background = new_background
                log_info(f"Switched to background: {os.path.basename(new_background)}")
                log_debug(f"Full path: {new_background}")
            else:
                log_warning("Failed to get next background image")
        except Exception as e:
            log_error(f"Error in background rotation: {e}")
            log_debug(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")

        # Wait for rotation interval or stop event
        log_debug(f"Waiting {IMAGE_ROTATION_INTERVAL} seconds for next rotation...")
        stop_event.wait(IMAGE_ROTATION_INTERVAL)

    log_debug("Background rotation thread stopped")

def sighandler(signum, frame):
    """Signal handler for graceful shutdown"""
    log_info("Received shutdown signal")
    stop_event.set()

def bundled_fonts():
    """Bundled fonts in res/fonts: {name (folder name, lowercase): (font file path, license file name)}"""
    fonts = {}
    for folder in sorted(files("res").joinpath("fonts").iterdir(), key=lambda entry: entry.name.lower()):
        if not folder.is_dir():
            continue
        entries = sorted(folder.iterdir(), key=lambda entry: entry.name)
        font_files = [entry for entry in entries if entry.name.lower().endswith(FONT_EXTENSIONS)]
        licenses = [entry.name for entry in entries if entry.name.lower().endswith(".txt")]
        if font_files:
            fonts[folder.name.lower()] = (str(font_files[0]), licenses[0] if licenses else "")
    return fonts

def print_font_list():
    """Print the bundled fonts usable as --font NAME"""
    fonts = bundled_fonts()
    name_width = max(len("NAME"), *(len(name) for name in fonts))
    file_width = max(len("FILE"), *(len(os.path.basename(path)) for path, _ in fonts.values()))
    print(f"{'NAME':<{name_width}}  {'FILE':<{file_width}}  LICENSE")
    for name, (path, license_file) in fonts.items():
        default = "  (default)" if name == DEFAULT_FONT else ""
        print(f"{name:<{name_width}}  {os.path.basename(path):<{file_width}}  {license_file}{default}")
    print("\nUsage: --font NAME (bundled) or --font /path/to/font.ttf (custom)")

def font_file(value):
    """argparse type: bundled font name (see --font-list) or path to a TrueType/OpenType font file.

    Values containing a path separator, starting with '~' or ending in .ttf/.otf are paths."""
    if "/" in value or os.sep in value or value.startswith("~") or value.lower().endswith(FONT_EXTENSIONS):
        path = os.path.expanduser(value)
    else:
        fonts = bundled_fonts()
        if value.lower() not in fonts:
            raise argparse.ArgumentTypeError(
                f"unknown bundled font '{value}' (available: {', '.join(fonts)}); "
                "use a path for a custom font, e.g. ~/fonts/MyFont.ttf")
        path = fonts[value.lower()][0]
    try:
        ImageFont.truetype(path, 10)
    except OSError as e:
        raise argparse.ArgumentTypeError(f"cannot load font '{path}': {e}")
    return path

def int_range(minimum, maximum=None):
    """argparse type factory: integer within [minimum, maximum] (no upper bound if maximum is None)"""
    def parse(value):
        try:
            number = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{value}' is not an integer")
        if number < minimum or (maximum is not None and number > maximum):
            bounds = f"{minimum}-{maximum}" if maximum is not None else f">= {minimum}"
            raise argparse.ArgumentTypeError(f"{number} is out of range ({bounds})")
        return number
    return parse

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Turing Smart Screen Image Slideshow")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output (default: INFO level only)")
    parser.add_argument("--images", type=str, default="images",
                       help="Path to images directory (default: 'images' in current location)")
    parser.add_argument("--recursive", action="store_true",
                       help="Search for images recursively in subdirectories")
    parser.add_argument("--font", type=font_file, default=DEFAULT_FONT, metavar="NAME|PATH",
                       help="Font for the time/date overlay: bundled font name (see --font-list) or path "
                            f"to a custom .ttf/.otf file (default: {DEFAULT_FONT})")
    parser.add_argument("--font-list", action="store_true",
                       help="List the bundled fonts usable as --font NAME and exit")
    parser.add_argument("--interval", type=int_range(1), default=IMAGE_ROTATION_INTERVAL, metavar="SEC",
                       help=f"Seconds between image changes (default: {IMAGE_ROTATION_INTERVAL})")
    parser.add_argument("--preload-images", type=int_range(0), default=PRELOAD_IMAGES, metavar="N",
                       help="Use only N random images of the discovered ones, re-sampled after all of them "
                            f"have been shown; 0 = no limit (default: {PRELOAD_IMAGES})")
    parser.add_argument("--revision", type=str.upper, choices=REVISIONS, default=REVISION,
                       help=f"Display hardware revision (default: {REVISION})")
    parser.add_argument("--port", default=COM_PORT,
                       help=f"Serial port, e.g. /dev/ttyACM0, or AUTO for auto-detection (default: {COM_PORT})")
    parser.add_argument("--brightness", type=int_range(0, 100), default=BRIGHTNESS, metavar="0-100",
                       help=f"Display brightness (default: {BRIGHTNESS})")
    parser.add_argument("--time-size", type=int_range(1), default=TIME_STYLE[0], metavar="N",
                       help=f"Time font size (default: {TIME_STYLE[0]})")
    parser.add_argument("--date-size", type=int_range(1), default=DATE_STYLE[0], metavar="N",
                       help=f"Date font size (default: {DATE_STYLE[0]})")
    parser.add_argument("--day-size", type=int_range(1), default=DAY_STYLE[0], metavar="N",
                       help=f"Day of week font size (default: {DAY_STYLE[0]})")
    parser.add_argument("--text-contrast", choices=TEXT_CONTRAST_MODES, default=TEXT_CONTRAST,
                       help="Keep the overlay readable on any background: auto+outline = color chosen per "
                            "background + outline, auto = color only, outline = outline only, box = translucent "
                            f"box behind the text, off = fixed colors (default: {TEXT_CONTRAST})")
    parser.add_argument("--scale-mode", choices=SCALE_MODES, default=SCALE_MODE,
                       help="How images are fitted to the screen: auto = crop at most --max-crop percent and "
                            "show the rest whole over a blurred background, fill = crop to fill, fit = whole "
                            f"image over black, blur = whole image over a blurred background (default: {SCALE_MODE})")
    parser.add_argument("--max-crop", type=int_range(0, 100), default=MAX_CROP, metavar="PCT",
                       help=f"Percent of the width or height auto may crop (default: {MAX_CROP})")
    parser.add_argument("--min-coverage", type=int_range(0, 100), default=MIN_COVERAGE, metavar="PCT",
                       help="Skip images that would cover less than PCT percent of the screen (of half the "
                            f"screen for portrait pairs), e.g. very wide panoramas; 0 = never, not used by fill "
                            f"(default: {MIN_COVERAGE})")
    parser.add_argument("--cache-size", type=int_range(1), default=CACHE_SIZE_MB, metavar="MB",
                       help=f"Max size of the processed images cache in {CACHE_DIR}; least recently used "
                            f"images are deleted first (default: {CACHE_SIZE_MB})")
    return parser.parse_args()

def main():
    """Main slideshow function"""
    global current_background, VERBOSE_LEVEL, FONT_PATH, overlay
    global IMAGE_ROTATION_INTERVAL, REVISION, COM_PORT, BRIGHTNESS, TIME_STYLE, DATE_STYLE, DAY_STYLE
    global TEXT_CONTRAST, SCALE_MODE, MAX_CROP, MIN_COVERAGE

    # Parse command line arguments
    args = parse_arguments()
    if args.font_list:
        print_font_list()
        return
    FONT_PATH = args.font
    IMAGE_ROTATION_INTERVAL = args.interval
    REVISION = args.revision
    COM_PORT = args.port
    BRIGHTNESS = args.brightness
    TIME_STYLE = (args.time_size,) + TIME_STYLE[1:]
    DATE_STYLE = (args.date_size,) + DATE_STYLE[1:]
    DAY_STYLE = (args.day_size,) + DAY_STYLE[1:]
    TEXT_CONTRAST = args.text_contrast
    SCALE_MODE = args.scale_mode
    MAX_CROP = args.max_crop
    MIN_COVERAGE = args.min_coverage

    # Set verbosity level based on arguments
    if args.debug:
        VERBOSE_LEVEL = "DEBUG"
        log_info("Debug mode enabled - showing all messages")
    else:
        VERBOSE_LEVEL = "INFO"
        log_info("Info mode - showing info, warning, and error messages only")

    configure_logging(VERBOSE_LEVEL)

    # Set up signal handlers
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    if os.name == 'posix':
        signal.signal(signal.SIGQUIT, sighandler)

    try:
        # Initialize display
        log_info("Initializing Turing Smart Screen Image Slideshow")
        initialize_display()
        overlay = build_overlay()

        # Create image manager with command line arguments
        cache = ImageCache(CACHE_DIR, args.cache_size * 1024 * 1024)
        log_info(f"Image cache: {CACHE_DIR} (max {args.cache_size} MB)")
        image_manager = ImageManager(source_images_dir=args.images,
                                   cache=cache,
                                   recursive_search=args.recursive,
                                   display_width=lcd_comm.get_width(),
                                   display_height=lcd_comm.get_height(),
                                   preload_images=args.preload_images)

        # Get initial background
        current_background = image_manager.get_next_image()

        # Start background rotation thread
        bg_thread = Thread(target=background_rotation_thread,
                          args=(image_manager,),
                          daemon=True)
        bg_thread.start()

        # Main display loop
        frame_count = 0
        log_info("Starting image slideshow (Press Ctrl+C to exit)")
        log_info(f"Display dimensions: {lcd_comm.get_width()}x{lcd_comm.get_height()}")
        log_info(f"Image rotation interval: {IMAGE_ROTATION_INTERVAL} seconds")
        log_info(f"Source directory: {os.path.abspath(args.images)}")
        log_info(f"Recursive search: {'enabled' if args.recursive else 'disabled'}")
        log_info(f"Total images: {len(image_manager.image_list)} in rotation, "
                 f"{len(image_manager.discovered_images)} discovered")

        while not stop_event.is_set():
            start_time = time.perf_counter()

            try:
                # Check if we need to force refresh (new background)
                force_refresh = (frame_count == 0 or last_background != current_background)

                # Display slideshow content (only refreshes background when changed)
                display_slideshow_content(current_background, force_refresh)

                frame_count += 1

                # Performance monitoring (less frequent)
                end_time = time.perf_counter()
                refresh_time = end_time - start_time

                # Target refresh rate - very relaxed 1 FPS
                target_fps = 1  # 1 FPS - updates once per second
                target_time = 1.0 / target_fps
                sleep_time = max(0.8, target_time - refresh_time)  # Minimum 0.8s sleep
                time.sleep(sleep_time)

            except Exception as e:
                log_error(f"Error in main loop: {e}")
                log_debug(f"Frame {frame_count} failed - Exception details: {type(e).__name__}: {str(e)}")
                import traceback
                log_debug(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)  # Wait before retrying

        log_info("Image slideshow stopped")

    except Exception as e:
        log_error(f"Fatal error: {e}")
        log_debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        log_debug(f"Traceback: {traceback.format_exc()}")

    finally:
        # Clean shutdown
        if lcd_comm:
            try:
                lcd_comm.closeSerial()
                log_info("LCD connection closed")
            except:
                pass

if __name__ == "__main__":
    main()
