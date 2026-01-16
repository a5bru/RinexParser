#!/usr/bin/env python3
"""Command-line interface for RinexParser."""

import argparse
import datetime
import gzip
import os
import sys
import traceback
import cProfile
import pstats
import threading
import queue
import logging
import time

from pathlib import Path
from typing import Optional, List, Tuple, Dict


from rinex_parser.logger import logger
from rinex_parser.obs_parser import (
    RinexParser,
    RinexParserResult,
    EPOCH_MIN,
    EPOCH_MAX,
)
from rinex_parser.obs_quality import RinexQuality
from rinex_parser.obs_epoch import RinexEpoch
from rinex_parser.utils import handle_rx3_info
from rinex_parser import __version__ as VERSION


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

    parser.add_argument("--profile", action="store_true", help="Enable CPU profiling")

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
    parser.add_argument(
        "-t",
        "--skeleton",
        type=str,
        default="",
        help="Path to skeleton file to edit header",
    )

    parser.add_argument(
        "-m",
        "--merge",
        action="store_true",
        help="Merge multiple RINEX files",
    )

    parser.add_argument(
        "-n", "--threads", type=int, default=1, help="Number of threads to use"
    )

    parser.add_argument(
        "--version", action="version", version=f"RinexParser v{VERSION}"
    )

    return parser


def parse_arguments() -> argparse.Namespace:
    parser = create_parser()
    return parser.parse_args()


def process_resample(
    parser: RinexParser,
    output_file: Optional[str] = None,
    show_output: bool = False,
    skeleton_file: Optional[str] = None,
) -> str:
    """Resample RINEX observations to specified interval."""
    logger.info(f"Resampling {parser.rinex_file} to {parser.sampling}s interval")

    try:
        logger.debug(f"Creating data dictionary {output_file}.")
        parser.do_create_datadict()
        # parser.rinex_reader.do_thinning(interval)

        # Write output
        logger.debug(f"Preparing output filename {output_file}.")

        country_file_in = parser.get_country_from_filename()
        country_file_out = "XXX"

        # Apply skeleton if provided
        if skeleton_file:
            parser.rinex_reader.header.apply_skeleton(skeleton_file)

        if output_file:
            country_file_out = parser.rinex_reader.header.get_country_from_filename(
                output_file
            )
            parser.rinex_reader.header.marker_name = (
                parser.rinex_reader.header.get_marker_name_from_filename(output_file)
            )

        # Determine country with priority: file_in > skeleton > file_out > XXX
        parser.rinex_reader.header.country = (
            parser.rinex_reader.header.determine_country(
                country_file_in, country_file_out
            )
        )

        out_dir = os.path.dirname(parser.rinex_file)

        if output_file is None or output_file == "":
            out_fil = parser.get_rx3_long(country=parser.rinex_reader.header.country)

        # get info from rx3 indicator '::RX3-cAUT-sGRAZ::
        elif output_file.startswith("::RX3"):
            rx3_info = handle_rx3_info(output_file)
            if rx3_info.country:
                parser.rinex_reader.header.country = rx3_info.country
            if rx3_info.marker_name:
                parser.rinex_reader.header.marker_name = rx3_info.marker_name
            if rx3_info.receiver_id:
                parser.rinex_reader.header.receiver_id = rx3_info.receiver_id
            if rx3_info.monument_id:
                parser.rinex_reader.header.monument_id = rx3_info.monument_id
            out_fil = parser.get_rx3_long(country=parser.rinex_reader.header.country)
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

    return output_file


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

    return output_file


def process_rinex_file(rinex_file: str, args: argparse.Namespace) -> RinexParserResult:
    """Process a single RINEX file based on CLI arguments."""

    output_file = args.output
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
            "skeleton": args.skeleton,
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
            output_file = process_resample(
                parser,
                output_file=args.output,
                show_output=args.show_output,
                skeleton_file=args.skeleton,
            )
        elif args.rinstat or args.rinstat_json:
            output_file = process_rinstat(
                parser,
                output_file=args.output,
                show_output=args.show_output,
                json_format=args.rinstat_json,
            )
        else:
            logger.error(
                "Please specify an operation (--resample, --rinstat, or --rinstat-json)"
            )
            return RinexParserResult(None, None)
    except Exception as e:
        logger.error(f"Error processing {rinex_file}: {e}")
        raise

    return RinexParserResult(output_file, parser)


LIST_LOCK = threading.Lock()


