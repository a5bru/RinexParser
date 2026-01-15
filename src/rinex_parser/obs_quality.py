#!/usr/bin/env python
"""RINEX observation quality checking and analysis module.

Provides functionality to assess data quality, detect gaps, and generate
quality reports for RINEX observation files.
"""

import os
import time
import datetime
from typing import Any, Dict, Generator, List

from rinex_parser import constants as cc
from rinex_parser.logger import logger
from rinex_parser.obs_epoch import RinexEpoch, Satellite, Observation, ts_epoch_to_time

class RinexQuality:
    """Quality assessment and analysis for RINEX observation data.
    
    Provides methods to validate epochs, detect gaps, and generate
    quality reports for RINEX observation files.
    """
    
    RINEX_PERIOD_UNITS = {
        "D": 60 * 60 * 24,
        "H": 60 * 60,
        "M": 60,
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the RINEX quality checker.
        
        Args:
            rinex_format: RINEX format version (2 or 3, default: 3).
        """
        self.rinex_format = kwargs.get("rinex_format", 3)

    def filter_by_observation_descriptor(
        self,
        epoch_satellites: List[Dict[str, Any]] | List[Satellite],
        observation_descriptor: str,
        satellite_system: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Filter satellites by observation descriptor and system.
        
        Args:
            epoch_satellites: List of satellite observations (dict or Satellite objects).
            observation_descriptor: Observation type to filter (e.g., "L1", "C1C").
            satellite_system: Satellite system ID (e.g., "G", "R", "E").
            
        Yields:
            dict: Satellite data matching the filter criteria.
        """
        for satellite in epoch_satellites:
            # Support both dict and Satellite object
            if isinstance(satellite, dict):
                sat_id = satellite.get("id", "")
                observations = satellite.get("observations", {})
            else:
                sat_id = satellite.id
                # Convert list of Observation objects to dict
                if isinstance(satellite.observations, list):
                    observations = {obs.code: obs.value for obs in satellite.observations}
                else:
                    observations = satellite.observations
            
            if sat_id and sat_id[0] == satellite_system:
                for obs_code in observations:
                    if obs_code == observation_descriptor or (
                        self.rinex_format == 3 and obs_code.startswith(observation_descriptor)
                    ):
                        yield satellite
                        break

    def is_valid_epoch(
        self,
        epoch: RinexEpoch,
        satellite_systems=["G"],
        observation_descriptors=["L1", "L2"],
        satellites=5,
    ):
        """Check if epoch meets validity criteria.
        
        Default criteria:
        - Contains GPS satellite system
        - Contains L1 and L2 observations
        - At least 5 satellites within each system
        
        Args:
            epoch: Epoch data dictionary or RinexEpoch object containing satellites.
            satellite_systems: List of required satellite systems (default: ["G"]).
            observation_descriptors: List of required observations (default: ["L1", "L2"]).
            satellites: Minimum number of satellites required (default: 5).
            
        Returns:
            bool: True if epoch meets all criteria, False otherwise.
        """
        
    @staticmethod
    def _build_datadict_from_reader(reader) -> Dict[str, Any]:
        """Build datadict structure from reader's rinex_epochs.
        
        Args:
            reader: RinexObsReader instance with rinex_epochs.
            
        Returns:
            dict: Datadict structure compatible with quality methods.
        """
        from rinex_parser import constants as cc
        
        datadict = {
            "epochs": [],
            "fileName": reader.rinex_obs_file,
            "year4": getattr(reader, 'year', 0),
            "doy": getattr(reader, 'doy', 0),
            "markerName": getattr(reader, 'station', reader.header.marker_name),
            "epochInterval": reader.header.interval,
            "epochFirst": None,
            "epochLast": None
        }
        
        # Add epochPeriod for RINEX 3
        if hasattr(reader, 'file_period'):
            datadict["epochPeriod"] = reader.file_period
        else:
            datadict["epochPeriod"] = "01D"
        
        # Convert rinex_epochs to dict format
        for epoch in reader.rinex_epochs:
            # Convert Satellite objects to dicts
            satellites = []
            for sat in epoch.satellites:
                if hasattr(sat, 'id'):
                    # It's a Satellite object with observations as a list
                    obs_dict = {}
                    if isinstance(sat.observations, list):
                        # observations is a list of Observation objects
                        for obs_obj in sat.observations:
                            if hasattr(obs_obj, 'code') and hasattr(obs_obj, 'value'):
                                obs_dict[obs_obj.code] = obs_obj.value
                    elif isinstance(sat.observations, dict):
                        # observations is already a dict
                        for obs_code, obs_obj in sat.observations.items():
                            if hasattr(obs_obj, 'value'):
                                obs_dict[obs_code] = obs_obj.value
                            else:
                                obs_dict[obs_code] = obs_obj
                    
                    sat_dict = {
                        "id": sat.id,
                        "observations": obs_dict
                    }
                    satellites.append(sat_dict)
                else:
                    # Assume it's already a dict
                    satellites.append(sat)
            
            epoch_dict = {
                "id": epoch.timestamp.strftime(cc.RNX_FORMAT_DATETIME),
                "satellites": satellites
            }
            datadict["epochs"].append(epoch_dict)
        
        # Set first/last
        if datadict["epochs"]:
            datadict["epochFirst"] = datadict["epochs"][0]["id"]
            datadict["epochLast"] = datadict["epochs"][-1]["id"]
        
        return datadict
      
    def is_valid_epoch_legacy(
        self,
        epoch: Dict[str, Any] | RinexEpoch,
        satellite_systems: List[str] | None = None,
        observation_descriptors: List[str] | None = None,
        satellites: int = 5,
    ) -> bool:
        """Check if epoch meets validity criteria.
        
        Default criteria:
        - Contains GPS satellite system
        - Contains L1 and L2 observations
        - At least 5 satellites within each system
        
        Args:
            epoch: Epoch data dictionary or RinexEpoch object containing satellites.
            satellite_systems: List of required satellite systems (default: ["G"]).
            observation_descriptors: List of required observations (default: ["L1", "L2"]).
            satellites: Minimum number of satellites required (default: 5).
            
        Returns:
            bool: True if epoch meets all criteria, False otherwise.
        """
        if satellite_systems is None:
            satellite_systems = ["G"]
        if observation_descriptors is None:
            observation_descriptors = ["L1", "L2"]
        
        # Support both dict and object formats
        if isinstance(epoch, dict):
            epoch_satellites = epoch.get("satellites", [])
        else:
            epoch_satellites = epoch.satellites
            
        for observation_descriptor in observation_descriptors:
            for satellite_system in satellite_systems:
                i_test = self.filter_by_observation_descriptor(
                    epoch_satellites=epoch_satellites,
                    observation_descriptor=observation_descriptor,
                    satellite_system=satellite_system,
                )
                if len(list(i_test)) < satellites:
                    return False
        return True

    @staticmethod
    def get_datetime_utc(epoch_str: str) -> datetime.datetime:
        """Parse datetime from RINEX format string.
        
        Args:
            epoch_str: Datetime string in RINEX format.
            
        Returns:
            datetime.datetime: Parsed datetime object.
        """
        return datetime.datetime.strptime(epoch_str, cc.RNX_FORMAT_DATETIME)

    @staticmethod
    def get_session_code(second_of_day: int) -> str:
        """Get RINEX session code for seconds of day.
        
        Args:
            second_of_day: Second of day (0..86399).
            
        Returns:
            str: Session code character (A..X).
        """
        i = int(second_of_day / 3600)
        return chr(i + 65)

    def do_prepare_datadict(self, reader_or_datadict, gapsize: int = 5):
        """Prepare and analyze epoch data for quality reporting.
        
        Processes epochs, identifies gaps, and computes quality metrics.
        
        Args:
            reader_or_datadict: RinexObsReader instance or legacy datadict.
            gapsize: Minimum gap size in epochs to report.
            
        Returns:
            dict: Quality analysis data with gap information.
        """
        # Support both reader objects and legacy datadict
        if hasattr(reader_or_datadict, 'rinex_epochs'):
            datadict = self._build_datadict_from_reader(reader_or_datadict)
        else:
            datadict = reader_or_datadict
        
        if not datadict.get("epochs"):
            logger.warning("No Epoch parsed")
            return {}

        # Set first/last epoch times if missing
        for zeitpunkt in ["epochFirst", "epochLast"]:
            if zeitpunkt not in datadict or datadict.get(zeitpunkt) is None:
                datadict[zeitpunkt] = datetime.datetime.now().strftime(cc.RNX_FORMAT_DATETIME)
        
        dt0 = datetime.datetime.strptime(
            f"{datadict['year4']}-{datadict['doy']:03d}",
            "%Y-%j"
        )

        if "epochPeriod" not in datadict:
            datadict["epochPeriod"] = "01D"  # Daily files as default

        period_count = int(datadict["epochPeriod"][:2])
        period_unit = datadict["epochPeriod"][-1]

        period_seconds = int(
            self.RINEX_PERIOD_UNITS[period_unit]
            * period_count
            / datadict["epochInterval"]
        )

        chkdoy = {
            "filename": os.path.basename(datadict["fileName"]),
            "station": datadict["markerName"],
            "year": datadict["year4"],
            "doy": datadict["doy"],
            "dom": dt0.day,
            "month": dt0.month,
            "gaps": [],
            "epoch_interval": int(datadict["epochInterval"]),
            "epochs_valid": 0,
            "epochs_max": int(period_seconds),
            "epochs_missing": 0,
            "epoch_first": datadict["epochFirst"],
            "epoch_last": datadict["epochLast"],
        }

        dt_epoch_first = datetime.datetime.strptime(
            chkdoy["epoch_first"],
            cc.RNX_FORMAT_DATETIME
        )
        dt_epoch_last = datetime.datetime.strptime(
            chkdoy["epoch_last"],
            cc.RNX_FORMAT_DATETIME
        )
        total_seconds = int((dt_epoch_last - dt_epoch_first).total_seconds())

        # Filter valid epochs
        epoch_valid = []
        for epoch in datadict["epochs"]:
            if not self.is_valid_epoch(epoch):
                continue
            if epoch["id"] not in epoch_valid:
                epoch_valid.append(epoch["id"])

        chkdoy["epochs_valid"] = len(epoch_valid)
        
        # Sort and deduplicate epochs
        epochs = []
        for epoch in epoch_valid:
            temp_utc = self.get_datetime_utc(epoch_str=epoch)
            if temp_utc not in epochs:
                epochs.append(temp_utc)
        epochs = sorted(epochs)

        # Detect gaps between epochs
        gaps_less = 0
        gaps_more = 0
        for i in range(len(epochs) - 1):
            epoch_delta = int((epochs[i + 1] - epochs[i]).total_seconds())
            if epoch_delta > chkdoy["epoch_interval"]:
                chkdoy["gaps"].append({
                    "gap_begin": epochs[i].strftime(cc.RNX_FORMAT_DATETIME),
                    "gap_end": epochs[i + 1].strftime(cc.RNX_FORMAT_DATETIME),
                    "gap_epoch_count": epoch_delta / chkdoy["epoch_interval"],
                    "gap_duration": epoch_delta,
                })

                if epoch_delta <= gapsize * chkdoy["epoch_interval"]:
                    gaps_less += 1
                else:
                    gaps_more += 1

        chkdoy.update(
            {
                "gaps_less": gaps_less,
                "gaps_more": gaps_more,
                "gapsize": gapsize,
                "date": dt0.strftime(cc.RNX_FORMAT_DATE),
                "epoch_first": dt_epoch_first.strftime(cc.RNX_FORMAT_DATETIME),
                "epoch_last": dt_epoch_last.strftime(cc.RNX_FORMAT_DATETIME),
                "total_secs": int(total_seconds),
            }
        )

        return chkdoy

    def get_rinex_availability_as_dict(
        self,
        reader_or_datadict,
        gapsize: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get RINEX availability data as list of dictionaries.
        
        Args:
            reader_or_datadict: RinexObsReader instance or legacy datadict.
            gapsize: Minimum gap size in epochs (default: 5).
            
        Returns:
            list: List of availability windows with time/station information.
        """
        # Support both reader objects and legacy datadict
        if hasattr(reader_or_datadict, 'rinex_epochs'):
            datadict = self._build_datadict_from_reader(reader_or_datadict)
        else:
            datadict = reader_or_datadict
        
        chkdoy = self.do_prepare_datadict(datadict, gapsize)
        rinex_v = []
        d = {
            "date": chkdoy["date"],
            "station_name": chkdoy["station"],
            "second_from": 0,
            "second_until": 1,
            "epoch_interval": chkdoy["epoch_interval"],
            "session_code": "A",
            "is_online": 1
        }

        window_list = []
        window = {"valid_from": chkdoy["epoch_first"], "valid_until": ""}
        for gap in chkdoy["gaps"]:
            window["valid_until"] = gap["gap_begin"]
            window_list.append(dict(**window))
            window["valid_from"] = gap["gap_end"]
        window["valid_until"] = chkdoy["epoch_last"]
        window_list.append(dict(**window))

        for w in window_list:
            w_from = datetime.datetime.strptime(
                w["valid_from"],
                cc.RNX_FORMAT_DATETIME
            )
            w_from_c = datetime.datetime(w_from.year, w_from.month, w_from.day)
            w_until = datetime.datetime.strptime(
                w["valid_until"],
                cc.RNX_FORMAT_DATETIME
            )
            w_until_c = datetime.datetime(
                w_until.year,
                w_until.month,
                w_until.day
            )
            w_delta = w_until - w_from
            w_delta_hours = w_delta.total_seconds() / 3600.0
            d["second_from"] = int((w_from - w_from_c).total_seconds())

            # Split by hours
            if w_delta_hours > 1:
                for i in range(int(w_delta_hours)):
                    d["second_until"] = int(
                        (w_from.hour + i + 1) * 3600
                        - chkdoy["epoch_interval"]
                    )
                    d["second_from"] = int(
                        d["second_until"] + chkdoy["epoch_interval"]
                    )
                    d["session_code"] = self.get_session_code(d["second_from"])
                    rinex_v.append(dict(**d))
            else:
                d["second_until"] = int((w_until - w_until_c).total_seconds())
                d["session_code"] = self.get_session_code(d["second_from"])
                rinex_v.append(dict(**d))

        return rinex_v

    def get_rinex_availability_as_str(
        self,
        availability_dict: List[Dict[str, Any]],
    ) -> str:
        """Format availability dictionary as a string report.
        
        Args:
            availability_dict: List of availability window dictionaries.
            
        Returns:
            str: Formatted availability report.
        """
        rinex_v = []
        for d in availability_dict:
            rinex_v_i = (
                "{date};{station_name};{second_from};{second_until};"
                "{epoch_interval};{session_code};{is_online}"
            ).format(**d)
            rinex_v.append(rinex_v_i)
        return "\n".join(rinex_v)

    def get_rinex_availability(
        self,
        reader_or_datadict,
        gapsize: int = 5,
    ) -> str:
        """Get RINEX availability report as formatted string.
        
        Format: 'YYYY-MM-DD;STATION;SECOND_BEGIN;SECOND_END;EPOCH_INTERVAL;SESSION_CODE;IS_ONLINE'
        
        Args:
            reader_or_datadict: RinexObsReader instance or legacy datadict.
            gapsize: Minimum gap size in epochs (default: 5).
            
        Returns:
            str: Formatted availability report.
        """
        rinex_v_dict = self.get_rinex_availability_as_dict(reader_or_datadict, gapsize)
        return self.get_rinex_availability_as_str(rinex_v_dict)

    def get_rinstat_as_dict(
        self,
        reader_or_datadict,
        gapsize: int = 5,
    ) -> Dict[str, Any]:
        """Get RINEX statistics as a dictionary.
        
        Args:
            reader_or_datadict: RinexObsReader instance or legacy datadict.
            gapsize: Minimum gap size in epochs (default: 5).
            
        Returns:
            dict: Statistics dictionary with gap details.
        """
        # Support both reader objects and legacy datadict
        if hasattr(reader_or_datadict, 'rinex_epochs'):
            datadict = self._build_datadict_from_reader(reader_or_datadict)
        else:
            datadict = reader_or_datadict
        
        chkdoy = self.do_prepare_datadict(datadict, gapsize)
        chkdoy["gaps_count"] = len(chkdoy["gaps"])
        chkdoy["epoch_first"] = datetime.datetime.strptime(
            chkdoy["epoch_first"],
            cc.RNX_FORMAT_DATETIME
        ).strftime(cc.RNX_FORMAT_TIME)
        chkdoy["epoch_last"] = datetime.datetime.strptime(
            chkdoy["epoch_last"],
            cc.RNX_FORMAT_DATETIME
        ).strftime(cc.RNX_FORMAT_TIME)
        chkdoy["gaps_prepared"] = []

        for gap in chkdoy["gaps"]:
            gap_dict = {
                "ge": int(gap["gap_epoch_count"]) - 1,
                "gs": gap["gap_duration"] - chkdoy["epoch_interval"],
                "gf": datetime.datetime.strptime(
                    gap["gap_begin"],
                    cc.RNX_FORMAT_DATETIME
                ) + datetime.timedelta(seconds=chkdoy["epoch_interval"]),
                "gu": datetime.datetime.strptime(
                    gap["gap_end"],
                    cc.RNX_FORMAT_DATETIME
                ),
            }
            chkdoy["gaps_prepared"].append(gap_dict)

        return chkdoy

    def get_rinstat_as_str(self, rinstat_dict: Dict[str, Any]) -> str:
        """Format statistics dictionary as a report string.
        
        Args:
            rinstat_dict: Statistics dictionary.
            
        Returns:
            str: Formatted statistics report.
        """
        rinstat_dict["gaps_list"] = ""
        for gap in rinstat_dict["gaps_prepared"]:
            gap_str = "--- GAP:  {gf} - {gu}  {gs:10.1f} s {ge:10d} e".format(
                **gap
            )
            rinstat_dict["gaps_list"] += f"\n{gap_str}"

        # Report
        return """+++ >>>   {filename}{gaps_list}
+++ RNX.SUM   {date} ({doy:03d})   {station}   {epoch_first} - {epoch_last}   {total_secs} s   {epoch_interval} s {gaps_count:7d}
+++    #maxepo #aepoch #mepoch #gaps>{gapsize} #gaps<{gapsize}
+++      {epochs_max:5d}   {epochs_valid:5d}   {epochs_missing:5d}   {gaps_more:5d}   {gaps_less:5d}
+++ <<<""".format(
            **rinstat_dict
        )

    def get_rinstat_out(
        self,
        reader_or_datadict,
        gapsize: int = 5,
    ) -> str:
        """Generate RINEX statistics report.
        
        Creates a detailed report with gap analysis and statistics.
        
        Args:
            reader_or_datadict: RinexObsReader instance or legacy datadict.
            gapsize: Minimum gap size in epochs to report (default: 5).
            
        Returns:
            str: Formatted statistics report.
        """
        chkdoy = self.get_rinstat_as_dict(reader_or_datadict, gapsize)
        return self.get_rinstat_as_str(chkdoy)

    def to_json(self, rinstat_dict: Dict[str, Any]) -> str:
        """Convert RINEX statistics dictionary to JSON string.
        
        Args:
            rinstat_dict: Statistics dictionary.
            
        Returns:
            str: JSON-formatted statistics report.
        """
        import json
        return json.dumps(rinstat_dict, indent=None)
