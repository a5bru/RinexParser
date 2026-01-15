"""RinexEpoch module for handling RINEX observation epoch data.

Created on Nov 10, 2016
Author: jurgen
"""

import traceback
import time
from typing import Any, Dict, List
import datetime

from rinex_parser import constants as cc
from rinex_parser.logger import logger

EPOCH_MIN = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc).timestamp()
EPOCH_MAX = datetime.datetime(
    datetime.MAXYEAR, 12, 31, tzinfo=datetime.timezone.utc
).timestamp()


def ts_epoch_to_list(line: str) -> list:
    """Use epoch line and generate list of [y, m, d, H, M, S].
    input: "> 2025 03 16 00 00  0.0000000  0 37"
    output: [2025, 3, 16, 0, 0, 0.0]
    """
    y = int(line[2:6])
    m = int(line[7:9])
    d = int(line[10:12])
    H = int(line[13:15])
    M = int(line[16:18])
    S = float(line[18:30])
    return [y, m, d, H, M, S]


def ts_to_epoch(ts: float) -> str:
    """Convert timestamp to epoch format string.
    Returns string in format:
    > 2025 03 16 00 00  0.0000000
    """
    t = time.gmtime(ts)
    y = t.tm_year
    m = t.tm_mon
    d = t.tm_mday
    H = t.tm_hour
    M = t.tm_min
    S = t.tm_sec + (ts - int(ts))
    return f"> {y:04d} {m:02d} {d:02d} {H:02d} {M:02d} {S:10.7f}"


def ts_to_list(ts: float) -> list:
    """Convert timestamp to list of [y, m, d, H, M, S]."""
    t = time.gmtime(ts)
    y = t.tm_year
    m = t.tm_mon
    d = t.tm_mday
    H = t.tm_hour
    M = t.tm_min
    S = t.tm_sec + (ts - int(ts))
    return [y, m, d, H, M, S]


def ts_epoch_to_time(line: str) -> float:
    y, m, d, H, M, S = ts_epoch_to_list(line)
    return time.mktime(
        time.strptime(
            f"{y:04d}-{m:02d}-{d:02d}T{H:02d}:{M:02d}:{S:09.6f}", "%Y-%m-%dT%H:%M:%S.%f"
        )
    )


