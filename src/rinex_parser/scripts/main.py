import os
import argparse

from rinex_parser.obs_parser import RinexParser
from rinex_parser.logger import logger

parser = argparse.ArgumentParser()
parser.add_argument("finp")
parser.add_argument("--fout", type=str, default="")
parser.add_argument("--smp", type=int, default=0)
parser.add_argument("--country", type=str, default="XXX")
parser.add_argument("--rnx-version", type=int, choices=[2,3], default=3)


def run():
    args = parser.parse_args()
    assert os.path.exists(args.finp)
    
    rnx_parser = RinexParser(rinex_file=args.finp, rinex_version=args.rnx_version, sampling=args.smp)
    rnx_parser.run()

    if args.fout:
        out_file = args.fout
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
