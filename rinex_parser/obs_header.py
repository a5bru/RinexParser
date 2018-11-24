'''
Created on Nov 7, 2016

@author: jurgen
'''

import datetime
import re

from pprint import pprint

from rinex_parser import constants as c
from rinex_parser.logger import logger


class RinexObsHeader(object):
    """
    """

    @classmethod
    def from_header(cls, header_string):
        """
        Args:
            header: str, Rinex Header
        Returns:
            Rinex2ObsHeader
        """
        tmp_header = cls()
        tmp_header.set_header(header_lines=header_string)
        return tmp_header

    def set_header(self, header_lines):
        """
        Args:
            header_lines: str, Lines are separated by "\n"
        """
        for line in header_lines.split("\n"):
            if line == "":
                continue

            header_label = line[60:]

            # logger.debug(line)

            if 'END OF HEADER' in header_label:
                break

            # RINEX VERSION / TYPE
            if "RINEX VERSION / TYPE" in header_label:
                self.set_version_type(line)
                # logger.debug("Rinex Version: '%f'" % self.format_version)

            if 'PGM / RUN BY / DATE' in header_label:
                self.set_pgm_by_date(line)

            if 'COMMENT' in header_label:
                self.set_comment(line)

            if 'MARKER NAME' in header_label:
                self.set_marker_name(line)

            if 'MARKER NUMBER' in header_label:
                self.set_marker_number(line)

            if 'OBSERVER / AGENCY' in header_label:
                self.set_observer_agency(line)

            if 'REC # / TYPE / VERS' in header_label:
                self.set_receiver(line)

            if 'ANT # / TYPE' in header_label:
                self.set_antenna(line)

            if 'APPROX POSITION XYZ' in header_label:
                self.set_approx_position(line)

            if 'ANTENNA: DELTA H/E/N' in header_label:
                self.set_antenna_delta(line)

            if 'WAVELENGTH FACT L1/2' in header_label:
                self.set_wavelength_fact(line)

            if '# / TYPES OF OBSERV' in header_label:
                self.set_observation_types(line)

            if 'INTERVAL' in header_label:
                self.set_interval(line)

            if 'TIME OF FIRST OBS' in header_label:
                self.set_first_observation(line)

            if 'TIME OF LAST OBS' in header_label:
                self.set_last_observation(line)

            if 'RCV CLOCK OFFS APPL' in header_label:
                self.set_rcv_clock_offset(line)

            if 'LEAP SECONDS' in header_label:
                self.set_leap_seconds(line)

            if '# OF SATELLITES' in header_label:
                self.set_total_satellites(line)


