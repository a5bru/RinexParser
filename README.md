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

# Get Rinex File and generate Data dictionary
rnx_parser = RinexParser(rinex_file=input_rinex, rinex_version=3)
rnx_parser.run()
# Apply filter. Could be made nicer... 
rnx_parser.rinex_reader.interval_filter = 60
rnx_parser.rinex_reader.header.interval = 60
# Output Rinex File
print(rnx_parser.rinex_reader.header.to_rinex3())
print(rnx_parser.rinex_reader.to_rinex3())

```


Have Fun!
