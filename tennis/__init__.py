"""Tennis court booking bot."""

import logging
from pathlib import Path

import yaml

# specify logging level as info
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

# Configuration.
with Path("conf.yml").open() as f:
    config = yaml.safe_load(f)