class Rinex2ObsHeader(RinexObsHeader):

    def __init__(self, **kwargs):
        self.format_version = float(kwargs.get("format_version", "2.11"))
        self.file_type = kwargs.get("file_type", "OBSERVATION DATA")
        self.satellite_system = kwargs.get("satellite_system", "M (MIXED)")
        self.satellites = {}
        self.rinex_export_version = 2

        self.comment = kwargs.get("comment", "")

        # self.program = kwargs.get("program", "RNXDMT")
        self.program = "RNXDMT"
        self.run_by = kwargs.get("run_by", "BEV/V15 APOS")
        self.run_date = kwargs.get(
            "run_date", datetime.datetime.now().strftime("%FT%H:%MZ"))

        self.marker_name = kwargs.get("marker_name")

        self.marker_number = kwargs.get("marker_number")

        self.observer = kwargs.get("observer")
        self.agency = kwargs.get("agency")

        self.receiver_number = kwargs.get("receiver_number")
        self.receiver_type = kwargs.get("receiver_type")
        self.receiver_version = kwargs.get("receiver_version")

        self.antenna_number = kwargs.get("antenna_number")
        self.antenna_type = kwargs.get("antenna_type")

        self.approx_position_x = kwargs.get(
            "approx_position_x", None)
        self.approx_position_y = kwargs.get(
            "approx_position_y", None)
        self.approx_position_z = kwargs.get(
            "approx_position_z", None)

        self.antenna_delta_height = kwargs.get("antenna_delta_height", None)
        self.antenna_delta_east = kwargs.get("antenna_delta_east", None)
        self.antenna_delta_north = kwargs.get("antenna_delta_north", None)

        self.wavelength_fact_l1 = kwargs.get("wavelength_fact_l1", None)
        self.wavelength_fact_l2 = kwargs.get("wavelength_fact_l2", None)
        self.wavelength_fact = kwargs.get("wavelength_fact", None)

        self.observation_types = kwargs.get("observation_types", None)

        self.interval = kwargs.get("interval", None)

        self.first_observation = kwargs.get("first_observation", None)
        self.last_observation = kwargs.get("last_observation", None)
        self.time_system = kwargs.get("time_system", None)

        self.rcv_clock_offset = kwargs.get("rcv_clock_offset", None)

        self.leap_seconds = kwargs.get("leap_seconds", None)

        self.total_satellites = 0

        self.empty = ""

    def to_rinex3(self):
        """
        """
        self.rinex_export_version = 3
        r3 = Rinex3ObsHeader(**self.__dict__)
        return r3.to_rinex3()

    def to_rinex2(self):
        """
        Return RINEX2 Header
        """
        self.rinex_export_version = 2
        r2h = """{format_version:9.2f}{empty:11s}{file_type:20s}{satellite_system:20s}RINEX VERSION / TYPE
{program:20s}{run_by:20s}{run_date:20s}PGM / RUN_BY / DATE
{comment}
{marker_name:60s}MARKER NAME
{marker_number:60s}MARKER NUMBER
{observer:20s}{agency:40s}OBSERVER / AGENCY
{receiver_number:20s}{receiver_type:20s}{receiver_version:20s}REC # / TYPE / VERS
{antenna_number:20s}{antenna_type:20s}{empty:20s}ANT # / TYPE
{approx_position_x:14.4f}{approx_position_x:14.4f}{approx_position_x:14.4f}{empty:18s}APPROX POSITION XYZ
{antenna_delta_height:14.4f}{antenna_delta_east:14.4f}{antenna_delta_north:14.4f}{empty:18s}ANTENNA: DELTA H/E/N
{wavelength_fact_l1:6d}{wavelength_fact_l2:6d}{wavelength_fact:6d}{empty:42s}WAVELENGTH FACT L1/L2
{interval:10.3f}{empty:50s}INTERVAL""".format(
            **self.__dict__
        )

        ots = self.get_observation_types()
        if ots:
            r2h += "\n%s" % ots

        if self.first_observation is not None:
            r2h += "\n{time_of_obs:30s}{empty:5s}{time_system:3s}{empty:9s}TIME OF FIRST OBS".format(
                time_of_obs=self.first_observation.strftime(
                    c.RNX_FORMAT_OBS_TIME),
                empty="",
                time_system=self.time_system
            )
        if self.last_observation is not None:
            r2h += "\n{time_of_obs:30s}{empty:5s}{time_system:3s}{empty:9s}TIME OF LAST OBS".format(
                time_of_obs=self.last_observation.strftime(
                    c.RNX_FORMAT_OBS_TIME),
                empty="",
                time_system=self.time_system
            )
        if self.rcv_clock_offset is not None:
            r2h += "\n{:6d}{:54s}RCV CLOCK OFFS APPL".format(
                self.rcv_clock_offset, "")
        if self.total_satellites > 0:
            r2h += "\n{:6d}{:54s}# OF SATELLITES"
        return "{}\n{:60s}END OF HEADER".format(r2h, "")

    def get_observation_types(self):
        ots = []
        for ot in self.observation_types:
            if ot == "C1C" and self.rinex_export_version == 2:
                ot = "C1"
            if ot in ["C2W", "C2P"] and self.rinex_export_version == 2:
                ot = "P2"
            if ot in ots:
                continue
            ots.append(ot)

        for i in range(len(ots)):
            ot = ots[i]
            if i % 9 == 0:
                if i == 0:
                    s = "{:6d}".format(len(ots))
                else:
                    s = "\n{:6s}".format("")
            s += "{:4s}{:2s}".format("", ot)
            if (i % 9 == 8) or (i == len(ots) - 1):
                s = "{:60s}# / TYPES OF OBSERV".format(s)
        return s

    @classmethod
    def from_header(cls, header_string):
        """
        Args:
            header: str, Rinex Header
        Returns:
            Rinex2ObsHeader
        """
        tmp_header = cls()
        tmp_header.set_header(header_lines=header_string)
        return tmp_header

    def set_version_type(self, line):
        self.format_version = float(line[:9].strip())
        self.file_type = line[9 + 11]
        self.satellite_system = line[9 + 11 + 1 + 19]

    def set_pgm_by_date(self, line):
        # self.program = line[:20].strip()
        self.run_by = line[20:20 + 20].strip()
        self.run_date = line[40:40 + 20].strip()

    def set_comment(self, line):
        # new_comment = line[:60].strip()
        new_comment = line
        if self.comment == "":
            self.comment = new_comment
        else:
            self.comment = "%s\n%s" % (self.comment, new_comment)

    def set_marker_name(self, line):
        self.marker_name = line[:60].strip()

    def set_marker_number(self, line):
        self.marker_number = line[:20].strip()

    def set_observer_agency(self, line):
        self.observer = line[00:20].strip()
        self.agency = line[20:60].strip()
        # clean ADDREF issue
        self.agency = self.agency.split("     ")[0]

    def set_receiver(self, line):
        self.receiver_number = line[:20].strip()
        self.receiver_type = line[20:40].strip()
        self.receiver_version = line[40:60].strip()

    def set_antenna(self, line):
        self.antenna_number = line[:20].strip()
        self.antenna_type = line[20:40].strip()

    def set_approx_position(self, line):
        self.approx_position_x = float(line[00:14])
        self.approx_position_y = float(line[14:28])
        self.approx_position_z = float(line[28:42])

    def set_antenna_delta(self, line):
        self.antenna_delta_height = float(line[00:14])
        self.antenna_delta_east = float(line[14:28])
        self.antenna_delta_north = float(line[28:42])

    def set_wavelength_fact(self, line):
        self.wavelength_fact_l1 = int(line[00:6])
        self.wavelength_fact_l2 = int(line[6:12])
        wlf = line[12:18].strip()
        if not wlf:
            wlf = 0
        self.wavelength_fact = int(wlf)

    def set_observation_types(self, line):
        self.observation_types_number = int(line.split("#")[0].split()[0])
        self.observation_types = line.split("#")[0].split()[1:]
        assert self.observation_types_number == len(self.observation_types)

    def set_interval(self, line):
        self.interval = int(float(line.split()[0].strip()))

    def set_first_observation(self, line):
        self.first_observation = datetime.datetime.strptime(
            line[:43], c.RNX_FORMAT_OBS_TIME)
        self.time_system = line[43 + 5:43 + 5 + 3]

    def set_last_observation(self, line):
        self.last_observation = datetime.datetime.strptime(
            line[:43], c.RNX_FORMAT_OBS_TIME)

    def set_rcv_clock_offset(self, line):
        self.rcv_clock_offset = int(line[:6])

    def set_leap_seconds(self, line):
        self.leap_seconds = int(line[:6])

    def set_total_satellites(self, line):
        self.total_satellites = int(line[:6])


