#!/usr/bin/env python3
# Simple Image Slideshow for Turing Smart Screen
# Based on turing-smart-screen-python library
#
# Changelog:
# 1.0.14 - --images can be repeated to show the images of several directories (--images A --images B);
#          each one must exist and be readable. A directory given twice (same device/inode, e.g. through a
#          symlink or a bind mount) is used once; with --recursive, a directory inside another --images
#          directory is ignored (logged), since the recursive search already reads it; the same file
#          under different paths (symlink, hardlink) counts once per path. --preload-images samples from
#          all directories together. An empty --images path is rejected instead of meaning the current
#          directory. During --auto-refresh each directory is checked against the device/inode recorded at
#          startup: one that cannot be read or changed (e.g. an unmounted share) keeps its known images
#          while the others are rescanned, as with a single directory before. An image that cannot be
#          opened when its turn comes is skipped and the next ones are tried, through the whole rotation if
#          needed (the limit of 5 attempts is removed; the search stops at shutdown); when the rotation
#          queues run empty they are rebuilt from the discovered images, so images skipped while a share
#          was unavailable come back also without --auto-refresh. With --recursive, nested --images
#          directories are detected by real path (symlinks resolved)
#          Default --interval (IMAGE_ROTATION_INTERVAL) changed from 30 to 60 seconds
# 1.0.13 - Image changes aligned to the clock: the first image is shown at startup, every following change
#          happens at a multiple of --interval counted from local midnight (30 -> :00 and :30, 1h -> X:00:00).
#          --interval accepts seconds or a number with unit s/m/h/d (30, 5m, 1h, 1d) and only values that
#          keep changes on round clock times: multiples of 5 s that divide an hour (5s ... 30m, 1h) or whole
#          hours that divide a day (2h, 3h, 4h, 6h, 8h, 12h, 1d); multiples follow the local wall clock
#          across daylight saving changes and are rescheduled after wall clock adjustments. The next image
#          is prepared and loaded in memory before its change time (the main loop no longer reads the
#          cache, so eviction cannot skip a change), and the main loop draws on whole seconds, so the
#          change starts on time.
#          --auto-refresh [DURATION] (seconds or s/m/h/d units like --interval, any value from 1 s; 1h
#          when given without a value) rescans the source directory in
#          its own thread: new images join the end of the rotation queue, deleted ones leave it, without
#          interrupting the clock or the rotation. Orientation of each image is remembered per
#          (path, mtime, size), so a rescan only opens new or modified files; an image whose orientation
#          changes at the same path moves to the other queue, and portraits pair again as soon as two
#          are available. A rescan where the images directory cannot be read is discarded and the current
#          images are kept; unreadable subdirectories are skipped and their known images kept. Images that cannot be read are retried on
#          every rescan. The fallback background is retained in memory rather than queued as an
#          evictable cache-file source. The rotation state has a single owner, the rotation thread: the
#          refresh thread only scans and classifies the images that can rotate (all of them, or the
#          current --preload-images sample, read from the immutable image_list tuple) and hands over only
#          the latest scan (a single slot swapped under a small lock); rescans, samples and selection are
#          applied by the rotation thread, so the queues need no lock. Classifications are shared through
#          the thread-safe OrientationCache. A failure while applying a rescan keeps the current images.
#          When none of a new sample's images can be shown, the current queues are kept and shown again.
#          An image that fails to process is classified again from the file and dropped if unreadable,
#          and the next image is tried, so the change is not skipped. Cache writes are best effort.
#          The date and day are redrawn when the date changes, also on the same background. A wake-up that
#          is late by the same amount on the wall and elapsed clocks (load, suspend) changes the image at
#          once instead of being taken for a wall clock jump. --auto-refresh accepts up to 365d
#          --images must be an existing, readable directory: otherwise the program exits with an argument
#          error instead of creating it (not checked with --font-list, which needs no images)
# 1.0.12 - The effective configuration is logged at startup, before the display is initialized: every
#          command line option with its value, including defaults, plus the cache directory and log file.
#          The scattered startup lines for the cache, log file, rotation interval, source directory and
#          recursive search were removed (now in that block)
# 1.0.11 - log.log moved from the current working directory to $XDG_CACHE_HOME/tspf (default
#          ~/.cache/tspf), SIMU screencap.png/tmp to its simu/ subdirectory: running from the images
#          directory no longer writes files there. CACHE_DIR now comes from library.log.APP_DIR
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
- Automatic image rotation at configurable intervals, aligned to the clock (multiples of the interval
  counted from local midnight)
- One or more source directories (--images, repeatable)
- Optional periodic rescan of the source directories (--auto-refresh)
- Support for multiple display hardware revisions (A, B, C, D, SIMU)
- Time and date overlay on displayed images
- Recursive directory searching for images
- Automatic creation of default image if none found

Configuration:
1. Command Line Arguments:
   --debug       : Enable debug output (more verbose logging)
   --images PATH : Existing, readable directory containing images; the program exits with an error
                   otherwise. Repeat it for several directories: --images A --images B (default: './images')
   --recursive   : Search for images recursively in subdirectories
   --font NAME|PATH: Font for the time/date overlay: bundled font name (folder name in
                   res/fonts, e.g. pacifico) or path to a custom .ttf/.otf (default: dejavu)
   --font-list   : List the bundled fonts usable as --font NAME and exit
   --interval DURATION: Time between image changes, aligned to its multiples from local midnight: seconds
                   or a number with unit s/m/h/d (e.g. 30, 5m, 1h, 1d); multiples of 5 s dividing an hour
                   or whole hours dividing a day (default: 60)
   --auto-refresh [DURATION]: Rescan the images directories every DURATION, seconds or a number with
                   unit s/m/h/d (e.g. 600, 30m, 2h), from 1s to 365d; default without a value: 1h; omitted = no rescan
   --preload-images N: Use only N random images of the discovered ones (all directories together),
                   re-sampled after all of them have been shown (default: 0 = no limit)
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
   - AUTO_REFRESH (None = disabled), AUTO_REFRESH_DEFAULT (--auto-refresh without a value)
   - CACHE_DIR: processed images cache ($XDG_CACHE_HOME/tspf, default ~/.cache/tspf)
   - TIME_STYLE, DATE_STYLE, DAY_STYLE: overlay (font size, color on dark bg, color on light bg)
   - TEXT_CONTRAST, OUTLINE_WIDTH, BOX_ALPHA: overlay contrast mode, outline px, box opacity
   - SCALE_MODE, MAX_CROP, MIN_COVERAGE, BLUR_RADIUS, BLUR_BRIGHTNESS: image scaling
   - OVERLAY_MARGIN, OVERLAY_LINE_GAP: overlay spacing in pixels
   - WIDTH, HEIGHT: Display dimensions in portrait mode (default: 320x480)

