
"""
    .. module:: specversion
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: specversion module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict

from xml.etree.ElementTree import Element

def process_spec_version(spec_ver_el: Element, namespaces: Dict[str, str]) -> "SpecVersion":
    """
        Parse a ``specVersion`` XML element into a :class:`SpecVersion` instance.

        :param spec_ver_el: XML element containing spec version.
        :param namespaces: Namespace mapping for XML parsing.

        :returns: Parsed :class:`SpecVersion` object.
        
        :raises ValueError: If required elements are missing or invalid.
    """
    
    major_el = spec_ver_el.find("major", namespaces=namespaces)
    if major_el is None or major_el.text is None:
        raise ValueError("Missing or empty 'major' element in specVersion")
    
    minor_el = spec_ver_el.find("minor", namespaces=namespaces)
    if minor_el is None or minor_el.text is None:
        raise ValueError("Missing or empty 'minor' element in specVersion")
    
    try:
        major = int(major_el.text)
        minor = int(minor_el.text)
    except ValueError as ex:
        raise ValueError(f"Invalid version numbers in specVersion: major='{major_el.text}', minor='{minor_el.text}'") from ex

    spec_ver = SpecVersion(major=major, minor=minor)

    return spec_ver


def xml_format_spec_version(
    major: int,
    minor: int,
    indent: str = ""
) -> str:
    """
        Create an XML representation of the spec version.

        :param major: Major version number.
        :param minor: Minor version number.
        :param indent: Indentation for the XML string.

        :returns: XML string representation of the spec version.
    """

    desc_lines = [
        f"{indent}<specVersion>",
        f"{indent}    <major>{major}</major>",
        f"{indent}    <minor>{minor}</minor>",
        f"{indent}</specVersion>"
    ]

    desc = "\n".join(desc_lines)

    return desc


class SpecVersion:
    """
        Data container for the UPnP specification version.
    """

    def __init__(self, *, major: int, minor: int):
        """
            Constructs a :class:`SpecVersion` instance.

            :param major: Major version number.
            :param minor: Minor version number.
        """
        self.major = major
        self.minor = minor
        return

    def as_dict(self) -> dict:
        """
            Convert the SpecVersion object to a dictionary.

            :returns: Dictionary representation of the SpecVersion object.
        """
        desc = {
            "major": self.major,
            "minor": self.minor
        }
        return desc
        

    def to_xml(self, indent="") -> str:
        """
            Convert the SpecVersion object to an XML string.

            :param indent: Indentation for the XML string.

            :returns: XML string representation of the SpecVersion object.
        """

        desc = xml_format_spec_version(
            major=self.major,
            minor=self.minor,
            indent=indent
        )

        return desc

