#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of rinexparser.
# https://github.com/dach.pos/rinexparser

# Licensed under the Apache 2.0 license:
# http://opensource.org/licenses/apache2.0
# Copyright (c) 2018, jiargei <juergen.fredriksson@bev.gv.at>

import os
import argparse
import datetime

from rinex_parser.constants import RNX_FORMAT_DATE
from rinex_parser.logger import logger
from rinex_parser.obs_factory import RinexObsFactory, RinexObsReader


def run():
    parser = argparse.ArgumentParser(description="Analyse your Rinex files.")
    parser.add_argument("file", type=str, help="rinex file including full path")
    parser.add_argument("version", type=int, help="rinex version (2 or 3)")
    args = parser.parse_args()
    rinex_parser = RinexParser(rinex_version=args.version, rinex_file=args.file)
    rinex_parser.run()


class RinexParser:

    def __init__(self, rinex_file: str, rinex_version: int, *args, **kwargs):
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
        self.__create_reader(self.rinex_version)
        self.rinex_reader.interval_filter = self.sampling

    @property
    def datadict(self):
        return self.get_datadict()

    def get_datadict(self):
        d = {}
        d["epochs"] = [e.to_dict() for e in self.rinex_reader.rinex_epochs]
        d["epochInterval"] = self.rinex_reader.header.interval
        d["epochFirst"] = self.rinex_reader.rinex_epochs[0]["id"]
        d["epochLast"] = self.rinex_reader.rinex_epochs[-1]["id"]
        dtF = datetime.datetime.strptime(d["epochFirst"], RNX_FORMAT_DATE)
        dtL = datetime.datetime.strptime(d["epochLast"], RNX_FORMAT_DATE)
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
        self.rinex_reader.header.interval = self.sampling
        # logger.info("done with header")
        self.rinex_reader.read_data_to_dict()

    def do_clear_datadict(self):
        """Read all epochs and find empty obs types and remove them from header."""
        found_obs_types = {}
        input_obs_types = {}
        for sat_sys in self.rinex_reader.header.sys_obs_types.keys():
            found_obs_types[sat_sys] = set()

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
                            found_obs_types[sat_sys].add(obs_type)
        else:
            found_obs_types = self.rinex_reader.found_obs_types

        # go through all obs types from header and remove those who are not listed
        for sat_sys in self.rinex_reader.header.sys_obs_types:
            input_obs_types[sat_sys] = set(
                self.rinex_reader.header.sys_obs_types[sat_sys]["obs_types"]
            )
            for obs_type in input_obs_types[sat_sys] - found_obs_types[sat_sys]:
                logger.info(f"Remove unused OBS TYPE {sat_sys}-{obs_type}")
                self.rinex_reader.header.sys_obs_types[sat_sys]["obs_types"].remove(
                    obs_type
                )

    def run(self):
        assert os.path.isfile(self.rinex_file), f"Not a file ({self.rinex_file})"
        self.do_create_datadict()