Usage:
1. Place images in the 'images' directory (or specify one or more custom paths with --images)
2. Run script: python3 turing-smart-picture-frame.py [options]
   or, once installed with 'pipx install .': turing-smart-picture-frame [options]
3. Press Ctrl+C to exit gracefully

Image Requirements:
- Supported formats: PNG, JPG/JPEG, BMP, GIF
- Any orientation (portrait or landscape)
- Will be automatically resized and formatted for display (see --scale-mode)

Notes:
- To run from any folder, install the project with 'pipx install .' instead of copying
  library/ into site-packages; the 'turing-smart-picture-frame' command is installed into ~/.local/bin.
  'pip install --user .' fails on distributions with an externally managed Python (PEP 668, e.g. Debian 12)
- Requirements: Python 3.9+, read/write access to the serial port (Linux: 'dialout' group) and a valid
  locale (library/log.py calls locale.setlocale(LC_ALL, ''))
- Text overlay uses the bundled font res/fonts/dejavu/DejaVuSans-Bold.ttf (see LICENSE.txt there)
  unless --font is given (bundled name, see --font-list, or path to a custom font)
- Processed images are cached in $XDG_CACHE_HOME/tspf (default ~/.cache/tspf), named by the hash of
  the source image content; they survive restarts and are shared by identical images in different
  directories. The least recently used files are deleted when the cache exceeds --cache-size MB.
- An image is processed the first time it is shown; later it is read from the cache.
- The log is written to $XDG_CACHE_HOME/tspf/log.log (max 1 MB); with --revision SIMU the simulated
  screen is written to $XDG_CACHE_HOME/tspf/simu/screencap.png. Nothing is written to the current directory.
- At startup the effective configuration is logged: every option with its value, defaults included,
  plus the cache directory and log file.
- The first image is shown at startup; the next ones change at the next multiple of --interval
  from local midnight. Every allowed interval divides a day, so each day starts aligned at 00:00:00.
  Multiples follow the local wall clock, also across daylight saving changes and clock adjustments.
- --auto-refresh adds new images to the end of the rotation queue and removes deleted ones; with
  --preload-images new images enter the next random sample. If an images directory or subdirectory
  cannot be read during a rescan, or the directory's device/inode changed since startup (e.g. an
  unmounted share), its known images are kept while the other directories are rescanned. An image
  that cannot be opened when its turn comes is skipped and the next one is tried.
