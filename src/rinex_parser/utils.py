"""
Docstring for rinex_parser.utils
"""

from typing import Dict, Optional


class RX3Info:
    """
    Class to handle RX3 info.
    """

    def __init__(self):
        self.marker_name: Optional[str] = None
        self.country: Optional[str] = None
        self.receiver_id: Optional[str] = None
        self.monument_id: Optional[str] = None


def handle_rx3_info(rx3_info: str) -> RX3Info:
    """
    Process RX3 info string.
    """
    info = RX3Info()

    # get station from rx3 indicator '::RX3-cAUT-sGRAZ-r0-m0::
    if rx3_info.startswith("::RX3") and rx3_info.endswith("::"):
        parts = rx3_info.replace("::RX3-", "").replace("::", "").split("-")
        for part in parts:
            if part.startswith("s") and len(part) == 5:
                info.marker_name = part[1:].upper()
            elif part.startswith("r") and len(part) == 2:
                info.receiver_id = part[1:]
            elif part.startswith("m") and len(part) == 2:
                info.monument_id = part[1:]
            elif part.startswith("c") and len(part) == 5:
                info.country = part[1:].upper()

    return info