class Rinex3ObsHeader(Rinex2ObsHeader):

    RE_SYS_OBS_TYPE = re.compile(c.RINEX3_FORMAT_SYS_OBS_TYPES)

    def __init__(self, **kwargs):
        """
        """
        kwargs["format_version"] = "3.03"
        super(Rinex3ObsHeader, self).__init__(**kwargs)
        self.rinex_export_version = 3
        self.last_sat_sys = ""

        self.marker_type = kwargs.get("marker_type", "NON_GEODETIC")

        self.antenna_delta_x = kwargs.get("antenna_delta_x", None)
        self.antenna_delta_y = kwargs.get("antenna_delta_y", None)
        self.antenna_delta_z = kwargs.get("antenna_delta_z", None)

        self.antenna_phasecenter = kwargs.get("antenna_phasecenter", None)

        self.antenna_b_sight_x = kwargs.get("b_sight_x", None)
        self.antenna_b_sight_y = kwargs.get("b_sight_y", None)
        self.antenna_b_sight_z = kwargs.get("b_sight_z", None)

        self.zerodir_azi = kwargs.get("zerodir_azi", None)
        self.zerodir_x = kwargs.get("zerodir_x", None)
        self.zerodir_y = kwargs.get("zerodir_y", None)
        self.zerodir_z = kwargs.get("zerodir_z", None)

        self.center_mass_x = kwargs.get(
            "center_mass_x", None)
        self.center_mass_y = kwargs.get(
            "center_mass_y", None)
        self.center_mass_z = kwargs.get(
            "center_mass_z", None)

        self.sys_obs_types = kwargs.get("sys_obs_types", {})

        self.signal_strength_unit = kwargs.get("signal_strength_unit", None)

        self.sys_dcbs_applied = kwargs.get("sys_dcbs_applied", None)
        self.sys_pcvs_applied = kwargs.get("sys_pcvs_applied", None)
        self.sys_scale_factor = kwargs.get("sys_scale_factor", None)

        self.sys_phase_shift = kwargs.get("sys_phase_shift", None)

        self.glonass_slot_frq = kwargs.get("glonass_slot_frq", None)

        self.glonass_cod_phs_bis = kwargs.get("glonass_cod_phs_bis", None)

        self.leap_second_current = kwargs.get("leap_second_current", None)
        self.leap_second_other = kwargs.get("leap_second_other", None)
        self.leap_second_week = kwargs.get("leap_second_week", None)
        self.leap_second_day = kwargs.get("leap_second_day", None)
        self.leap_second_time_system = kwargs.get(
            "leap_second_time_system", None)

        self.prn_obs = None

    @classmethod
    def from_header(cls, header_string):
        """
        Args:
            header: str, Rinex Header
        Returns:
            Rinex3ObsHeader
        """
        tmp_header = cls()
        try: 
            tmp_header.set_header(header_lines=header_string)
            return tmp_header
        except Exception as e:
            logger.error(e)
            return None

    def to_rinex3(self):
        self.rinex_export_version = 3
        rinex_header = """{format_version:9.2f}{empty:11s}{file_type:20s}{satellite_system:20s}RINEX VERSION / TYPE
{program:20s}{run_by:20s}{run_date:20s}PGM / RUN_BY / DATE
{comment}
{marker_name:60s}MARKER NAME
{marker_number:60s}MARKER NUMBER
{marker_type:20s}{empty:40s}MARKER TYPE
{observer:20s}{agency:40s}OBSERVER / AGENCY
{receiver_number:20s}{receiver_type:20s}{receiver_version:20s}REC # / TYPE / VERS
{antenna_number:20s}{antenna_type:20s}{empty:20s}ANT # / TYPE
{approx_position_x:14.4f}{approx_position_y:14.4f}{approx_position_z:14.4f}{empty:18s}APPROX POSITION XYZ
{antenna_delta_height:14.4f}{antenna_delta_east:14.4f}{antenna_delta_north:14.4f}{empty:18s}ANTENNA: DELTA H/E/N""".format(**self.__dict__)
        adx = self.get_antenna_delta_xyz()
        if adx:
            rinex_header += "\n%s" % adx

        ots = self.get_observation_types()
        if ots:
            rinex_header += "\n%s" % ots

        rinex_header += """\n{interval:10.3f}{empty:50s}INTERVAL
{wavelength_fact_l1:6d}{wavelength_fact_l2:6d}{wavelength_fact:6d}{empty:42s}WAVELENGTH FACT L1/L2""".format(
            ots=self.get_observation_types(),
            **self.__dict__
        )
        if self.first_observation is not None:
            rinex_header += "\n{time_of_obs:30s}{empty:5s}{time_system:3s}{empty:9s}TIME OF FIRST OBS".format(
                time_of_obs=self.first_observation.strftime(
                    c.RNX_FORMAT_OBS_TIME),
                empty="",
                time_system=self.time_system
            )
        if self.last_observation is not None:
            rinex_header += "\n{time_of_obs:30s}{empty:5s}{time_system:3s}{empty:9s}TIME OF LAST OBS".format(
                time_of_obs=self.last_observation.strftime(
                    c.RNX_FORMAT_OBS_TIME),
                empty="",
                time_system=self.time_system
            )
        if self.rcv_clock_offset is not None:
            rinex_header += "\n{:6d}{:54s}RCV CLOCK OFFS APPL".format(
                self.rcv_clock_offset, "")
        if self.total_satellites > 0:
            rinex_header += "\n{:6d}{:54s}# OF SATELLITES"

        apc = self.get_antenna_phasecenter()
        if apc:
            rinex_header += "\n%s" % apc

        bsi = self.get_antenna_b_sight()
        if bsi:
            rinex_header = "{}\n{}".format(rinex_header, bsi)

        aza = self.get_antenna_zerodir_azi()
        if aza:
            rinex_header = "{}\n{}".format(rinex_header, aza)

        azx = self.get_antenna_zerodir_xyz()
        if azx:
            rinex_header = "{}\n{}".format(rinex_header, azx)

        com = self.get_center_mass_xyz()
        if com:
            rinex_header = "{}\n{}".format(rinex_header, com)

        return "{}\n{:60s}END OF HEADER".format(rinex_header, "")

        sot = self.get_sys_obs_types()
        if sot:
            rinex_header = "{}\n{}".format(rinex_header, sot)
        return rinex_header

    def get_antenna_delta_xyz(self):
        """
        """
        if self.antenna_delta_x is None or \
                self.antenna_delta_y is None or \
                self.antenna_delta_z is None:
            return None
        return "{:14.4f}{:14.4f}{:14.4f}{:18s}ANTENNA: DELTA X/Y/Z".format(
            self.antenna_delta_x,
            self.antenna_delta_y,
            self.antenna_delta_z,
            ""
        )

    def get_antenna_phasecenter(self):
        """
        """
        if not self.antenna_phasecenter:
            return None
        apc = ""
        for ss in c.RINEX3_SATELLITE_SYSTEMS:
            if ss in self.antenna_phasecenter:
                temp = "{} {:3s}{:9.4f}{:14.4f}{:14.4f}".format(
                    ss,
                    self.antenna_phasecenter[ss]["observation_code"],
                    self.antenna_phasecenter[ss]["fixed_station_north"],
                    self.antenna_phasecenter[ss]["fixed_station_east"],
                    self.antenna_phasecenter[ss]["fixed_station_up"],
                )
                apc += "{:60s}ANTENNA: PHASECENTER" % temp
                if ss != "S":
                    apc += "\n"
        return apc

    def get_antenna_b_sight(self):
        if self.antenna_b_sight_x is None or \
                self.antenna_b_sight_y is None or \
                self.antenna_b_sight_z is None:
            return None
        return "{:14.4f}{:14.4f}{:14.4f}{:18s}ANTENNA: B.SIGHT XYZ".format(
            self.antenna_b_sight_x,
            self.antenna_b_sight_y,
            self.antenna_b_sight_z,
            ""
        )

    def get_antenna_zerodir_azi(self):
        if self.zerodir_azi is None:
            return None

        return "{:14.4}{:46s}ANTENNA: ZERODIR AZI".format(
            self.zerodir_azi, ""
        )

    def get_antenna_zerodir_xyz(self):
        if self.zerodir_x is None or \
                self.zerodir_y is None or \
                self.zerodir_z is None:
            return None
        return "{:14.4f}{:14.4f}{:14.4f}{:18s}ANTENNA: ZERODIR XYZ".format(
            self.zerodir_x,
            self.zerodir_y,
            self.zerodir_z,
            ""
        )

    def get_center_mass_xyz(self):
        if self.center_mass_x is None or \
                self.center_mass_y is None or \
                self.center_mass_z is None:
            return None
        return "{:14.4f}{:14.4f}{:14.4f}{:18s}CENTER OF MASS: XYZ".format(
            self.center_mass_x,
            self.center_mass_y,
            self.center_mass_z,
            ""
        )

    def get_sys_obs_types(self):
        """
        """
        if self.sys_obs_types is None:
            return None
        sot = ""
        for ss in c.RINEX3_SATELLITE_SYSTEMS:
            if ss in self.sys_obs_types:
                temp = "{}  {:3d}".format(
                    ss,
                    self.sys_obs_types[ss]["obs_amount"]
                )
                for i in range(len(self.sys_obs_types[ss]["obs_types"])):
                    if (i % 13 == 0) and (i != 0):
                        temp = "{:60s}SYS / # / OBS TYPES\n{:6s}".format(
                            temp, "")
                    temp += "{:3s}".format(
                        self.sys_obs_types[ss]["obs_types"][i])
                sot += "{:60s}SYS / # / OBS TYPES".format(temp)
            if ss != "S":
                sot += "\n"

        return sot

    def set_marker_type(self, line):
        self.marker_type = line[:20].strip()

    def set_antenna_delta_xyz(self, line):
        self.antenna_delta_x = float(line[00:14])
        self.antenna_delta_y = float(line[14:28])
        self.antenna_delta_z = float(line[28:42])

    def set_antenna_phasecenter(self, line):
        phase_center = {}
        satellite_system = line[0]
        phase_center["satellite_system"] = satellite_system
        phase_center["observation_code"] = line[2:2 + 3]
        phase_center["fixed_station_north"] = float(line[5:14])
        phase_center["fixed_station_east"] = float(line[14:28])
        phase_center["fixed_station_up"] = float(line[28:42])

        self.antenna_phasecenter = {
            satellite_system: phase_center
        }

    def set_antenna_b_sight_xyz(self, line):
        self.antenna_b_sight_x = float(line[00:14])
        self.antenna_b_sight_y = float(line[14:28])
        self.antenna_b_sight_z = float(line[28:42])

    def set_antenna_zerodir_azi(self, line):
        self.zerodir_azi = float(line[00:14])

    def set_antenna_zerodir_xyz(self, line):
        self.zerodir_x = float(line[00:14])
        self.zerodir_y = float(line[14:28])
        self.zerodir_z = float(line[28:42])

    def set_center_mass_xyz(self, line):
        self.center_mass_x = float(line[00:14])
        self.center_mass_y = float(line[14:28])
        self.center_mass_z = float(line[28:42])

    def set_sys_obs_types(self, line):
        result = self.RE_SYS_OBS_TYPE.match(line)
        d = result.groupdict()
        sat_sys = ""

        # line of SYS OBS TYPES
        if "sat_sys" in d and d["sat_sys"] is not None:
            sat_sys = d["sat_sys"]
            # No SYS OBS TYPE exists so far
            if sat_sys not in self.sys_obs_types:
                self.sys_obs_types[sat_sys] = {"obs_types": []}
            self.last_sat_sys = sat_sys
            # logger.info("Setting LastSatSys to {}".format(self.last_sat_sys))

        # Continuation line SYS OBS TYPES
        elif "obs_cont" in d and self.last_sat_sys:
            sat_sys = self.last_sat_sys

        # get all observation descriptors 
        if len(sat_sys) > 0:
            for obs_descriptor in re.finditer(c.RINEX3_FORMAT_OBS_DESCRIPTOR, line):
                obs_descriptor_clean = obs_descriptor.group(0).strip()
                if obs_descriptor_clean not in self.sys_obs_types[sat_sys]["obs_types"]:
                    self.sys_obs_types[sat_sys]["obs_types"].append(obs_descriptor_clean)

        return sat_sys

    def set_signal_strength_unit(self, line):
        self.signal_strength_unit = line[:20].strip()

    def set_interval(self, line):
        self.interval = float(line[:10])

    def set_sys_dcbs_applied(self, line):
        satellite_system = line[0]
        dcbs = {
            "satellite_system": satellite_system,
            "program_name": line[2:19],
            "correction_url": line[19:60]
        }
        self.sys_dcbs_applied[satellite_system].update(dcbs)

    def set_sys_pcvs_applied(self, line):
        satellite_system = line[0]
        pcvs = {
            "satellite_system": satellite_system,
            "program_name": line[2:19],
            "correction_url": line[19:60]
        }
        self.sys_pcvs_applied[satellite_system].update(pcvs)

    def set_sys_scale_factor(self, line):
        satellite_system = line[0]
        nos = line[8:10].strip()
        if nos == "":
            nos = 0
        else:
            nos = int(nos)

        scale_factor = {
            "satellite_system": satellite_system,
            "scale_factor": int(line[2:6]),
            "involved_satellites_number": nos,
            "involved_satellites_list": []
        }
        self.sys_scale_factor[satellite_system] = scale_factor
        self.set_sys_scale_factor_extra(line, satellite_system)

    def set_sys_scale_factor_extra(self, line, satellite_system):
        self.sys_scale_factor[satellite_system][
            "involved_satellites_list"] += line[10:58].split()

    def set_phase_shift(self, line):
        satellite_system = line[0]
        carrier_phase = line[2:5]
        correction_applied = line[5:13].strip()
        if correction_applied == "":
            correction_applied = 0.0
        nis = 0
        if line[16:18].strip() != "":
            nis = int(line[16:18])
        phase_shift = {
            "satellite_system": satellite_system,
            "carrier_phase": carrier_phase,
            satellite_system: {
                carrier_phase: {
                    "correction_applied": correction_applied,
                    "involved_satellites_number": nis,
                    "involved_satellites_list": []
                }
            }
        }
        if self.sys_phase_shift is None:
            self.sys_phase_shift = {}
        if satellite_system in self.sys_phase_shift:
            if carrier_phase in self.sys_phase_shift[satellite_system]:
                self.sys_phase_shift[satellite_system][carrier_phase].update(
                    phase_shift[satellite_system][carrier_phase])
            else:
                self.sys_phase_shift[satellite_system][
                    carrier_phase] = phase_shift[satellite_system][carrier_phase]
        else:
            self.sys_phase_shift[
                satellite_system] = phase_shift[satellite_system]

        self.set_phase_shift_extra(line, satellite_system, carrier_phase)
        return phase_shift

    def set_phase_shift_extra(self, line, satellite_system, carrier):
        self.sys_phase_shift[satellite_system][carrier][
            "involved_satellites_list"] += line[18:58].split()

    def set_glonass_slot_frq(self, line):
        nos = int(line[0:3])
        self.glonass_slot_frq = {
            "satellites_number": nos,
            "satellites_list": {}
        }
        self.set_glonass_slot_frq_extra(line)

    def set_glonass_slot_frq_extra(self, line):
        for g in range(8):
            pos = g * 7
            pnr = line[4 + pos:7 + pos].strip()
            if pnr == "":
                continue
            frq = int(line[8 + pos:10 + pos])
            self.glonass_slot_frq["satellites_list"][pnr] = {
                "pnr": pnr, "frq": frq
            }

    def set_glonass_cod_phs_bis(self, line):
        for i in range(4):
            pos = 13 * i
            si = line[1 + pos:4 + pos].strip()
            if si == "":
                continue
            if self.glonass_cod_phs_bis is None:
                self.glonass_cod_phs_bis = {}
            self.glonass_cod_phs_bis[si] = float(line[5 + pos:13 + pos])

    def set_leap_seconds(self, line):
        self.leap_second_current = int(line[00:6])
        self.leap_second_other = int(line[6:12])
        self.leap_second_week = int(line[12:18])
        self.leap_second_day = int(line[18:24])
        time_system = line[24:27].strip()
        if time_system == "":
            time_system = "GPS"
        self.leap_second_time_system = time_system

    def set_header(self, header_lines):
        """
        Args:
            header_lines: str, Lines are separated by "\n"
        """
        super(Rinex3ObsHeader, self).set_header(header_lines)
        last_sat_sys_ps = ""
        last_sat_sys_ps_cp = ""
        last_sat_sys_ot = ""
        last_sat_sys_sf = ""

        for line in header_lines.split("\n"):
            if line == "":
                continue

            header_label = line[60:]
            if 'MARKER TYPE' in header_label:
                self.set_marker_type(line)

            if 'ANTENNA: DELTA X/Y/Z' in header_label:
                self.set_antenna_delta_xyz(line)

            if 'ANTENNA: PHASECENTER' in header_label:
                self.set_antenna_phasecenter(line)

            if 'ANTENNA: B.SIGHT XYZ' in header_label:
                self.set_antenna_b_sight_xyz(line)

            if 'ANTENNA: ZERODIR AZI' in header_label:
                self.set_antenna_zerodir_azi(line)

            if 'ANTENNA: ZERODIR XYZ' in header_label:
                self.set_antenna_zerodir_xyz(line)

            if 'CENTER OF MASS: XYZ' in header_label:
                self.set_center_mass_xyz(line)

            if 'SYS / # / OBS TYPES' in header_label:
                self.set_sys_obs_types(line)
                # last_sat_sys_ot = ot["satellite_system"]

            # if 'SYS / # / OBS TYPES' in header_label and line[0] == " ":
            #     self.set_sys_obs_types_extra(line, last_sat_sys_ot)

            if 'SIGNAL STRENGTH UNIT' in header_label:
                self.set_signal_strength_unit(line)

            if 'SYS / DCBS APPLIED' in header_label:
                self.set_sys_dcbs_applied(line)

            if 'SYS / PCVS APPLIED' in header_label:
                self.set_sys_pcvs_applied(line)

            if 'SYS / SCALE FACTOR' in header_label and line[0] != " ":
                sf = self.set_sys_scale_factor(line)
                last_sat_sys_sf = sf["satellite_system"]

            if 'SYS / SCALE FACTOR' in header_label and line[0] == " ":
                self.set_sys_scale_factor_extra(line, last_sat_sys_sf)

            if 'SYS / PHASE SHIFT' in header_label and line[0] != " ":
                ps = self.set_phase_shift(line)
                last_sat_sys_ps = ps["satellite_system"]
                last_sat_sys_ps_cp = ps["carrier_phase"]

            if 'SYS / PHASE SHIFT' in header_label and line[0] == " ":
                self.set_phase_shift_extra(
                    line, last_sat_sys_ps, last_sat_sys_ps_cp
                )

            if 'GLONASS SLOT / FRQ #' in header_label and line[0:3].strip() != "":
                self.set_glonass_slot_frq(line)

            if 'GLONASS SLOT / FRQ #' in header_label and line[0:3].strip() == "":
                self.set_glonass_slot_frq_extra(line)

            if 'GLONASS COD/PHS/BIS' in header_label:
                self.set_glonass_cod_phs_bis(line)

            if 'LEAP SECONDS' in header_label:
                self.set_leap_seconds(line)

            if 'PRN / # OF OBS' in header_label:
                pass
                # logger.debug(
                #     "Feature 'PRN / # OF OBS' not implemented yet, sorry...")
