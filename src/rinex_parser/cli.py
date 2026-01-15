#!/usr/bin/env python3
"""Command-line interface for RinexParser."""

import argparse
import datetime
import gzip
import logging
import os
import sys
import traceback
import cProfile
import pstats

from pathlib import Path
from typing import Optional


from rinex_parser.logger import logger
from rinex_parser.obs_parser import RinexParser, EPOCH_MIN, EPOCH_MAX
from rinex_parser.obs_quality import RinexQuality


def detect_rinex_version(rinex_file: str) -> int:
    """Detect RINEX file version by reading first line."""
    try:
        # Handle gzipped files
        if rinex_file.endswith(".gz"):
            with gzip.open(rinex_file, "rt") as f:
                first_line = f.readline()
        else:
            with open(rinex_file, "r") as f:
                first_line = f.readline()

        # RINEX version is in columns 0-9, format like "     3.04"
        if first_line:
            version_str = first_line[0:9].strip()
            return int(float(version_str))
    except Exception as e:
        logger.warning(f"Could not detect version from {rinex_file}: {e}")

    return 3  # Default to version 3


def get_output_filename(input_file: str, operation: str, suffix: str = "rnx") -> str:
    """Generate output filename based on input and operation."""
    base = Path(input_file).stem

    return f"{base}_{operation}.{suffix}"


def parse_crop_timestamp(timestamp_str: str) -> Optional[float]:
    """Parse ISO format timestamp string to epoch time.

    Args:
        timestamp_str: Timestamp in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).

    Returns:
        float: Epoch timestamp, or None if parsing fails.
    """
    if not timestamp_str:
        return None

    try:
        # Try parsing with time component
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt0 = datetime.datetime.strptime(timestamp_str, fmt)
                # Assume UTC if no timezone provided
                if dt0.tzinfo is None:
                    dt = datetime.datetime(
                        dt0.year,
                        dt0.month,
                        dt0.day,
                        dt0.hour,
                        dt0.minute,
                        dt0.second,
                        dt0.microsecond,
                        tzinfo=datetime.timezone.utc,
                    )
                return dt.timestamp()
            except ValueError:
                continue

        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None
    except Exception as e:
        logger.warning(f"Error parsing timestamp '{timestamp_str}': {e}")
        return None


def create_parser() -> argparse.ArgumentParser:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="rxp", description="RINEX observation file parser and processor"
    )

    parser.add_argument(
        "rinex_files", nargs="+", help="RINEX observation file(s) to process"
    )

    parser.add_argument(
        "--resample",
        type=int,
        metavar="SECONDS",
        help="Resample observations to specified interval (seconds)",
    )

    parser.add_argument(
        "--rinstat", action="store_true", help="Generate RINSTAT quality report"
    )

    parser.add_argument(
        "--rinstat-json",
        action="store_true",
        help="Generate RINSTAT quality report in JSON format",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output filename (auto-generated if not specified)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--show-output",
        action="store_true",
        help="Print the generated output to console",
    )

    parser.add_argument(
        "--crop-start",
        metavar="DATETIME",
        help="Start time for cropping (ISO format: YYYY-MM-DD[[T]HH:MM:SS], YYYY-DOY)",
    )

    parser.add_argument(
        "--crop-end",
        metavar="DATETIME",
        help="End time for cropping (ISO format: YYYY-MM-DD[[T]HH:MM:SS], YYYY-DOY)",
    )

    parser.add_argument(
        "--filter-sat-pnr",
        type=str,
        default="",
        help="Remove satellites (G01,R04,E12,...)",
    )
    parser.add_argument(
        "--filter-sat-sys",
        type=str,
        default="",
        help="Remove satellite system (G,I,S) from epoch.",
    )
    parser.add_argument(
        "--filter-sat-obs",
        type=str,
        default="",
        help="Remove observation type (G1C,R1C,E8I,C6Q).",
    )
    return parser


def parse_arguments() -> argparse.Namespace:
    parser = create_parser()
    return parser.parse_args()


