"""
Created on Nov 10, 2016

@author: jurgen
"""

import traceback
import time
import datetime
from rinex_parser import constants as cc
from rinex_parser.logger import logger

EPOCH_MIN = datetime.datetime(1970, 1, 1).timestamp()
EPOCH_MAX = datetime.datetime(datetime.MAXYEAR, 12, 31).timestamp()


def ts_epoch_to_list(line: str) -> list:
    """Use epoch line and generate list of [y, m, d, H, M, S]."""
    y = int(line[2:6])
    m = int(line[7:9])
    d = int(line[10:12])
    H = int(line[13:15])
    M = int(line[16:18])
    S = float(line[18:30])
    return [y, m, d, H, M, S]


def ts_epoch_to_time(line: str) -> float:
    y, m, d, H, M, S = ts_epoch_to_list(line)
    return time.mktime(
        time.strptime(
            f"{y:04d}-{m:02d}-{d:02d}T{H:02d}:{M:02d}:{S:09.6f}", "%Y-%m-%dT%H:%M:%S.%f"
        )
    )


def get_second_of_day(h: int, m: int, s: float) -> float:
    return h * 3600.0 + m * 60.0 + s


def ts_epoch_to_header(epoch: str) -> str:
    """Convert date from epoch format to header format."""
    # > 2025 03 16 00 00  0.0000000  0 37
    #   2025    03    17    19    00   00.0000000     GPS         TIME OF FIRST OBS
    line = f"> {epoch}"
    y, m, d, H, M, S = ts_epoch_to_list(line)
    s = f"  {y}    {m:02d}    {d:02d}    {H:02d}    {M:02d}  {S:11.7f}"
    return s


