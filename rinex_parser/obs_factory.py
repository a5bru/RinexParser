from .obs_reader import Rinex2ObsReader, Rinex3ObsReader
from .obs_header import Rinex2ObsHeader, Rinex3ObsHeader, RinexObsHeader


RINEX_CLASSES = {
    "versions": {
        "2": {
            "reader": Rinex2ObsReader,
            "header": Rinex2ObsHeader
        },
        "3": {
            "reader": Rinex3ObsReader,
            "header": Rinex3ObsHeader
        }
    }
}


class RinexObsFactory(object):
    """

    """

    def __create_obs_type_by_version(self, rinex_version, class_type):
        assert str(rinex_version) in RINEX_CLASSES["versions"]
        return RINEX_CLASSES["versions"][str(rinex_version)][class_type]

    def create_obs_reader_by_version(self, rinex_version):
        return self.__create_obs_type_by_version(rinex_version, "reader")

    def create_obs_header_by_version(self, rinex_version):
        return self.__create_obs_type_by_version(rinex_version, "header")

    def __create_obs_type_by_file(self, rinex_file, class_type):
        with open(rinex_file, 'r') as handler:
            version_dict = RinexObsHeader.parse_version_type(handler.readline())
            version = int(version_dict["format_version"])
            return self.__create_obs_type_by_version(version, class_type)

    def create_obs_reader_by_file(self, rinex_file):
        return self.__create_obs_type_by_file(rinex_file, "reader")

    def create_obs_header_by_file(self, rinex_file):
        return self.__create_obs_type_by_file(rinex_file, "header")