def process_resample(
    parser: RinexParser,
    output_file: Optional[str] = None,
    show_output: bool = False,
) -> None:
    """Resample RINEX observations to specified interval."""
    logger.info(f"Resampling {parser.rinex_file} to {parser.sampling}s interval")

    try:
        logger.info("Creating data dictionary.")
        parser.do_create_datadict()
        # parser.rinex_reader.do_thinning(interval)

        # Write output
        logger.info("Preparing output filename.")
        country = parser.get_country_from_filename()
        out_dir = os.path.dirname(parser.rinex_file)
        out_fil = parser.get_rx3_long(country=country)

        if output_file is None or output_file == "" or output_file == "::RX3::":
            pass
        else:
            out_fil = os.path.basename(output_file)
            out_dir = os.path.dirname(output_file)

        output_file = os.path.join(out_dir, out_fil)

        # Write RINEX file
        logger.info(f"Writing resampled RINEX to {output_file}.")
        with open(output_file, "w") as f:
            f.write(parser.rinex_reader.to_rinex3())

        logger.info(f"Output written to {output_file}.")

        if show_output:
            with open(output_file, "r") as f:
                print(f.read())

    except Exception as e:
        logger.error(f"Error resampling {parser.rinex_file}: {e}")
        raise


def process_rinstat(
    parser: RinexParser,
    output_file: Optional[str] = None,
    show_output: bool = False,
    json_format: bool = False,
) -> None:
    """Generate RINSTAT quality report."""
    logger.info(f"Generating RINSTAT report for {parser.rinex_file}")

    try:

        parser.do_create_datadict()
        quality = RinexQuality()

        if json_format:
            rinstat_dict = quality.get_rinstat_as_dict(parser.rinex_reader)
            report = quality.to_json(rinstat_dict).strip()
        else:
            report = quality.get_rinstat_out(parser.rinex_reader)

        if output_file is None:
            suffix = "json" if json_format else "txt"
            output_file = get_output_filename(parser.rinex_file, "rinstat", suffix)

        output_file = os.path.abspath(output_file)

        with open(output_file, "w") as f:
            f.write(report)

        logger.info(f"Output written to: {output_file}")

        if show_output:
            print(report)

    except Exception as e:
        logger.error(f"Error generating RINSTAT for {parser.rinex_file}: {e}")
        raise


def process_rinex_file(rinex_file: str, args: argparse.Namespace) -> None:
    """Process a single RINEX file based on CLI arguments."""
    try:
        if not os.path.exists(rinex_file):
            logger.error(f"File not found: {rinex_file}")
            return 1

        # Parse crop timestamps
        crop_start = (
            parse_crop_timestamp(args.crop_start) if args.crop_start else EPOCH_MIN
        )
        crop_end = parse_crop_timestamp(args.crop_end) if args.crop_end else EPOCH_MAX

        kwargs = {
            "rinex_file": rinex_file,
            "sampling": args.resample if args.resample else 0,
            "crop_beg": crop_start,
            "crop_end": crop_end,
            # "skeleton": args.skeleton,
            "filter_sat_sys": args.filter_sat_sys,
            "filter_sat_pnr": args.filter_sat_pnr,
            "filter_sat_obs": args.filter_sat_obs,
        }

        rinex_version = detect_rinex_version(rinex_file)
        parser = RinexParser(
            rinex_file=rinex_file,
            rinex_version=rinex_version,
            crop_beg=crop_start,
            crop_end=crop_end,
            sampling=args.resample if args.resample else 0,
            filter_sat_obs=kwargs.get("filter_sat_obs", ""),
            filter_sat_pnr=kwargs.get("filter_sat_pnr", ""),
            filter_sat_sys=kwargs.get("filter_sat_sys", ""),
        )

        if args.resample >= 0:
            process_resample(
                parser,
                output_file=args.output,
                show_output=args.show_output,
            )
        elif args.rinstat or args.rinstat_json:
            process_rinstat(
                parser,
                output_file=args.output,
                show_output=args.show_output,
                json_format=args.rinstat_json,
            )
        else:
            logger.error(
                "Please specify an operation (--resample, --rinstat, or --rinstat-json)"
            )
            return 1
    except Exception as e:
        logger.error(f"Error processing {rinex_file}: {e}")
        raise

    return 0


def main() -> int:
    """Main entry point for CLI."""
    args = parse_arguments()

    # Setup logging
    if args.verbose:
        # logging.getLogger("rinex_parser").setLevel(logging.DEBUG)
        # logger.setLevel(logging.DEBUG)
        # start profiling
        profiler = cProfile.Profile()
        profiler.enable()

    try:
        for rinex_file in args.rinex_files:
            return process_rinex_file(rinex_file, args)
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        return 1

    finally:
        if args.verbose:
            # stop profiling
            profiler.disable()
            # Print profiling results
            stats = pstats.Stats(profiler)
            stats.sort_stats("cumulative")
            print("\n=== CPU Profiling Results ===")
            stats.print_stats(20)  # Top 20 functions


if __name__ == "__main__":
    sys.exit(main())