class RinexEpoch(object):
    """
    classdocs
    """

    def __init__(
        self, timestamp, observation_types, satellites, raw=list[str], **kwargs
    ):
        """
        Constructor
        Args:
            timestamp: datetime, Timestamp of epoch
            observation_types: list, List of observation types.
                               It's order will be used for export order
            satellites: dict, including the epoch's data
            epoch_flag: int, Epoch Flag (default 0)
            rcv_clock_offset: float, Offset of Receiver (default 0.0)
        """
        # self.timestamp: datetime.datetime = timestamp
        self.timestamp: str = timestamp
        self.observation_types = observation_types
        self.satellites = satellites
        self.epoch_flag = kwargs.get("epoch_flag", 0)
        self.rcv_clock_offset = kwargs.get("rcv_clock_offset", 0.0)
        self.raw: list[str] = raw

    def to_dict(self):
        d = {
            # "id": self.timestamp.strftime(cc.RNX_FORMAT_DATETIME),
            "id": self.timestamp,
            "satellites": self.satellites,
        }
        return d

    def is_valid(
        self,
        satellite_systems=["G"],
        observation_types=["L1", "L2", "L1C", "L1W"],
        satellites=5,
    ):
        """
        Checks if epoch suffices validity criterias. Per default these are:

        * Satellite System contains is GPS
        * Contains L1 and L2 observation Types
        * At Least 5 Satellites within each Satellite System

        Returns: bool, True, if suffices criterias, else False
        """
        for observation_type in observation_types:
            for satellite_system in satellite_systems:
                i = 0
                for satellite in self.satellites:
                    if satellite["id"].startswith(satellite_system):
                        if (
                            observation_type in satellite["observations"]
                            and satellite["observations"][observation_type] is not None
                        ):
                            i += 1

                if i < satellites:
                    return False
        return True

    @staticmethod
    def get_val(val):
        try:
            if val is None:
                raise ValueError
            v = "{:14.3f}".format(float(val))
        except Exception as e:
            v = " " * 14
        return v

    @staticmethod
    def get_d(val):
        try:
            d = "{:d}".format(int(val))
            if d == "0":
                d = " "
        except Exception as e:
            d = " "
        return d

    def has_satellite_system(self, sat_sys):
        """
        Checks if Satellite Systems is present or not

        Args:
            sat_sys: str, Satellite System "GREJIS"

        Returns:
            bool, True, if Satellite System is present, else False
        """
        for sat in self.satellites:
            if sat.upper().startswith(sat_sys[0].upper()):
                return True
        return False

    def to_rinex2(self):
        """
        Exports Epoch with Rinex2 format

        Returns: str, Rinex2 Format
        """
        prn1 = ""
        prn2 = ""
        nos = len(self.satellites)
        data_lines = ""

        for i in range(nos):

            j = 0
            for ot in self.observation_types:
                j += 1
                if self.satellites[i]["observations"].has_key(ot):
                    val = self.satellites[i]["observations"][ot][0]
                    lli = self.satellites[i]["observations"][ot][1]
                    ssi = self.satellites[i]["observations"][ot][2]
                    new_data = "{}{}{}".format(val, lli, ssi)
                else:
                    new_data = " " * 16

                if ((j) % 5 == 0) and len(self.observation_types) > 5:
                    new_data = "%s\n" % new_data
                data_lines = "%s%s" % (data_lines, new_data)

            if i < nos - 1:
                data_lines += "\n"

            if i < 12:
                prn1 = "%s%s" % (prn1, self.satellites[i]["id"])
            else:
                if i % 12 == 0:
                    prn2 = "%s\n%s" % (prn2, " " * 32)
                prn2 = "%s%s" % (prn2, self.satellites[i]["id"])

        header_line = " {}  {:d}{:3d}{}{:12.9f}".format(
            # self.timestamp.strftime(cc.RINEX3_FORMAT_OBS_TIME),
            self.timestamp,
            self.epoch_flag,
            nos,
            prn1,
            self.rcv_clock_offset,
        )

        if prn2 != "":
            header_line = "%s%s" % (header_line, prn2)

        return "%s\n%s" % (header_line, data_lines)

    def get_satellite_systems(self):
        """
        Checks epoch for occuring satellite systems
        """
        satellite_systems = []
        for satellite_system in cc.RINEX3_SATELLITE_SYSTEMS:
            for satellite in self.satellites:
                if (
                    satellite["id"].startswith(satellite_system)
                    and satellite_system not in satellite_systems
                ):
                    satellite_systems.append(satellite_system)
        return satellite_systems

    def from_rinex2(self, rinex):
        """ """
        pass

    def to_rinex3(
        self, observation_types: dict = {}, use_raw: bool = False
    ) -> list[str]:
        """
        Exports Epoch with Rinex3 format

        Returns: str, Rinex3 Format
        """

        if use_raw:
            return self.raw

        nos = len(self.satellites)
        rco = self.rcv_clock_offset if self.rcv_clock_offset else " "

        data_lines = [
            "> {epoch_time}  {epoch_flag}{nos:3d}{empty:6s}{rcvco}\n".format(
                epoch_time=self.timestamp,
                epoch_flag=self.epoch_flag,
                nos=nos,
                empty="",
                rcvco=rco,
            )
        ]

        # sort order
        # sat_sys_order = "GRECJS"
        sat_sys_order = "CEGIJRQS"

        if not observation_types:
            observation_types = self.observation_types

        sorted_items = {}
        for sat_sys in sat_sys_order:
            sorted_items[sat_sys] = []

        # self.observation_types {"G": set [..], "R": set [...], ...}
        for item in self.satellites:
            # item {"id": "G01", "observations": {"C1C_[value,lli,ss]": ...}}
            try:
                new_data = ""
                sat_sys = item["id"][0]  # G,R,E,C...
                for obs_code in list(observation_types[sat_sys]):
                    try:
                        val = item["observations"][obs_code][0]
                        lli = item["observations"][obs_code][1]
                        ssi = item["observations"][obs_code][2]
                        if obs_code.startswith("L") and ssi != " " and lli == " ":
                            lli = "0"
                        new_part = f"{val}{lli}{ssi}"
                    except KeyError:
                        # Satellite does not have this code
                        new_part = " " * 16
                    except Exception as e:
                        traceback.print_exc()
                        new_part = " " * 16
                    finally:
                        new_data = f"{new_data}{new_part}"
                new_data = f"{item['id']:3s}{new_data}\n"
                sorted_items[sat_sys].append(new_data)
                # data_lines.append(new_data)
            except Exception as e:
                print(e)

        items_keys = sorted_items.keys()
        for sat_sys in sat_sys_order:
            if sat_sys in items_keys:
                data_lines += sorted_items[sat_sys]
        return data_lines

    def from_rinex3(self, rinex):
        """ """
        raise NotImplementedError
