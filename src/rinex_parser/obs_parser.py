#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RINEX parser module for reading and analyzing RINEX observation files.

This file is part of rinexparser.
https://github.com/dach.pos/rinexparser

Licensed under the Apache 2.0 license:
http://opensource.org/licenses/apache2.0
Copyright (c) 2018, jiargei <juergen.fredriksson@bev.gv.at>
"""

import os
import math
import argparse
import datetime

from typing import Optional, Tuple
from pathlib import Path

from rinex_parser.constants import RNX_FORMAT_OBS_TIME
from rinex_parser.logger import logger
from rinex_parser.obs_factory import RinexObsFactory, RinexObsReader
from rinex_parser.obs_epoch import (
    ts_epoch_to_header,
    ts_to_datetime,
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
    """Parser for RINEX observation files (versions 2 and 3).

    Handles reading, processing, and manipulation of RINEX observation data.
    """

    def __init__(
        self,
        rinex_file: str,
        rinex_version: int,
        sampling: int = 0,
        crop_beg: float = EPOCH_MIN,
        crop_end: float = EPOCH_MAX,
        filter_sat_sys: str = "",
        filter_sat_pnr: str = "",
        filter_sat_obs: str = "",
        *args,
        **kwargs,
    ):
        """Initialize the RINEX parser.

        Args:
            rinex_file: Path to the RINEX observation file.
            rinex_version: RINEX format version (2 or 3).
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If rinex_version is not 2 or 3.
            FileNotFoundError: If rinex_file does not exist.
        """
        assert rinex_version in [
            2,
            3,
        ], f"Unknown version ({rinex_version} not in [2,3])"
        assert Path(rinex_file).is_file(), f"Not a File ({rinex_file})"
        # assert os.path.isfile(rinex_file), f"Not a File ({rinex_file})"

        if rinex_version not in [2, 3]:
            raise ValueError(f"Unknown RINEX version {rinex_version} (must be 2 or 3)")

        self.rinex_version = rinex_version
        self.rinex_file = rinex_file
        self.rinex_reader_factory = RinexObsFactory()
        self.rinex_reader: RinexObsReader = None
        self.filter_on_read: bool = kwargs.get("filter_on_read", True)
        self.sampling = sampling
        self.__create_reader(self.rinex_version)
        self.rinex_reader.interval_filter = self.sampling
        self.rinex_reader.filter_sat_sys = filter_sat_sys
        self.rinex_reader.filter_sat_pnr = filter_sat_pnr
        self.rinex_reader.filter_sat_obs = filter_sat_obs
        self.rinex_reader.crop_beg = crop_beg
        self.rinex_reader.crop_end = crop_end

    @property
    def datadict(self):
        return self.get_datadict()

    def get_country_from_filename(self) -> str:
        """
        Extract country code from the RINEX filename.
        Returns:
            str: Country code (3 characters) or "XXX" if not found.
        """
        rinex_path = os.path.basename(self.rinex_file)
        country = "XXX"
        if len(rinex_path) > 32:
            country = rinex_path[6:9].upper().ljust(3, "X")
        return country

    def get_period(self, ts_f: float, ts_l: float) -> Tuple[str, int]:
        """
        Calculate the observation period between two timestamps.

        Args:
            ts_f: First timestamp.
            ts_l: Last timestamp.

        Returns:
            Tuple[str, int]: A tuple containing the period string and unit count.
        """
        dtD = ts_l - ts_f
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
        period = f"{unitCount:02d}{unitPeriod}"
        return period, unitCount

    def get_rx3_long(self, country: str = "XXX") -> str:
        """
        Generate a long RINEX 3 filename based on the observation data.
        Args:
            country: Country code for the filename (default "XXX").
        Returns:
            str: Generated RINEX 3 filename.
        """
        code = self.rinex_reader.header.marker_name[:4].upper()
        ts_f = self.rinex_reader.rinex_epochs[0].timestamp
        ts_l = self.rinex_reader.rinex_epochs[-1].timestamp
        period, _ = self.get_period(ts_f, ts_l)
        dtF = ts_to_datetime(ts_f)
        doy = int(dtF.strftime("%03j"))
        rinex_origin = "S"
        rinex_path = os.path.basename(self.rinex_file)
        monument_id = "0"
        receiver_id = "0"

        if len(rinex_path) > 32:
            # get data origin
            if rinex_path[10] in ["R", "S"]:
                rinex_origin = rinex_path[10]
            # get country
            if country.upper().ljust(3, "X")[:3] == "XXX":
                country = rinex_path[6:9].upper().ljust(3, "X")
            # get monument_id
            monument_id = rinex_path[4]
            # get receiver_id
            receiver_id = rinex_path[5]

        # c     c     y   j  h m
        # HKB200AUT_R_20250761900_01H_01S_MO.rnx
        # HKB200XXX_R_20250761900_01H_30S_MO.rnx
        smp = self.rinex_reader.header.interval
        if self.sampling > 0:
            smp = self.sampling
        smp = int(smp)
        logger.info(f"Sampling interval for filename: {smp} seconds")
        return f"{code}{monument_id}{receiver_id}{country}_{rinex_origin}_{dtF.year:04d}{doy:03d}{dtF.hour:02d}{dtF.minute:02d}_{period}_{smp:02d}S_MO.rnx"

    def get_datadict(self):
        """Create a data dictionary from the RINEX observation data.
        It contains various metadata and epoch information.
        """

        d = {}
        d["epochs"] = [e.to_dict() for e in self.rinex_reader.rinex_epochs]
        interval = self.rinex_reader.header.interval
        if interval <= 0:
            interval = (
                self.rinex_reader.rinex_epochs[1].timestamp
                - self.rinex_reader.rinex_epochs[0].timestamp
            )

        d["epochInterval"] = interval
        d["epochFirst"] = self.rinex_reader.rinex_epochs[0].timestamp
        d["epochLast"] = self.rinex_reader.rinex_epochs[-1].timestamp
        dtF = ts_to_datetime(d["epochFirst"])
        period, _ = self.get_period(d["epochFirst"], d["epochLast"])
        d["epochPeriod"] = period
        d["year4"] = dtF.strftime("%Y")
        d["doy"] = dtF.strftime("%j")
        d["markerName"] = self.rinex_reader.header.marker_name
        d["fileName"] = os.path.dirname(self.rinex_file)
        return d

    def __create_reader(self, rinex_version) -> RinexObsReader:
        self.rinex_reader: Optional[RinexObsReader] = None
        self._create_reader(self.rinex_version)

    def _create_reader(self, rinex_version: int, **reader_kwargs) -> None:
        """Create a RINEX reader instance for the specified version.

        Args:
            rinex_version: RINEX format version (2 or 3).
            **reader_kwargs: Additional arguments passed to reader constructor.
        """
        self.rinex_reader = self.rinex_reader_factory.create_obs_reader_by_version(
            rinex_version
        )(**reader_kwargs)

    def do_create_datadict(self):
        """Read Rinex file and create datadict."""
        assert self.rinex_file != "", "Rinex file not specified"
        assert os.path.exists(
            self.rinex_file
        ), f"Could not find file ({self.rinex_file})"

        self.rinex_reader.set_rinex_obs_file(self.rinex_file)
        self.rinex_reader.read_header_from_file()
        self.rinex_reader.read_epochs_from_file()

    def do_clear_datadict(self) -> None:
        """Clear unused observation types from header data.

        Reads all epochs to find observation types that don't have data,
        then removes them from the header.
        """
        found_obs_types = {}
        for sat_sys in self.rinex_reader.header.sys_obs_types.keys():
            found_obs_types[sat_sys] = set()

        # Iterate through all epochs and satellites to find used obs types
        for rinex_epoch in self.rinex_reader.rinex_epochs:
            for item in rinex_epoch.satellites:
                sat_sys = item.id[0]  # Satellite system (G, R, E, C, J, S)
                for sat_obs in item.observations:
                    found_obs_types[sat_sys].add(sat_obs.code)

        # Remove obs types from header that weren't found in any epoch
        for sat_sys in self.rinex_reader.header.sys_obs_types:
            input_obs_types = set(self.rinex_reader.header.sys_obs_types[sat_sys])
            for obs_type in input_obs_types - found_obs_types[sat_sys]:
                logger.info(f"Remove unused OBS TYPE {obs_type}")
                self.rinex_reader.header.sys_obs_types[sat_sys].remove(obs_type)

    def run(self) -> None:
        """Run the parser on the configured RINEX file.

        Raises:
            FileNotFoundError: If the RINEX file does not exist.
        """
        if not os.path.isfile(self.rinex_file):
            raise FileNotFoundError(f"Not a file: {self.rinex_file}")
        self.do_create_datadict()
        # remove unused header
        if self.filter_on_read:
            logger.debug(f"Filter data {self.rinex_file}")
            self.do_clear_datadict()
        # crop epochs to time windows
        cleared_epochs = []
        for epoch in self.rinex_reader.rinex_epochs:
            # CROP
            if epoch.timestamp < self.rinex_reader.crop_beg:
                continue
            if epoch.timestamp > self.rinex_reader.crop_end:
                continue
            # APPEND
            cleared_epochs.append(epoch)

        self.rinex_reader.rinex_epochs = cleared_epochs
        self.rinex_reader.header.first_observation = ts_to_datetime(
            self.rinex_reader.rinex_epochs[0].timestamp
        )
        self.rinex_reader.header.last_observation = ts_to_datetime(
            self.rinex_reader.rinex_epochs[-1].timestamp
        )

    def to_rinex3(self, country: str = "XXX", use_raw: bool = False):

        self.rinex_reader.header.first_observation = ts_to_datetime(
            self.rinex_reader.rinex_epochs[0].timestamp
        )
        self.rinex_reader.header.last_observation = ts_to_datetime(
            self.rinex_reader.rinex_epochs[-1].timestamp
        )
        out_file = os.path.join(
            os.path.dirname(self.rinex_file), self.get_rx3_long(country)
        )

        # make sure parser and header have the same obs types:
        for sat_sys in self.rinex_reader.header.sys_obs_types.keys():
            if set(self.rinex_reader.header.sys_obs_types[sat_sys]) != set(
                self.rinex_reader.found_obs_types[sat_sys]
            ):
                logger.warning("OBS Type missmatch!")

        # Output Rinex File
        logger.debug(f"Append Header")
        outlines = ["\n".join(self.rinex_reader.header.to_rinex3())]
        outlines += ["\n"]
        logger.debug(f"Append Epochs")
        outlines += self.rinex_reader.to_rinex3(
            use_raw=use_raw,
            sys_obs_types=self.rinex_reader.header.sys_obs_types,
            sys_order=self.rinex_reader.header.sys_obs_types.keys(),
        )
        # outlines += ["\n"]
        logger.debug(f"Start writing to file {out_file}.")
        with open(out_file, "w") as rnx:
            rnx.writelines(outlines)
        logger.info(f"Done writing to file {out_file}.")
