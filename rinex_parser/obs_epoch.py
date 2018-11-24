'''
Created on Nov 10, 2016

@author: jurgen
'''

import datetime
from rinex_parser import constants as cc
from rinex_parser.logger import logger


class RinexEpoch(object):
    '''
    classdocs
    '''

    def __init__(self, **kwargs):
        '''
        Constructor
        Args:
            timestamp: datetime, Timestamp of epoch
            observation_types: list, List of observation types. 
                               It's order will be used for export order
            satellites: dict, including the epoch's data
            epoch_flag: int, Epoch Flag (default 0)
            rcv_clock_offset: float, Offset of Receiver (default 0.0)
        '''
        self.timestamp = kwargs.get("timestamp")
        self.observation_types = kwargs.get("observation_types")
        self.satellites = kwargs.get("satellites")
        self.epoch_flag = kwargs.get("epoch_flag", 0)
        self.rcv_clock_offset = kwargs.get("rcv_clock_offset", 0.)

    def get_day_seconds(self):
        """
        :return: int, seconds till 00:00:00 of timestamp date
        """
        return self.timestamp.second + self.timestamp.minute * 60 + self.timestamp * 3600

    def is_valid(self, satellite_systems=["G"], observation_types=["L1", "L2", "L1C", "L1W"], satellites=5):
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
                        if observation_type in satellite["observations"] and satellite["observations"][observation_type] is not None:
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
            d = "{:d}".format(
                int(val))
            if d == "0":
                raise KeyError
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
                    val = self.get_val(self.satellites[i]["observations"][ot])
                    lli = self.get_d(
                        self.satellites[i]["observations"][ot + "_lli"])
                    ss = self.get_d(
                        self.satellites[i]["observations"][ot + "_ss"])

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
            self.timestamp.strftime("%y %m %d %H %M %S.0000000"),
            self.epoch_flag,
            nos,
            prn1,
            self.rcv_clock_offset
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
                if satellite["id"].startswith(satellite_system) and satellite_system not in satellite_systems:
                    satellite_systems.append(satellite_system)
        return satellite_systems

    def from_rinex2(self, rinex):
        """
        """
        pass

    def to_rinex3(self):
        """
        Exports Epoch with Rinex3 format

        Returns: str, Rinex3 Format
        """
        nos = len(self.satellites)
        data_lines = ""

        data_lines += "> {epoch_time}  {epoch_flag}{nos:3d}{empty:6s}{rcvco}".format(
            epoch_time=self.timestamp.strftime(cc.RINEX3_FORMAT_OBS_TIME),
            epoch_flag=self.epoch_flag,
            nos=nos,
            empty="",
            rcvco=self.rcv_clock_offset
        )
        for i in range(nos):
            new_data = "\n{:3s}".format(self.satellites[i]["id"])
            for ot in self.observation_types:
                if self.satellites[i]["observations"].has_key(ot):
                    val = self.get_val(self.satellites[i]["observations"][ot])
                    lli = self.get_d(
                        self.satellites[i]["observations"][ot + "_lli"])
                    ss = self.get_d(
                        self.satellites[i]["observations"][ot + "_ss"])
                    new_data += "{}{}{}".format(val, lli, ss)

                else:
                    new_data += "{:16s}".format("")
            data_lines += new_data

        return data_lines

    def from_rinex3(self, rinex):
        """
        """
