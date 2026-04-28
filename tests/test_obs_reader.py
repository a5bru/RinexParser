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
        self.rinex_reader = SimpleNamespace(
            rinex_obs_file=rinex_file,
            header=SimpleNamespace(
                country="AUT",
                first_observation=1,
                last_observation=3601,
            ),
            read_header_from_file=lambda: None,
            read_epochs_from_file=lambda: None,
        )

    def do_create_datadict(self):
        return None

    def get_rx3_long(self, country: str = "XXX", ts_source: str = "epoch", origin: str = None) -> str:
        return self.target_name


class DummyFallbackReader:
    def __init__(self):
        self.rinex_obs_file = ""
        self.header = SimpleNamespace(
            country="AUT",
            first_observation=None,
            last_observation=None,
        )
        self.read_header_called = False
        self.read_epochs_called = False

    def read_header_from_file(self):
        self.read_header_called = True

    def read_epochs_from_file(self):
        self.read_epochs_called = True


class DummyRinexParserFilenameFallback:
    target_name = "ABCD00AUT_R_20261000000_01H_30S_MO.rnx"

    def __init__(self, rinex_file: str, rinex_version: int):
        self.rinex_file = rinex_file
        self.rinex_version = rinex_version
        self.rinex_reader = DummyFallbackReader()

    def do_create_datadict(self):
        raise ValueError(
            f"Invalid RINEX filename for version 3.03: {os.path.basename(self.rinex_file)}"
        )

    def get_rx3_long(self, country: str = "XXX", ts_source: str = "epoch", origin: str = None) -> str:
        return self.target_name


