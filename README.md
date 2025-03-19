# RinexParser

Python scripts to analyse Rinex data. Supports Rinex 2 and Rinex 3

# Install

``` python -m pip install RinexParser ```

Within your program you can then import the package.

# Datastructure

After parsing the data is stored in a dictionary. I tried to use Xarray, netCDF4, pickles, etc. but the parsing and storing took either very long or consumed a lot of storage. That's why i sticked with a classic dictionary.

The rnx_parser.datadict shows the following structure:

```
d: {
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
                        ...
                    }
                }, 
                { ... }
            ]            
        }
    ]
}
```

# Known Issues

- Epoch dates are zero-padded ("2025 02 01 00 00 00.000000  0  35")
- Doppler values for example are also zero padded (-0.124 vs -.124)
- RinexHeader values are different sorted compared to input file

# Examples

## Example to parse and write Rinex

```
#!/usr/bin/python

from rinex_parser.obs_parser import RinexParser

input_file = "full_path_to_your.rnx"

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