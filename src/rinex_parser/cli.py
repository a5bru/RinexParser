#!/usr/bin/env python3
"""Command-line interface for RinexParser."""

import argparse
import gzip
import logging
import os
import sys
import traceback

from pathlib import Path
from typing import List, Optional

from rinex_parser.logger import logger
from rinex_parser.obs_parser import RinexParser
from rinex_parser.obs_quality import RinexQuality


def detect_rinex_version(rinex_file: str) -> int:
    """Detect RINEX file version by reading first line."""
    try:
        # Handle gzipped files
        if rinex_file.endswith('.gz'):
            with gzip.open(rinex_file, 'rt') as f:
                first_line = f.readline()
        else:
            with open(rinex_file, 'r') as f:
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


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='rxp',
        description='RINEX observation file parser and processor'
    )
    
    parser.add_argument(
        'rinex_files',
        nargs='+',
        help='RINEX observation file(s) to process'
    )
    
    parser.add_argument(
        '--resample',
        type=int,
        metavar='SECONDS',
        help='Resample observations to specified interval (seconds)'
    )
    
    parser.add_argument(
        '--rinstat',
        action='store_true',
        help='Generate RINSTAT quality report'
    )
    
    parser.add_argument(
        '--rinstat-json',
        action='store_true',
        help='Generate RINSTAT quality report in JSON format'
    )
    
    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Output filename (auto-generated if not specified)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--show-output',
        action='store_true',
        help='Print the generated output to console'
    )
    
    return parser.parse_args()


def process_resample(
    rinex_file: str,
    interval: int,
    output_file: Optional[str] = None,
    verbose: bool = False,
    show_output: bool = False
) -> None:
    """Resample RINEX observations to specified interval."""
    logger.info(f"Resampling {rinex_file} to {interval}s interval")
    
    try:
        rinex_version = detect_rinex_version(rinex_file)
        parser = RinexParser(
            rinex_file=rinex_file,
            rinex_version=rinex_version
        )
        parser.do_create_datadict()
        parser.rinex_reader.do_thinning(interval)

        # Write output
        if output_file is None:
            output_file = get_output_filename(rinex_file, 'resample')
        
        output_file = os.path.abspath(output_file)

        # Write RINEX file
        with open(output_file, 'w') as f:
            f.write(parser.rinex_reader.to_rinex3())
        
        logger.info(f"Output written to: {output_file}")
        
        if show_output:
            with open(output_file, 'r') as f:
                print(f.read())
        
    except Exception as e:
        logger.error(f"Error resampling {rinex_file}: {e}")
        raise


def process_rinstat(
    rinex_file: str,
    json_format: bool = False,
    output_file: Optional[str] = None,
    verbose: bool = False,
    show_output: bool = False
) -> None:
    """Generate RINSTAT quality report."""
    logger.info(f"Generating RINSTAT report for {rinex_file}")
    
    try:
        rinex_version = detect_rinex_version(rinex_file)
        parser = RinexParser(
            rinex_file=rinex_file,
            rinex_version=rinex_version
        )
        parser.do_create_datadict()
        
        quality = RinexQuality()
        
        if json_format:
            rinstat_dict = quality.get_rinstat_as_dict(parser.rinex_reader)
            report = quality.to_json(rinstat_dict).strip()
        else:
            report = quality.get_rinstat_out(parser.rinex_reader)
        
        if output_file is None:
            suffix = 'json' if json_format else 'txt'
            output_file = get_output_filename(rinex_file, 'rinstat', suffix)
        
        output_file = os.path.abspath(output_file)
        
        with open(output_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Output written to: {output_file}")
        
        if show_output:
            print(report)
        
    except Exception as e:
        logger.error(f"Error generating RINSTAT for {rinex_file}: {e}")
        raise


def main() -> int:
    """Main entry point for CLI."""
    args = parse_arguments()
    
    # Setup logging
    if args.verbose:
        logging.getLogger('rinex_parser').setLevel(logging.DEBUG)
    
    try:
        for rinex_file in args.rinex_files:
            if not os.path.exists(rinex_file):
                logger.error(f"File not found: {rinex_file}")
                continue
            
            if args.resample:
                process_resample(
                    rinex_file,
                    args.resample,
                    args.output,
                    args.verbose,
                    args.show_output
                )
            elif args.rinstat or args.rinstat_json:
                process_rinstat(
                    rinex_file,
                    args.rinstat_json,
                    args.output,
                    args.verbose,
                    args.show_output
                )
            else:
                logger.error("Please specify an operation (--resample, --rinstat, or --rinstat-json)")
                return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
