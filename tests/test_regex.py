#!/usr/bin/python
'''
Created on Oct 25, 2016

@author: jurgen
'''
import datetime
import os
import pprint
import re

from .context import rinex_parser

import unittest

from rinex_parser.logger import logger
from rinex_parser import constants

class RegexTestSuite(unittest.TestCase):
    """Advanced test cases."""


    def parse_rinex3(self, rnx3_obs_line):
        all_obs = []
        m = re.match(constants.RINEX3_DATA_OBSEVATION_REGEXP, rnx3_obs_line)
        if m:
            regexp_dict = m.groupdict()
            if "first_o" in regexp_dict and regexp_dict["first_o"] is not None:
                keys = ["obs", "lli", "ss"]
                for n in re.finditer(constants.RINEX3_MULTIPLE_OBS_REGEXP, rnx3_obs_line):
                    d = {}
                    n_filter = n.groups()[1:]
                    for i in range(len(n_filter)):
                        vs = n_filter[i].strip()
                        v = None if vs == "" else float(vs)
                        k = keys[i]
                        d.update({k: v})
                    all_obs.append(d)
            if "last_o" in regexp_dict and regexp_dict["last_o"] is not None:
                d = {
                    "lli": None, 
                    "ss": None,
                    "obs": float(regexp_dict["last_o"])
                }
                all_obs.append(d)
        return all_obs

    def parse_rinex2():
        d0 = datetime.datetime.now()
        rinex_file = os.path.join(
            os.path.dirname(__file__),
            "data", "2016", "218",
            # "trf2170a.16o"
            "CSOR2180.16O"
        )
        logger.info("Using RNX: %s" % rinex_file)
        # ror = Rinex2ObsReader(
        #     rinex_obs_file=rinex_file
        # )
        ror = None
        ror.read_header()
        ror.read_data_to_dict()
        logger.info("chkday similar output:\n%s" % ror.get_availability())

        logger.info("update first and last observation")
        ror.update_header_obs()

        logger.info("to RINEX2")
        # logger.info("\n" + ror.to_rinex2())
        logger.info("\n" + ror.header.to_rinex2())

        logger.info("to RINEX3")
        # logger.info("\n" + ror.to_rinex3())
        logger.info("\n" + ror.header.to_rinex3())

        d1 = datetime.datetime.now()
        logger.info("Took %f seconds" % (d1 - d0).total_seconds())
    
    def test_rinex_3(self):
        logger.info("Test Rinex3::5")
        rnx3_obs_line = "G06  23619095.450      -53875.632 8    -41981.375 4  23619095.008          25.234"
        rnx3_obs_list = self.parse_rinex3(rnx3_obs_line)
        self.assertEqual(len(rnx3_obs_list), 5)

        logger.info("Test Rinex3::1")
        rnx3_obs_line = "G12        36.765"
        rnx3_obs_list = self.parse_rinex3(rnx3_obs_line)
        self.assertEqual(len(rnx3_obs_list), 1)

        logger.info("Test Rinex3::3")
        rnx3_obs_line = "G06  23619095.450      -53875.632 8    -41981.375 4"
        rnx3_obs_list = self.parse_rinex3(rnx3_obs_line)
        self.assertEqual(len(rnx3_obs_list), 3)

        logger.info("Test Rinex3::5")
        rnx3_obs_line = "G06  23619095.450      -53875.632 8    -41981.375 4                        25.234"
        rnx3_obs_list = self.parse_rinex3(rnx3_obs_line)
        self.assertEqual(len(rnx3_obs_list), 5)

        logger.info("Test Rinex3::1")
        rnx3_obs_line = "G06    -41981.375 4"
        rnx3_obs_list = self.parse_rinex3(rnx3_obs_line)
        self.assertEqual(len(rnx3_obs_list), 1)

if __name__ == "__main__":
    unittest.main()
