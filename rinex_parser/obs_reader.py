'''
Created on Oct 25, 2016


@author: jurgen
'''
import datetime
import os
import re

from rinex_parser import constants as cc

from rinex_parser.ext.convertdate.convertdate import year_doy
from rinex_parser.logger import logger
from rinex_parser.obs_header import Rinex2ObsHeader, Rinex3ObsHeader, RinexObsHeader
from rinex_parser.obs_epoch import RinexEpoch


# from src.common.logging import logger
__updated__ = "2016-11-16"


class RinexObsReaderFactory(object):
    """

    """

    def create_obs_reader_by_version(self, rinex_version=2):
        """
        :returns: RinexObsReader
        """
        if rinex_version == 2:
            return Rinex2ObsReader
        elif rinex_version == 3:
            return Rinex3ObsReader
        assert rinex_version not in [2, 3]

    def create_osb_reader_by_file(self, rinex_file):
        """
        :returns: RinexObsReader
        """
        return Rinex3ObsReader


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
        self.epochs = []
        self.datadict = {}
        self.backup_epochs = []
        self.rinex_obs_file = kwargs.get("rinex_obs_file", "")
        self.rinex_epochs = kwargs.get("rinex_epochs", [])
        self.rinex_date = kwargs.get(
            "rinex_date", datetime.datetime.now().date())

    @staticmethod
    def get_start_time(file_sequence):
        """
        """
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
            datetime.date.today(), Rinex2ObsReader.get_start_time(file_sequence))
        el = datetime.datetime.combine(
            datetime.date.today(), Rinex2ObsReader.get_end_time(file_sequence, interval))
        return int((el - ef).total_seconds() / interval) + 1

    @staticmethod
    def prepare_line(line):
        new_line = line.replace("\r", "").replace("\n", "")
        if len(new_line) % 16 != 0:
            new_line += " " * (16 - len(new_line) % 16)
        return new_line

    @staticmethod
    def get_end_time(file_sequence, interval):
        """
        """
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
        elif (rinex_version >= 3):
            filename_regex = Rinex3ObsReader.RINEX_FILE_NAME_REGEX
        else:
            return False
        return re.match(filename_regex, filename) is not None

    def correct_year2(self, year2):
        """
        Accourding to the RINEX Manual 2.10, chapter "6.5 2-digit Years"
        """
        if year2 < 80:
            return year2 + 2000
        else:
            return year2 + 1900

    def do_thinning(self, interval):
        """
        """
        thinned_epochs = [epoch for epoch in self.rinex_epochs
                          if epoch.get_day_seconds() % interval == 0]
        if len(self.backup_epochs) == 0:
            self.backup_epochs = self.rinex_epochs
        self.rinex_epochs = thinned_epochs

    def undo_thinning(self):
        """
        """
        self.rinex_epochs = self.backup_epochs
        self.backup_epochs = []

    def to_rinex2(self):
        """

        """
        out = ""
        for rinex_epoch in self.rinex_epochs:
            out += "%s\n" % rinex_epoch.to_rinex2()
        return out

    def to_rinex3(self):
        """

        """
        out = ""
        for rinex_epoch in self.rinex_epochs:
            out += "%s\n" % rinex_epoch.to_rinex3()
        return out

    def read_header(self, sort_obs_types=True):
        """
        """
        header = ""
        with open(self.rinex_obs_file, "r") as handler:
            for i, line in enumerate(handler):
                header += line
        self.header = self.RINEX_HEADER_CLASS.from_header(header_string=header)

    def add_satellite(self, satellite):
        """
        Adds satellite to satellite list if not already added

        Args:
            satellite: Satid as str regexp '[GR][ \d]{2}'
        """
        if satellite not in  self.header.satellites:
            self.header.satellites[satellite] = 0
        self.header.satellites[satellite] += 1

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

    def add_epoch(self, epoch):
        """
        Adds epoch to epoch list if not already added

        Args:
            epoch: Epoch as str '%Y-%m-%dT%H:%M:%SZ'
        """
        if epoch not in self.epochs:
            self.epochs.append(epoch)


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
        '''
        Constructor
        '''
        super(Rinex2ObsReader, self).__init__(**kwargs)

    def set_rinex_obs_file(self, rinex_obs_file):
        self.rinex_obs_file = rinex_obs_file
        self.station_doy_session = os.path.basename(
            self.rinex_obs_file).split(".")[0]
        assert self.__class__.is_valid_filename(
            os.path.basename(self.rinex_obs_file), self.header.format_version)
        self.station = self.station_doy_session[:4]
        self.doy = int(self.station_doy_session[4:7])
        year2 = int(self.rinex_obs_file.split(".")[-1][:2])
        self.year = self.correct_year2(year2)

        self.rinex_file_sequence = self.station_doy_session[7]
        self.epochs = []
        self.datadict = {}
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

        sat_dict = {"id": sat_id, "observations": {}}
        for k in range(len(self.header.observation_types)):
            obs_type = self.header.observation_types[k]
            obs_col = line[(16 * k):(16 * (k + 1))]
            # print("obs_col: '{}'".format(obs_col))
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

            sat_dict["observations"].update(
                {
                    obs_type + "_value": obs_val,
                    obs_type + "_lli": obs_lli,
                    obs_type + "_ss": obs_ss
                }
            )
        # print(sat_dict)
        return sat_dict

    def read_data_to_dict(self):
        """
        """
        # SKIP HEADER
        with open(self.rinex_obs_file, "r") as handler:
            for i, line in enumerate(handler):
                if 'END OF HEADER' in line:
                    break
            del i
            i = 0
            rinex_obs = {
                "epochs": [], 
                "fileName": self.rinex_obs_file,
                "year4": self.year,
                "doy": self.doy,
                "markerName": self.header.marker_name,
                "epochInterval": self.header.interval,
                "epochFirst": None,
                "epochLast": None
            } 
            with open(self.rinex_obs_file, "r") as handler:
                while True:

                    # Check for END_OF_FILE
                    line = handler.readline()
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
                            int(float(r.group("second")))
                        )
                        epoch = timestamp.strftime("%FT%TZ")
                        self.add_epoch(epoch)

                        rnx_epoch = {
                            "id": epoch,
                            "satellites": [],
                        }
                        sats = r.group('sat1').strip()
                        # Number of Satellites
                        nos = int(r.group("nos"))
                        # print("# of Sats: '%d'" % nos)
                        if nos == 0:
                            continue

                        additional_lines = int((nos-1)/12 % 12)
                        for j in range(additional_lines):
                            line = handler.readline()
                            r2 = re.search(self.RINEX_DATELINE_REGEXP_SHORT, line)
                            if r2 is not None:
                                sats += r2.group('sat2').strip()

                        # Get Observation Data
                        for j in range(nos):
                            i += 1
                            sat_num = sats[(3 * j):(3 * (j + 1))]
                            self.add_satellite(sat_num)

                            raw_obs = ""
                            for k in range(1 + int(len(self.header.observation_types) / 5)):
                                raw_obs = "%s%s" % (
                                    raw_obs, self.prepare_line(handler.readline()))

                            rnx_epoch["satellites"].append(
                                self.read_satellite(
                                    sat_id=sat_num, line=raw_obs)
                            )

                        # Sort Satellites within epoch
                        rnx_epoch["satellites"] = sorted(
                            rnx_epoch["satellites"], key=lambda sat: sat["id"])

                        rinex_obs["epochs"].append(rnx_epoch)
                        rinex_epoch = RinexEpoch(
                            timestamp=datetime.datetime.strptime(
                                rnx_epoch["id"], cc.RNX_FORMAT_DATETIME),
                            observation_types=self.header.observation_types,
                            satellites=rnx_epoch["satellites"],
                            rcv_clock_offset=self.header.rcv_clock_offset
                        )
                        if rinex_epoch.is_valid():
                            self.rinex_epochs.append(rinex_epoch)

            if len(rinex_obs["epochs"]) > 0:
                rinex_obs["epochFirst"] = rinex_obs["epochs"][0]["id"]
                rinex_obs["epochLast"] = rinex_obs["epochs"][-1]["id"]
            self.datadict = rinex_obs
            logger.debug("Successfully created data dict")


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
        '''
        Constructor, use the same as Rinex2ObsReader
        '''
        super(Rinex3ObsReader, self).__init__(**kwargs)
        # assert self.is_valid_filename(
        #     os.path.basename(self.rinex_obs_file), self.header.format_version)
        # m = re.match(self.RINEX_FILE_NAME_REGEX, os.path.basename(self.rinex_obs_file))

        # d = m.groupdict()
        # self.station = d["station"]
        # self.doy = int(d["doy"])
        # self.year = int(d["year4"])
        # self.file_period = d["file_period"]
        # self.rinex_file_sequence = -1  # g[6]

    def set_rinex_obs_file(self, rinex_obs_file):
        self.rinex_obs_file = rinex_obs_file

        assert self.is_valid_filename(
            os.path.basename(self.rinex_obs_file), self.header.format_version)
        m = re.match(self.RINEX_FILE_NAME_REGEX, os.path.basename(self.rinex_obs_file))

        d = m.groupdict()
        self.station = d["station"]
        self.doy = int(d["doy"])
        self.year = int(d["year4"])
        self.file_period = d["file_period"]
        self.rinex_file_sequence = -1  # g[6]
       
        self.rinex_obs_file = rinex_obs_file

        self.epochs = []
        self.datadict = {}
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
        """
        """
        # SKIP HEADER
        with open(self.rinex_obs_file, "r") as handler:
            for i, line in enumerate(handler):
                if 'END OF HEADER' in line:
                    break
            # del i
            i = 0
            rinex_obs = {
                "epochs": [], 
                "fileName": self.rinex_obs_file,
                "year4": self.year,
                "doy": self.doy,
                "markerName": self.station,
                "epochPeriod": self.file_period,
                "epochInterval": self.header.interval,
                "epochFirst": None,
                "epochLast": None
            }            
            with open(self.rinex_obs_file, "r") as handler:
                while True:

                    # Check for END_OF_FILE
                    line = handler.readline()
                    if line == "":
                        break
                    # Get DateLine
                    r = re.search(self.RINEX_DATELINE_REGEXP, line)
                    if r is not None:
                        # logger.debug("Found Date")
                        timestamp = datetime.datetime(
                            int(r.group("year4")),
                            int(r.group("month")),
                            int(r.group("day")),
                            int(r.group("hour")),
                            int(r.group("minute")),
                            int(float(r.group("second")))
                        )
                        epoch = timestamp.strftime("%FT%TZ")
                        self.add_epoch(epoch)

                        rnx_epoch = {
                            "id": epoch,
                            "satellites": [],
                        }

                        epoch_flag = r.group("epoch_flag")
                        if epoch_flag not in ["0", "1"]:
                            logger.info("Special event: {}".format(epoch_flag))

                        # Number of Satellites
                        nos = int(r.group("num_of_sats"))
                        # logger.debug("Number of Sats: {}".format(nos))
                        for j in range(nos):
                            line = handler.readline()
                            sat_data = re.search(cc.RINEX3_DATA_OBSEVATION_REGEXP, line)

                            # Get Observation Data
                            if sat_data is not None:
                                sat_num = sat_data.group("sat_num")
                                self.add_satellite(sat_num)
                                rnx_epoch["satellites"].append(
                                    self.read_satellite(sat_id=sat_num, line=line)
                                )

                        # Sort Satellites within epoch
                        rnx_epoch["satellites"] = sorted(
                            rnx_epoch["satellites"], key=lambda sat: sat["id"])

                        rinex_obs["epochs"].append(rnx_epoch)
                        # rinex_epoch = RinexEpoch(
                        #     timestamp=datetime.datetime.strptime(
                        #         rnx_epoch["id"], cc.RNX_FORMAT_DATETIME),
                        #     observation_types=self.header.observation_types,
                        #     satellites=rnx_epoch["satellites"],
                        #     rcv_clock_offset=self.header.rcv_clock_offset
                        # )
                        # if rinex_epoch.is_valid():
                        #     self.rinex_epochs.append(rinex_epoch)

            if len(rinex_obs["epochs"]) > 0:
                rinex_obs["epochFirst"] = rinex_obs["epochs"][0]["id"]
                rinex_obs["epochLast"] = rinex_obs["epochs"][-1]["id"]
            self.datadict = rinex_obs
            logger.debug("Successfully created data dict")

    def read_satellite(self, sat_id, line):
        """
        Parses trough rnx observation and creates dict. Referring to the RINEX Handbook 3.03
        
        Args:
            sat_id: str satellite number/name
            line: str rnx line containing observations
        Returns:
            dict: {sat_id: {otk1: otv1, otk2: otv2, ... otkn: otvn}}
        """

        all_obs = []
        m = re.match(cc.RINEX3_DATA_OBSEVATION_REGEXP, line)
        if m:
            regexp_dict = m.groupdict()
            if "first_o" in regexp_dict and regexp_dict["first_o"] is not None:
                keys = ["value", "lli", "ss"]
                for n in re.finditer(cc.RINEX3_MULTIPLE_OBS_REGEXP, line):
                    d = {}
                    n_filter = n.groups()[1:]
                    for i in range(len(n_filter)):
                        vs = n_filter[i].strip()
                        v = None if vs == "" else float(vs)
                        k = keys[i]
                        d.update({k: v})
                    all_obs.append(d)
            if "last_o" in regexp_dict and regexp_dict["last_o"] is not None:
                d = {
                    "lli": None, 
                    "ss": None,
                    "value": float(regexp_dict["last_o"])
                }
                all_obs.append(d)

        sat_dict = {"id": sat_id, "observations": {}}
        d = {}

        sat_sys = sat_id[0]
        for i in range(len(all_obs)):
            obs_descriptor = self.header.sys_obs_types[sat_sys]["obs_types"][i]
            for k in ["value", "lli", "ss"]:
                d["{}_{}".format(obs_descriptor, k)] = all_obs[i][k]

        sat_dict["observations"].update(d)
        return sat_dict
