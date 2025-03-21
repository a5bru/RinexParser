#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of rinexparser.
# https://github.com/dach.pos/rinexparser

# Licensed under the Apache 2.0 license:
# http://opensource.org/licenses/apache2.0
# Copyright (c) 2018, jiargei <juergen.fredriksson@bev.gv.at>

import os
import math
import argparse
import datetime
import time

from rinex_parser.constants import RNX_FORMAT_OBS_TIME
from rinex_parser.logger import logger
from rinex_parser.obs_factory import RinexObsFactory, RinexObsReader
from rinex_parser.obs_epoch import (
    ts_epoch_to_header,
    ts_epoch_to_list,
    ts_epoch_to_time,
    EPOCH_MIN,
    EPOCH_MAX,
)


def run():
    parser = argparse.ArgumentParser(description="Analyse your Rinex files.")
    parser.add_argument("file", type=str, help="rinex file including full path")
    parser.add_argument(
        "version",
        type=int,
        choices=[2, 3],
        default=3,
        help="rinex version (2 or 3), currently only 3 supported",
    )
    args = parser.parse_args()
    rinex_parser = RinexParser(rinex_version=args.version, rinex_file=args.file)
    rinex_parser.run()


class RinexParser:

    def __init__(
        self,
        rinex_file: str,
        rinex_version: int,
        crop_beg=EPOCH_MIN,
        crop_end=EPOCH_MAX,
        *args,
        **kwargs,
    ):
        assert rinex_version in [
            2,
            3,
        ], f"Unknown version ({rinex_version} not in [2,3])"
        assert os.path.isfile(rinex_file), f"Not a File ({rinex_file})"
        self.rinex_version = rinex_version
        self.rinex_file = rinex_file
        if self.rinex_file != "":
            self.set_rinex_file(self.rinex_file)
        self.rinex_reader_factory = RinexObsFactory()
        self.rinex_reader: RinexObsReader = None
        self.filter_on_read: bool = kwargs.get("filter_on_read", True)
        self.sampling: int = kwargs.get("sampling", 0)
        self.crop_beg = crop_beg
        self.crop_end = crop_end
        self.__create_reader(self.rinex_version)
        self.rinex_reader.interval_filter = self.sampling
        self.found_obs_types = {}

    @property
    def datadict(self):
        return self.get_datadict()

    def get_rx3_long(self, country: str = "XXX") -> str:
        code = self.rinex_reader.header.marker_name[:4].upper()
        ts_f = ts_epoch_to_list("> " + self.rinex_reader.rinex_epochs[0].timestamp)
        ts_l = ts_epoch_to_list("> " + self.rinex_reader.rinex_epochs[-1].timestamp)
        ts_f[-1] = int(ts_f[-1])
        ts_l[-1] = int(ts_l[-1])
        dtF = datetime.datetime(*ts_f)
        dtL = datetime.datetime(*ts_l)
        dtD = (dtL - dtF).total_seconds()
        dtD_M = dtD / 60.0
        dtD_H = dtD_M / 60.0
        dtD_D = dtD_H / 24.0
        dtD_W = dtD_D / 7.0
        unitPeriod = "M"
        unitCount = math.ceil(dtD_M)
        if dtD_M > 59:
            unitPeriod = "H"
            unitCount = math.ceil(dtD_H)
            if dtD_H > 23:
                unitPeriod = "D"
                unitCount = math.ceil(dtD_D)
                if dtD_D > 7:
                    unitPeriod = "W"
                    unitCount = math.ceil(dtD_W)
        doy = int(dtF.strftime("%03j"))
        period = f"{unitCount:02d}{unitPeriod}"
        rinex_origin = "S"
        if len(self.rinex_file) > 32 and self.rinex_file[10] in ["R", "S"]:
            rinex_origin = self.rinex_file[10]

            if country.upper().ljust(3, "X")[:3] == "XXX":
                country = self.rinex_file[6:9].upper().ljust(3, "X")
        # c     c     y   j  h m
        # HKB200AUT_R_20250761900_01H_01S_MO.rnx
        # HKB200XXX_R_20250761900_01H_30S_MO.rnx
        smp = self.rinex_reader.header.interval
        if self.sampling > 0:
            smp = self.sampling
        smp = int(smp)
        return f"{code}00{country}_{rinex_origin}_{dtF.year:04d}{doy:03d}{dtF.hour:02d}{dtF.minute:02d}_{period}_{smp:02d}S_MO.rnx"

    def get_datadict(self):
        d = {}
        d["epochs"] = [e.to_dict() for e in self.rinex_reader.rinex_epochs]
        d["epochInterval"] = self.rinex_reader.header.interval
        d["epochFirst"] = self.rinex_reader.rinex_epochs[0]["id"]
        d["epochLast"] = self.rinex_reader.rinex_epochs[-1]["id"]
        dtF = datetime.datetime.strptime(d["epochFirst"], RNX_FORMAT_OBS_TIME)
        dtL = datetime.datetime.strptime(d["epochLast"], RNX_FORMAT_OBS_TIME)
        dtD = (dtL - dtF).total_seconds()
        dtD_H = dtD / 3600.0
        dtD_D = dtD_H / 24.0
        dtD_W = dtD_D / 7.0
        unitPeriod = "H"
        unitCount = int(dtD_H)
        if dtD_H > 23:
            unitPeriod = "D"
            unitCount = int(dtD_D)
            if dtD_D > 7:
                unitPeriod = "W"
                unitCount = int(dtD_W)
        d["epochPeriod"] = f"{unitCount}{unitPeriod}"
        d["year4"] = dtF.strftime("%Y")
        d["doy"] = dtF.strftime("%j")
        d["markerName"] = self.rinex_reader.header.marker_name
        d["fileName"] = os.path.dirname(self.rinex_file)
        return d

    def __create_reader(self, rinex_version) -> RinexObsReader:
        self.rinex_reader = self.rinex_reader_factory.create_obs_reader_by_version(
            rinex_version
        )()

    def set_rinex_file(self, rinex_file):
        if os.path.isfile(rinex_file):
            self.rinex_file = rinex_file
        else:
            logger.warn("Could not find file: {}".format(rinex_file))
            self.rinex_file = ""

    def get_rinex_file(self):
        return self.rinex_file

    def do_create_datadict(self):
        """Read Rinex file and create datadict."""
        assert self.rinex_file != "", "Rinex file not specified"
        assert os.path.exists(
            self.rinex_file
        ), f"Could not find file ({self.rinex_file})"
        self.rinex_reader.set_rinex_obs_file(self.rinex_file)
        self.rinex_reader.read_header()
        # logger.info("done with header")
        self.rinex_reader.read_data_to_dict()

    def do_clear_datadict(self):
        """Read all epochs and find empty obs types and remove them from header."""
        input_obs_types = {}
        for sat_sys in self.rinex_reader.header.sys_obs_types.keys():
            self.found_obs_types[sat_sys] = set()

        # go through all epochs and satellites and their obs types
        if not self.filter_on_read:
            for rinex_epoch in self.rinex_reader.rinex_epochs:
                for _, item in enumerate(rinex_epoch.satellites):
                    sat_sys = item["id"][0]  # GREC
                    for sat_obs in item["observations"].keys():
                        if (
                            sat_obs.endswith("_value")
                            and item["observations"][sat_obs] is not None
                        ):
                            obs_type = sat_obs.split("_")[0]
                            self.found_obs_types[sat_sys].add(obs_type)
        else:
            self.found_obs_types = self.rinex_reader.found_obs_types

        # go through all obs types from header and remove those who are not listed
        for sat_sys in self.rinex_reader.header.sys_obs_types:
            input_obs_types[sat_sys] = set(
                self.rinex_reader.header.sys_obs_types[sat_sys]["obs_types"]
            )
            for obs_type in input_obs_types[sat_sys] - self.found_obs_types[sat_sys]:
                logger.info(f"Remove unused OBS TYPE {sat_sys}-{obs_type}")
                self.rinex_reader.header.sys_obs_types[sat_sys]["obs_types"].remove(
                    obs_type
                )

    def run(self):
        assert os.path.isfile(self.rinex_file), f"Not a file ({self.rinex_file})"
        self.do_create_datadict()
        # remove unused header
        if self.filter_on_read:
            self.do_clear_datadict()
        # crop epochs to time windows
        cleared_epochs = []
        for epoch in self.rinex_reader.rinex_epochs:
            et = ts_epoch_to_time("> " + epoch.timestamp)
            # CROP
            if et < self.crop_beg:
                continue
            if et > self.crop_end:
                continue

            # SAMPLING
            # if self.crop_beg:
            #     pass

            # APPEND
            cleared_epochs.append(epoch)

        self.rinex_reader.rinex_epochs = cleared_epochs
        self.rinex_reader.header.first_observation = ts_epoch_to_header(
            self.rinex_reader.rinex_epochs[0].timestamp
        )
        self.rinex_reader.header.last_observation = ts_epoch_to_header(
            self.rinex_reader.rinex_epochs[-1].timestamp
        )

    def to_rinex3(self, country: str = "XXX"):

        self.rinex_reader.header.first_observation = ts_epoch_to_header(
            self.rinex_reader.rinex_epochs[0].timestamp
        )
        self.rinex_reader.header.last_observation = ts_epoch_to_header(
            self.rinex_reader.rinex_epochs[-1].timestamp
        )
        out_file = os.path.join(
            os.path.dirname(self.rinex_file), self.get_rx3_long(country)
        )

        # Output Rinex File
        logger.info(f"Write to file: {out_file}")
        with open(out_file, "w") as rnx:
            rnx.write(self.rinex_reader.header.to_rinex3())
            rnx.write("\n")
            rnx.write(self.rinex_reader.to_rinex3())
            rnx.write("\n")
