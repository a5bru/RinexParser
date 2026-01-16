"""Factory for creating RINEX reader and header instances.

Provides factory methods to create appropriate reader and header objects
based on RINEX version (2 or 3).
"""

from .obs_reader import Rinex2ObsReader, Rinex3ObsReader, RinexObsReader
from .obs_header import Rinex2ObsHeader, Rinex3ObsHeader, RinexObsHeader


RINEX_CLASSES = {
    "versions": {
        "2": {"reader": Rinex2ObsReader, "header": Rinex2ObsHeader},
        "3": {"reader": Rinex3ObsReader, "header": Rinex3ObsHeader},
    }
}


class RinexObsFactory:
    """Factory for creating RINEX reader and header instances.
    
    Supports creating readers and headers for RINEX versions 2 and 3,
    both from explicit version specification and by reading file headers.
    """

    @staticmethod
    def _create_obs_type_by_version(
        rinex_version: int | str,
        class_type: str,
    ) -> type:
        """Get the appropriate class for a given RINEX version and type.
        
        Args:
            rinex_version: RINEX version as int or str (2 or 3).
            class_type: Type of class to retrieve ("reader" or "header").
            
        Returns:
            type: The requested class type.
            
        Raises:
            KeyError: If rinex_version is not supported.
        """
        version_key = str(rinex_version)
        if version_key not in RINEX_CLASSES["versions"]:
            raise KeyError(
                f"Unsupported RINEX version: {rinex_version} "
                f"(supported: {list(RINEX_CLASSES['versions'].keys())})"
            )
        return RINEX_CLASSES["versions"][version_key][class_type]

    def create_obs_reader_by_version(
        self,
        rinex_version: int | str,
    ) -> type[RinexObsReader]:
        """Create a reader class for the specified RINEX version.
        
        Args:
            rinex_version: RINEX version (2 or 3).
            
        Returns:
            type[RinexObsReader]: Reader class for the version.
        """
        return self._create_obs_type_by_version(rinex_version, "reader")

    def create_obs_header_by_version(
        self,
        rinex_version: int | str,
    ) -> type[RinexObsHeader]:
        """Create a header class for the specified RINEX version.
        
        Args:
            rinex_version: RINEX version (2 or 3).
            
        Returns:
            type[RinexObsHeader]: Header class for the version.
        """
        return self._create_obs_type_by_version(rinex_version, "header")

    def create_obs_reader_by_file(
        self,
        rinex_file: str,
    ) -> type[RinexObsReader]:
        """Create a reader class by detecting version from file header.
        
        Args:
            rinex_file: Path to the RINEX file.
            
        Returns:
            type[RinexObsReader]: Reader class for the detected version.
        """
        with open(rinex_file, 'r') as handler:
            version_dict = RinexObsHeader.parse_version_type(handler.readline())
            version = int(version_dict["format_version"])
            return self._create_obs_type_by_version(version, "reader")

    def create_obs_header_by_file(
        self,
        rinex_file: str,
    ) -> type[RinexObsHeader]:
        """Create a header class by detecting version from file header.
        
        Args:
            rinex_file: Path to the RINEX file.
            
        Returns:
            type[RinexObsHeader]: Header class for the detected version.
        """
        with open(rinex_file, 'r') as handler:
            version_dict = RinexObsHeader.parse_version_type(handler.readline())
            version = int(version_dict["format_version"])
            return self._create_obs_type_by_version(version, "header")

