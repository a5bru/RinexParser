#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of rinexparser.
# https://github.com/dach.pos/rinexparser

# Licensed under the Apache 2.0 license:
# http://opensource.org/licenses/apache2.0
# Copyright (c) 2018, jiargei <juergen.fredriksson@bev.gv.at>

import os
import argparse

import obs_reader


parser = argparse.ArgumentParser(description="Analyse your Rinex files.")
parser.add_argument("rinex_file", type=str, help="rinex file including full path")

args = parser.parse_args()


class RinexParser():

    def __init__(self, *args, **kwargs):
        rinex_version = kwargs.get("rinex_version", 3)
        assert rinex_version in [2, 3]
        self.__rinex_version = rinex_version
        self.__rinex_file = kwargs.get("rinex_file", "")
        self.__rinex_reader_factory = obs_reader.RinexObsReaderFactory()
        self.__create_reader(self.__rinex_version)

    def __create_reader(self, rinex_version):
        self.__rinex_reader = self.__rinex_reader_factory.create_obs_reader_by_version(
            self.__rinex_version
        )

    def get_rinex_file(self):
        return self.__rinex_file

    def parse_rinex(self, rinex_file):
        if not os.path.isfile(rinex_file):
            raise LookupError("is not a valid file: {}".format(rinex_file))
        self.__rinex_file = rinex_file
    
    def do_create_datadict(self):
        assert self.__rinex_file != ""


    def run(self):
