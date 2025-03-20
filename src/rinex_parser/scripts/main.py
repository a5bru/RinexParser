import os
import argparse
import datetime

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
parser.add_argument("finp", help="Path to input file")
parser.add_argument("--fout", type=str, default="", help="Path to output file")
parser.add_argument("--smp", type=int, default=0, help="Sampling Rate for output")
parser.add_argument("--country", type=str, default="", help="Country Flag to use")
parser.add_argument(
    "--rnx-version",
    type=int,
    choices=[2, 3],
    default=3,
    help="Output rinex version. Currently only 3",
)
parser.add_argument(
    "--crop-beg", type=float, default=EPOCH_MIN, help="Crop Window Beg, Unix Timestamp"
)
parser.add_argument(
    "--crop-end", type=float, default=EPOCH_MAX, help="Crop Window End, Unix Timestamp"
)
parser.add_argument(
    "--skeleton", type=str, default="", help="Path to skeleton to edit header"
)


def run():
    args = parser.parse_args()
    assert os.path.exists(args.finp)

    rnx_parser = RinexParser(
        rinex_file=args.finp,
        rinex_version=args.rnx_version,
        sampling=args.smp,
        crop_beg=args.crop_beg,
        crop_end=args.crop_end,
    )
    rnx_parser.run()
    country = args.country
    if country == "":
        country = "XXX"

    if args.skeleton:
        if os.path.exists(args.skeleton):
            header_lines = ""
            with open(args.skeleton, "r") as skel:
                for line in skel.readlines():
                    if line == "":
                        break
                    # What rinex fields are relevant?
                    for field in list(SKEL_FIELDS):
                        if field in line[60:]:
                            header_lines += line
                            break
            rnx_header = Rinex3ObsHeader.from_header(header_lines)
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
            if args.country == "":
                for comment in rnx_header.comment.split("\n"):
                    if comment.startswith("CountryCode="):
                        country = comment[12:15]
                    else:
                        country = "XXX"
            else:
                country = args.country.strip()[:3]

        else:
            logger.warning("Skeleton not found, continue")

    if args.fout:
        out_dir = os.path.dirname(args.fout)
        out_fil = os.path.basename(args.fout)
        if out_fil == "::RX3::":
            out_fil = rnx_parser.get_rx3_long(country=country)
        if out_dir == "":
            out_dir = os.path.dirname(args.finp)
        out_file = os.path.join(out_dir, out_fil)
    else:
        out_file = os.path.join(
            os.path.dirname(args.finp), rnx_parser.get_rx3_long(country=country)
        )

    # Output Rinex File
    with open(out_file, "w") as rnx:
        logger.info(f"Write to file: {out_file}")
        rnx.write(rnx_parser.rinex_reader.header.to_rinex3())
        rnx.write("\n")
        rnx.write(rnx_parser.rinex_reader.to_rinex3())
        rnx.write("\n")

    logger.info("Done processing")
