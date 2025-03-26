"""
Created on Oct 25, 2016


@author: jurgen
"""

import datetime
import os
import re
import traceback
from typing import List

from rinex_parser import constants as cc

from rinex_parser.logger import logger
from rinex_parser.obs_header import Rinex2ObsHeader, Rinex3ObsHeader, RinexObsHeader
from rinex_parser.obs_epoch import RinexEpoch, ts_epoch_to_list, get_second_of_day


__updated__ = "2016-11-16"


class RinexObsReader(object):
    """
    Doc of Class RinexObsReader

    Args:
        datadict: {
            "epochs": [
                {
                    "id": "YYYY-mm-ddTHH:MM:SSZ",
                    "satellites": [
                        {
                            "id": "<Satellite Number>",
                            "observations": {
                                "<Observation Descriptor>": {
                                    "value": ..,
                                    "lli": ..,
                                    "ss": ..
                                }
                            }
                        },
                        {
                            "id": "...",
                            "observations": {...}
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

    RINEX_HEADER_CLASS = RinexObsHeader

    def __init__(self, **kwargs):
        self.header = self.RINEX_HEADER_CLASS()
        self.interval_filter: int = kwargs.get("interval_filter", 0)
        self.backup_epochs = []
        self.rinex_obs_file = kwargs.get("rinex_obs_file", "")
        self.rinex_epochs: List[RinexEpoch] = kwargs.get("rinex_epochs", [])
        self.rinex_date = kwargs.get("rinex_date", datetime.datetime.now().date())
        self.filter_on_read: bool = kwargs.get("filter_on_read", True)
        self.found_obs_types = {}
        self.filter_sat_sys: list = kwargs.get("filter_sat_sys", "").split(",")
        self.filter_sat_pnr: list = kwargs.get("filter_sat_pnr", "").split(",")
        self.filter_sat_obs: list = kwargs.get("filter_sat_obs", "").split(",")

    @staticmethod
    def get_start_time(file_sequence):
        """ """
        if file_sequence == "0":
            return datetime.time(0, 0)
        return datetime.time(ord(file_sequence.lower() - 97), 0)

    @staticmethod
    def get_epochs_possible(file_sequence, interval):
        """
        Get maximal epochs for rinex file sequence

        Args:
            file_sequence: str, [a-x0]
            interval: int, Rinex Epoch Interval

        Returns:
            int, Possible Epochs in File
        """
        ef = datetime.datetime.combine(
            datetime.date.today(), Rinex2ObsReader.get_start_time(file_sequence)
        )
        el = datetime.datetime.combine(
            datetime.date.today(), Rinex2ObsReader.get_end_time(file_sequence, interval)
        )
        return int((el - ef).total_seconds() / interval) + 1

    @staticmethod
    def prepare_line(line):
        new_line = line.replace("\r", "").replace("\n", "")
        if len(new_line) % 16 != 0:
            new_line += " " * (16 - len(new_line) % 16)
        return new_line

    @staticmethod
    def get_end_time(file_sequence, interval):
        """ """
        if file_sequence == "0":
            return datetime.time(23, 59, 60 - interval)
        return datetime.time(ord(file_sequence.lower() - 97), 59, 60 - interval)

    @staticmethod
    def is_valid_filename(filename, rinex_version=2):
        """
        Checks if filename is rinex conform
        """
        rinex_version = float(rinex_version)
        if (rinex_version < 3) & (rinex_version >= 2):
            filename_regex = Rinex2ObsReader.RINEX_FILE_NAME_REGEX
        elif rinex_version >= 3:
            filename_regex = Rinex3ObsReader.RINEX_FILE_NAME_REGEX
        else:
            return False
        return re.match(filename_regex, filename) is not None

    def set_rinex_obs_file(self, rinex_obs_file: str):
        raise NotImplementedError

    def correct_year2(self, year2):
        """
        Accourding to the RINEX Manual 2.10, chapter "6.5 2-digit Years"
        """
        if year2 < 80:
            return year2 + 2000
        else:
            return year2 + 1900

    # def do_thinning(self, interval):
    #     """ """
    #     thinned_epochs = [
    #         epoch
    #         for epoch in self.rinex_epochs
    #         if epoch.get_day_seconds() % interval == 0
    #     ]
    #     if len(self.backup_epochs) == 0:
    #         self.backup_epochs = self.rinex_epochs
    #     self.rinex_epochs = thinned_epochs

    # def undo_thinning(self):
    #     """ """
    #     self.rinex_epochs = self.backup_epochs
    #     self.backup_epochs = []

    def to_rinex2(self):
        """ """
        out = ""
        for rinex_epoch in self.rinex_epochs:
            out += "%s\n" % rinex_epoch.to_rinex2()
        return out

    def to_rinex3(
        self, use_raw: bool = False, sys_obs_types={}, sys_order: str = "CEGIJQRS"
    ) -> list[str]:
        """ """
        out = []
        for rinex_epoch in self.rinex_epochs:
            if not sys_obs_types:
                sys_obs_types = self.found_obs_types
            out += rinex_epoch.to_rinex3(
                observation_types=sys_obs_types, sat_sys_order=sys_order
            )
        return out

    def read_header(self, sort_obs_types=True):
        """ """
        header = []
        with open(self.rinex_obs_file, "r") as handler:
            for _, line in enumerate(handler):
                header.append(line)
                if "END OF HEADER" in line:
                    break
        self.header = self.RINEX_HEADER_CLASS.from_header(
            header_string="\n".join(header)
        )
        for sat_sys in self.header.sys_obs_types:
            self.found_obs_types[sat_sys] = list()

    def has_satellite_system(self, sat_sys):
        """
        Checks if Satellite Systems is present or not

        Args:
            sat_sys: str, Satellite System "GREJIS"

        Returns:
            bool, True, if Satellite System is present, else False
        """
        for epoch in self.rinex_epochs:
            if epoch.has_satellite_system(sat_sys):
                return True
        return False

    def update_header_obs(self):
        """
        Updates header information about first and last observation
        """

        # First and Last Observation
        self.header.first_observation = self.rinex_epochs[0].timestamp
        self.header.last_observation = self.rinex_epochs[-1].timestamp

    def read_satellite(self, sat_id, line):
        raise NotImplementedError

    def read_data_to_dict(self):
        raise NotImplementedError


class Rinex2ObsReader(RinexObsReader):
    """
    classdocs

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

    def __init__(self, **kwargs):
        """
        Constructor
        """
        super(Rinex2ObsReader, self).__init__(**kwargs)

    def set_rinex_obs_file(self, rinex_obs_file):
        self.rinex_obs_file = rinex_obs_file
        self.station_doy_session = os.path.basename(self.rinex_obs_file).split(".")[0]
        assert self.__class__.is_valid_filename(
            os.path.basename(self.rinex_obs_file), self.header.format_version
        )
        self.station = self.station_doy_session[:4]
        self.doy = int(self.station_doy_session[4:7])
        year2 = int(self.rinex_obs_file.split(".")[-1][:2])
        self.year = self.correct_year2(year2)

        self.rinex_file_sequence = self.station_doy_session[7]
        self.backup_epochs = []

    def read_satellite(self, sat_id, line):
        """
        Parses trough rnx observation and creates dict. Referring to the RINEX Handbook 2.10
        there are only up to 5 observation types per line. This method parses any line length

        Args:
            sat_id: str satellite number/name
            line: str rnx line containing observations
        Returns:
            dict: {sat_id: {otk1: otv1, otk2: otv2, ... otkn: otvn}}
        """

        sat_dict = {"id": sat_id, "observations": ()}
        for k in range(len(self.header.observation_types)):
            obs_type = self.header.observation_types[k]
            obs_col = line[(16 * k) : (16 * (k + 1))]
            obs_val = obs_col[:14].strip()

            if obs_val == "":
                obs_val = None
            else:
                float(obs_val)

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

            sat_dict["observations"][obs_type] = (obs_val, obs_lli, obs_ss)

        return sat_dict

    def read_data_to_dict(self):
        """ """
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
                r = re.search(self.RINEX_DATELINE_REGEXP, line)
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

                    sats = r.group("sat1").strip()
                    # Number of Satellites
                    nos = int(r.group("nos"))
                    if nos == 0:
                        continue

                    additional_lines = int((nos - 1) / 12 % 12)
                    for j in range(additional_lines):
                        line = handler.readline()
                        r2 = re.search(self.RINEX_DATELINE_REGEXP_SHORT, line)
                        if r2 is not None:
                            sats += r2.group("sat2").strip()

                    # Get Observation Data
                    for j in range(nos):
                        sat_num = sats[(3 * j) : (3 * (j + 1))]

                        raw_obs = ""
                        for k in range(1 + int(len(self.header.observation_types) / 5)):
                            raw_obs = "%s%s" % (
                                raw_obs,
                                self.prepare_line(handler.readline()),
                            )

                        epoch_satellites.append(
                            self.read_satellite(sat_id=sat_num, line=raw_obs)
                        )

                    rinex_epoch = RinexEpoch(
                        timestamp=epoch,
                        observation_types=self.header.observation_types,
                        satellites=epoch_satellites,
                        rcv_clock_offset=self.header.rcv_clock_offset,
                    )
                    self.rinex_epochs.append(rinex_epoch)
            logger.debug(f"Parsed data {self.rinex_obs_file}")


