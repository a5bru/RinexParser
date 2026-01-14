"""RINEX observation file reader module.

Created on Oct 25, 2016
Author: jurgen
"""

import datetime
import os
import re
import traceback
from functools import lru_cache
from io import StringIO
from typing import Any, Dict, List

from rinex_parser import constants as cc
from rinex_parser.logger import logger
from rinex_parser.obs_header import (
    Rinex2ObsHeader,
    Rinex3ObsHeader,
    RinexObsHeader,
)
from rinex_parser.obs_epoch import RinexEpoch, Satellite, Observation, Satellite, Observation

__updated__ = "2016-11-16"


class RinexObsReader:
    """Base class for reading RINEX observation files.
    
    Handles reading and parsing of RINEX observation data in both versions 2 and 3.
    Subclasses implement version-specific parsing logic.
    
    Attributes:
        header: RinexObsHeader instance containing file header information.
        datadict: Dictionary containing parsed observation epochs.
        rinex_obs_file: Path to the RINEX observation file.
        rinex_epochs: List of RinexEpoch objects parsed from the file.
    """

    RINEX_HEADER_CLASS = RinexObsHeader

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the RINEX observation reader.
        
        Args:
            interval_filter: Epoch interval filter in seconds (default: 0).
            rinex_obs_file: Path to RINEX observation file (default: "").
            rinex_epochs: List of pre-existing RinexEpoch objects (default: []).
            rinex_date: Date for the observations (default: today).
            skip_datadict: Skip building full datadict for performance (default: False).
        """
        self.header = self.RINEX_HEADER_CLASS()
        self.interval_filter: int = kwargs.get("interval_filter", 0)
        self.filter_on_read: bool = kwargs.get("filter_on_read", True)
        self.found_obs_types = {}
        self.filter_sat_sys: list = kwargs.get("filter_sat_sys", "").split(",")
        self.filter_sat_pnr: list = kwargs.get("filter_sat_pnr", "").split(",")
        self.filter_sat_obs: list = kwargs.get("filter_sat_obs", "").split(",")
        self.sat_stats = {}  # {"G01": {"C1C": 4}, ...}
        self.backup_epochs: List[RinexEpoch] = []
        self.backup_interval: int = 0
        self.rinex_obs_file: str = kwargs.get("rinex_obs_file", "")
        self.rinex_epochs: List[RinexEpoch] = kwargs.get("rinex_epochs", [])
        self.rinex_date: datetime.date = kwargs.get(
            "rinex_date", datetime.datetime.now().date()
        )
        self.skip_datadict: bool = kwargs.get("skip_datadict", False)

    @staticmethod
    def get_start_time(file_sequence: str) -> datetime.time:
        """Get start time for a RINEX file sequence.
        
        Args:
            file_sequence: File sequence code ("0" or "a"-"x").
            
        Returns:
            datetime.time: Start time of the file sequence.
        """
        if file_sequence == "0":
            return datetime.time(0, 0)
        return datetime.time(ord(file_sequence.lower()) - 97, 0)

    @staticmethod
    def get_epochs_possible(
        file_sequence: str,
        interval: int,
    ) -> int:
        """Get maximum number of epochs for a file sequence.
        
        Args:
            file_sequence: File sequence code ("0" or "a"-"x").
            interval: Epoch interval in seconds.
            
        Returns:
            int: Maximum number of epochs possible in the file.
        """
        start = datetime.datetime.combine(
            datetime.date.today(),
            Rinex2ObsReader.get_start_time(file_sequence)
        )
        end = datetime.datetime.combine(
            datetime.date.today(),
            Rinex2ObsReader.get_end_time(file_sequence, interval)
        )
        return int((end - start).total_seconds() / interval) + 1

    @staticmethod
    def prepare_line(line: str) -> str:
        """Prepare a line for parsing by normalizing line endings and padding.
        
        Args:
            line: Raw line from file.
            
        Returns:
            str: Normalized line padded to 16-character boundary.
        """
        new_line = line.replace("\r", "").replace("\n", "")
        if len(new_line) % 16 != 0:
            new_line += " " * (16 - len(new_line) % 16)
        return new_line

    @staticmethod
    def get_end_time(file_sequence: str, interval: int) -> datetime.time:
        """Get end time for a RINEX file sequence.
        
        Args:
            file_sequence: File sequence code ("0" or "a"-"x").
            interval: Epoch interval in seconds.
            
        Returns:
            datetime.time: End time of the file sequence.
        """
        if file_sequence == "0":
            return datetime.time(23, 59, 60 - interval)
        return datetime.time(ord(file_sequence.lower()) - 97, 59, 60 - interval)

    @staticmethod
    def is_valid_filename(filename: str, rinex_version: int | float = 2) -> bool:
        """Check if a filename conforms to RINEX naming standards.
        
        Args:
            filename: The filename to validate.
            rinex_version: RINEX version (2 or 3, default: 2).
            
        Returns:
            bool: True if filename matches the appropriate RINEX format.
        """
        rinex_version = float(rinex_version)
        if 2.0 <= rinex_version < 3.0:
            filename_regex = Rinex2ObsReader.RINEX_FILE_NAME_REGEX
        elif rinex_version >= 3.0:
            filename_regex = Rinex3ObsReader.RINEX_FILE_NAME_REGEX
        else:
            return False
        return re.match(filename_regex, filename) is not None
    
    def set_rinex_obs_file(self, rinex_obs_file: str) -> None:
        """Set the RINEX observation file path.
        
        Must be implemented by subclasses.
        
        Args:
            rinex_obs_file: Path to the RINEX observation file.
            
        Raises:
            NotImplementedError: Always (must be implemented in subclass).
        """
        raise NotImplementedError

    def correct_year2(self, year2: int) -> int:
        """Convert 2-digit year to 4-digit year.
        
        According to the RINEX Manual 2.10, chapter "6.5 2-digit Years":
        - Years 80-99 map to 1980-1999
        - Years 00-79 map to 2000-2079
        
        Args:
            year2: Two-digit year.
            
        Returns:
            int: Four-digit year.
        """
        if year2 < 80:
            return year2 + 2000
        else:
            return year2 + 1900

    def do_thinning(self, interval: int) -> None:
        """Reduce epochs to only those at specified interval boundaries.
        
        Backs up original epochs and replaces them with thinned set.
        Optimized to pre-calculate times for faster filtering.
        
        Args:
            interval: Epoch interval in seconds.
        """
        if interval <= 0:
            return
        
        # Pre-calculate all day_seconds to avoid repeated computation
        thinned_epochs = []
        for epoch in self.rinex_epochs:
            seconds = epoch.get_day_seconds()
            if seconds % interval == 0:
                thinned_epochs.append(epoch)
        
        if len(self.backup_epochs) == 0:
            self.backup_epochs = self.rinex_epochs
            self.backup_interval = self.header.interval
        self.rinex_epochs = thinned_epochs
        self.header.interval = interval

    def undo_thinning(self) -> None:
        """Restore original epochs before thinning was applied."""
        self.rinex_epochs = self.backup_epochs
        self.backup_epochs = []
        self.header.interval = self.backup_interval
        self.backup_interval = 0

    def to_rinex2(self) -> str:
        """Export header and epochs in RINEX 2 format.
        
        Uses StringIO for efficient string building.
        """
        if self.rinex_epochs:
            self.update_header_obs()

        output = StringIO()
        output.write(self.header.to_rinex2())
        output.write('\n')
        
        for rinex_epoch in self.rinex_epochs:
            if not isinstance(rinex_epoch, RinexEpoch):
                raise TypeError("rinex_epochs must contain RinexEpoch instances")
            output.write(rinex_epoch.to_rinex2())
            output.write('\n')
        
        return output.getvalue()

    def to_rinex3(self) -> str:
        """Export header and epochs in RINEX 3 format.
        
        Uses StringIO for efficient string building.
        """
        if self.rinex_epochs:
            self.update_header_obs()

        output = StringIO()
        output.write(self.header.to_rinex3())
        output.write('\n')
        
        for rinex_epoch in self.rinex_epochs:
            if not isinstance(rinex_epoch, RinexEpoch):
                raise TypeError("rinex_epochs must contain RinexEpoch instances")

            seconds_of_day = (
                rinex_epoch.timestamp.hour * 3600
                + rinex_epoch.timestamp.minute * 60
                + rinex_epoch.timestamp.second
            )

            if self.interval_filter <= 0 or (
                seconds_of_day % self.interval_filter == 0
            ):
                output.write(rinex_epoch.to_rinex3())
                output.write('\n')
        
        return output.getvalue()

    def read_header(self, sort_obs_types: bool = True) -> None:
        """Read and parse the RINEX file header.
        
        Args:
            sort_obs_types: Whether to sort observation types (default: True).
        """
        header = ""
        with open(self.rinex_obs_file, "r") as handler:
            for line in handler:
                header += line
                if "END OF HEADER" in line:
                    break
        self.header = self.RINEX_HEADER_CLASS.from_header(header_string=header)

    def add_satellite(self, satellite: str) -> None:
        """Add or increment count for a satellite in the header.
        
        Args:
            satellite: Satellite ID matching regex pattern [GR][ \\d]{2}.
        """
        if satellite not in self.header.satellites:
            self.header.satellites[satellite] = 0
        self.header.satellites[satellite] += 1

    def has_satellite_system(self, sat_sys: str) -> bool:
        """Check if a satellite system is present in the data.
        
        Args:
            sat_sys: Satellite system ID (e.g., "G", "R", "E").
            
        Returns:
            bool: True if system is present, False otherwise.
        """
        for epoch in self.rinex_epochs:
            if epoch.has_satellite_system(sat_sys):
                return True
        return False

    def update_header_obs(self) -> None:
        """Update header with first and last observation times."""
        # First and Last Observation
        self.header.first_observation = self.rinex_epochs[0].timestamp
        self.header.last_observation = self.rinex_epochs[-1].timestamp

    def read_satellite(
        self,
        sat_id: str,
        line: str,
    ) -> Dict[str, Any]:
        """Parse satellite observation data from a line.
        
        Must be implemented by subclasses.
        
        Args:
            sat_id: Satellite identifier.
            line: Raw observation line data.
            
        Returns:
            dict: Satellite observation dictionary.
            
        Raises:
            NotImplementedError: Always (must be implemented in subclass).
        """
        raise NotImplementedError

    def read_data_to_dict(self) -> None:
        """Read observation data and populate datadict.
        
        Must be implemented by subclasses.
        
        Raises:
            NotImplementedError: Always (must be implemented in subclass).
        """
        raise NotImplementedError
    
    def to_rinex2_file(self, output_path: str) -> None:
        """Stream RINEX 2 output directly to file for better performance.
        
        Args:
            output_path: Path to output file.
        """
        if self.rinex_epochs:
            self.update_header_obs()
        
        with open(output_path, 'w', buffering=65536, encoding='utf-8') as f:
            f.write(self.header.to_rinex2())
            f.write('\n')
            
            for rinex_epoch in self.rinex_epochs:
                if not isinstance(rinex_epoch, RinexEpoch):
                    raise TypeError("rinex_epochs must contain RinexEpoch instances")
                f.write(rinex_epoch.to_rinex2())
                f.write('\n')
    
    def to_rinex3_file(self, output_path: str) -> None:
        """Stream RINEX 3 output directly to file for better performance.
        
        Args:
            output_path: Path to output file.
        """
        if self.rinex_epochs:
            self.update_header_obs()
        
        with open(output_path, 'w', buffering=65536, encoding='utf-8') as f:
            f.write(self.header.to_rinex3())
            f.write('\n')
            
            for rinex_epoch in self.rinex_epochs:
                if not isinstance(rinex_epoch, RinexEpoch):
                    raise TypeError("rinex_epochs must contain RinexEpoch instances")
                
                seconds_of_day = (
                    rinex_epoch.timestamp.hour * 3600
                    + rinex_epoch.timestamp.minute * 60
                    + rinex_epoch.timestamp.second
                )
                
                if self.interval_filter <= 0 or (
                    seconds_of_day % self.interval_filter == 0
                ):
                    f.write(rinex_epoch.to_rinex3())
                    f.write('\n')
    
    def to_rinex2_file(self, output_path: str) -> None:
        """Stream RINEX 2 output directly to file for better performance.
        
        Args:
            output_path: Path to output file.
        """
        if self.rinex_epochs:
            self.update_header_obs()
        
        with open(output_path, 'w', buffering=65536, encoding='utf-8') as f:
            f.write(self.header.to_rinex2())
            f.write('\n')
            
            for rinex_epoch in self.rinex_epochs:
                if not isinstance(rinex_epoch, RinexEpoch):
                    raise TypeError("rinex_epochs must contain RinexEpoch instances")
                f.write(rinex_epoch.to_rinex2())
                f.write('\n')
    
    def to_rinex3_file(self, output_path: str) -> None:
        """Stream RINEX 3 output directly to file for better performance.
        
        Args:
            output_path: Path to output file.
        """
        if self.rinex_epochs:
            self.update_header_obs()
        
        with open(output_path, 'w', buffering=65536, encoding='utf-8') as f:
            f.write(self.header.to_rinex3())
            f.write('\n')
            
            for rinex_epoch in self.rinex_epochs:
                if not isinstance(rinex_epoch, RinexEpoch):
                    raise TypeError("rinex_epochs must contain RinexEpoch instances")
                
                seconds_of_day = (
                    rinex_epoch.timestamp.hour * 3600
                    + rinex_epoch.timestamp.minute * 60
                    + rinex_epoch.timestamp.second
                )
                
                if self.interval_filter <= 0 or (
                    seconds_of_day % self.interval_filter == 0
                ):
                    f.write(rinex_epoch.to_rinex3())
                    f.write('\n')


class Rinex2ObsReader(RinexObsReader):
    """RINEX 2 observation reader with optimized parsing.

    Args:
        datadict: {
            "epochs": [
                {
                    "id": "YYYY-mm-ddTHH:MM:SSZ",
                    "satellites": [
                        {
                            "id": "[GR][0-9]{2},
                            "observations": {
                                "[CLSPD][12]": {
                                    "value": ..,
                                    "lli": ..,
                                    "ss": ..
                                }
                            }{1,}
                        }
                    ]
                },
                {
                    "id": "..."
                    "satellites": [..]
                },
                {..}
            ]
        }
    """

    RINEX_HEADER_CLASS = Rinex2ObsHeader
    RINEX_FILE_NAME_REGEX = r"....\d\d\d[a-x0]\.\d\d[oO]"
    RINEX_FORMAT = 2
    RINEX_DATELINE_REGEXP = cc.RINEX2_DATELINE_REGEXP
    RINEX_DATELINE_REGEXP_SHORT = cc.RINEX2_DATELINE_REGEXP_SHORT
    RINEX_SATELLITES_REGEXP = cc.RINEX2_SATELLITES_REGEXP
    
    # Cached compiled regex patterns for performance
    _dateline_re = None
    _dateline_short_re = None
    
    @classmethod
    def _get_dateline_re(cls):
        """Get cached compiled dateline regex."""
        if cls._dateline_re is None:
            cls._dateline_re = re.compile(cls.RINEX_DATELINE_REGEXP)
        return cls._dateline_re
    
    @classmethod
    def _get_dateline_short_re(cls):
        """Get cached compiled short dateline regex."""
        if cls._dateline_short_re is None:
            cls._dateline_short_re = re.compile(cls.RINEX_DATELINE_REGEXP_SHORT)
        return cls._dateline_short_re

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a RINEX 2 observation reader."""
        super().__init__(**kwargs)

    def set_rinex_obs_file(self, rinex_obs_file: str) -> None:
        self.rinex_obs_file = rinex_obs_file
        self.station_doy_session = os.path.basename(
            self.rinex_obs_file).split(".")[0]
        if not self.__class__.is_valid_filename(
            os.path.basename(self.rinex_obs_file), self.header.format_version):
            raise ValueError(
                f"Invalid RINEX filename for version {self.header.format_version}: "
                f"{os.path.basename(self.rinex_obs_file)}"
            )
        self.station = self.station_doy_session[:4]
        self.doy = int(self.station_doy_session[4:7])
        year2 = int(self.rinex_obs_file.split(".")[-1][:2])
        self.year = self.correct_year2(year2)

        self.rinex_file_sequence = self.station_doy_session[7]
        self.backup_epochs = []

    def read_satellite(self, sat_id: str, line: str) -> Satellite:
        """
        Parses trough rnx observation and creates Satellite object. Referring to the RINEX Handbook 2.10
        there are only up to 5 observation types per line. This method parses any line length 

        Args:
            sat_id: str satellite number/name
            line: str rnx line containing observations
        Returns:
            Satellite: Satellite object with Observation objects
        """

        observations = []
        for k in range(len(self.header.observation_types)):
            obs_type = self.header.observation_types[k]
            obs_col = line[(16 * k) : (16 * (k + 1))]
            obs_val = obs_col[:14].strip()

            if obs_val == "":
                obs_val = None
            else:
                obs_val = float(obs_val)

            if len(obs_col) < 15:
                obs_lli = 0
            else:
                obs_lli = obs_col[14].strip()
                if obs_lli == "":
                    obs_lli = 0
                else:
                    obs_lli = int(obs_lli)

            if len(obs_col) < 16:
                obs_ss = 0
            else:
                obs_ss = obs_col[15].strip()
                if obs_ss == "":
                    obs_ss = 0
                else:
                    obs_ss = int(obs_ss)

            if obs_val is None:
                # Do not store empty obs_type
                continue

            observations.append(Observation(
                code=obs_type,
                value=obs_val,
                lli=obs_lli,
                ss=obs_ss
            ))
        
        return Satellite(sat_id, observations)

    def read_data_to_dict(self) -> None:
        """
        """
        # SKIP HEADER
        with open(self.rinex_obs_file, "r") as handler:
            end_of_header = False
            while True:

                # Check for END_OF_FILE
                line = handler.readline()
                if "END OF HEADER" in line:
                    logger.debug("End of Header Reached")
                    end_of_header = True
                if not end_of_header:
                    continue
                if line == "":
                    break

                # Get DateLine
                r = self._get_dateline_re().search(line)
                if r is not None:
                    timestamp = datetime.datetime(
                        self.correct_year2(year2=int(r.group("year2"))),
                        int(r.group("month")),
                        int(r.group("day")),
                        int(r.group("hour")),
                        int(r.group("minute")),
                        int(float(r.group("second"))),
                    )
                    # 2025 03 16 00 00  0.0000000
                    epoch = timestamp.strftime("%Y %m %d %H %M %S.%f").ljust(27, "0")
                    epoch_satellites = []

                    sats = r.group('sat1').strip()
                    # Number of Satellites
                    nos = int(r.group("nos"))
                    if nos == 0:
                        continue

                    additional_lines = int((nos - 1) / 12 % 12)
                    for j in range(additional_lines):
                        line = handler.readline()
                        r2 = self._get_dateline_short_re().search(line)
                        if r2 is not None:
                            sats += r2.group("sat2").strip()

                    # Get Observation Data
                    satellites = []
                    for j in range(nos):
                        sat_num = sats[(3 * j):(3 * (j + 1))]
                        self.add_satellite(sat_num)

                        raw_obs = ""
                        for k in range(1 + int(len(self.header.observation_types) / 5)):
                            raw_obs = "%s%s" % (
                                raw_obs,
                                self.prepare_line(handler.readline()),
                            )

                        satellites.append(
                            self.read_satellite(sat_id=sat_num, line=raw_obs)
                        )

                    rinex_epoch = RinexEpoch(
                        timestamp=datetime.datetime.strptime(
                            timestamp.strftime("%FT%TZ"), cc.RNX_FORMAT_DATETIME),
                        observation_types=self.header.observation_types,
                        satellites=satellites,
                        rcv_clock_offset=self.header.rcv_clock_offset
                    )
                    self.rinex_epochs.append(rinex_epoch)

            logger.debug("Successfully read data")
            

