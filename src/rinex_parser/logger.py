#!/usr/bin/env python
"""Logging configuration for RINEX parser.

Sets up a configured logger instance for use throughout the RINEX parser module.
"""

import logging


def create_logger(name: str = "rxp", log_level=logging.INFO):
    """creating a logger."""

    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(log_level)

    # create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    return logger


logger = create_logger()