class Rinex3ObsReader(RinexObsReader):
    """
    classdocs

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

    def __init__(self, **kwargs):
        """
        Constructor, use the same as Rinex2ObsReader
        """
        super(Rinex3ObsReader, self).__init__(**kwargs)

    def set_rinex_obs_file(self, rinex_obs_file):
        self.rinex_obs_file = rinex_obs_file

        assert self.is_valid_filename(
            os.path.basename(self.rinex_obs_file), self.header.format_version
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
    def is_valid_filename(filename, rinex_version=3):
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

    def read_data_to_dict(self):
        """ """
        # SKIP HEADER
        with open(self.rinex_obs_file, "r") as handler:

            logger.debug(f"Parse Header {self.rinex_obs_file}")
            keep_running = True
            while keep_running:
                line = handler.readline()
                if "END OF HEADER" in line:
                    keep_running = False

            logger.debug(f"Parse Epochs {self.rinex_obs_file}")
            keep_running = True
            while keep_running:
                # Check for END_OF_FILE
                line = handler.readline()
                if line == "":
                    keep_running = False
                    continue
                # Get DateLine
                r = line.startswith(">")
                if not r:
                    continue

                # > 2025 03 16 00 00  0.0000000  0 37
                # y = line[2:6]
                # m = line[7:9]
                # d = line[10:12]
                H = line[13:15]
                M = line[16:18]
                S = line[18:30]
                if self.interval_filter > 0:
                    # updating the header entry INTERVAL
                    self.header.sampling = self.interval_filter
                    sec_of_day = int(H) * 3600
                    sec_of_day = int(M) * 60
                    sec_of_day = int(float(S))
                    if sec_of_day % self.interval_filter != 0:
                        continue

                e = line[31]
                n = line[32:35]
                epoch = line[2:29]

                epoch_satellites = []

                if e not in ["0", "1"]:
                    logger.info("Special event: {}".format(e))

                # Number of Satellites
                nos = int(n)

                raw = [line]

                for j in range(nos):
                    line = handler.readline()
                    epoch_sat = self.read_epoch_satellite(line)
                    if epoch_sat:
                        epoch_satellites.append(epoch_sat["sat_data"])
                    raw.append(line)

                rinex_epoch = RinexEpoch(
                    timestamp=epoch,
                    observation_types=self.header.sys_obs_types,
                    satellites=epoch_satellites,
                    rcv_clock_offset=self.header.rcv_clock_offset,
                    raw=raw,
                )
                self.rinex_epochs.append(rinex_epoch)

        if not self.header.interval and len(self.rinex_epochs) > 1:
            el1 = ts_epoch_to_list("> " + self.rinex_epochs[0].timestamp)
            el2 = ts_epoch_to_list("> " + self.rinex_epochs[1].timestamp)
            sd1 = get_second_of_day(el1[3], el1[4], el1[5])
            sd2 = get_second_of_day(el2[3], el2[4], el2[5])
            self.header.interval = sd2 - sd1
            logger.info(f"Set the epoch interval to {self.header.interval}")

        logger.debug(f"Parsed data {self.rinex_obs_file}")

    def read_epoch_satellite(self, line):
        """ """
        # sat_data = re.search(cc.RINEX3_DATA_OBSEVATION_REGEXP, line)
        sat_num = line[:3]

        # Get Observation Data
        if sat_num is not None:
            d = {
                "sat_num": sat_num,
                "sat_data": self.read_satellite(sat_id=sat_num, line=line),
            }
            if d["sat_data"]["observations"]:
                return d
        return {}

    def read_satellite(self, sat_id, line):
        """
        Parses trough rnx observation and creates dict. Referring to the RINEX Handbook 3.03

        Args:
            sat_id: str satellite number/name
            line: str rnx line containing observations
        Returns:
            dict: {
                id: "sat_id",
                observations: {otk1: otv1, otk2: otv2, ... otkn: otvn}
            }
        """
        sat_dict = {"id": sat_id, "observations": {}}
        try:
            sat_sys = sat_id[0]
            chunk = line[3:]

            # Filter by Satellite System
            if sat_sys in self.filter_sat_sys:
                return sat_dict

            # Filter by Satellite PNR
            if sat_id in self.filter_sat_pnr:
                return sat_dict

            for obs_type in self.header.sys_obs_types[sat_sys]:

                # Filter System Obs Type
                sys_obs_type = f"{sat_sys}{obs_type[1:]}"
                if sys_obs_type in self.filter_sat_obs:
                    continue

                if not chunk:
                    break

                val = lli = ssi = None
                try:
                    val = chunk[:14]
                    chunk = chunk[14:]
                    lli = chunk[0]
                    chunk = chunk[1:]
                    ssi = chunk[0]
                    chunk = chunk[1:]
                except:
                    pass

                if val.strip() == "":
                    continue

                if (obs_type) not in self.found_obs_types[sat_sys]:
                    self.found_obs_types[sat_sys].append(obs_type)
                sat_dict["observations"][obs_type] = [val, lli, ssi]

        except Exception as e:
            traceback.print_exc()
            raise (e)

        return sat_dict
