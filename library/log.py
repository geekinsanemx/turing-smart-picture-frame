# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Configure logging format
import locale
import logging
import os
from logging.handlers import RotatingFileHandler

APP_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "tspf")
LOG_FILE = os.path.join(APP_DIR, "log.log")
os.makedirs(APP_DIR, exist_ok=True)

# use current locale for date/time formatting in logs
locale.setlocale(locale.LC_ALL, '')

logging.basicConfig(  # format='%(asctime)s [%(levelname)s] %(message)s in %(pathname)s:%(lineno)d',
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=1000000, backupCount=0),  # Log in textfile max 1MB
        logging.StreamHandler()  # Log also in console
    ],
    datefmt='%x %X')

logger = logging.getLogger('turing')
logger.setLevel(logging.DEBUG)  # Lowest log level : print all messages
