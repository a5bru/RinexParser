#!/usr/bin/python

import logging
import pprint

import obs_reader
import obs_quality
from logger import logger

logger.setLevel(logging.INFO)

RINEX3_FILE = "data/GRAZ00AUT_R_20182540000_01D_30S_MO.rnx"
RINEX2_FILE = "data/graz2540.18o"


def test_rinex3(rnx_file):
    obs_reader3 = obs_reader.Rinex3ObsReader(rinex_obs_file=rnx_file)
    obs_reader3.read_header()
    obs_reader3.read_data_to_dict()
    obs_quality3 = obs_quality.RinexQuality()
    print(obs_quality3.get_rinstat_out(obs_reader3.datadict))
    print(obs_quality3.get_rinex_availability(obs_reader3.datadict))


def test_rinex2(rnx_file):
    obs_reader2 = obs_reader.Rinex2ObsReader(rinex_obs_file=rnx_file)
    obs_reader2.read_header()
    obs_reader2.read_data_to_dict()
    obs_quality2 = obs_quality.RinexQuality()
    print(obs_quality2.get_rinstat_out(obs_reader2.datadict))
    print(obs_quality2.get_rinex_availability(obs_reader2.datadict))


if __name__ == "__main__":
    # test_rinex3(RINEX3_FILE)
    test_rinex2(RINEX2_FILE)
