"""RINEX format constants and regular expressions.

Contains regular expressions and patterns for parsing RINEX observation files
in versions 2 and 3, as well as format constants for datetime and marker types.

Created on Oct 25, 2016
Author: jurgen
"""

# Satellite identifier pattern for RINEX files
RINEX_SATELLITE_IDENTIFIER = r"(?P<satellite_system>[%s])(?P<satellite_number>[ \d]{2})"

# RINEX 2 format constants
RINEX2_SATELLITE_SYSTEMS = "GRE"
RINEX2_SATELLITES_REGEXP = RINEX_SATELLITE_IDENTIFIER % RINEX2_SATELLITE_SYSTEMS
RINEX2_DATELINE_REGEXP = (
    r"^ (?P<year2>\d{2}) (?P<month>[ \d]{2}) (?P<day>[ \d]{2}) "
    r"(?P<hour>[ \d]{2}) (?P<minute>[ \d]{2}) (?P<second>[ \d]{2}\.\d{7})  "
    r"(?P<epoch_flag>[0-9])(?P<nos>[ \d]{3})(?P<sat1>(%s){0,12})"
    r"(?P<clock_offset>.|[ \d]{2}\.\d{9})?" % RINEX2_SATELLITES_REGEXP
)
RINEX2_DATELINE_REGEXP_SHORT = (
    r"^\ {32}(?P<sat2>(%s){,12})" % RINEX2_SATELLITES_REGEXP
)
RINEX2_DATA_OBSERVATION_DESCRIPTOR_REGEXP = (
    r"(?P<value>[-\ \d]{10}\.\d{3})(?P<lli>[\ \d])()(?P<ss>[\ \d])"
)
RINEX2_DATA_OBSERVATION_REGEXP = (
    r"^(%s|\ {16}){,5}" % RINEX2_DATA_OBSERVATION_DESCRIPTOR_REGEXP
)
RINEX2_HEADER_OBS_DESCRIPTOR = r"\ {4}[CPLDS][125678]"
RINEX2_HEADER_OBSERVATION_TYPES = (
    r"^(?P<noo>[\ \d]{6})(?P<ots>(%s){0,9})" % RINEX2_HEADER_OBS_DESCRIPTOR
)

# RINEX 3 format constants
RINEX3_SATELLITE_SYSTEMS = "GREJCIS"
RINEX3_SATELLITES_REGEXP = RINEX_SATELLITE_IDENTIFIER % RINEX3_SATELLITE_SYSTEMS
RINEX3_DATELINE_REGEXP = (
    r"^> (?P<year4>\d{4}) (?P<month>[ \d]{2}) (?P<day>[ \d]{2}) "
    r"(?P<hour>[ \d]{2}) (?P<minute>[ \d]{2})(?P<second>[ \d]{3}.\d{7})  "
    r"(?P<epoch_flag>\d)(?P<num_of_sats>[\d ]{3})"
    r"((\ {6})(?P<rec_clock_offset>[\ \d-]{2}\.\d{12}))?"
)
RINEX3_MULTIPLE_OBS_REGEXP = (
    r"(?P<first_o>([-\d\ ]{10}[\.\ ][\ \d]{3})([\d\ ])([\d\ ]))"
)
RINEX3_DATA_OBSEVATION_REGEXP = (
    r"^(?P<sat_num>(%s))(?P<first_o>(([-\d\ ]{10}[\.\ ][\ \d]{3})"
    r"([\d\ ])([\d\ ])))*(?P<last_o>([-\d\ ]{10}[\.\ ][\ \d]{3})"
    r"([\d\ ])?([\d\ ])?)?" % RINEX3_SATELLITES_REGEXP
)
RINEX3_FORMAT_OBS_TIME = "%Y %m %d %H %M %S.0000000"
RINEX3_FORMAT_OBS_DESCRIPTOR = r"\ [CDLSX]\d[ABCDILMNPQSWX]?"
RINEX3_FORMAT_SYS_OBS_TYPES = (
    r"^(((?P<sat_sys>[%s])  (?P<obs_amount>[\ \d]{3})|"
    r"(?P<obs_cont>\ {6})))(?P<obs_descriptor>%s){0,13}.*(SYS / # / OBS TYPES)"
    % (RINEX3_SATELLITE_SYSTEMS, RINEX3_FORMAT_OBS_DESCRIPTOR)
)
RINEX3_FORMAT_FILE_NAME = (
    r"(?P<station>\w{4})(\d)(\d)(?P<country>[A-Z]{3})_\w_(?P<year4>\d{4})"
    r"(?P<doy>\d{3})(?P<hour>\d{2})(?P<minute>\d{2})_(?P<file_period>\d\d[A-Z])"
    r"_((?P<data_freq>\d\d[A-Z])_)?\w\w.[rc]nx"
)
RINEX3_DATA_OBSERVATION_FIELD_REGEXP = (
    r"((?P<value>\ *[\-\+]?[0-9]*\.?[0-9]{3})(?P<lli>[\ \d])?(?P<ssi>[\ \d])?)"
)
RINEX3_HEADER_OBS_DESCRIPTOR = r"\ {4}[CDLSX][125678][ABCDILMNPQSWX]"

# DateTime format constants
RNX_FORMAT_DATETIME = "%Y-%m-%dT%H:%M:%SZ"
RNX_FORMAT_DATE = "%Y-%m-%d"
RNX_FORMAT_TIME = "%H:%M:%SZ"
RNX_FORMAT_DATETIME_SHORT = "%Y%m%d %H%M%S"
RNX_FORMAT_OBS_TIME = "  %Y    %m    %d    %H    %M   %S.%f0"

# Marker types (antenna location classifications)
MARKER_TYPES = (
    "GEODETIC",         # Earth-fixed, high-precision monument
    "NON_GEODETIC",     # Earth-fixed, low-precision monument
    "NON_PHYSICAL",     # Generated from network processing
    "SPACEBORNE",       # Orbiting space vehicle
    "GROUND_CRAFT",     # Mobile terrestrial vehicle
    "WATER_CRAFT",      # Mobile water craft
    "AIRBORNE",         # Aircraft, balloon, etc.
    "FIXED_BUOY",       # Fixed on water surface
    "FLOATING_BUOY",    # Floating on water surface
    "FLOATING_ICE",     # Floating ice sheet, etc.
    "GLACIER",          # Fixed on a glacier
    "BALLISTIC",        # Rockets, shells, etc.
    "ANIMAL",           # Animal carrying a receiver
    "HUMAN"             # Human being
)
