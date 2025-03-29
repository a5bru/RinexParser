#!/usr/bin/python

import os
import time
import datetime

from rinex_parser import constants as cc
from rinex_parser.logger import logger
from rinex_parser.obs_parser import RinexParser
from rinex_parser.obs_epoch import RinexEpoch, ts_epoch_to_time, ts_epoch_to_datetime


class RinexQuality(object):
    """ """

    RINEX_PERIOD_UNITS = {
        "D": 60 * 60 * 24,
        "H": 60 * 60,
        "M": 60,
    }

    def __init__(self, **kwargs):
        super(RinexQuality, self).__init__()
        self.rinex_format = kwargs.get("rinex_format", 3)

    def filter_by_observation_descriptor(
        self, epoch_satellites, observation_descriptor, satellite_system
    ):
        """ """
        for satellite in epoch_satellites:
            if (
                "id" in satellite
                and satellite["id"][0] == satellite_system
                and "observations" in satellite
            ):
                for observation in satellite["observations"]:
                    if (
                        observation == observation_descriptor
                        and satellite["observations"][observation][0] is not None
                    ):
                        yield satellite
                    elif (
                        self.rinex_format == 3
                        and observation.startswith(observation_descriptor)
                        and satellite["observations"][observation][0] is not None
                    ):
                        yield satellite
                        continue

    def is_valid_epoch(
        self,
        epoch: RinexEpoch,
        satellite_systems=["G"],
        observation_descriptors=["L1", "L2"],
        satellites=5,
    ):
        """
        Checks if epoch suffices validity criterias. Per default these are:

        * Satellite System contains is GPS
        * At Least 5 Satellites within each Satellite System

        Returns: bool, True, if suffices criterias, else False
        """
        for observation_descriptor in observation_descriptors:
            for satellite_system in satellite_systems:
                i = 0
                i_test = self.filter_by_observation_descriptor(
                    epoch_satellites=epoch.satellites,
                    observation_descriptor=observation_descriptor,
                    satellite_system=satellite_system,
                )
                i += len(list(i_test))
                if i < satellites:
                    return False
        return True

    @staticmethod
    def get_datetime_utc(epoch_str):
        """ """
        return datetime.datetime.strptime(epoch_str, cc.RNX_FORMAT_OBS_TIME.strip())

    @staticmethod
    def get_session_code(second_of_day):
        """
        Args:
            second_of_day (int): Second of day (0..86399)
        Returns:
            str: The Hour Code (A..X)
        """
        i = int(second_of_day / 3600)
        return chr(i + 65)

    def do_prepare_datadict(self, rinex_parser: RinexParser, gapsize: int = 5):
        """ """
        if len(rinex_parser.rinex_reader.rinex_epochs) == 0:
            logger.warning("No Epoch parsed")
            return ""

        datadict = rinex_parser.get_datadict()

        for zeitpunkt in ["epochFirst", "epochLast"]:
            if (
                zeitpunkt not in datadict and not isinstance(datadict[zeitpunkt], float)
            ) or (zeitpunkt in datadict and datadict[zeitpunkt] is None):
                datadict[zeitpunkt] = time.time()

        dt0 = datetime.datetime.fromtimestamp(
            ts_epoch_to_time("> " + datadict["epochFirst"])
        )
        dtD = dt0.strftime("%j")

        if "epochPeriod" not in datadict:
            datadict["epochPeriod"] = "01D"  # Daily Files as default

        period_count = int(datadict["epochPeriod"][:2])
        period_unit = datadict["epochPeriod"][-1]

        period_seconds = int(
            self.RINEX_PERIOD_UNITS[period_unit]
            * period_count
            / datadict["epochInterval"]
        )

        chkdoy = {
            "filename": os.path.basename(rinex_parser.rinex_file),
            "station": rinex_parser.rinex_reader.header.marker_name,
            "year": dt0.year,
            "doy": dtD,
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

        print(chkdoy)

        # logger.debug("Prepare")
        dt_epoch_first = datetime.datetime.strptime(
            chkdoy["epoch_first"], cc.RNX_FORMAT_OBS_TIME.strip()
        )
        dt_epoch_last = datetime.datetime.strptime(
            chkdoy["epoch_last"], cc.RNX_FORMAT_OBS_TIME.strip()
        )
        total_seconds = int((dt_epoch_last - dt_epoch_first).total_seconds())

        epoch_valid = []
        for epoch in rinex_parser.rinex_reader.rinex_epochs:
            if not self.is_valid_epoch(epoch):
                continue
            if epoch.timestamp not in epoch_valid:
                epoch_valid.append(ts_epoch_to_time("> " + epoch.timestamp))

        chkdoy["epochs_valid"] = len(epoch_valid)
        epochs = sorted(epoch_valid)

        gaps_less = 0
        gaps_more = 0
        for i in range(len(epochs) - 1):
            epoch_delta = int(epochs[i + 1] - epochs[i])
            if epoch_delta > chkdoy["epoch_interval"]:
                chkdoy["gaps"].append(
                    {
                        "gap_begin": datetime.datetime.fromtimestamp(
                            epochs[i]
                        ).strftime(cc.RNX_FORMAT_DATETIME),
                        "gap_end": datetime.datetime.fromtimestamp(
                            epochs[i + 1]
                        ).strftime(cc.RNX_FORMAT_DATETIME),
                        "gap_epoch_count": epoch_delta / chkdoy["epoch_interval"],
                        "gap_duration": epoch_delta,  # (gap_epoch_count * datadict["epochInterval"])
                    }
                )

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

    def get_rinex_availability_as_dict(self, rinex_parser: RinexParser, gapsize=5):
        """
        Get RinexAvailability as dictionary
        """
        chkdoy = self.do_prepare_datadict(rinex_parser, gapsize)
        rinex_v = []
        d = {
            "date": chkdoy["date"],
            "station_name": chkdoy["station"],
            "second_from": 0,
            "second_until": 1,
            "epoch_interval": chkdoy["epoch_interval"],
            "session_code": "A",
            "is_online": 1,
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
            w_from = datetime.datetime.strptime(w["valid_from"], cc.RNX_FORMAT_DATETIME)
            w_from_c = datetime.datetime(w_from.year, w_from.month, w_from.day)
            w_until = datetime.datetime.strptime(
                w["valid_until"], cc.RNX_FORMAT_DATETIME
            )
            w_until_c = datetime.datetime(w_until.year, w_until.month, w_until.day)
            w_delta = w_until - w_from
            w_delta_hours = w_delta.total_seconds() / 3600.0
            d["second_from"] = int((w_from - w_from_c).total_seconds())
            # split by hours, not tested for bigger than daily files
            i = 0
            if w_delta_hours > 1:
                for i in range(int(w_delta_hours)):
                    d["second_until"] = int(
                        (w_from.hour + i + 1) * 3600 - chkdoy["epoch_interval"]
                    )
                    # rinex_v_i = "{date};{station_name};{second_from};{second_until};{epoch_interval};{session_code};{is_online}".format(
                    #     **d
                    # )
                    # rinex_v.append(rinex_v_i)
                    d["second_from"] = int(d["second_until"] + chkdoy["epoch_interval"])
                    d["session_code"] = self.get_session_code(d["second_from"])
                    rinex_v.append(d)
            else:
                d["second_until"] = int((w_until - w_until_c).total_seconds())
                d["session_code"] = self.get_session_code(d["second_from"])
                rinex_v.append(d)
        return rinex_v

    def get_rinex_availability_as_str(self, availability_dict):
        """ """
        rinex_v = []
        for d in availability_dict:
            rinex_v_i = "{date};{station_name};{second_from};{second_until};{epoch_interval};{session_code};{is_online}".format(
                **d
            )
            rinex_v.append(rinex_v_i)
        return "\n".join(rinex_v)

    def get_rinex_availability(self, datadict, gapsize=5):
        """
        Should generate an output like:

        'YYYY-MM-DD;STATION;SECOND_BEGIN;SECOND_END;EPOCH_INTERVAL;SESSION_CODE;IS_ONLINE'
        """
        rinex_v_dict = self.get_rinex_availability_as_dict(datadict, gapsize)
        return self.get_rinex_availability_as_str(rinex_v_dict)

    def get_rinstat_as_dict(self, rinex_parser: RinexParser, gapsize=5):
        """
        Get RinstatData as a dictionary
        """
        chkdoy = self.do_prepare_datadict(rinex_parser, gapsize)
        chkdoy["gaps_count"] = len(chkdoy["gaps"])
        chkdoy["epoch_first"] = datetime.datetime.strptime(
            chkdoy["epoch_first"], cc.RNX_FORMAT_DATETIME
        ).strftime(cc.RNX_FORMAT_TIME)
        chkdoy["epoch_last"] = datetime.datetime.strptime(
            chkdoy["epoch_last"], cc.RNX_FORMAT_DATETIME
        ).strftime(cc.RNX_FORMAT_TIME)
        chkdoy["gaps_prepared"] = []
        for gap in chkdoy["gaps"]:
            gap_dict = {
                "ge": int(gap["gap_epoch_count"]) - 1,
                "gs": gap["gap_duration"] - chkdoy["epoch_interval"],
                "gf": datetime.datetime.strptime(
                    gap["gap_begin"], cc.RNX_FORMAT_DATETIME
                )
                + datetime.timedelta(seconds=chkdoy["epoch_interval"]),
                "gu": datetime.datetime.strptime(
                    gap["gap_end"], cc.RNX_FORMAT_DATETIME
                ),
            }
            chkdoy["gaps_prepared"].append(gap_dict)
        return chkdoy

    def get_rinstat_as_str(self, rinstat_dict):
        """ """
        rinstat_dict["gaps_list"] = ""
        for gap in rinstat_dict["gaps_prepared"]:
            gap_str = "--- GAP:  {gf} - {gu}  {gs:10.1f} s {ge:10d} e".format(**gap)
            rinstat_dict["gaps_list"] += "\n{}".format(gap_str)

        # Report
        return """+++ >>>   {filename}{gaps_list}
+++ RNX.SUM   {date} ({doy})   {station}   {epoch_first} - {epoch_last}   {total_secs} s   {epoch_interval} s {gaps_count:7d}
+++    #maxepo #aepoch #mepoch #gaps>{gapsize} #gaps<{gapsize}
+++      {epochs_max:5d}   {epochs_valid:5d}   {epochs_missing:5d}   {gaps_more:5d}   {gaps_less:5d}
+++ <<<""".format(
            **rinstat_dict
        )

    def get_rinstat_out(self, rinex_parser: RinexParser, gapsize=5):
        """
        Create Dataframe with filter:
        - more than 5 GPS per epoch
        - having at least L1 and L2

        old report format:

        +++ >>>   SSSSDOYS.YYo
        +++ RNX.SUM   YY MM DD (DOY)   SSSS   HH MM SS -  HH MM SS   DDDDD s   DD s
        +++    #maxepo  #epoch   #gaps #gaps>5 #gaps<5
        +++       DDDD    DDDD     DDD     DDD     DDD
        +++ <<<
         +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        Values to Prepare
        * Filename
        * Date of File (YY MM DD)
        * Day of Year (DOY)
        * Stationname (SSSS)
        * Time of first epoch
        * Time of last epoch
        * Total seconds of file
        * epoch interval of file
        * Maximal possible Epochs
        * Actual amount of Epochs
        * Total number of Gaps in file
        * Number of Gaps greater than 5 epochs
        * Number of Gaps less-equal than 5 epochs

        Args:
            gapsize: int, Amount of gaps to bother

        """
        chkdoy = self.get_rinstat_as_dict(rinex_parser, gapsize)
        return self.get_rinstat_as_str(chkdoy)

    def get_signal_strength(self, rinex_parser: RinexParser, obs_types=[]) -> dict:
        s_data = {}
        for epoch in rinex_parser.rinex_reader.rinex_epochs:
            s_data[epoch.timestamp] = {}
            for satellite in epoch.satellites:
                if satellite["id"] not in s_data[epoch.timestamp]:
                    s_data[epoch.timestamp][satellite["id"]] = []
                for obs_type in satellite["observations"].keys():
                    if not obs_types:
                        if obs_type.startswith("S"):
                            s_data[epoch.timestamp][satellite["id"]].append(
                                (obs_type, satellite["observations"][obs_type][0])
                            )
                    else:
                        if obs_type in obs_types:
                            s_data[epoch.timestamp][satellite["id"]].append(
                                (obs_type, satellite["observations"][obs_type][0])
                            )
        return s_data
