
"""
    .. module:: icondesc
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: icondesc module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

import json

def xml_format_icon_desc(mimetype: str, width: int, height: int, depth: int, url: str, indent: str = "") -> str:
    """
        Format an icon description as an XML string.

        :param mimetype: MIME type of the icon.
        :param width: Width of the icon.
        :param height: Height of the icon.
        :param depth: Color depth of the icon in bits.
        :param url: URL of the icon.
        :param indent: Indentation for the XML string.

        :returns: XML string representation of the icon description.
    """

    # Create XML representation

    desc_lines = [
        f"{indent}<icon>",
        f"{indent}    <mimetype>{mimetype}</mimetype>",
        f"{indent}    <width>{width}</width>",
        f"{indent}    <height>{height}</height>",
        f"{indent}    <depth>{depth}</depth>",
        f"{indent}    <url>{url}</url>",
        f"{indent}</icon>"
    ]

    # Use string line separator for XML content
    desc = "\n".join(desc_lines)

    return desc

class IconDesc:
    """
        Class representing an icon description in a UPnP 'iconList' xml segment.
    """

    def __init__(self, *, mimetype: str, width: int, height: int, depth: int, url: str):
        """
            Initialize the IconDesc object.

            :param mimetype: MIME type of the icon.
            :param width: Width of the icon.
            :param height: Height of the icon.
            :param depth: Color depth of the icon in bits.
            :param url: URL of the icon.
            
        """
        self.mimetype = mimetype
        self.width = width
        self.height = height
        self.depth = depth
        self.url = url
        return

    def as_dict(self) -> dict:
        """
            Convert the IconDesc object to a dictionary.

            :returns: Dictionary representation of the IconDesc object.
        """
        desc = {
            "mimetype": self.mimetype,
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "url": self.url
        }
        return desc

    def to_json(self) -> str:
        """
            Convert the IconDesc object to a JSON string.

            :returns: JSON string representation of the IconDesc object.
        """
        desc = self.as_dict()
        json_desc = json.dumps(desc, indent=4)
        return json_desc

    def to_xml(self, indent="") -> str:
        """
            Convert the IconDesc object to an XML string.

            :returns: XML string representation of the IconDesc object.
        """

        desc = xml_format_icon_desc(
            mimetype=self.mimetype,
            width=self.width,
            height=self.height,
            depth=self.depth,
            url=self.url,
            indent=indent
        )

        return desc

    def as_xml(self, indent="") -> str:
        """
            Convert the IconDesc object to an XML string.
            This method provides compatibility with the interface expected by device descriptions.

            :param indent: Indentation for the XML string.

            :returns: XML string representation of the IconDesc object.
        """
        return self.to_xml(indent=indent)

    def __repr__(self) -> str:
        """
            Return a string representation of the IconDesc object.

            :returns: String representation of the IconDesc object.
        """
        rval = f"IconDesc(mimetype={self.mimetype}, width={self.width}, height={self.height}, depth={self.depth}, url={self.url})"
        return rval

    def __str__(self) -> str:
        """
            Return a string representation of the IconDesc object.

            :returns: String representation of the IconDesc object.
        """
        sval = self.to_xml()
        return sval

