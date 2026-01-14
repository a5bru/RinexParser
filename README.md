# RinexParser

Python toolkit to parse, analyze, and resample RINEX observation files. Supports RINEX versions 2 and 3.

## Features

- Parse RINEX 2 and RINEX 3 observation files
- Resample/thin epochs to specified intervals
- Generate quality statistics (rinstat reports)
- Support for gzip-compressed files (.gz)
- Command-line interface for batch processing
- Python API for programmatic access

## Installation

```bash
pip install RinexParser
```

The `rxp` command-line tool will be available after installation.

## Command-Line Usage

### Resample RINEX files

Thin epochs to a specified interval (e.g., 30 seconds):

```bash
# Single file
rxp --resample 30 station.rnx

# Multiple files (creates *_resample.rnx for each)
rxp --resample 30 *.rnx

# Compressed files
rxp --resample 30 station.rnx.gz

# Show output while writing files
rxp --resample 30 *.rnx --show-output
```

Output: `station_resample.rnx`

### Generate Quality Statistics

Create rinstat reports:

```bash
# Text format
rxp --rinstat station.rnx
# Output: station_rinstat.txt

# JSON format
rxp --rinstat-json station.rnx
# Output: station_rinstat.json

# Multiple files
rxp --rinstat *.rnx.gz
```

### Options

- `--version {2,3}`: Force RINEX version (auto-detected by default)
- `--show-output`: Print results to stdout in addition to writing files

## Data Structure

After parsing the data is stored in a dictionary with the following structure:

```python
{
    "epochs": [
        {
            "id": "YYYY-mm-ddTHH:MM:SSZ",
            "satellites": [
                {
                    "id": "G01",
                    "observations": {
                        "C1P_value": ...,
                        "C1P_lli": ...,
                        "C1P_ssi": ...,
                    }
                }
            ]            
        }
    ]
}
```

## Python API

### Basic Usage

```python
from rinex_parser.obs_parser import RinexParser

# Parse RINEX file
parser = RinexParser(rinex_file="station.rnx", rinex_version=3)
parser.do_create_datadict()

rnx_parser = RinexParser(rinex_file=RINEX3_FILE, rinex_version=3, sampling=30)
rnx_parser.run()

out_file = os.path.join(
    os.path.dirname(input_file),
    rnx_parser.get_rx3_long()
)

# Output Rinex File
with open(out_file, "w") as rnx:
    logger.info(f"Write to file: {rnx_parser.get_rx3_long()}")
    rnx.write(rnx_parser.rinex_reader.header.to_rinex3())
    rnx.write("\n")
    rnx.write(rnx_parser.rinex_reader.to_rinex3())
    rnx.write("\n")
# Access parsed epochs (efficient __slots__ objects)
epochs = parser.rinex_reader.rinex_epochs
for epoch in epochs:
    print(f"Time: {epoch.timestamp}, Satellites: {len(epoch.satellites)}")

# Export to RINEX 3 format (includes header)
output = parser.rinex_reader.to_rinex3()
print(output)
```

There is an entry point that allows you to use it from the command line:

```
usage: ridah-main [-h] [--fout FOUT] [--smp SMP] [--country COUNTRY] [--rnx-version {2,3}] [--crop-beg CROP_BEG] [--crop-end CROP_END] [--skeleton SKELETON] finp

positional arguments:
  finp                 Path to input file

options:
  -h, --help           show this help message and exit
  --fout FOUT          Path to output file
  --smp SMP            Sampling Rate for output
  --country COUNTRY    Country Flag to use
  --rnx-version {2,3}  Output rinex version. Currently only 3
  --crop-beg CROP_BEG  Crop Window Beg, Unix Timestamp
  --crop-end CROP_END  Crop Window End, Unix Timestamp
  --skeleton SKELETON  Path to skeleton to edit header
  
```

# Notice

This code is currently under active development and is provided as-is. The author makes no warranties, express or implied, regarding the functionality, reliability, or safety of this code. By using this code, you assume all risks associated with its use. The author is not liable for any damages, loss of data, or other issues that may arise from the use of this code. Please use at your own discretion.
### Resample/Thin Epochs

```python
from rinex_parser.obs_parser import RinexParser

parser = RinexParser(rinex_file="station.rnx", rinex_version=3)
parser.do_create_datadict()

# Thin to 30-second intervals
parser.rinex_reader.do_thinning(30)

# Export resampled data
output = parser.rinex_reader.to_rinex3()
with open("station_30s.rnx", "w") as f:
    f.write(output)
```

### Generate Quality Reports

```python
from rinex_parser.obs_parser import RinexParser
from rinex_parser.obs_quality import RinexQuality

parser = RinexParser(rinex_file="station.rnx", rinex_version=3)
parser.do_create_datadict()

# Generate rinstat report (pass reader object directly)
quality = RinexQuality(rinex_format=parser.rinex_version)
report = quality.get_rinstat_out(parser.rinex_reader)
print(report)

# Get statistics as dictionary
stats_dict = quality.get_rinstat_as_dict(parser.rinex_reader)
```

## Known Issues

- Epoch dates are zero-padded in output
- Some observation values may have different padding than input
- Header field ordering may differ from input file

## Requirements

- Python 3.8+
- pytz

## License

GNU General Public License v3.0

## Contributing

Contributions welcome! The codebase follows PEP 8 standards with comprehensive type hints and docstrings.
