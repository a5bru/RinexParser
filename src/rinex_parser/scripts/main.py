from ast import arg
import os
import glob
import argparse
import queue
import time
import threading
import pathlib
import logging
import traceback
from typing import List, Tuple

from rinex_parser import __version__
from rinex_parser.obs_parser import RinexParser, EPOCH_MAX, EPOCH_MIN
from rinex_parser.obs_header import Rinex3ObsHeader
from rinex_parser.logger import logger

SKEL_FIELDS = [
    "MARKER NAME",
    "MARKER NUMBER",
    "MARKER TYPE",
    "REC # / TYPE / VERS",
    "ANT # / TYPE",
    "APPROX POSITION XYZ",
    "ANTENNA: DELTA H/E/N",
    "OBSERVER / AGENCY",
    "COMMENT",
]

parser = argparse.ArgumentParser()
parser.add_argument("finp", nargs="+", help="Path to input file(s)")
parser.add_argument(
    "-v", "--version", action="version", version=f"RinexParser v{__version__}"
)
parser.add_argument("--verbose", action="store_true", help="Show debug")
parser.add_argument("-o", "--fout", type=str, default="", help="Path to output file")
parser.add_argument(
    "-s", "--sampling", type=int, default=0, help="Sampling Rate for output"
)
parser.add_argument(
    "-d", "--delete", action="store_true", help="Delete origin file after processing"
)
parser.add_argument(
    "-c", "--country", type=str, default="XXX", help="Country ISO 3166-1 alpha-3"
)
parser.add_argument(
    "-m", "--merge", action="store_true", help="Merge files with same marker name."
)
parser.add_argument(
    "-fm", "--use-raw", action="store_true", help="Merge without checking obs types!"
)
parser.add_argument(
    "-r",
    "--rnx-version",
    type=int,
    choices=[2, 3],
    default=3,
    help="Output rinex version. Currently only 3",
)
parser.add_argument(
    "-b",
    "--crop-beg",
    type=float,
    default=EPOCH_MIN,
    help="Crop Window Beg, Unix Timestamp",
)
parser.add_argument(
    "-e",
    "--crop-end",
    type=float,
    default=EPOCH_MAX,
    help="Crop Window End, Unix Timestamp",
)
parser.add_argument(
    "-t", "--skeleton", type=str, default="", help="Path to skeleton to edit header"
)
parser.add_argument(
    "-n",
    "--threads",
    type=int,
    default=1,
    help="Number of threads to process rinex files",
)
parser.add_argument(
    "--remove-sat-pnr",
    type=str,
    default="",
    help="Remove satellites (G01,R04,E12,...)",
)
parser.add_argument(
    "--remove-sat-sys",
    type=str,
    default="",
    help="Remove satellite system (G,I,S) from epoch.",
)
parser.add_argument(
    "--remove-sat-obs",
    type=str,
    default="",
    help="Remove observation type (G1C,R1C,E8I,C6Q).",
)

LIST_LOCK = threading.Lock()


def run_thread(
    queue: queue.Queue, namespace: dict, path_list: List[Tuple[str, RinexParser]]
):
    while not queue.empty():
        try:
            path = queue.get()
            logger.debug(f"Process {path}")
            with LIST_LOCK:
                path_list.append(run_single(path, **namespace))
                logger.debug(f"Created {path_list[-1][0]}")
            queue.task_done()
        except Exception as e:
            traceback.print_exc()
            pass


def run():
    args = parser.parse_args()
    # paths = glob.glob(args.finp)
    paths = [f for f in args.finp]
    parsed_files = []
    grouped_files = {}

    logger.info("Start parsing rinex file(s).")

    if args.verbose:
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    parse_queue = queue.Queue()
    parse_threads: List[threading.Thread] = []

    # Fill Queue with tasks
    for path in paths:
        assert os.path.exists(path)
        logger.debug(f"Queuing {path}")
        parse_queue.put(path)

    # Start Threads
    kwargs = {
        "fout": args.fout,
        "rnx_version": args.rnx_version,
        "sampling": args.sampling,
        "crop_beg": args.crop_beg,
        "crop_end": args.crop_end,
        "country": args.country,
        "skeleton": args.skeleton,
        "filter_sat_sys": args.remove_sat_sys,
        "filter_sat_pnr": args.remove_sat_pnr,
        "filter_sat_obs": args.remove_sat_obs,
    }
    for _ in range(args.threads):
        t = threading.Thread(
            target=run_thread, args=(parse_queue, kwargs, parsed_files)
        )
        parse_threads.append(t)
        t.start()

    while not parse_queue.empty():
        time.sleep(0.01)

    for t in parse_threads:
        t.join()
    logger.debug(f"Finished processing input file(s)")

    for item in parsed_files:
        station = item[0][:4]
        if station not in grouped_files:
            grouped_files[station] = []
        grouped_files[station].append(item)

    for station in grouped_files.keys():
        for i, item in enumerate(grouped_files[station]):
            if args.merge:
                logger.debug("Start merging")
                if i == 0:
                    rnx_path, rnx_parser = grouped_files[station][0]
                else:
                    rnx_parser: RinexParser
                    # TODO check if marker names are the same...
                    rnx_parser2: RinexParser = grouped_files[station][i][1]
                    rnx_path2: str = grouped_files[station][i][0]
                    # rnx_parser.rinex_reader.header.set_comment(f"Add file {rnx_path2}")
                    if not args.use_raw:
                        for sat_sys in rnx_parser.rinex_reader.found_obs_types.keys():
                            if (
                                sat_sys in rnx_parser2.rinex_reader.found_obs_types
                                and set(
                                    rnx_parser.rinex_reader.found_obs_types[sat_sys]
                                )
                                == set(
                                    rnx_parser2.rinex_reader.found_obs_types[sat_sys]
                                )
                            ):
                                rnx_parser.rinex_reader.rinex_epochs += (
                                    rnx_parser2.rinex_reader.rinex_epochs
                                )
                            else:
                                logger.warning(
                                    f"Sat obs types do not align [{sat_sys}, {rnx_path}, {rnx_path2}]"
                                )
                    else:
                        logger.warning("Merging epochs without checking obs types.")
                        rnx_parser.rinex_reader.rinex_epochs += (
                            rnx_parser2.rinex_reader.rinex_epochs
                        )

                # generate rinex after last item
                if i == len(grouped_files[station]) - 1:
                    rnx_parser.to_rinex3(country=args.country, use_raw=args.use_raw)

            else:
                rnx_path, rnx_parser = grouped_files[station][i]
                rnx_parser: RinexParser
                rnx_path: str
                rnx_parser.to_rinex3(country=args.country)

    if args.delete:
        for path in paths:
            logger.info(f"Deleted {path}")
            pathlib.Path.unlink(path)


