import os
import argparse
import datetime

from rinex_parser.obs_parser import RinexParser, EPOCH_MAX, EPOCH_MIN
from rinex_parser.logger import logger

parser = argparse.ArgumentParser()
parser.add_argument("finp", help="Path to input file")
parser.add_argument("--fout", type=str, default="", help="Path to output file")
parser.add_argument("--smp", type=int, default=0, help="Sampling Rate for output")
parser.add_argument("--country", type=str, default="XXX", help="Country Flag to use")
parser.add_argument("--rnx-version", type=int, choices=[2,3], default=3, help="Output rinex version. Currently only 3")
parser.add_argument("--crop-beg", type=float, default=EPOCH_MIN, help="Crop Window Beg, Unix Timestamp")
parser.add_argument("--crop-end", type=float, default=EPOCH_MAX, help="Crop Window End, Unix Timestamp")


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

    if args.fout:
        out_dir = os.path.dirname(args.fout)
        out_fil = os.path.basename(args.fout)
        if out_fil == "::RX3::":
            out_fil = rnx_parser.get_rx3_long(country=args.country)
        if out_dir == "":
            out_dir = os.path.dirname(args.finp)
        out_file = os.path.join(out_dir, out_fil)
    else:
        out_file = os.path.join(
            os.path.dirname(args.finp),
            rnx_parser.get_rx3_long(country=args.country)
        )

    # Output Rinex File
    with open(out_file, "w") as rnx:
        logger.info(f"Write to file: {out_file}")
        rnx.write(rnx_parser.rinex_reader.header.to_rinex3())
        rnx.write("\n")
        rnx.write(rnx_parser.rinex_reader.to_rinex3())
        rnx.write("\n")

    logger.info("Done processing")
