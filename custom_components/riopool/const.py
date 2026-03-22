"""Constants for the Riopool Rio750 pool pump integration."""

import logging
from datetime import timedelta

DOMAIN = "riopool"
LOGGER = logging.getLogger(__package__)

LAN_PORT = 12416
DISCOVERY_PORT = 12414

UPDATE_INTERVAL = timedelta(seconds=5)
TIMEOUT = 10

PLATFORMS = ["sensor", "switch", "number", "binary_sensor"]

# Gizwits protocol constants
GIZWITS_HEADER = b"\x00\x00\x00\x03"

# Speed conversion: raw value * ratio = RPM
SPEED_RATIO = 50
SPEED_RAW_MIN = 23   # 1150 RPM
SPEED_RAW_MAX = 69   # 3450 RPM
SPEED_RPM_MIN = SPEED_RAW_MIN * SPEED_RATIO  # 1150
SPEED_RPM_MAX = SPEED_RAW_MAX * SPEED_RATIO  # 3450

# Timer: minutes from midnight, max 1440 (24h)
TIMER_MAX_MINUTES = 1440

MANUAL_GEARS = ["LOW", "MEDI", "HIGH", "FULL"]
MODES = ["Auto", "Manual"]
