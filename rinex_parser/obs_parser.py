#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of rinexparser.
# https://github.com/dach.pos/rinexparser

# Licensed under the Apache 2.0 license:
# http://opensource.org/licenses/apache2.0
# Copyright (c) 2018, jiargei <juergen.fredriksson@bev.gv.at>

import os
import argparse

from rinex_parser.logger import logger
from rinex_parser.obs_reader import RinexObsReaderFactory


def run():
    parser = argparse.ArgumentParser(description="Analyse your Rinex files.")
    parser.add_argument("file", type=str, help="rinex file including full path")
    parser.add_argument("version", type=int, help="rinex version (2 or 3)")
    args = parser.parse_args()
    rinex_parser = RinexParser(rinex_version=args.version, rinex_file=args.file)
    rinex_parser.run()


class RinexParser():

    def __init__(self, *args, **kwargs):
        rinex_version = kwargs.get("rinex_version", 2)
        assert rinex_version in [2, 3]
        self.rinex_version = rinex_version
        self.rinex_file = kwargs.get("rinex_file", "")
        if self.rinex_file != "":
            self.set_rinex_file(self.rinex_file)
        self.rinex_reader_factory = RinexObsReaderFactory()
        self.__create_reader(self.rinex_version)

    @property
    def datadict(self):
        return self.get_datadict()

    def get_datadict(self):
        return self.rinex_reader.datadict

    def __create_reader(self, rinex_version):
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
        assert self.rinex_file != ""
        self.rinex_reader.set_rinex_obs_file(self.rinex_file)
        self.rinex_reader.read_header()
        # logger.info("done with header")
        self.rinex_reader.read_data_to_dict()

    def run(self):
        if os.path.isfile(self.rinex_file):
            self.do_create_datadict()
