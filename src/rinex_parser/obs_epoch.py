"""
Created on Nov 10, 2016

@author: jurgen
"""

import datetime
import traceback
from rinex_parser import constants as cc
from rinex_parser.logger import logger


class RinexEpoch(object):
    """
    classdocs
    """

    def __init__(self, timestamp, observation_types, satellites, **kwargs):
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

    def to_dict(self):
        d = {
            # "id": self.timestamp.strftime(cc.RNX_FORMAT_DATETIME),
            "id": self.timestamp,
            "satellites": self.satellites,
        }
        return d

    # def get_day_seconds(self):
    #     """
    #     :return: int, seconds till 00:00:00 of timestamp date
    #     """
    #     return (
    #         self.timestamp.second + self.timestamp.minute * 60 + self.timestamp * 3600
    #     )

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
            # logger.debug("Looking for Observation Type '%s'" % observation_type)
            for satellite_system in satellite_systems:
                # logger.debug("Looking for Satellite System '%s'" % satellite_system)
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
        except:
            v = " " * 14
        return v

    @staticmethod
    def get_d(val):
        try:
            #             if val is None:
            #                 raise ValueError
            d = "{:d}".format(int(val))
            if d == "0":
                d = " "
            # if d == "0":
            #     raise KeyError
        except:
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
                    val = self.get_val(
                        self.satellites[i]["observations"][ot + "_value"]
                    )
                    lli = self.get_d(self.satellites[i]["observations"][ot + "_lli"])
                    ss = self.get_d(self.satellites[i]["observations"][ot + "_ss"])

                    new_data = "{}{}{}".format(val, lli, ss)
                else:
                    new_data = " " * 16

                if ((j) % 5 == 0) and len(self.observation_types) > 5:
                    # logger.debug("New Data Line")
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

    def to_rinex3(self):
        """
        Exports Epoch with Rinex3 format

        Returns: str, Rinex3 Format
        """
        nos = len(self.satellites)
        data_lines = ""

        rco = self.rcv_clock_offset if self.rcv_clock_offset else " "

        data_lines += (
            "> {epoch_time}  {epoch_flag}{nos:3d}{empty:6s}{rcvco}".format(
                epoch_time=self.timestamp,
                epoch_flag=self.epoch_flag,
                nos=nos,
                empty="",
                rcvco=rco,
            ).strip()
            + "\n"
        )

        # sort order

        sat_sys_order = "GRECJS"
        sat_sys_block = {}
        for sat_sys in sat_sys_order:
            sat_sys_block[sat_sys] = []

        # self.observation_types {"G": {"obs_types": [..]}, "R": {...}, ...}
        for _, item in enumerate(self.satellites):
            # item {"id": "G01", "observations": {"C1C_[value,lli,ss]": ...}}
            try:
                sat_sys = item["id"][0]  # G,R,E,C...
                obs_codes = self.observation_types[sat_sys]["obs_types"]
                new_data = "{:3s}".format(item["id"])
                for obs_code in obs_codes:
                    try:
                        val = self.get_val(item["observations"][f"{obs_code}_value"])
                        lli = self.get_d(item["observations"][f"{obs_code}_lli"])
                        ssi = self.get_d(item["observations"][f"{obs_code}_ssi"])
                        if obs_code.startswith("L") and ssi != " " and lli == " ":
                            lli = "0"
                        new_data += f"{val}{lli}{ssi}"
                    except KeyError:
                        # Satellite does not have this code
                        new_data += " " * 16
                    except Exception as e:
                        traceback.print_exc()
                        new_data += " " * 16

                sat_sys_block[sat_sys].append(new_data.strip())
            except Exception as e:
                print(e)

        sat_blocks = []
        for sat_sys in sat_sys_order:
            sat_blocks += sat_sys_block[sat_sys]
        data_lines += "\n".join(sat_blocks)

        return data_lines

    def from_rinex3(self, rinex):
        """ """
