'''
__created__: 03. Okt. 2016

@author: friedrich
'''

import datetime

from .julian import from_datetime as julian_from_datetime
from .julian import from_jd as julian_from_jd

MON = 0
TUE = 1
WED = 2
THU = 3
FRI = 4
SAT = 5
SUN = 6

GPS_WEEK_DAYS = (
    MON, TUE, WED, THU, FRI, SAT, SUN
)


def from_jd(jd):
    '''Return tuple of ISO (year, week, day) for Julian day'''
    gpsweek = int((jd - 2444244.5) / 7)
    dow = (((jd - 2444244.5) / 7 - gpsweek) * 7)
    dow = int(round(dow * 86400) / 86400)
    return gpsweek, dow


def to_jd(gpsweek, day_of_week):
    return gpsweek * 7 + day_of_week + 2444244.5 + 13


def to_gpsweek_dos(gpsweek, day_of_week):
    jd = to_jd(gpsweek, day_of_week)
    return round(
        (((jd - 2444244.5) / 7 - gpsweek) * 7) * (24 * 60 * 60)
    )


def to_datetime(gpsweek, day_of_week):
    year, month, day = julian_from_jd(to_jd(gpsweek, day_of_week))
    return datetime.datetime(year, month, day)


def from_datetime(date_time):
    assert isinstance(date_time, datetime.datetime)
    return from_jd(julian_from_datetime(date_time))
