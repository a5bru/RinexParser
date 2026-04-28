#!/usr/bin/python

import unittest
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

from rinex_parser.obs_quality import RinexQuality
from rinex_parser.obs_parser import RinexParser
from rinex_parser import cli
from rinex_parser.logger import logger

# logger.setLevel(logging.INFO)

RINEX3_FILE = "data/r3/AGOC/AGOC00SVK_R_20250750000_01H_30S_MO.rnx"
RINEX3_FILE = "data/r3/AGOC/AGOC00SVK_S_20250750000_01H_01S_MO.rnx"
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


class DummyRinexParser:
    target_name = "ABCD00AUT_R_20261000000_01H_30S_MO.rnx"

    def __init__(self, rinex_file: str, rinex_version: int):
        self.rinex_file = rinex_file
        self.rinex_version = rinex_version
        self.rinex_reader = SimpleNamespace(header=SimpleNamespace(country="AUT"))

    def do_create_datadict(self):
        return None

    def get_rx3_long(self, country: str = "XXX") -> str:
        return self.target_name


class NameConversionTestSuite(unittest.TestCase):
    def test_convert_name_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "legacy_name.obs")
            with open(source, "w") as f:
                f.write("dummy")

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=3), mock.patch(
                "rinex_parser.cli.RinexParser", DummyRinexParser
            ):
                result = cli.convert_single_rinex_name(source, apply=False)

            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(result["target"], os.path.join(tmp_dir, DummyRinexParser.target_name))
            self.assertTrue(os.path.exists(source))

    def test_convert_name_apply_rename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "legacy_name.obs")
            target = os.path.join(tmp_dir, DummyRinexParser.target_name)
            with open(source, "w") as f:
                f.write("dummy")

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=3), mock.patch(
                "rinex_parser.cli.RinexParser", DummyRinexParser
            ):
                result = cli.convert_single_rinex_name(source, apply=True)

            self.assertEqual(result["status"], "renamed")
            self.assertFalse(os.path.exists(source))
            self.assertTrue(os.path.exists(target))

    def test_convert_name_noop_when_already_compliant(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, DummyRinexParser.target_name)
            with open(source, "w") as f:
                f.write("dummy")

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=3), mock.patch(
                "rinex_parser.cli.RinexParser", DummyRinexParser
            ):
                result = cli.convert_single_rinex_name(source, apply=True)

            self.assertEqual(result["status"], "noop")
            self.assertTrue(os.path.exists(source))

    def test_convert_name_collision(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "legacy_name.obs")
            target = os.path.join(tmp_dir, DummyRinexParser.target_name)
            with open(source, "w") as f:
                f.write("dummy")
            with open(target, "w") as f:
                f.write("already exists")

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=3), mock.patch(
                "rinex_parser.cli.RinexParser", DummyRinexParser
            ):
                result = cli.convert_single_rinex_name(source, apply=True)

            self.assertEqual(result["status"], "collision")
            self.assertTrue(os.path.exists(source))

    def test_convert_name_skips_version_2(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "legacy_name.18o")
            with open(source, "w") as f:
                f.write("dummy")

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=2), mock.patch(
                "rinex_parser.cli.RinexParser"
            ) as parser_cls:
                result = cli.convert_single_rinex_name(source, apply=True)

            self.assertEqual(result["status"], "skip-v2")
            parser_cls.assert_not_called()
            self.assertTrue(os.path.exists(source))

    def test_collect_convert_candidates_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            supported = os.path.join(tmp_dir, "a.rnx")
            supported_gz = os.path.join(tmp_dir, "b.obs.gz")
            unsupported = os.path.join(tmp_dir, "ignore.txt")
            with open(supported, "w") as f:
                f.write("dummy")
            with open(supported_gz, "w") as f:
                f.write("dummy")
            with open(unsupported, "w") as f:
                f.write("dummy")

            args = SimpleNamespace(
                rinex_files=[],
                input_dir=[tmp_dir],
                recursive=False,
            )
            candidates = cli.collect_convert_name_candidates(args)

            self.assertEqual(len(candidates), 2)
            self.assertIn(os.path.abspath(supported), candidates)
            self.assertIn(os.path.abspath(supported_gz), candidates)


if __name__ == "__main__":
    unittest.main()