def run_single(
    finp: str,
    fout: str,
    rnx_version: int,
    sampling: int,
    crop_beg: float,
    crop_end: float,
    country: str = "XXX",
    skeleton: str = "",
    filter_sat_sys: str = "",
    filter_sat_pnr: str = "",
    filter_sat_obs: str = "",
) -> Tuple[str, RinexParser]:

    rnx_parser = RinexParser(
        rinex_file=finp,
        rinex_version=rnx_version,
        sampling=sampling,
        crop_beg=crop_beg,
        crop_end=crop_end,
        filter_sat_sys=filter_sat_sys,
        filter_sat_pnr=filter_sat_pnr,
        filter_sat_obs=filter_sat_obs,
    )
    rnx_parser.run()

    if len(finp) >= 34:
        country = finp[6:9].upper().ljust(3, "X")

    if skeleton:
        if os.path.exists(skeleton):
            header_lines = []
            with open(skeleton, "r") as skel:
                for line in skel.readlines():
                    if line == "":
                        break
                    # What rinex fields are relevant?
                    for field in list(SKEL_FIELDS):
                        if field in line[60:]:
                            header_lines.append(line)
                            break
            rnx_header = Rinex3ObsHeader.from_header("\n".join(header_lines))
            rnx_parser.rinex_reader.header.marker_name = rnx_header.marker_name
            rnx_parser.rinex_reader.header.marker_number = rnx_header.marker_number
            rnx_parser.rinex_reader.header.approx_position_x = (
                rnx_header.approx_position_x
            )
            rnx_parser.rinex_reader.header.approx_position_y = (
                rnx_header.approx_position_y
            )
            rnx_parser.rinex_reader.header.approx_position_z = (
                rnx_header.approx_position_z
            )
            rnx_parser.rinex_reader.header.receiver_number = rnx_header.receiver_number
            rnx_parser.rinex_reader.header.receiver_type = rnx_header.receiver_type
            rnx_parser.rinex_reader.header.receiver_version = (
                rnx_header.receiver_version
            )
            rnx_parser.rinex_reader.header.antenna_number = rnx_header.antenna_number
            rnx_parser.rinex_reader.header.antenna_type = rnx_header.antenna_type
            rnx_parser.rinex_reader.header.antenna_delta_height = (
                rnx_header.antenna_delta_height
            )
            rnx_parser.rinex_reader.header.antenna_delta_east = (
                rnx_header.antenna_delta_east
            )
            rnx_parser.rinex_reader.header.antenna_delta_north = (
                rnx_header.antenna_delta_north
            )
            rnx_parser.rinex_reader.header.observer = rnx_header.observer
            rnx_parser.rinex_reader.header.agency = rnx_header.agency
            if country == "" or country == "XXX":
                for comment in rnx_header.comment.split("\n"):
                    if comment.startswith("CountryCode="):
                        country = comment[12:15]
                    else:
                        country = "XXX"
            else:
                country = country.strip()[:3]

        else:
            logger.warning("Skeleton not found, continue")

    if fout:
        if len(country) != 3:
            country = "XXX"
        out_dir = os.path.dirname(fout)
        out_fil = os.path.basename(fout)
        if out_fil == "::RX3::":
            out_fil = rnx_parser.get_rx3_long(country=country)
        if out_dir == "":
            out_dir = os.path.dirname(finp)
        out_file = os.path.join(out_dir, out_fil)
    else:
        out_file = os.path.join(
            os.path.dirname(finp), rnx_parser.get_rx3_long(country=country)
        )
    return (out_file, rnx_parser)
