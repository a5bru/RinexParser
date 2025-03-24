#!/usr/bin/python

import unittest
import os

from rinex_parser.obs_quality import RinexQuality
from rinex_parser.obs_parser import RinexParser
from rinex_parser.logger import logger

# logger.setLevel(logging.INFO)

RINEX3_FILE = "data/r3/AGOC00SVK_R_20250750000_01H_30S_MO.rnx"
RINEX3_FILE = "data/r3/AGOC00SVK_S_20250750000_01H_01S_MO.rnx"
RINEX2_FILE = "data/r2/graz2540.18o"


class ObsReaderTestSuite(unittest.TestCase):
    """Advanced test cases."""

    def test_rinex_parser(self):

        logger.info("Test RinexParser 2+3")

        def tmp(rnx_version, rnx_file):
            rnx_file = os.path.join(os.path.dirname(__file__), rnx_file)
            obs_parser = RinexParser(rinex_version=rnx_version, rinex_file=rnx_file)
            obs_parser.run()
            obs_quality = RinexQuality()
            logger.info("\n\n%s\n" % obs_quality.get_rinstat_out(obs_parser.datadict))
            logger.info(
                "\n\n%s\n" % obs_quality.get_rinex_availability(obs_parser.datadict)
            )
            logger.debug("-" * 80)

        l = [
            # [2, RINEX2_FILE],
            [3, RINEX3_FILE]
        ]

        for i in l:
            logger.info("Testing Rinex Version {}".format(i[0]))
            logger.info("Rinex File: {}".format(i[1]))
            tmp(i[0], i[1])
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
