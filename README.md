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

### Output filename formats

Use special output format specifiers to automatically generate filenames:

```bash
# Standard RINEX 3 long name format
rxp --resample 30 -o "::RX3::" station.rnx

# With country code (Austria)
rxp --resample 30 -o "::RX3-cAUT::" station.rnx

# Full format with country and station name (when implemented)
rxp --resample 30 -o "::RX3-cAUT-sGRAZ::" station.rnx
```

The output format specifiers work as follows:
- `::RX3::` - Converts to RINEX 3 long name format (auto-extracts country from input filename if available)
- `::RX3-cXXX::` - Converts to RINEX 3 long name with specified country code (e.g., `cAUT` for Austria, `cDEU` for Germany)
- `::RX3-cXXX-sSTATION::` - RINEX 3 long name with country and station name (not yet implemented)

When not using special format specifiers, provide a standard output filename:

```bash
rxp --resample 30 -o output.rnx station.rnx
```

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

### Crop observations by time window

Extract observations from a specific time period:

```bash
# Crop with ISO format timestamps
rxp --crop-start 2026-01-20T00:00:00 --crop-end 2026-01-21T00:00:00 --resample 30 station.rnx

# Date only (uses full day)
rxp --crop-start 2026-01-20 --crop-end 2026-01-21 --resample 30 station.rnx
```

### Filter satellite observations

Remove specific satellites or observation types:

```bash
# Remove specific satellites
rxp --filter-sat-pnr G01,R04,E12 --resample 30 station.rnx

# Remove entire satellite system (GPS, GLONASS, Galileo, etc.)
rxp --filter-sat-sys G,R --resample 30 station.rnx

# Remove observation types
rxp --filter-sat-obs G1C,R1C --resample 30 station.rnx
```

### Update header fields using skeleton file

Use a skeleton file to copy header information (marker, receiver, antenna, observer details) to processed files:

```bash
# Apply skeleton header
rxp --skeleton skeleton.rnx --resample 30 station.rnx

# Skeleton can also set country code
rxp --skeleton skeleton.rnx -o output.rnx --resample 30 station.rnx
```

The skeleton file should contain valid RINEX header lines. Supported fields include:
- `MARKER NAME` and `MARKER NUMBER`
- `REC # / TYPE / VERS` (receiver info)
- `ANT # / TYPE` (antenna info)
- `APPROX POSITION XYZ` (station coordinates)
- `ANTENNA: DELTA H/E/N` (antenna offsets)
- `OBSERVER / AGENCY`
- `COMMENT` (can include `CountryCode=XX` for automatic country detection)

Example skeleton file:
```
     3.04           OBSERVATION DATA    G (GPS)             RINEX VERSION / TYPE
My Marker Station                       MARKER NAME
123456                                  MARKER NUMBER
SWIFTNAV PiksiMulti                     REC # / TYPE / VERS
TrimbleChoke_MC2000                     ANT # / TYPE
 3771234.1234  3456789.5678   5123456.9 APPROX POSITION XYZ
        0.0000        0.0000        0.0000 ANTENNA: DELTA H/E/N
Observer Name                           OBSERVER / AGENCY
CountryCode=AUT                         COMMENT
```

### Merge Multiple RINEX Files

Combine multiple RINEX files from the same station into a single continuous file:

```bash
# Merge multiple files (groups by 4-letter station code)
rxp --merge *.rnx

# Merge with resampling
rxp --resample 30 --merge *.rnx

# Merge multiple files with output format specifier
rxp --resample 30 --merge -o "::RX3-cAUT::" *.rnx
```

The merge operation:
- Groups files by the 4-letter station code (first 4 characters of filename)
- Sorts files chronologically
- Combines headers and epochs into a single continuous file
- Logs header changes between merged files as comments

### Parallel Processing

Use multiple threads for faster batch processing:

```bash
# Process 4 files in parallel
rxp --resample 30 --threads 4 *.rnx

# Combine with merge for fast batch operations
rxp --resample 30 --merge --threads 4 *.rnx
```

### Performance Profiling

Enable CPU profiling to analyze performance:

```bash
# Run with CPU profiling enabled
rxp --resample 30 --profile station.rnx

# Profiling results showing top 20 functions by execution time
```

### Help reference

The help of rxp shows the following output:

```
usage: rxp [-h] [--resample SECONDS] [--rinstat] [--rinstat-json] [-o FILE] [-v] [--show-output] [--crop-start DATETIME] [--crop-end DATETIME]
           [--filter-sat-pnr FILTER_SAT_PNR] [--filter-sat-sys FILTER_SAT_SYS] [--filter-sat-obs FILTER_SAT_OBS] [-t SKELETON]
           [-m] [-n THREADS] [--profile] [--version]
           rinex_files [rinex_files ...]

RINEX observation file parser and processor

positional arguments:
  rinex_files           RINEX observation file(s) to process

options:
  -h, --help            show this help message and exit
  --resample SECONDS    Resample observations to specified interval (seconds)
  --rinstat             Generate RINSTAT quality report
  --rinstat-json        Generate RINSTAT quality report in JSON format
  -o, --output FILE     Output filename (auto-generated if not specified)
  -v, --verbose         Enable verbose logging
  --show-output         Print the generated output to console
  --crop-start DATETIME
                        Start time for cropping (ISO format: YYYY-MM-DD[[T]HH:MM:SS], YYYY-DOY)
  --crop-end DATETIME   End time for cropping (ISO format: YYYY-MM-DD[[T]HH:MM:SS], YYYY-DOY)
  --filter-sat-pnr FILTER_SAT_PNR
                        Remove satellites (G01,R04,E12,...)
  --filter-sat-sys FILTER_SAT_SYS
                        Remove satellite system (G,I,S) from epoch.
  --filter-sat-obs FILTER_SAT_OBS
                        Remove observation type (G1C,R1C,E8I,C6Q).
  -t, --skeleton SKELETON
                        Path to skeleton file to edit header
  -m, --merge           Merge multiple RINEX files
  -n, --threads THREADS
                        Number of threads to use
  --profile             Enable CPU profiling
  --version             Show version and exit
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

There is an entry point that allows you to use it from the command line via the `rxp` command (see command-line usage above).


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