def run_thread(
    queue: queue.Queue,
    namespace: argparse.Namespace,
    path_list: List[Tuple[str, RinexParser]],
):
    while not queue.empty():
        try:
            path = queue.get()
            logger.debug(f"Process {path}")
            with LIST_LOCK:
                path_list.append(
                    process_rinex_file(
                        rinex_file=path,
                        args=namespace,
                    )
                )
                logger.debug(f"Appended {path_list[-1].rinex_file}")
            queue.task_done()
        except Exception as e:
            logger.error(f"Error in thread processing {path}: {e}")
            traceback.print_exc()


def main() -> int:
    """Main entry point for CLI."""
    args = parse_arguments()

    # Setup logging
    if args.profile:
        # start profiling
        profiler = cProfile.Profile()
        profiler.enable()

    if args.verbose:
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    parse_queue = queue.Queue()
    parse_threads: List[threading.Thread] = []

    parsed_files: List[RinexParserResult] = []
    grouped_files: Dict[str, List[RinexParserResult]] = {}
    paths = [f for f in args.rinex_files]

    kwargs = {}

    try:

        # Fill Queue with tasks
        for path in paths:
            assert os.path.exists(path)
            logger.debug(f"Queuing {path}")
            parse_queue.put(path)

        for _ in range(args.threads):
            t = threading.Thread(
                target=run_thread, args=(parse_queue, args, parsed_files)
            )
            parse_threads.append(t)
            t.start()

        while not parse_queue.empty():
            time.sleep(0.01)

        for t in parse_threads:
            t.join()
        logger.debug(f"Finished processing input file(s)")

        if args.merge:
            logger.info("Merging processed RINEX files")

            for item in parsed_files:
                if item.rinex_file is None or item.rinex_parser is None:
                    continue

                station = os.path.basename(item.rinex_file)[:4].upper().ljust(4, "X")
                if station not in grouped_files:
                    grouped_files[station] = []
                grouped_files[station].append(item)

            # merge each station's files
            for station in grouped_files.keys():
                groupd_files_len = len(grouped_files[station])
                if groupd_files_len <= 0:
                    logger.info(f"No files to merge for station {station}")
                    continue
                elif groupd_files_len == 1:
                    logger.info(f"Only one file for station {station}, skipping merge")
                    continue
                else:
                    logger.info(
                        f"Merging station {station} with {groupd_files_len} files"
                    )
                    # sort files by start time
                    result_list: List[RinexParserResult] = sorted(
                        list(grouped_files[station]),
                        key=lambda x: x.rinex_parser.rinex_reader.header.first_observation,
                    )
                    for rinex_result in result_list:
                        logger.info(f" - {rinex_result.rinex_file}")

                    result_list[0].rinex_parser.rinex_reader.update_header_obs()
                    result_list[0].rinex_parser.rinex_reader.header.last_observation = (
                        result_list[
                            -1
                        ].rinex_parser.rinex_reader.header.last_observation
                    )

                    output_dir = os.path.dirname(result_list[0].rinex_file)
                    output_file = "MERGED.rnx"
                    output_file = result_list[0].rinex_parser.get_rx3_long(
                        country=result_list[0].rinex_parser.rinex_reader.header.country,
                        ts_source="header",
                    )
                    output_file = os.path.join(output_dir, output_file)

                    logger.info(f"Writing merged RINEX to {output_file}.")

                    with open(output_file, "w") as f:
                        # write header from first file
                        f.write(
                            result_list[0].rinex_parser.rinex_reader.header.to_rinex3()
                        )
                        f.write("\n")
                        # write epochs from all files
                        for rinex_result in result_list:
                            logger.debug(
                                f"Processing RINEX 3 epochs ({rinex_result.rinex_file},{len(rinex_result.rinex_parser.rinex_epochs)} total)"
                            )
                            # TODO: check if header changes between files
                            differ = result_list[
                                0
                            ].rinex_parser.rinex_reader.header.has_other_info(
                                rinex_result.rinex_parser.rinex_reader.header
                            )

                            if differ:
                                # TODO: write epoch flag to rinex file
                                f.write(f">{'':30s}4 {len(differ)+1:2d}\n")
                                for field in differ:
                                    f.write(f"{field}\n")
                                f.write(
                                    f"{'  --> HEADER CHANGES DURING MERGE <--':60s}COMMENT\n"
                                )

                            # optimize epoch writing to avoid loading all epochs in memory
                            for rinex_epoch in rinex_result.rinex_parser.rinex_epochs:
                                f.write(rinex_epoch.to_rinex3())
                                f.write("\n")

                    logger.info(f"Merged output written to {output_file}.")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        return 1

    finally:
        if args.profile:
            # stop profiling
            profiler.disable()
            # Print profiling results
            stats = pstats.Stats(profiler)
            stats.sort_stats("cumulative")
            print("\n=== CPU Profiling Results ===")
            stats.print_stats(20)  # Top 20 functions
        return 0


if __name__ == "__main__":
    sys.exit(main())
