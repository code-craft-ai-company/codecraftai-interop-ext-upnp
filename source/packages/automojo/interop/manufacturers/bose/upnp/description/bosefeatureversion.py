"""
    .. module:: bosefeatureversion
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the BoseFeatureVersion class.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


class BoseFeatureVersion:
    """
        Represents a major/minor version for a Bose feature.
    """

    def __init__(self, major: int, minor: int):
        """
            Creates a Bose feature version object.

            :param major: Major version value.
            :param minor: Minor version value.

            :returns: None
        """

        self._major = major
        self._minor = minor
        return