"""

import os
import math
import signal
import sys
import time
import random
import argparse
import calendar
import hashlib
import re
from collections import namedtuple
from functools import partial
from itertools import chain
import logging
from datetime import datetime
from importlib.resources import files
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat
from threading import Thread, Event, Lock

# Import LCD communication modules
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_comm_rev_c import LcdCommRevC
from library.lcd.lcd_comm_rev_d import LcdCommRevD
from library.lcd.lcd_simulated import LcdSimulated
from library.log import APP_DIR, LOG_FILE, logger

__version__ = "1.0.14"

# Configuration (defaults of the command line options)
COM_PORT = "AUTO"  # Set your COM port or "AUTO" for auto-discovery
REVISION = "A"     # Display revision (A, B, C, D, or SIMU)
REVISIONS = ("A", "B", "C", "D", "SIMU")
WIDTH, HEIGHT = 320, 480  # Display dimensions in portrait mode
IMAGE_ROTATION_INTERVAL = 60
SECONDS_PER_HOUR, SECONDS_PER_DAY = 3600, 86400
DURATION_UNITS = {"s": 1, "m": 60, "h": SECONDS_PER_HOUR, "d": SECONDS_PER_DAY}
MIN_INTERVAL = 5
ALLOWED_INTERVALS = (tuple(s for s in range(MIN_INTERVAL, SECONDS_PER_HOUR + 1, 5) if SECONDS_PER_HOUR % s == 0)
                     + tuple(h * SECONDS_PER_HOUR for h in range(2, 25) if 24 % h == 0))
CLOCK_TOLERANCE = 1.0
AUTO_REFRESH = None
AUTO_REFRESH_DEFAULT = 3600
MAX_AUTO_REFRESH = 365 * SECONDS_PER_DAY
PRELOAD_IMAGES = 0  # Random sample size of discovered images, 0 = no limit
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
BRIGHTNESS = 50    # Display brightness 0-100
CACHE_DIR = APP_DIR
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

Background = namedtuple("Background", "path frame")

# Global variables
stop_event = Event()
wake_event = Event()
lcd_comm = None
current_background = None
last_background = None
background_frame = None
last_date = None
overlay = None
transition_lock = Lock()
pending_transition = None

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
        """SHA-256 memoized once per path and current file metadata."""
        stat = os.stat(image_path)
        path = os.path.abspath(image_path)
        version = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        remembered = self.content_hashes.get(path)
        if remembered is None or remembered[0] != version:
            digest = hashlib.sha256()
            with open(image_path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    digest.update(chunk)
            remembered = (version, digest.hexdigest())
            self.content_hashes[path] = remembered
        return remembered[1]

    def prune_hashes(self, discovered):
        present = {os.path.abspath(path) for path in discovered}
        for path in self.content_hashes.keys() - present:
            del self.content_hashes[path]

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

def owner(path, directories):
    """The most specific of directories that contains path, or None"""
    return max((directory for directory in directories if path.startswith(os.path.join(directory, ""))),
               key=len, default=None)

def retained(path, unreadable, scanned):
    """True if a known image a rescan did not find is kept: the most specific directory containing it,
    among the unreadable directories (source directories that could not be read or whose device/inode
    changed, and unreadable subdirectories) and the scanned source directories, is unreadable"""
    return owner(path, chain(unreadable, scanned)) in unreadable

class OrientationCache:
    """Thread-safe memo of image classifications, shared by the rotation and refresh threads; the
    single source of truth for them.

    One classification is remembered per path together with the (mtime, size) it was read for; a cache
    hit only needs os.stat. An entry is never replaced by one for an older mtime, so a slower thread
    cannot overwrite a newer classification. A failed read drops the entry and is not remembered, so
    an image that becomes readable again (e.g. restored permissions) is classified on the next call.
    A read error is logged as an error once per image, repeats as debug. The lock only guards the
    dictionaries and is never held while a file is read."""

    def __init__(self, kind_for_size):
        self.kind_for_size = kind_for_size
        self.lock = Lock()
        self.kinds = {}
        self.errors = set()
        self.invalid = {}

    def classify(self, image_path):
        """portrait, landscape, skipped (below --min-coverage) or error"""
        try:
            stat = os.stat(image_path)
            version = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
            with self.lock:
                if self.invalid.get(image_path) == version:
                    return "error"
                self.invalid.pop(image_path, None)
                remembered = self.kinds.get(image_path)
                if remembered and remembered[0] == version:
                    self.errors.discard(image_path)
                    return remembered[1]
            kind = self.read(image_path)
        except Exception as e:
            with self.lock:
                self.kinds.pop(image_path, None)
                first = image_path not in self.errors
                self.errors.add(image_path)
            (log_error if first else log_debug)(f"Error reading image {image_path}: {e}")
            return "error"
        with self.lock:
            remembered = self.kinds.get(image_path)
            if remembered is None or remembered[0][0] <= version[0]:
                self.kinds[image_path] = (version, kind)
            self.errors.discard(image_path)
        return kind

    def reject(self, image_path):
        try:
            stat = os.stat(image_path)
            version = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        except OSError:
            return
        with self.lock:
            self.kinds.pop(image_path, None)
            self.invalid[image_path] = version

    def forget(self, image_path):
        """Drop the classification of image_path, so the next classify() reads the file again"""
        with self.lock:
            self.kinds.pop(image_path, None)

    def read(self, image_path):
        """Open image_path and classify its size with kind_for_size; raises if it cannot be read"""
        with Image.open(image_path) as img:
            width, height = img.size
        kind, coverage = self.kind_for_size(width, height)
        if kind == "skipped":
            log_debug(f"Skipped: {os.path.basename(image_path)} ({width}x{height}) would cover "
                      f"{coverage:.0%} of its area, below --min-coverage {MIN_COVERAGE}%")
        else:
            log_debug(f"{kind.capitalize()}: {os.path.basename(image_path)} ({width}x{height})")
        return kind

    def prune(self, present, unreadable=(), scanned=()):
        """Forget classifications and errors of images that are no longer discovered; entries of images
        retained under unreadable directories (see retained()) are kept"""
        unreadable = set(unreadable)

        def kept(path):
            return retained(path, unreadable, scanned)

        with self.lock:
            for path in self.kinds.keys() - present:
                if not kept(path):
                    del self.kinds[path]
            self.errors = {path for path in self.errors if path in present or kept(path)}
            for path in self.invalid.keys() - present:
                if not kept(path):
                    del self.invalid[path]

class ImageManager:
    """Handles image loading, resizing, and rotation with orientation detection.

    The rotation state (discovered images, sample, queues, default background) has a single owner: the
    main thread until the rotation thread starts, then only the rotation thread. The refresh thread
    only calls scan(), which reads configuration, the image_list tuple (replaced, never modified, by
    the rotation thread) and the thread-safe OrientationCache, and hands the result over with
    offer_scan(); get_next_image() applies it. No lock guards the queues because no other thread
    touches them."""

    def __init__(self, source_identities, cache, recursive_search=False, display_width=320, display_height=480,
                 preload_images=0):
        self.recursive_search = recursive_search
        self.source_identities = self.without_nested(source_identities, recursive_search)
        self.source_dirs = list(self.source_identities)
        self.cache = cache
        self.display_width = display_width
        self.display_height = display_height
        self.preload_images = preload_images

        self.discovered_images = []
        self.image_list = ()
        self.portrait_images = []
        self.landscape_images = []
        self.shown_images = set()
        self.current_index = 0
        self.default_background = None
        self.orientations = OrientationCache(partial(ImageManager.kind_for_size,
                                                     display_width=display_width, display_height=display_height))
        self.pending_lock = Lock()
        self.pending_scan = None
        self.load_images()

    @staticmethod
    def without_nested(source_identities, recursive_search):
        """source_identities without the directories that the recursive search of another one already
        reads: compared by real path (symlinks resolved), since the search does not follow symlinked
        subdirectories, and not under a hidden directory, which the search skips"""
        if not recursive_search:
            return dict(source_identities)
        real = {source_dir: os.path.realpath(source_dir) for source_dir in source_identities}

        def reads(other, source_dir):
            return (real[source_dir].startswith(os.path.join(real[other], ""))
                    and not any(part.startswith('.')
                                for part in os.path.relpath(real[source_dir], real[other]).split(os.sep)))

        kept = {}
        for source_dir, identity in source_identities.items():
            parent = next((other for other in source_identities if other != source_dir
                           and reads(other, source_dir)), None)
            if parent:
                log_info(f"Ignoring --images {source_dir}: already read by the recursive search of {parent}")
            else:
                kept[source_dir] = identity
        return kept

    def load_images(self):
        """Scan the source directories for supported image files and categorize them by orientation.
        The same file under different paths (symlink, hardlink) is discovered under each path."""
        log_info(f"Recursive search: {'enabled' if self.recursive_search else 'disabled'}")

        discovered = {}
        for source_dir in self.source_dirs:
            log_info(f"Scanning for images in: {source_dir}")
            images = list(self.find_images(source_dir))
            log_info(f"Found {len(images)} images in {source_dir}")
            if self.recursive_search:
                subdirs = {os.path.dirname(os.path.relpath(img_path, source_dir)) for img_path in images}
                subdirs.discard('')
                if subdirs:
                    log_info(f"Images found in subdirectories of {source_dir}: {', '.join(sorted(subdirs))}")
            discovered.update(dict.fromkeys(images))
        self.discovered_images = list(discovered)

        if not self.discovered_images:
            log_warning(f"No images found in {', '.join(self.source_dirs)}")
            self.create_default_image()
        else:
            if len(self.source_dirs) > 1:
                log_info(f"Found {len(self.discovered_images)} images in {len(self.source_dirs)} directories")
            self.select_sample()

    def find_images(self, source_dir, onerror=None):
        """Yield supported image files of source_dir (extension matched case-insensitively), skipping
        hidden files/dirs.

        onerror is passed to os.walk: by default unreadable directories are skipped silently."""
        for root, dirs, filenames in os.walk(source_dir, onerror=onerror):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.')) if self.recursive_search else []
            for name in sorted(filenames):
                if not name.startswith('.') and os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                    yield os.path.join(root, name)

    def scan(self):
        """Scan the source directories for the refresh thread; modifies no rotation state.

        Returns (discovered images, unreadable directories, scanned source directories). Each source
        directory is checked against the device/inode recorded at startup before its walk; a source
        directory that cannot be read or whose device/inode changed (e.g. an unmounted share) is
        unreadable, like an unreadable subdirectory (e.g. lost+found at a mount point): apply_scan() keeps
        its known images (see retained()), so a partial scan is not mistaken for deleted images. An image
        that cannot be opened when its turn comes is skipped (see get_next_image()).
        The images that can rotate (rotation_pool: all
        discovered, or the current sample from the image_list tuple) are classified here, so the files
        are opened on the refresh thread; apply_scan() then finds them in the OrientationCache with a
        single os.stat. The cache is pruned to this scan."""
        unreadable = []
        scanned = []
        found = {}
        for source_dir, identity in self.source_identities.items():
            top = os.path.normpath(source_dir)
            subdirs = []

            def skip_unreadable(error, top=top, subdirs=subdirs):
                if os.path.normpath(error.filename) == top:
                    raise error
                subdirs.append(error.filename)
                log_debug(f"Auto refresh: skipping unreadable directory {error.filename}: {error}")

            try:
                source_stat = os.stat(source_dir)
                if (source_stat.st_dev, source_stat.st_ino) != identity:
                    log_warning(f"Auto refresh: device/inode of {source_dir} changed; keeping its current images")
                    unreadable.append(source_dir)
                    continue
                images = list(self.find_images(source_dir, onerror=skip_unreadable))
            except OSError as e:
                log_warning(f"Auto refresh: cannot read {source_dir} ({e}), keeping its current images")
                unreadable.append(source_dir)
                continue
            scanned.append(source_dir)
            unreadable.extend(subdirs)
            found.update(dict.fromkeys(images))
        discovered = list(found)
        self.orientations.prune(set(discovered), unreadable, scanned)
        for image_path in self.rotation_pool(discovered):
            self.orientations.classify(image_path)
        return discovered, unreadable, scanned

    def offer_scan(self, result):
        """Hand a scan() result to the rotation thread. A newer result replaces an unapplied older one,
        so at most one is ever pending; pending_lock is held only for the swap, never during I/O."""
        with self.pending_lock:
            self.pending_scan = result

    def apply_pending_scans(self):
        """Apply the scan result handed over by the refresh thread, if any. If applying it fails (e.g. the
        default background cannot be written to the cache), the current state is kept and the next
        rescan offers the change again; the rotation continues with the current images."""
        with self.pending_lock:
            result, self.pending_scan = self.pending_scan, None
        if result is None:
            return
        try:
            self.apply_scan(*result)
        except Exception as e:
            log_error(f"Auto refresh: cannot apply the rescan ({e}), keeping the current images")

    def apply_scan(self, discovered, unreadable, scanned):
        """Apply a scan() result: deleted images leave the queues, new ones join the end of their queue in
        random order (with --preload-images they can enter the next sample); the default background is
        used while no images exist. The new state is computed first and assigned at the end, so a failure
        leaves the previous state intact and the next rescan retries it. Known images under unreadable
        directories (see retained()) stay discovered."""
        unreadable = set(unreadable)
        found = set(discovered)
        discovered = discovered + [image_path for image_path in self.discovered_images if image_path not in found
                                   and retained(image_path, unreadable, scanned)]
        previous = set(self.discovered_images)
        current = set(discovered)
        self.cache.prune_hashes(discovered)
        added, removed = len(current - previous), len(previous - current)

        if not discovered:
            default_background = self.default_background or self.prepare_default_background()
            self.discovered_images = discovered
            self.image_list = ()
            self.portrait_images = []
            self.landscape_images = []
            self.default_background = default_background
            if previous:
                log_warning(f"Auto refresh: no images left in {', '.join(self.source_dirs)}")
            else:
                log_debug("Auto refresh: still no images")
            return

        pool = self.rotation_pool(discovered)
        kinds = {image_path: self.orientations.classify(image_path) for image_path in pool}
        portraits = {image_path for image_path, kind in kinds.items() if kind == "portrait"}
        landscapes = {image_path for image_path, kind in kinds.items() if kind == "landscape"}
        kept_portraits = [p for p in self.portrait_images if p in portraits]
        kept_landscapes = [p for p in self.landscape_images if p in landscapes or p in portraits]
        queued = set(kept_portraits + kept_landscapes)
        new_portraits = [p for p in pool if p in portraits and p not in queued]
        new_landscapes = [p for p in pool if p in landscapes and p not in queued]
        random.shuffle(new_portraits)
        random.shuffle(new_landscapes)
        portrait_images, landscape_images = self.balanced(kept_portraits + new_portraits,
                                                          kept_landscapes + new_landscapes, portraits)

        self.discovered_images = discovered
        self.default_background = None
        self.image_list = tuple(pool)
        self.portrait_images = portrait_images
        self.landscape_images = landscape_images
        if self.is_sampled() and not portrait_images and not landscape_images:
            self.select_sample()

        if added or removed:
            log_info(f"Auto refresh: {len(discovered)} images discovered (+{added}, -{removed}), "
                     f"{len(self.portrait_images)} portrait, {len(self.landscape_images)} landscape in rotation")
        else:
            log_debug("Auto refresh: no changes")

    def rotation_pool(self, discovered):
        """Images eligible for the rotation: all discovered, or the current sample still present"""
        if self.sampled(len(discovered)):
            present = set(discovered)
            return [image_path for image_path in self.image_list if image_path in present]
        return list(discovered)

    @staticmethod
    def balanced(portrait_images, landscape_images, portraits):
        """(portrait queue, landscape queue) with lone portraits balanced: a lone portrait can never form a
        pair, so it is shown full screen from the landscape queue, and portraits kept there (lone, or
        landscape images replaced by portraits at the same path) move back to the portrait queue
        whenever together with it they can form a pair"""
        portrait_images, landscape_images = list(portrait_images), list(landscape_images)
        lone = [image_path for image_path in landscape_images if image_path in portraits]
        if lone and len(lone) + len(portrait_images) >= 2:
            landscape_images = [image_path for image_path in landscape_images if image_path not in portraits]
            portrait_images.extend(lone)
        if len(portrait_images) == 1 and landscape_images:
            landscape_images.append(portrait_images.pop())
        return portrait_images, landscape_images

    def sampled(self, count):
        """True when --preload-images limits count discovered images to a random sample"""
        return 0 < self.preload_images < count

    def is_sampled(self):
        """True when --preload-images limits the discovered images to a random sample"""
        return self.sampled(len(self.discovered_images))

    def select_sample(self):
        """Pick the images to rotate (a random sample of preload_images, or all) and categorize them.

        If none of the new candidates can be used (e.g. they were deleted after the last applied scan)
        while the current queues still hold images, the current queues are kept."""
        if self.is_sampled():
            candidates = random.sample(self.discovered_images, self.preload_images)
        else:
            candidates = list(self.discovered_images)
        kinds = {image_path: self.orientations.classify(image_path) for image_path in candidates}
        portraits = [p for p in candidates if kinds[p] == "portrait"]
        landscapes = [p for p in candidates if kinds[p] == "landscape"]
        if not portraits and not landscapes and (self.portrait_images or self.landscape_images):
            log_warning("None of the new sample's images can be shown, keeping the current ones")
            self.shown_images = set()
            return
        if self.is_sampled():
            log_info(f"Selected random sample of {self.preload_images} of {len(self.discovered_images)} images")
        portraits, landscapes = self.balanced(portraits, landscapes, set(portraits))
        random.shuffle(portraits)
        random.shuffle(landscapes)
        self.image_list = tuple(candidates)
        self.shown_images = set()
        self.portrait_images = portraits
        self.landscape_images = landscapes
        skipped = sum(1 for p in candidates if kinds[p] == "skipped")
        log_info(f"Categorized images: {len(self.portrait_images)} portrait, {len(self.landscape_images)} landscape"
                 + (f", {skipped} skipped (below --min-coverage {MIN_COVERAGE}%)" if skipped else ""))

    def sample_exhausted(self):
        """True when every image of the current random sample has been shown"""
        if not self.is_sampled():
            return False
        return self.shown_images.issuperset(self.portrait_images + self.landscape_images)

    @classmethod
    def kind_for_size(cls, width, height, display_width, display_height):
        """(portrait, landscape or skipped, coverage) for an image of width x height; skipped when it
        covers less than --min-coverage; portraits are shown in pairs, each one in half of the screen"""
        portrait = height > width
        target_width = display_width // 2 if portrait else display_width
        coverage = cls.coverage(width, height, target_width, display_height)
        if coverage < MIN_COVERAGE / 100:
            return "skipped", coverage
        return ("portrait" if portrait else "landscape"), coverage

    def create_default_image(self):
        """Keep the default gradient background in memory when no source images are found."""
        self.default_background = self.prepare_default_background()

    def prepare_default_background(self):
        """Return a loaded fallback independent of disk-cache eviction."""
        default_path = self.cache.path_for("default", self.display_width, self.display_height, FONT_PATH)
        cached = self.load_cached(default_path)
        if cached:
            log_info(f"Using cached default background: {default_path}")
            return cached

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

        self.store(default_path, img)
        log_info(f"Created default background: {default_path}")
        return Background(default_path, img)

    def store(self, processed_path, image):
        """Write a processed image to the cache; best effort, since the Background already holds it in
        memory (a full or read-only cache must not stop the slideshow)"""
        try:
            self.cache.put(processed_path, image)
        except OSError as e:
            log_error(f"Cannot write to the image cache ({e}); showing the image without caching it")

    def load_cached(self, processed_path):
        """Background read from the cache file processed_path, or None if it is not cached (or was evicted
        or damaged since), in which case the caller processes the source image again"""
        if not self.cache.get(processed_path):
            return None
        try:
            with Image.open(processed_path) as img:
                return Background(processed_path, img.convert("RGB"))
        except OSError as e:
            log_debug(f"Cached image unavailable, processing again: {processed_path}: {e}")
            return None

    def resize_portrait_pair(self, image_path1, image_path2):
        """Resize two portrait images to fit side by side on screen; returns a Background or None"""
        try:
            processed_path = self.cache.path_for("pair", self.display_width, self.display_height,
                                                 SCALE_MODE, MAX_CROP, BLUR_RADIUS, BLUR_BRIGHTNESS,
                                                 self.cache.content_hash(image_path1),
                                                 self.cache.content_hash(image_path2))
            cached = self.load_cached(processed_path)
            if cached:
                log_info(f"Cached portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")
                return cached

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

                self.store(processed_path, final_img)

                log_info(f"Created portrait pair: {os.path.basename(image_path1)} + {os.path.basename(image_path2)}")
                log_debug(f"Saved to: {processed_path}")

                return Background(processed_path, final_img)

        except Exception as e:
            log_error(f"Error processing portrait pair {image_path1}, {image_path2}: {e}")
            return None

    def resize_landscape_single(self, image_path):
        """Scale a single image to the full screen according to SCALE_MODE; returns a Background or None"""
        try:
            processed_path = self.cache.path_for("landscape", self.display_width, self.display_height,
                                                 SCALE_MODE, MAX_CROP, BLUR_RADIUS, BLUR_BRIGHTNESS,
                                                 self.cache.content_hash(image_path))
            cached = self.load_cached(processed_path)
            if cached:
                log_info(f"Cached landscape ({SCALE_MODE}): {os.path.basename(image_path)}")
                return cached

            log_debug(f"Processing landscape image: {os.path.basename(image_path)}")
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                final_img = self.compose(img, self.display_width, self.display_height)

                self.store(processed_path, final_img)

                log_info(f"Processed landscape ({SCALE_MODE}): {os.path.basename(image_path)}")
                log_debug(f"Saved to: {processed_path}")

                return Background(processed_path, final_img)

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

    @classmethod
    def coverage(cls, width, height, target_width, target_height):
        """Fraction of the target area the image covers in the current SCALE_MODE (1.0 for fill)"""
        left, top, right, bottom = cls.crop_box(width, height, target_width / target_height, cls.mode_max_crop())
        fitted_width, fitted_height = cls.fitted_size(right - left, bottom - top, target_width, target_height)
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
        """Next background to show: applies the latest queued rescan, replaces an exhausted
        --preload-images sample, selects the next images and processes them. Images that fail to
        process (missing, unreadable, or on a share that is not available) are dropped if unreadable and
        the next ones are tried, through the whole rotation if needed, so a change is not skipped."""
        self.apply_pending_scans()
        if self.default_background is not None and not self.discovered_images:
            return self.default_background
        if self.sample_exhausted():
            log_info("All images of the current sample have been shown, selecting a new sample")
            self.select_sample()
        if not self.portrait_images and not self.landscape_images and self.discovered_images:
            log_debug("No images left in the rotation queues, trying the discovered images again")
            self.select_sample()
        for _ in range(len(self.portrait_images) + len(self.landscape_images)):
            if stop_event.is_set():
                break
            selection = self.select_next()
            if not selection:
                break
            if len(selection) == 2:
                background = self.resize_portrait_pair(*selection)
            else:
                background = self.resize_landscape_single(selection[0])
            if background is not None:
                return background
            self.drop_unreadable(selection)
        if self.default_background is None:
            self.default_background = self.prepare_default_background()
        return self.default_background

    @staticmethod
    def decodes(image_path):
        """True if the whole image can be decoded (not only its header)"""
        try:
            with Image.open(image_path) as img:
                img.load()
        except Exception as e:
            log_debug(f"Cannot decode {image_path}: {e}")
            return False
        return True

    def drop_unreadable(self, selection):
        """After selection failed to process: classify its images again from the files and fully decode
        them, removing the ones that fail from the queues (e.g. permissions revoked without changing mtime
        or size, or a truncated file whose header still parses); a later rescan adds them back once they
        can be read"""
        kinds = {}
        for image_path in selection:
            self.orientations.forget(image_path)
            kind = self.orientations.classify(image_path)
            if kind != "error" and not self.decodes(image_path):
                self.orientations.reject(image_path)
                kind = "error"
            kinds[image_path] = kind
        portraits = [p for p in self.portrait_images if p not in kinds]
        landscapes = [p for p in self.landscape_images if p not in kinds]
        portraits.extend(p for p, kind in kinds.items() if kind == "portrait")
        landscapes.extend(p for p, kind in kinds.items() if kind == "landscape")
        portrait_paths = set(portraits)
        self.portrait_images, self.landscape_images = self.balanced(portraits, landscapes, portrait_paths)

    def select_next(self):
        """Advance the rotation queues: (portrait1, portrait2) for a pair, (image,) for a single image, or None"""
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
            return (img,)

        return None

    def _get_portrait_pair(self):
        """Helper method to get a portrait pair"""
        # Get two random portrait images
        img1 = self.portrait_images.pop(0)
        img2 = self.portrait_images.pop(0)

        # Add them back to the end for rotation
        self.portrait_images.extend([img1, img2])
        self.shown_images.update([img1, img2])

        return img1, img2

    def _get_landscape_single(self):
        """Helper method to get a landscape image"""
        # Get one landscape image
        img = self.landscape_images.pop(0)

        # Add it back to the end for rotation
        self.landscape_images.append(img)
        self.shown_images.add(img)

        return (img,)

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

def display_slideshow_content(background, force_background_refresh=False):
    """Display slideshow content with time and date.

    background is a Background already loaded in memory by the rotation thread, so the main loop never
    reads the cache and cache eviction cannot affect a published or displayed image."""
    global last_background, background_frame, last_date

    if not background:
        logger.warning("No background image available")
        return

    try:
        # Only refresh background if it changed or forced
        background_changed = last_background != background.path
        if background_changed or force_background_refresh:
            last_background = background.path
            logger.info(f"Displaying background: {os.path.basename(background.path)}")
            start_bg = time.perf_counter()
            background_frame = background.frame
            lcd_comm.DisplayPILImage(background_frame)
            end_bg = time.perf_counter()
            logger.debug(f"Background display took: {end_bg - start_bg:.3f}s")

        time_line, date_line, day_line = overlay
        now = datetime.now()

        # Current time (updates every second) - bottom right corner
        time_line.draw(now.strftime("%H:%M:%S"), background_frame)

        # Redraw static content when the background or the date changes
        date = now.strftime("%Y-%m-%d")
        if background_changed or force_background_refresh or date != last_date:
            logger.debug("Redrawing date and day")
            last_date = date
            date_line.draw(date, background_frame)
            day_line.draw(now.strftime("%A"), background_frame)

        logger.debug("Slideshow content display completed successfully")

    except Exception as e:
        logger.error(f"Error displaying slideshow content: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")

def utc_offset(timestamp):
    """Local UTC offset in seconds at timestamp"""
    return time.localtime(timestamp).tm_gmtoff

def seconds_to_multiple(wall, inclusive):
    """Seconds from the local wall-clock time wall (naive datetime) to the next multiple of
    IMAGE_ROTATION_INTERVAL seconds counted from its midnight; inclusive also accepts wall itself.

    Every allowed interval divides a day, so the last multiple of a day is the next midnight."""
    elapsed = (wall - wall.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    if inclusive:
        steps = math.ceil(elapsed / IMAGE_ROTATION_INTERVAL)
    else:
        steps = math.floor(elapsed / IMAGE_ROTATION_INTERVAL) + 1
    return steps * IMAGE_ROTATION_INTERVAL - elapsed

def offset_change(start, end):
    """First whole second in (start, end] whose local UTC offset differs from the one at start (DST), or None.

    Offset changes happen on whole seconds, so floor(start) shares the offset of start."""
    offset = utc_offset(start)
    low, high = math.floor(start), math.floor(end)
    if high <= low or utc_offset(high) == offset:
        return None
    while high - low > 1:
        middle = (low + high) // 2
        if utc_offset(middle) == offset:
            low = middle
        else:
            high = middle
    return high

def next_transition(timestamp):
    """First instant after timestamp whose local wall-clock time is a multiple of IMAGE_ROTATION_INTERVAL
    seconds from midnight.

    Every allowed interval divides a day, so every day starts aligned at 00:00:00.
    When a daylight saving change comes first, the multiple is taken from the wall clock after the
    change: a repeated hour is not waited out and a skipped hour is not scheduled."""
    due = timestamp + seconds_to_multiple(datetime.fromtimestamp(timestamp), inclusive=False)
    change = offset_change(timestamp, due)
    if change is None:
        return due
    return change + seconds_to_multiple(datetime.fromtimestamp(change), inclusive=True)

def elapsed_clock():
    """Seconds of a clock unaffected by wall clock changes that keeps counting during suspend
    (CLOCK_BOOTTIME where available, otherwise time.monotonic)"""
    if hasattr(time, "CLOCK_BOOTTIME"):
        return time.clock_gettime(time.CLOCK_BOOTTIME)
    return time.monotonic()

def wait_for_transition(due):
    """Wait for the transition scheduled at due; returns the transition instant reached, or None if
    stop_event was set first.

    Wakes at least once a minute to follow wall clock adjustments (NTP, manual changes). Lateness is
    measured against an elapsed-time clock that also counts suspend: when the wall clock passed due by
    about the same amount (a late wake-up after load, a VM pause or suspend), the transition happens at
    once; when the wall clock moved by more than that elapsed time (a jump forward), or back so that an
    earlier transition comes first, the transition is rescheduled with next_transition."""
    elapsed_due = elapsed_clock() + (due - time.time())
    while True:
        now, elapsed = time.time(), elapsed_clock()
        if now >= due:
            late = now - due
            if (late < IMAGE_ROTATION_INTERVAL or
                    abs(late - (elapsed - elapsed_due)) <= CLOCK_TOLERANCE):
                return due
            due = next_transition(now)
            elapsed_due = elapsed + (due - now)
            log_info(f"Wall clock changed, next background change at {datetime.fromtimestamp(due):%Y-%m-%d %H:%M:%S}")
            continue
        earlier = next_transition(now)
        if earlier < due - CLOCK_TOLERANCE:
            due = earlier
            elapsed_due = elapsed + (due - now)
            log_info(f"Wall clock changed, next background change at {datetime.fromtimestamp(due):%Y-%m-%d %H:%M:%S}")
        if stop_event.wait(min(due - now, 60)):
            return None

def consume_transition():
    global pending_transition, current_background
    with transition_lock:
        if pending_transition is not None and time.time() >= pending_transition[0]:
            due, background, elapsed_due = pending_transition
            now = time.time()
            late = now - due
            if (late >= IMAGE_ROTATION_INTERVAL and
                    abs(late - (elapsed_clock() - elapsed_due)) > CLOCK_TOLERANCE):
                due = next_transition(now)
                pending_transition = (due, background, elapsed_clock() + due - now)
                return
            pending_transition = None
            if background is not None:
                current_background = background

def background_rotation_thread(image_manager):
    """Thread function for rotating background images on the clock schedule of next_transition.

    The next image is prepared and loaded in memory first, then published at its transition time; when
    preparing it takes longer than that, it is shown at the following one."""
    global pending_transition

    log_debug("Background rotation thread started")

    due = time.time()
    while not stop_event.is_set():
        new_background = None
        try:
            log_debug("Getting next background image...")
            new_background = image_manager.get_next_image()
        except Exception as e:
            log_error(f"Error in background rotation: {e}")
            log_debug(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")

        due = next_transition(time.time())
        log_debug(f"Next background change at {datetime.fromtimestamp(due):%Y-%m-%d %H:%M:%S}")
        with transition_lock:
            pending_transition = (due, new_background, elapsed_clock() + due - time.time())
        due = wait_for_transition(due)
        if due is None:
            break
        with transition_lock:
            if pending_transition is not None and pending_transition[1] is new_background:
                pending_transition = (due, new_background, elapsed_clock() + due - time.time())
        if new_background:
            wake_event.set()
            log_info(f"Switched to background: {os.path.basename(new_background.path)}")
            log_debug(f"Full path: {new_background.path}")
        else:
            log_warning("Failed to get next background image")
        while not stop_event.is_set():
            with transition_lock:
                waiting = pending_transition is not None
            if not waiting:
                break
            stop_event.wait(0.01)

    log_debug("Background rotation thread stopped")

def source_refresh_thread(image_manager):
    """Thread function rescanning the images directories every AUTO_REFRESH seconds.

    It only scans and classifies the images that can rotate; the result is handed to the rotation
    thread with image_manager.offer_scan(), and the rotation thread applies it to the queues."""
    log_debug("Source refresh thread started")

    while not stop_event.wait(AUTO_REFRESH):
        try:
            log_debug("Rescanning images directories...")
            image_manager.offer_scan(image_manager.scan())
        except Exception as e:
            log_error(f"Error in auto refresh: {e}")
            log_debug(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")

    log_debug("Source refresh thread stopped")

def sighandler(signum, frame):
    """Signal handler for graceful shutdown"""
    log_info("Received shutdown signal")
    stop_event.set()
    wake_event.set()

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

def source_directory(value):
    """argparse type: absolute path ('~' expanded; neither normalized nor resolved, so '..' after a
    symlink keeps its meaning and a repointed symlink is detected as a device/inode change by the
    rescans) of an existing, readable directory; it is never created"""
    if not value:
        raise argparse.ArgumentTypeError("empty path")
    path = os.path.join(os.getcwd(), os.path.expanduser(value))
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"'{value}' does not exist or is not a directory")
    if not os.access(path, os.R_OK | os.X_OK):
        raise argparse.ArgumentTypeError(f"'{value}' is not readable")
    return path

def source_directories(values):
    """{path: (st_dev, st_ino)} of the validated source directories (see source_directory) in the given
    order, without repeating a directory given more than once (same device/inode, e.g. through a symlink
    or a bind mount); the identities are the ones the rescans check against"""
    directories = {}
    for value in values:
        path = source_directory(value)
        try:
            source_stat = os.stat(path)
        except OSError as e:
            raise argparse.ArgumentTypeError(f"'{value}' cannot be read ({e})")
        directories.setdefault((source_stat.st_dev, source_stat.st_ino), path)
    return {path: identity for identity, path in directories.items()}

def parse_duration(value):
    """Seconds in a duration: a plain number of seconds, or a number followed by s, m, h or d
    (case-insensitive), e.g. 30, 30s, 5m, 1h, 1d. Raises ValueError otherwise."""
    match = re.fullmatch(r"(\d+)([smhd]?)", value.strip().lower())
    if not match:
        raise ValueError(f"'{value}' is not a duration (e.g. 30, 30s, 5m, 1h, 1d)")
    return int(match[1]) * DURATION_UNITS[match[2] or "s"]

def format_duration(seconds):
    """Shortest exact form of seconds in the largest whole unit: 86400 -> 1d, 7200 -> 2h, 300 -> 5m, 75 -> 75s"""
    for unit, size in sorted(DURATION_UNITS.items(), key=lambda item: -item[1]):
        if seconds % size == 0:
            return f"{seconds // size}{unit}"

def duration_range(minimum, maximum):
    """argparse type factory: duration (see parse_duration) between minimum and maximum seconds"""
    def parse(value):
        try:
            seconds = parse_duration(value)
        except ValueError as e:
            raise argparse.ArgumentTypeError(str(e))
        if seconds < minimum:
            raise argparse.ArgumentTypeError(f"'{value}' is shorter than {format_duration(minimum)}")
        if seconds > maximum:
            raise argparse.ArgumentTypeError(f"'{value}' is longer than {format_duration(maximum)}")
        return seconds
    return parse

def rotation_interval(value):
    """argparse type: --interval as a duration (see parse_duration) that is one of ALLOWED_INTERVALS"""
    try:
        seconds = parse_duration(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))
    if seconds not in ALLOWED_INTERVALS:
        raise argparse.ArgumentTypeError(
            f"'{value}' ({seconds} s) does not keep changes on round clock times; allowed: "
            + ", ".join(format_duration(allowed) for allowed in ALLOWED_INTERVALS))
    return seconds

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Turing Smart Screen Image Slideshow")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output (default: INFO level only)")
    parser.add_argument("--images", action="append", metavar="PATH",
                       help="Path to an existing, readable images directory; repeat it to show the images of "
                            "several directories, e.g. --images DIR1 --images DIR2 (default: 'images' in "
                            "current location)")
    parser.add_argument("--recursive", action="store_true",
                       help="Search for images recursively in subdirectories")
    parser.add_argument("--font", type=font_file, default=DEFAULT_FONT, metavar="NAME|PATH",
                       help="Font for the time/date overlay: bundled font name (see --font-list) or path "
                            f"to a custom .ttf/.otf file (default: {DEFAULT_FONT})")
    parser.add_argument("--font-list", action="store_true",
                       help="List the bundled fonts usable as --font NAME and exit")
    parser.add_argument("--interval", type=rotation_interval, default=IMAGE_ROTATION_INTERVAL, metavar="DURATION",
                       help="Time between image changes: seconds, or a number with unit s/m/h/d (e.g. 30, 5m, "
                            "1h, 1d). Changes happen at multiples of it counted from local midnight, e.g. 30 = "
                            "at :00 and :30. Allowed: multiples of 5 s that divide an hour (5s ... 30m, 1h) or "
                            f"whole hours that divide a day (2h, 3h, 4h, 6h, 8h, 12h, 1d) "
                            f"(default: {IMAGE_ROTATION_INTERVAL})")
    parser.add_argument("--auto-refresh", type=duration_range(1, MAX_AUTO_REFRESH), nargs="?", const=AUTO_REFRESH_DEFAULT,
                       default=AUTO_REFRESH, metavar="DURATION",
                       help="Rescan the images directories for new or deleted images every DURATION, without "
                            "interrupting the slideshow: seconds or a number with unit s/m/h/d (e.g. 600, 30m, "
                            f"2h, 1d), up to {format_duration(MAX_AUTO_REFRESH)}; without a value every "
                            f"{format_duration(AUTO_REFRESH_DEFAULT)} "
                            "(default: no rescan)")
    parser.add_argument("--preload-images", type=int_range(0), default=PRELOAD_IMAGES, metavar="N",
                       help="Use only N random images of the discovered ones (of all --images directories "
                            "together), re-sampled after all of them have been shown; 0 = no limit "
                            f"(default: {PRELOAD_IMAGES})")
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
    args = parser.parse_args()
    if not args.font_list:
        try:
            args.images = source_directories(args.images or ["images"])
        except argparse.ArgumentTypeError as e:
            parser.error(f"argument --images: {e}")
    return args

def log_configuration(args):
    """Log every option with its effective value, defaults included"""
    settings = {f"--{dest.replace('_', '-')}": value
                for dest, value in vars(args).items() if dest != "font_list"}
    settings["--images"] = ", ".join(args.images)
    settings["cache dir"] = CACHE_DIR
    settings["log file"] = LOG_FILE
    width = max(len(name) for name in settings)
    for name, value in settings.items():
        log_info(f"{name:<{width}}  {value}")

def main():
    """Main slideshow function"""
    global current_background, VERBOSE_LEVEL, FONT_PATH, overlay
    global IMAGE_ROTATION_INTERVAL, REVISION, COM_PORT, BRIGHTNESS, TIME_STYLE, DATE_STYLE, DAY_STYLE
    global TEXT_CONTRAST, SCALE_MODE, MAX_CROP, MIN_COVERAGE, AUTO_REFRESH

    # Parse command line arguments
    args = parse_arguments()
    if args.font_list:
        print_font_list()
        return
    FONT_PATH = args.font
    IMAGE_ROTATION_INTERVAL = args.interval
    AUTO_REFRESH = args.auto_refresh
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
    log_configuration(args)

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
        image_manager = ImageManager(source_identities=args.images,
                                   cache=cache,
                                   recursive_search=args.recursive,
                                   display_width=lcd_comm.get_width(),
                                   display_height=lcd_comm.get_height(),
                                   preload_images=args.preload_images)

        # Get initial background
        current_background = image_manager.get_next_image()
        log_info(f"Total images: {len(image_manager.image_list)} in rotation, "
                 f"{len(image_manager.discovered_images)} discovered")

        # Start background rotation thread
        bg_thread = Thread(target=background_rotation_thread,
                          args=(image_manager,),
                          daemon=True)
        bg_thread.start()

        if AUTO_REFRESH:
            Thread(target=source_refresh_thread, args=(image_manager,), daemon=True).start()

        # Main display loop
        frame_count = 0
        log_info("Starting image slideshow (Press Ctrl+C to exit)")
        log_info(f"Display dimensions: {lcd_comm.get_width()}x{lcd_comm.get_height()}")

        while not stop_event.is_set():
            wake_event.clear()
            try:
                consume_transition()
                display_slideshow_content(current_background, frame_count == 0)
                frame_count += 1
            except Exception as e:
                log_error(f"Error in main loop: {e}")
                log_debug(f"Frame {frame_count} failed - Exception details: {type(e).__name__}: {str(e)}")
                import traceback
                log_debug(f"Traceback: {traceback.format_exc()}")
            wake_event.wait(1 - time.time() % 1)

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
