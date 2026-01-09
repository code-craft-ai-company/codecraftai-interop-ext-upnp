"""
    .. module:: bosefeatureversion
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the BoseFeatureVersion class.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Optional


class BoseFeatureVersion:
    """
        Represents a major/minor version for a Bose feature.
    """

    def __init__(self, major: Optional[int], minor: Optional[int]):
        """
            Creates a Bose feature version object.

            :param major: Major version value or None if unknown.
            :param minor: Minor version value or None if unknown.

            :returns: None
        """

        self._major = major
        self._minor = minor
        return

    @property
    def major(self) -> Optional[int]:
        """
            Returns the major version number.

            :returns: The major version value or None if unknown.
        """
        return self._major

    @property
    def minor(self) -> Optional[int]:
        """
            Returns the minor version number.

            :returns: The minor version value or None if unknown.
        """
        return self._minor

    def __str__(self) -> str:
        """
            Returns a string representation of the version.

            :returns: Version string in format "major.minor" or "unknown" if values are None.
        """
        if self._major is None and self._minor is None:
            return "unknown"
        elif self._major is None:
            return f"?.{self._minor}"
        elif self._minor is None:
            return f"{self._major}.?"
        else:
            return f"{self._major}.{self._minor}"

    def __repr__(self) -> str:
        """
            Returns a detailed string representation of the version object.

            :returns: Detailed version representation.
        """
        return f"BoseFeatureVersion(major={self._major}, minor={self._minor})"
