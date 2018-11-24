# RinexParser

Python scripts to analyse Rinex data. Supports Rinex 2 and Rinex 3

# Install

```
git clone https://gitlab.com/dach.pos/rinexparser.git
cd rinexparser
make cleanAll
make prepareVenv
source env/bin/activate
make install
make test
```

# Example

* Download repository via `git clone https://gitlab.com/dach.pos/rinexparser.git`
* Create a folder named **data** if it does not already exists
* Copy a Rinex 2 or 3 file into the folder named **data**
* Open the file **test_obs_ready.py** and edit the filename of *RINEX2_FILE* or *RINEX3_FILE* corresponding to the file you just copied to the folder named **data**
* Execute the test via `python test_obs_reader.py`

Have Fun!