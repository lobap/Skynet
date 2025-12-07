"""Centralized logging configuration."""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logging.getLogger("uvicorn.access").handlers = []

logger = logging.getLogger("skynet")
