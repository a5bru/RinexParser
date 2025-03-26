import math
import datetime

IGREG = 15 + 31 * (10 + 12 * 1582)

MON = 0
TUE = 1
WED = 2
THU = 3
FRI = 4
SAT = 5
SUN = 6

GPS_WEEK_DAYS = (MON, TUE, WED, THU, FRI, SAT, SUN)

T0_GPS = datetime.datetime(1980, 1, 6)


def jd2ymd(jd) -> tuple[int, int, int]:
    """Convert Julian Date to (y, m, d)."""

    jd += 0.5
    z = math.trunc(jd)

    a = z
    b = a + 1524
    c = math.trunc((b - 122.1) / 365.25)
    d = math.trunc(365.25 * c)
    e = math.trunc((b - d) / 30.6001)

    if math.trunc(e < 14):
        month = e - 1
    else:
        month = e - 13

    if math.trunc(month > 2):
        year = c - 4716
    else:
        year = c - 4715

    day = b - d - math.trunc(30.6001 * e)

    return (year, month, day)


def ymd2jd(year: int, month: int, day: int) -> float:
    """Convert date (y, m, d) to Julian day."""
    jul = 0
    jy = year
    jm = 0
    ja = 0

    assert jy != 0, "julday: there is no year zero."

    if jy < 0:
        jy += 1

    if month > 2:
        jm = month + 1
    else:
        jy -= 1
        jm = month + 13

    jul = math.floor(365.25 * jy) + math.floor(30.6001 * jm) + day + 1720995 - 0.5

    if day + 31 * (month + 12 * year) >= IGREG:
        ja = int(0.01 * jy)
        jul += 2 - ja + int(0.25 * ja)

    return jul


def ts2jd(timestamp: float) -> float:
    """Convert UNIX timestamp to Julian datetime."""
    dt = datetime.datetime.fromtimestamp(timestamp)
    jd = ymd2jd(dt.year, dt.month, dt.day)
    sod = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond * 1e-6
    jd += sod / 86400
    return jd


def ts2mjd(timestamp: float) -> float:
    """Convert UNIX timestamp to Modified Julian Date."""
    jd = ts2jd(timestamp)
    return jd - 2400000.5


def jd2dow(jd: float) -> tuple[int, int]:
    """Return tuple GPSWeek and DayofWeek for Julian day"""
    gpsweek = int((jd - 2444244.5) / 7)
    dow = ((jd - 2444244.5) / 7 - gpsweek) * 7
    dow = int(round(dow * 86400) / 86400)
    return gpsweek, dow


def dow2jd(gpsweek: int, day_of_week: int) -> float:
    """Return Julian day for GPSWeek and DayOfWeek"""
    tdiff = datetime.timedelta(days=gpsweek * 7 + day_of_week)
    ti = T0_GPS + tdiff
    return ts2jd(ti.timestamp())


def dow2sod(gpsweek: int, day_of_week: int) -> int:
    """Convert Day of week into seconds of day."""
    jd = dow2jd(gpsweek, day_of_week)
    return round((((jd - 2444244.5) / 7 - gpsweek) * 7) * (24 * 60 * 60))


def dow2dt(gpsweek: int, day_of_week: int):
    """Convert GPSWeek and DayOfWeek to Datetime"""
    y, m, d = jd2ymd(dow2jd(gpsweek, day_of_week))
    return datetime.datetime(y, m, d)