def ts_to_datetime(ts: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def ts_epoch_to_datetime(line: str) -> datetime.datetime:
    dt = ts_to_datetime(ts_epoch_to_time(line))
    return dt


def ts_to_second_of_day(ts: float) -> float:
    """Get seconds of day from timestamp."""
    dt = ts_to_datetime(ts)
    return get_second_of_day(dt.hour, dt.minute, dt.second + (ts - int(ts)))


def get_second_of_day(h: int, m: int, s: float) -> float:
    return h * 3600.0 + m * 60.0 + s


def ts_to_header(ts: float) -> str:
    """Convert date from timestamp to header format."""
    # > 2025 03 16 00 00  0.0000000  0 37
    #   2025    03    17    19    00   00.0000000     GPS         TIME OF FIRST OBS
    line = ts_to_epoch(ts)
    y, m, d, H, M, S = ts_epoch_to_list(line)
    s = f"  {y}    {m:02d}    {d:02d}    {H:02d}    {M:02d}  {S:11.7f}"
    return s


def ts_epoch_to_header(epoch: str) -> str:
    """Convert date from epoch format to header format."""
    # > 2025 03 16 00 00  0.0000000  0 37
    #   2025    03    17    19    00   00.0000000     GPS         TIME OF FIRST OBS
    line = f"> {epoch}"
    y, m, d, H, M, S = ts_epoch_to_list(line)
    s = f"  {y}    {m:02d}    {d:02d}    {H:02d}    {M:02d}  {S:11.7f}"
    return s


class Observation:
    """Represents a single observation value with metadata.

    Uses __slots__ for memory efficiency.
    """

    __slots__ = ("code", "value", "lli", "ss")

    def __init__(
        self,
        code: str,
        value: str | None = None,
        lli: str | None = None,
        ss: str | None = None,
    ) -> None:
        """Initialize an observation.

        Args:
            code: Observation code (e.g., "L1", "C1C", "L2W").
            value: Observation value.
            lli: Loss of Lock Indicator.
            ss: Signal Strength Indicator (also called ssi in RINEX 3).
        """
        self.code: str = code
        self.value: str = value
        self.lli: str | None = lli
        self.ss: str | None = ss  # 'ss' for RINEX 2, same as 'ssi' in RINEX 3

    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary format for backwards compatibility.

        Returns:
            dict: Dictionary with '{code}_value', '{code}_lli', '{code}_ss' keys.
        """
        return {
            f"{self.code}_value": self.value,
            f"{self.code}_lli": self.lli,
            f"{self.code}_ss": self.ss,
        }

    @classmethod
    def from_flat_dict(cls, code: str, data: Dict[str, Any]) -> "Observation":
        """Create Observation from flat dictionary format.

        Args:
            code: Observation code.
            data: Dictionary with '{code}_value', '{code}_lli', '{code}_ss' keys.

        Returns:
            Observation: New Observation instance.
        """
        return cls(
            code=code,
            value=data.get(f"{code}_value"),
            lli=data.get(f"{code}_lli"),
            ss=data.get(f"{code}_ss")
            or data.get(f"{code}_ssi"),  # Handle both ss and ssi
        )


class Satellite:
    """Represents a single satellite's observations within an epoch.

    Uses __slots__ for memory efficiency.
    """

    __slots__ = ("id", "observations")

    def __init__(
        self, sat_id: str, observations: List[Observation] | None = None
    ) -> None:
        """Initialize a satellite observation.

        Args:
            sat_id: Satellite identifier (e.g., "G01", "R12").
            observations: List of Observation objects.
        """
        self.id: str = sat_id

        if observations is None:
            self.observations: List[Observation] = []
        elif isinstance(observations, list):
            self.observations = observations
        elif isinstance(observations, dict):
            # Convert dict format to list of Observation objects
            self.observations = [
                obs for obs in observations.values() if isinstance(obs, Observation)
            ]
        else:
            self.observations = []

    @staticmethod
    def _convert_flat_dict(flat_dict: Dict[str, Any]) -> List[Observation]:
        """Convert flat dictionary format to Observation objects.

        Args:
            flat_dict: Dict with keys like 'L1_value', 'L1_lli', 'L1_ss'.

        Returns:
            List of Observation objects.
        """
        observations = []
        processed = set()

        for key in flat_dict.keys():
            if "_value" in key:
                code = key.replace("_value", "")
                if code not in processed:
                    observations.append(
                        Observation(
                            code=code,
                            value=flat_dict.get(f"{code}_value"),
                            lli=flat_dict.get(f"{code}_lli"),
                            ss=flat_dict.get(f"{code}_ss")
                            or flat_dict.get(f"{code}_ssi"),
                        )
                    )
                    processed.add(code)

        return observations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for backwards compatibility.

        Returns:
            dict: Dictionary with 'id' and flat 'observations' dict.
        """
        flat_obs = {}
        for obs in self.observations:
            flat_obs.update(obs.to_flat_dict())

        return {"id": self.id, "observations": flat_obs}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Satellite":
        """Create Satellite from dictionary.

        Args:
            data: Dictionary with 'id' and 'observations' keys.

        Returns:
            Satellite: New Satellite instance.
        """
        return cls(data["id"], data.get("observations", {}))

    def get_system(self) -> str:
        """Get satellite system identifier.

        Returns:
            str: Single character system ID (G, R, E, C, J, S).
        """
        return self.id[0] if self.id else ""


class RinexEpoch:
    """Represents a single epoch in a RINEX observation file.

    Contains timestamp, observation types, and satellite observations.
    """

    __slots__ = (
        "timestamp",
        "observation_types",
        "satellites",
        "epoch_flag",
        "rcv_clock_offset",
        "raw",
    )

    def __init__(
        self,
        timestamp: float,
        observation_types: Dict[str, Dict[str, List[str]]],
        satellites: List[Dict[str, Any] | Satellite],
        **kwargs: Any,
    ) -> None:
        """Initialize a RINEX epoch.

        Args:
            timestamp: float object representing epoch timestamp.
            observation_types: Dict mapping satellite systems to observation types.
            satellites: List of Satellite objects or dicts (dicts converted automatically).
            epoch_flag: Epoch flag value (default 0).
            rcv_clock_offset: Receiver clock offset in seconds (default 0.0).
        """
        assert isinstance(timestamp, float), "timestamp must be a float"

        self.timestamp: float = timestamp
        self.observation_types = observation_types
        # Convert dicts to Satellite objects if needed
        self.satellites: List[Satellite] = [
            sat if isinstance(sat, Satellite) else Satellite.from_dict(sat)
            for sat in satellites
        ]
        self.epoch_flag = kwargs.get("epoch_flag", 0)
        self.rcv_clock_offset = kwargs.get("rcv_clock_offset", 0.0)
        raw = kwargs.get("raw", [])
        self.raw: list[str] = raw

    def get_day_seconds(self) -> int:
        """Get seconds elapsed since midnight of the epoch date.

        Returns:
            int: Seconds since 00:00:00 of the epoch date.
        """
        return ts_to_second_of_day(self.timestamp)

    def is_valid(
        self,
        satellite_systems: List[str] | None = None,
        observation_types: List[str] | None = None,
        satellites: int = 5,
    ) -> bool:
        """Check if epoch meets validity criteria.

        Default criteria:
        - Contains GPS satellite system
        - Contains L1 and L2 observation types
        - At least 5 satellites within each system

        Args:
            satellite_systems: List of required satellite systems (default: ["G"]).
            observation_types: List of required observation types (default: ["L1", "L2", "L1C", "L1W"]).
            satellites: Minimum number of satellites required (default: 5).

        Returns:
            bool: True if epoch meets all criteria, False otherwise.
        """
        if satellite_systems is None:
            satellite_systems = ["G"]
        if observation_types is None:
            observation_types = ["L1", "L2", "L1C", "L1W"]

        for observation_type in observation_types:
            for satellite_system in satellite_systems:
                sat_count = 0
                for satellite in self.satellites:
                    if satellite.id.startswith(satellite_system):
                        obs = satellite.observations.get(observation_type)
                        if obs is not None and obs.value is not None:
                            sat_count += 1

                if sat_count < satellites:
                    return False
        return True

    @staticmethod
    def get_val(val: Any) -> str:
        """Format observation value as a 14-character string.

        Args:
            val: Numeric value to format.

        Returns:
            str: Formatted value (14 chars) or spaces if formatting fails.
        """
        return f"{val:14}"  # type: ignore
        try:
            if val is None:
                return " " * 14
            return f"{val:14.3f}"
        except (ValueError, TypeError):
            return " " * 14

    @staticmethod
    def get_d(val: Any) -> str:
        """Format descriptor value as a single character string.

        Args:
            val: Value to format as integer descriptor.

        Returns:
            str: Single character (digit or space if zero/invalid).
        """
        if val is None:
            return " "
        return val

    def has_satellite_system(self, sat_sys: str) -> bool:
        """Check if a satellite system is present in this epoch.

        Args:
            sat_sys: Single-character satellite system ID (\"G\", \"R\", \"E\", etc.).

        Returns:
            bool: True if satellite system is present, False otherwise.
        """
        for sat in self.satellites:
            if sat.id.upper().startswith(sat_sys[0].upper()):
                return True
        return False

    def to_rinex2(self) -> str:
        """Export epoch in RINEX 2 format.

        Returns:
            str: Formatted epoch data in RINEX 2 format.
        """
        prn1 = ""
        prn2 = ""
        nos = len(self.satellites)
        data_lines = []

        for i in range(nos):
            sat = self.satellites[i]
            for j, ot in enumerate(self.observation_types, 1):
                obs = sat.observations.get(ot)
                if obs and obs.value is not None:
                    # val = self.get_val(obs.value)
                    # lli = self.get_d(obs.lli)
                    # ss = self.get_d(obs.ss)
                    new_data = f"{obs.val:14s}{obs.lli:1s}{obs.ss:1s}"
                else:
                    new_data = " " * 16

                if (j % 5 == 0) and len(self.observation_types) > 5:
                    new_data = f"{new_data}\n"
                data_lines.append(new_data)

            if i < nos - 1:
                # data_lines += "\n"
                pass

            if i < 12:
                prn1 += sat.id
            else:
                if i % 12 == 0:
                    prn2 += f"\n{' ' * 32}"
                prn2 += sat.id

        ts_rnx = ts_to_epoch(self.timestamp)

        header_line = (
            f" {ts_rnx}  {self.epoch_flag:d}{nos:3d}{prn1}{self.rcv_clock_offset:12.9f}"
        )

        if prn2:
            header_line += prn2

        return f"{header_line}\n{'\n'.join(data_lines)}"

    def from_rinex2(self, rinex: str) -> None:
        """Parse epoch from RINEX 2 format string.

        Args:
            rinex: RINEX 2 formatted epoch string.
        """

    def to_rinex3(self, use_raw: bool = False) -> str:
        """Export epoch in RINEX 3 format.

        Returns:
            str: Formatted epoch data in RINEX 3 format.
        """
        nos = len(self.satellites)
        data_lines = []

        if use_raw and self.raw:
            return self.raw

        nos = len(self.satellites)
        rco = self.rcv_clock_offset if self.rcv_clock_offset else " "

        ts_rnx = ts_to_epoch(self.timestamp)

        data_lines.append(f"{ts_rnx}  {self.epoch_flag}{nos:3d}{'':6s}{rco}".strip())

        # Sort satellite systems in standard order
        sat_sys_order = sorted("GRECJS")
        sat_sys_block = {sat_sys: [] for sat_sys in sat_sys_order}

        # Process each satellite
        # observation_types format: {"G": [...]}, "R": ︃[...︃], ...}
        for sat in self.satellites:
            try:
                sat_sys = sat.id[0]  # Satellite system: G, R, E, C, J, S
                obs_codes = self.observation_types[sat_sys]
                sat_data = [f"{sat.id:3s}"]

                for obs_code in obs_codes:
                    found_obs_code = False
                    for obs in sat.observations:
                        if found_obs_code:
                            break
                        if obs.code == obs_code:
                            if obs.value is not None:
                                # val = self.get_val(obs.value)
                                # lli = self.get_d(obs.lli)
                                # ssi = self.get_d(obs.ss)
                                # if (
                                #    obs_code.startswith("L")
                                #    and ssi != " "
                                #    and lli == " "
                                # ):
                                #    lli = "0"
                                sat_data.append(
                                    f"{obs.value:>14s}{obs.lli:1s}{obs.ss:1s}"
                                )
                            else:
                                # Satellite does not have this observation code
                                sat_data.append(" " * 16)
                            found_obs_code = True
                            break

                    if not found_obs_code:
                        # Observation code not found for this satellite
                        sat_data.append(" " * 16)

                sat_sys_block[sat_sys].append("".join(sat_data).strip())
            except KeyError as e:
                logger.warning(f"Missing satellite system data: {e}")
            except Exception as e:
                logger.error(f"Error processing satellite data: {e}")
                traceback.print_exc()

        sat_blocks = []
        for sat_sys in sat_sys_order:
            if sat_sys_block[sat_sys]:
                sat_blocks.append("\n".join(sat_sys_block[sat_sys]))
        data_lines.append("\n".join(sat_blocks))
        return "\n".join(data_lines)

    def from_rinex3(self, rinex: str) -> None:
        """Parse epoch from RINEX 3 format string.

        Args:
            rinex: RINEX 3 formatted epoch string.
        """
