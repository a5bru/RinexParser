# RinexParser

Python scripts to analyse Rinex data. Supports Rinex 2 and Rinex 3

# Install

```
git clone https://gitlab.com/dach.pos/rinexparser.git
cd rinexparser
make cleanAll
make prepareVenv
source env/bin/activate
make setupVenv
make test
```

If the test was successfull:

``` python setup.py install ```

Within your program you can then import the package.

# Example

Please check the file *tests/test_obs_reader.py* for examples

Have Fun!
