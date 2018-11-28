#!/usr/bin/python

import unittest
import os
import pprint
import logging

from .context import rinex_parser

from rinex_parser.obs_quality import RinexQuality
from rinex_parser.obs_parser import RinexParser
from rinex_parser.logger import logger

# logger.setLevel(logging.INFO)

RINEX3_FILE = "data/GRAZ00AUT_R_20182540000_01D_30S_MO.rnx"
RINEX2_FILE = "data/graz2540.18o"

class ObsReaderTestSuite(unittest.TestCase):
    """Advanced test cases."""

    def test_rinex_parser(self):

        def tmp(rnx_version, rnx_file):
            rnx_file = os.path.join(os.path.dirname(__file__), rnx_file)
            obs_parser = RinexParser(rinex_version=rnx_version, rinex_file=rnx_file)
            obs_parser.run()
            obs_quality = RinexQuality()
            logger.info("\n\n%s\n" % obs_quality.get_rinstat_out(obs_parser.datadict))
            logger.info("\n\n%s\n" % obs_quality.get_rinex_availability(obs_parser.datadict))
            logger.debug("-"*80)

        l = [
            [2, RINEX2_FILE],
            [3, RINEX3_FILE]
        ]

        for i in l:
            logger.info("Testing Rinex Version {}".format(i[0]))
            logger.info("Rinex File: {}".format(i[1]))
            tmp(i[0], i[1])
            self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