class Rinex3ObsReader(RinexObsReader):
    """RINEX 3 observation reader with optimized parsing.

    Args:
        datadict: {
            "epochs": [
                {
                    "id": "YYYY-mm-ddTHH:MM:SSZ",
                    "satellites": [
                        {
                            "id": "[GR][0-9]{2},
                            "observations": {
                                "[CLSPD][1258][ACPQW]": {
                                    "value": ..,
                                    "lli": ..,
                                    "ss": ..
                                }
                            }{1,}
                        }
                    ]
                },
                {
                    "id": "..."
                    "satellites": [..]
                },
                {..}
            ]
        }
    """

    RINEX_FORMAT = 3
    RINEX_HEADER_CLASS = Rinex3ObsHeader
    RINEX_DATELINE_REGEXP = cc.RINEX3_DATELINE_REGEXP
    RINEX_DATELINE_REGEXP_SHORT = cc.RINEX3_DATELINE_REGEXP
    RINEX_SATELLITES_REGEXP = cc.RINEX3_SATELLITES_REGEXP
    RINEX_FILE_NAME_REGEX = cc.RINEX3_FORMAT_FILE_NAME
    
    # Cached compiled regex patterns for performance
    _dateline_re = None
    _data_obs_re = None
    _obs_field_re = None
    
    @classmethod
    def _get_dateline_re(cls):
        """Get cached compiled dateline regex."""
        if cls._dateline_re is None:
            cls._dateline_re = re.compile(cls.RINEX_DATELINE_REGEXP)
        return cls._dateline_re
    
    @classmethod
    def _get_data_obs_re(cls):
        """Get cached compiled data observation regex."""
        if cls._data_obs_re is None:
            cls._data_obs_re = re.compile(cc.RINEX3_DATA_OBSEVATION_REGEXP)
        return cls._data_obs_re
    
    @classmethod
    def _get_obs_field_re(cls):
        """Get cached compiled observation field regex."""
        if cls._obs_field_re is None:
            cls._obs_field_re = re.compile(cc.RINEX3_DATA_OBSERVATION_FIELD_REGEXP)
        return cls._obs_field_re

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a RINEX 3 observation reader."""
        super().__init__(**kwargs)


    def set_rinex_obs_file(self, rinex_obs_file: str) -> None:
        self.rinex_obs_file = rinex_obs_file

        if not self.is_valid_filename(
            os.path.basename(self.rinex_obs_file), self.header.format_version):
            raise ValueError(
                f"Invalid RINEX filename for version {self.header.format_version}: "
                f"{os.path.basename(self.rinex_obs_file)}"
            )
        m = re.match(self.RINEX_FILE_NAME_REGEX, os.path.basename(self.rinex_obs_file))

        d = m.groupdict()
        self.station = d["station"]
        self.doy = int(d["doy"])
        self.year = int(d["year4"])
        self.file_period = d["file_period"]
        self.rinex_file_sequence = -1  # g[6]

        self.rinex_obs_file = rinex_obs_file

        self.backup_epochs = []

    @staticmethod
    def is_valid_filename(filename: str, rinex_version: int | float = 3):
        """
        Checks if filename is rinex conform
        """
        rinex_version = float(rinex_version)
        if rinex_version >= 3.0:
            filename_regex = Rinex3ObsReader.RINEX_FILE_NAME_REGEX
        else:
            return False
        m = re.match(filename_regex, filename)
        return m is not None

    def read_data_to_dict(self) -> None:
        """
        """
        with open(self.rinex_obs_file, "r") as handler:
            i = 0
            header_reached = False
            while True:
                line = handler.readline()
                i += 1

                if "END OF HEADER" in line:
                    logger.debug("End of Header Reached")
                    header_reached = True

                if not header_reached:
                    continue

                # Check for END_OF_FILE
                if line == "":
                    break

                # Get DateLine
                r = self._get_dateline_re().search(line)
                if not r:
                    continue

                # logger.debug("Found Date")
                timestamp = datetime.datetime(
                    int(r.group("year4")),
                    int(r.group("month")),
                    int(r.group("day")),
                    int(r.group("hour")),
                    int(r.group("minute")),
                    int(float(r.group("second")))
                )

                epoch_flag = r.group("epoch_flag")
                if epoch_flag not in ["0", "1"]:
                    logger.info("Special event: {}".format(epoch_flag))

                # Number of Satellites
                nos = int(r.group("num_of_sats"))

                satellites = []
                for _ in range(nos):
                    sat_line = handler.readline()
                    i += 1
                    epoch_sat = self.read_epoch_satellite(sat_line)
                    if epoch_sat:
                        satellites.append(epoch_sat)
                    else:
                        logger.debug("No Data")

                rinex_epoch = RinexEpoch(
                    timestamp=timestamp,
                    observation_types=self.header.sys_obs_types,
                    satellites=satellites,
                    rcv_clock_offset=self.header.rcv_clock_offset
                )
                # if rinex_epoch.is_valid():
                self.rinex_epochs.append(rinex_epoch)

        logger.debug("Successfully read data")

    def read_epoch_satellite(self, line: str) -> Satellite | None:
        """Parse satellite observation data from epoch line.
        
        Args:
            line: Raw line containing satellite observations.
            
        Returns:
            Dictionary with satellite number and Satellite object.
        """
        sat_data = self._get_data_obs_re().search(line)
        # Get Observation Data
        if sat_data is not None:
            sat_num = sat_data.group("sat_num")
            self.add_satellite(sat_num)
            return self.read_satellite(sat_id=sat_num, line=line)
        return None

    def read_satellite(self, sat_id: str, line: str) -> Satellite:
        """
        Parses trough rnx observation and creates Satellite object. Referring to the RINEX Handbook 3.03
        
        Args:
            sat_id: str satellite number/name
            line: str rnx line containing observations
        Returns:
            Satellite: Satellite object with Observation objects
        """
        observations = []
        try:
            sat_sys = sat_id[0]
            m = self._get_data_obs_re().match(line)
    
            if m:
                ofp = self._get_obs_field_re()
                obs_raw = [line[3+i*16:3+(i+1)*16] for i in range((len(line)-3) // 16)] + \
                    [line[3+((len(line)-3)//16)*16:]]
                for i, obs_field in enumerate(obs_raw):
                    if i >= len(self.header.sys_obs_types[sat_sys]):
                        break
                    
                    obs_code = self.header.sys_obs_types[sat_sys][i]
                    obs_value = None
                    obs_lli = None
                    obs_ssi = 0
                    
                    r = ofp.match(obs_field)
                    if r:
                        rd = r.groupdict()
                        obs_value = float(rd["value"])
                        obs_ssi = 0 if not str(rd["ssi"]).isnumeric() else int(rd["ssi"])
                        obs_lli = None if not str(rd["lli"]).isnumeric() else int(rd["lli"])
                    
                    if obs_value is not None:
                        observations.append(Observation(
                            code=obs_code,
                            value=obs_value,
                            lli=obs_lli,
                            ss=obs_ssi
                        ))
        except Exception as e:
            traceback.print_exc()
            raise(e)
        
        return Satellite(sat_id, observations)