class DummyRinexParserCountryAware:
    def __init__(self, rinex_file: str, rinex_version: int):
        self.rinex_file = rinex_file
        self.rinex_version = rinex_version
        self.rinex_reader = SimpleNamespace(
            rinex_obs_file=rinex_file,
            header=SimpleNamespace(
                country="XXX",
                first_observation=1,
                last_observation=3601,
            ),
            read_header_from_file=lambda: None,
            read_epochs_from_file=lambda: None,
        )

    def do_create_datadict(self):
        return None

    def get_rx3_long(self, country: str = "XXX", ts_source: str = "epoch", origin: str = None) -> str:
        return f"ABCD00{country}_R_20261000000_01H_30S_MO.rnx"


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

    def test_convert_name_fallback_on_invalid_v3_filename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "amst058e.26o")
            target = os.path.join(tmp_dir, DummyRinexParserFilenameFallback.target_name)
            with open(source, "w") as f:
                f.write("dummy")

            parser_instances = []

            def parser_factory(rinex_file: str, rinex_version: int):
                parser = DummyRinexParserFilenameFallback(rinex_file, rinex_version)
                parser_instances.append(parser)
                return parser

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=3), mock.patch(
                "rinex_parser.cli.RinexParser", side_effect=parser_factory
            ):
                result = cli.convert_single_rinex_name(source, apply=False)

            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(result["target"], target)
            self.assertEqual(len(parser_instances), 1)
            self.assertTrue(parser_instances[0].rinex_reader.read_header_called)
            self.assertTrue(parser_instances[0].rinex_reader.read_epochs_called)

    def test_collect_convert_candidates_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            supported = os.path.join(tmp_dir, "a.rnx")
            supported_gz = os.path.join(tmp_dir, "b.obs.gz")
            supported_r2_daily = os.path.join(tmp_dir, "amst0580.26o")
            supported_r2_hourly = os.path.join(tmp_dir, "amst058e.26o")
            unsupported = os.path.join(tmp_dir, "ignore.txt")
            with open(supported, "w") as f:
                f.write("dummy")
            with open(supported_gz, "w") as f:
                f.write("dummy")
            with open(supported_r2_daily, "w") as f:
                f.write("dummy")
            with open(supported_r2_hourly, "w") as f:
                f.write("dummy")
            with open(unsupported, "w") as f:
                f.write("dummy")

            args = SimpleNamespace(
                rinex_files=[],
                input_dir=[tmp_dir],
                recursive=False,
            )
            candidates = cli.collect_convert_name_candidates(args)

            self.assertEqual(len(candidates), 4)
            self.assertIn(os.path.abspath(supported), candidates)
            self.assertIn(os.path.abspath(supported_gz), candidates)
            self.assertIn(os.path.abspath(supported_r2_daily), candidates)
            self.assertIn(os.path.abspath(supported_r2_hourly), candidates)

    def test_collect_convert_candidates_from_hourly_glob(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hourly = os.path.join(tmp_dir, "amst058e.26o")
            daily = os.path.join(tmp_dir, "amst0580.26o")
            with open(hourly, "w") as f:
                f.write("dummy")
            with open(daily, "w") as f:
                f.write("dummy")

            args = SimpleNamespace(
                rinex_files=[os.path.join(tmp_dir, "amst058[a-x].26o")],
                input_dir=[],
                recursive=False,
            )
            candidates = cli.collect_convert_name_candidates(args)

            self.assertEqual(len(candidates), 1)
            self.assertIn(os.path.abspath(hourly), candidates)

    def test_convert_name_uses_default_country(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "amst058e.26o")
            with open(source, "w") as f:
                f.write("dummy")

            with mock.patch("rinex_parser.cli.detect_rinex_version", return_value=3), mock.patch(
                "rinex_parser.cli.RinexParser", DummyRinexParserCountryAware
            ):
                result = cli.convert_single_rinex_name(
                    source,
                    apply=False,
                    default_country="AUT",
                )

            self.assertEqual(result["status"], "dry-run")
            self.assertTrue(result["target"].endswith("ABCD00AUT_R_20261000000_01H_30S_MO.rnx"))

    def test_resolve_default_country_precedence(self):
        args = SimpleNamespace(default_country="deu")
        self.assertEqual(cli.resolve_default_country(args), "DEU")

    def test_resolve_default_country_env(self):
        args = SimpleNamespace(default_country="")
        with mock.patch.dict(os.environ, {"RXP_DEFAULT_COUNTRY": "aut"}, clear=False):
            with mock.patch("rinex_parser.cli.read_country_from_dotenv", return_value=None):
                self.assertEqual(cli.resolve_default_country(args), "AUT")

    def test_resolve_default_country_dotenv(self):
        args = SimpleNamespace(default_country="")
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("rinex_parser.cli.read_country_from_dotenv", return_value="CHE"):
                self.assertEqual(cli.resolve_default_country(args), "CHE")

    def test_resolve_default_origin_cli(self):
        args = SimpleNamespace(default_origin="r")
        self.assertEqual(cli.resolve_default_origin(args), "R")

    def test_resolve_default_origin_env(self):
        args = SimpleNamespace(default_origin="")
        with mock.patch.dict(os.environ, {"RXP_DEFAULT_ORIGIN": "S"}, clear=False):
            with mock.patch("rinex_parser.cli.read_origin_from_dotenv", return_value=None):
                self.assertEqual(cli.resolve_default_origin(args), "S")

    def test_resolve_default_origin_dotenv(self):
        args = SimpleNamespace(default_origin="")
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("rinex_parser.cli.read_origin_from_dotenv", return_value="R"):
                self.assertEqual(cli.resolve_default_origin(args), "R")

    def test_resolve_default_origin_invalid(self):
        args = SimpleNamespace(default_origin="X")
        self.assertIsNone(cli.resolve_default_origin(args))

    def test_normalize_origin_allowed_values(self):
        self.assertEqual(cli.normalize_origin("R"), "R")
        self.assertEqual(cli.normalize_origin("S"), "S")
        self.assertEqual(cli.normalize_origin("r"), "R")
        self.assertIsNone(cli.normalize_origin("X"))
        self.assertIsNone(cli.normalize_origin(""))
        self.assertIsNone(cli.normalize_origin(None))


if __name__ == "__main__":
    unittest.main()
