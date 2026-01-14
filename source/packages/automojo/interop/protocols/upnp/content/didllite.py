"""
    .. module:: didllite
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: didllite module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import List, NamedTuple, Optional

from enum import Enum

from xml.etree.ElementTree import fromstring as from_xml_string
from xml.etree.ElementTree import Element

from automojo.errors.exceptions import ProtocolError


DIDL_LINESEP = "\n"

DIDL_NAMESPACES = {
    "": "urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "r": "urn:schemas-rinconnetworks-com:metadata-1-0/",
    "upnp": "urn:schemas-upnp-org:metadata-1-0/upnp/",
}

def _parse_restricted_value(restricted_value: str) -> bool:
    """
        Parse the ``restricted`` attribute string into a boolean.

        :param restricted_value: Value of the restricted attribute.

        :returns: ``True`` when restricted, otherwise ``False``.
    """
    normalized = restricted_value.strip().lower()
    if normalized in ("1", "true", "yes"):
        return True
    if normalized in ("0", "false", "no"):
        return False

    raise ProtocolError(
        f"DIDL message has an invalid 'restricted' attribute value '{restricted_value}'."
    )


class DidlDesc:
    """
        Represents a generic DIDL-Lite ``desc`` element.
    """

    def __init__(self, *, desc: str, **attrs):
        """
            :param desc: Description string.
            :param attrs: Optional attributes for the desc element.
        """
        self._desc = desc
        self._attrs = attrs
        return

    def to_xml_lines(self, indent=""):
        """
            Return XML lines representing this description element.
        """

        xlines = [
            "{}<desc{}>".format(indent),
            "{}    {}".format(indent, self._desc),
            "{}</desc>".format(indent),
        ]

        return xlines

    def to_xml(self):
        """
            Return the XML string for this description element.
        """

        attrs_str = ""

        attr_items = self._attrs.items()
        if len(attr_items) > 0:
            for ak, av in self._attrs.items():
                attrs_str = "{} {}='{}' ".format(attrs_str, ak, av)

        xstr = "<desc{}>{}</desc>".format(attrs_str, self._desc)

        return xstr


class DidlResource(NamedTuple):
    """
        Information about a resource associated with a DIDL item.
    """

    protocol_info: str
    uri: str
    duration: Optional[str] = None
    size: Optional[int] = None

    @classmethod
    def from_xml(cls, res_element: Element):
        """
            Create a :class:`DidlResource` from an XML element.
        """
        # Extract required protocolInfo attribute
        try:
            protocol_info = res_element.attrib["protocolInfo"]
        except KeyError:
            raise ProtocolError("DIDL resource element is missing required attribute 'protocolInfo'.")
        
        # Extract URI from element text
        uri = res_element.text
        if uri is None:
            raise ProtocolError("DIDL resource element is missing URI content.")
        
        # Extract optional attributes
        duration = res_element.attrib.get("duration")
        
        size = None
        size_str = res_element.attrib.get("size")
        if size_str is not None:
            try:
                size = int(size_str)
            except ValueError:
                raise ProtocolError(f"DIDL resource element has invalid size attribute: '{size_str}'")
        
        resource = cls(
            protocol_info=protocol_info,
            uri=uri,
            duration=duration,
            size=size
        )
        
        return resource

    def to_xml_lines(self, indent=""):
        """
            Return XML lines for this resource.
        """

        sizeattr = ""
        if self.size is not None:
            sizeattr = " size='{}'".format(self.size)

        xlines = [
            "{}<res protocolInfo='{}'{}>".format(indent, self.protocol_info, sizeattr),
            "{}    {}".format(indent, self.uri),
            "{}</res>".format(indent),
        ]

        return xlines

    def to_xml(self):
        """
            Return the XML string for this resource.
        """

        sizeattr = ""
        if self.size is not None:
            sizeattr = " size='{}'".format(self.size)

        xstr = "<res protocolInfo='{}'{}>{}</res>".format(
            self.protocol_info, sizeattr, self.uri
        )

        return xstr


class DidlWriteStatus(str, Enum):
    """
        Enumeration of write status values for DIDL objects.
    """

    MIXED = "MIXED"
    NOT_WRITABLE = "NOT_WRITABLE"
    PROTECTED = "PROTECTED"
    UNKNOWN = "UNKNOWN"
    WRITABLE = "WRITABLE"


class DidlObject:
    """
        Base DIDL object with core properties and XML helpers.
    """

    element_tag = None
    upnp_class = None

    def __init__(
        self,
        *,
        oid: str,
        parent_id: str,
        restricted: bool,
        title: str,
        res: Optional[DidlResource] = None
    ):
        """
            Initialize a new :class:`DidlObject` instance.

            :param oid: Object identifier for the DIDL object.
            :param parent_id: Identifier of the parent object.
            :param restricted: Indicates if the object is read-only.
            :param title: Title string for the object.
            :param res: Resource associated with the object, if any.
        """
        self._oid = oid
        self._parent_id = parent_id
        self._restricted = restricted
        self._title = title
        self._res = res
        return

    @property
    def oid(self) -> str:
        """
            Unique object identifier.

            :returns: Object identifier string.
        """
        return self._oid

    @property
    def parent_id(self) -> str:
        """
            Identifier of the parent object.

            :returns: Identifier of the parent object.
        """
        return self._parent_id

    @property
    def restricted(self) -> bool:
        """
            Indicates if the object is read-only.

            :returns: ``True`` if the object is read-only.
        """
        return self._restricted

    @property
    def res(self) -> Optional[DidlResource]:
        """
            Primary :class:`DidlResource` for this object.

            :returns: The primary :class:`DidlResource` instance, if present.
        """
        return self._res

    @property
    def title(self) -> str:
        """
            Title string for this object.

            :returns: Title string value.
        """
        return self._title

    def create_opening_element(self):
        """
            Return the opening XML element string for this object.
        """

        estr = "<{} id='{}' parentID='{}' restricted='{}' >".format(
            self.element_tag, self._oid, self._parent_id, self._restricted
        )
        return estr

    def create_closing_element(self):
        """
            Return the closing XML element string for this object.
        """

        estr = "</{}>".format(self.element_tag)
        return estr

    def to_xml_lines(self, indent=""):
        """
            Return a list of XML lines describing this DIDL object.
        """

        xlines = [self.create_opening_element()]

        if self._title is not None:
            xlines.append("<dc:title>{}</dc:title>".format(self._title))

        if self.upnp_class is not None:
            xlines.append("<upnp:class>{}</upnp:class>".format(self.upnp_class))

        if self._res is not None:
            res_lines = self._res.to_xml_lines()
            xlines.extend(res_lines)

        xlines.append(self.create_closing_element())

        return xlines

    def to_xml(self):
        """
            Return the XML string representation of this DIDL object.
        """

        xml_parts = [self.create_opening_element()]

        if self._title is not None:
            xml_parts.append("<dc:title>{}</dc:title>".format(self._title))

        if self.upnp_class is not None:
            xml_parts.append("<upnp:class>{}</upnp:class>".format(self.upnp_class))

        if self._res is not None:
            xml_parts.append(self._res.to_xml())

        xml_parts.append(self.create_closing_element())

        xmlstr = "".join(xml_parts)

        return xmlstr


class DidlContainerPhotoAlbum(DidlObject):
    """
        Container object representing a photo album.
    """

    element_tag = "container"
    upnp_class = "object.container.album.photoAlbum"

    def __init__(
        self,
        *,
        oid: str,
        parent_id: str,
        restricted: bool,
        title: str,
        child_count: int,
        storage_used: int,
        write_status: str = DidlWriteStatus.UNKNOWN
    ):
        """
            Initialize a photo album container.

            :param oid: Object identifier for the album.
            :param parent_id: Identifier of the parent container.
            :param restricted: Indicates if the album is read-only.
            :param title: Title string for the album.
            :param child_count: Number of child items.
            :param storage_used: Storage used by this album.
            :param write_status: Write status for the album.
        """
        super().__init__(
            oid=oid, parent_id=parent_id, restricted=restricted, title=title
        )
        self._child_count = child_count
        self._storage_used = storage_used
        self._write_status = write_status
        return

    @classmethod
    def from_xml(cls, obj_element: Element, namespaces: Optional[dict] = None):
        """
            Create a :class:`DidlContainerPhotoAlbum` from an XML element.

            :param obj_element: XML element describing the DIDL container.
            :param namespaces: Optional namespace map for element lookup.

            :returns: Instance of :class:`DidlContainerPhotoAlbum`.
        """

        # Read the Required attributes with proper error handling
        try:
            oid = obj_element.attrib["id"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlContainerPhotoAlbum is missing required attribute 'id'.")
        
        try:
            parent_id = obj_element.attrib["parentID"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlContainerPhotoAlbum is missing required attribute 'parentID'.")
        
        try:
            restricted = obj_element.attrib["restricted"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlContainerPhotoAlbum is missing required attribute 'restricted'.")
        restricted = _parse_restricted_value(restricted)

        # Read the Required elements
        e_title = obj_element.find("dc:title", namespaces=namespaces)
        if e_title is None:
            errmsg = "DIDL message for DidlContainerPhotoAlbum is missing a required element 'title'."
            raise ProtocolError(errmsg)
        title = e_title.text

        # Set default values for optional parameters
        child_count = -1
        storage_used = -1
        write_status = DidlWriteStatus.UNKNOWN

        obj = DidlContainerPhotoAlbum(
            oid=oid,
            parent_id=parent_id,
            restricted=restricted,
            title=title,
            child_count=child_count,
            storage_used=storage_used,
            write_status=write_status,
        )
        return obj


class DidlContainerStorageFolder(DidlObject):
    """
        Container object representing a generic storage folder.
    """

    element_tag = "container"
    upnp_class = "object.container.storageFolder"

    def __init__(
        self,
        *,
        oid: str,
        parent_id: str,
        restricted: bool,
        title: str,
        child_count: int,
        storage_used: int,
        write_status: str = DidlWriteStatus.UNKNOWN
    ):
        """
            Initialize a storage folder container.

            :param oid: Object identifier for the folder.
            :param parent_id: Identifier of the parent container.
            :param restricted: Indicates if the folder is read-only.
            :param title: Title string for the folder.
            :param child_count: Number of child items.
            :param storage_used: Storage used by this folder.
            :param write_status: Write status for the folder.
        """
        super().__init__(
            oid=oid, parent_id=parent_id, restricted=restricted, title=title
        )
        self._child_count = child_count
        self._storage_used = storage_used
        self._write_status = write_status
        return

    @classmethod
    def from_xml(cls, obj_element: Element, namespaces: Optional[dict] = None):
        """
            Create a :class:`DidlContainerStorageFolder` from an XML element.

            :param obj_element: XML element describing the folder.
            :param namespaces: Optional namespace map for element lookup.

            :returns: Instance of :class:`DidlContainerStorageFolder`.
        """

        # Read the Required attributes with proper error handling
        try:
            oid = obj_element.attrib["id"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlContainerStorageFolder is missing required attribute 'id'.")
        
        try:
            parent_id = obj_element.attrib["parentID"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlContainerStorageFolder is missing required attribute 'parentID'.")
        
        try:
            restricted = obj_element.attrib["restricted"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlContainerStorageFolder is missing required attribute 'restricted'.")
        restricted = _parse_restricted_value(restricted)

        # Read the Required elements
        e_title = obj_element.find("dc:title", namespaces=namespaces)
        if e_title is None:
            errmsg = "DIDL message for DidlContainerStorageFolder is missing a required element 'title'."
            raise ProtocolError(errmsg)
        title = e_title.text

        child_count = -1
        storage_used = -1
        write_status = DidlWriteStatus.UNKNOWN

        obj = DidlContainerStorageFolder(
            oid=oid,
            parent_id=parent_id,
            restricted=restricted,
            title=title,
            child_count=child_count,
            storage_used=storage_used,
            write_status=write_status,
        )
        return obj


class DidlItemAlbumArt(DidlObject):
    """
        Item representing vendor supplied album artwork.
    """

    element_tag = "item"
    upnp_class = "object.item.imageItem.photo.vendorAlbumArt"

    def __init__(
        self,
        *,
        oid: str,
        parent_id: str,
        restricted: bool,
        title: str,
        res: DidlResource
    ):
        """
            Initialize a vendor album art item.

            :param oid: Object identifier for the item.
            :param parent_id: Identifier of the parent container.
            :param restricted: Indicates if the item is read-only.
            :param title: Title string for the item.
            :param res: Resource for the album art image.
        """
        super().__init__(
            oid=oid, parent_id=parent_id, restricted=restricted, title=title, res=res
        )
        return

    @classmethod
    def from_xml(cls, obj_element: Element, namespaces: Optional[dict] = None):
        """
            Create a :class:`DidlItemAlbumArt` from an XML element.

            :param obj_element: XML element describing the item.
            :param namespaces: Optional namespace map for element lookup.

            :returns: Instance of :class:`DidlItemAlbumArt`.
        """

        # Read the Required attributes with proper error handling
        try:
            oid = obj_element.attrib["id"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemAlbumArt is missing required attribute 'id'.")
        
        try:
            parent_id = obj_element.attrib["parentID"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemAlbumArt is missing required attribute 'parentID'.")
        
        try:
            restricted = obj_element.attrib["restricted"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemAlbumArt is missing required attribute 'restricted'.")
        restricted = _parse_restricted_value(restricted)

        title = ""
        e_title = obj_element.find("dc:title", namespaces=namespaces)
        if e_title is not None and e_title.text is not None:
            title = e_title.text

        e_res = obj_element.find("res", namespaces=namespaces)
        if e_res is None:
            errmsg = "DIDL message for DidlItemAlbumArt is missing a required element 'res'."
            raise ProtocolError(errmsg)
        res = DidlResource.from_xml(e_res)

        obj = DidlItemAlbumArt(
            oid=oid,
            parent_id=parent_id,
            restricted=restricted,
            title=title,
            res=res,
        )
        return obj


class DidlItemMusicTrack(DidlObject):
    """
        Item describing a single music track resource.
    """

    element_tag = "item"
    upnp_class = "object.item.audioItem.musicTrack"

    def __init__(
        self,
        *,
        oid: str,
        parent_id: str,
        restricted: bool,
        title: str,
        res: DidlResource,
        creator: str,
        album_art: Optional[str] = None,
        genre: Optional[str] = None
    ):
        """
            Initialize a music track item.

            :param oid: Object identifier for the item.
            :param parent_id: Identifier of the parent container.
            :param restricted: Indicates if the item is read-only.
            :param title: Title string for the item.
            :param res: Primary resource for the music track.
            :param creator: Creator of the track.
            :param album_art: Album art URI if available.
            :param genre: Genre of the track.
        """
        super().__init__(
            oid=oid, parent_id=parent_id, restricted=restricted, title=title, res=res
        )
        self._creator = creator
        self._album_art = album_art
        self._genre = genre
        return

    @classmethod
    def from_xml(cls, obj_element: Element, namespaces: Optional[dict] = None):
        """
            Create a :class:`DidlItemMusicTrack` from an XML element.

            :param obj_element: XML element describing the item.
            :param namespaces: Optional namespace map for element lookup.

            :returns: Instance of :class:`DidlItemMusicTrack`.
        """

        # Read the Required attributes with proper error handling
        try:
            oid = obj_element.attrib["id"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemMusicTrack is missing required attribute 'id'.")
        
        try:
            parent_id = obj_element.attrib["parentID"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemMusicTrack is missing required attribute 'parentID'.")
        
        try:
            restricted = obj_element.attrib["restricted"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemMusicTrack is missing required attribute 'restricted'.")
        restricted = _parse_restricted_value(restricted)

        # Read the Required elements
        e_title = obj_element.find("dc:title", namespaces=namespaces)
        if e_title is None:
            errmsg = "DIDL message for DidlItemMusicTrack is missing a required element 'title'."
            raise ProtocolError(errmsg)
        title = e_title.text

        e_res = obj_element.find("res", namespaces=namespaces)
        if e_res is None:
            errmsg = "DIDL message for DidlItemMusicTrack is missing a required element 'res'."
            raise ProtocolError(errmsg)
        res = DidlResource.from_xml(e_res)

        # Read the Optional elements
        creator = None
        e_creator = obj_element.find("dc:creator", namespaces=namespaces)
        if e_creator is not None:
            creator = e_creator.text

        album_art = None
        e_album_art = obj_element.find("upnp:albumArtURI", namespaces=namespaces)
        if e_album_art is not None:
            album_art = e_album_art.text

        obj = DidlItemMusicTrack(
            oid=oid,
            parent_id=parent_id,
            restricted=restricted,
            title=title,
            res=res,
            creator=creator,
            album_art=album_art,
        )

        return obj


class DidlItemPhoto(DidlObject):
    """
        Item representing a still photo image.
    """

    element_tag = "item"
    upnp_class = "object.item.imageItem.photo"

    def __init__(
        self,
        *,
        oid: str,
        parent_id: str,
        restricted: bool,
        title: str,
        res: DidlResource,
        date: str
    ):
        """
            Initialize a photo item.

            :param oid: Object identifier for the item.
            :param parent_id: Identifier of the parent container.
            :param restricted: Indicates if the item is read-only.
            :param title: Title string for the item.
            :param res: Primary resource for the photo.
            :param date: Date associated with the photo.
        """
        super().__init__(
            oid=oid, parent_id=parent_id, restricted=restricted, title=title, res=res
        )
        self._date = date
        return

    @property
    def date(self):
        """
            Date string associated with the photo item.

            :returns: The date string for the photo.
        """
        return self._date

    @classmethod
    def from_xml(self, obj_element: Element, namespaces: Optional[dict] = None):
        """
            Create a :class:`DidlItemPhoto` from an XML element.

            :param obj_element: XML element describing the item.
            :param namespaces: Optional namespace map for element lookup.

            :returns: Instance of :class:`DidlItemPhoto`.
        """

        # Read the Required attributes with proper error handling
        try:
            oid = obj_element.attrib["id"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemPhoto is missing required attribute 'id'.")
        
        try:
            parent_id = obj_element.attrib["parentID"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemPhoto is missing required attribute 'parentID'.")
        
        try:
            restricted = obj_element.attrib["restricted"]
        except KeyError:
            raise ProtocolError("DIDL message for DidlItemPhoto is missing required attribute 'restricted'.")
        restricted = _parse_restricted_value(restricted)

        e_title = obj_element.find("dc:title", namespaces=namespaces)
        if e_title is None or e_title.text is None:
            errmsg = "DIDL message for DidlItemPhoto is missing a required element 'title'."
            raise ProtocolError(errmsg)
        title = e_title.text

        e_date = obj_element.find("dc:date", namespaces=namespaces)
        if e_date is None or e_date.text is None:
            errmsg = "DIDL message for DidlItemPhoto is missing a required element 'date'."
            raise ProtocolError(errmsg)
        date = e_date.text

        e_res = obj_element.find("res", namespaces=namespaces)
        if e_res is None:
            errmsg = "DIDL message for DidlItemPhoto is missing a required element 'res'."
            raise ProtocolError(errmsg)
        res = DidlResource.from_xml(e_res)

        obj = DidlItemPhoto(
            oid=oid,
            parent_id=parent_id,
            restricted=restricted,
            title=title,
            res=res,
            date=date,
        )
        return obj


class DidlLitePacket:
    """
        Collection of :class:`DidlObject` items serialized to DIDL-Lite XML.
    """

    xml_namespaces = {
        "dc": "http://purl.org/dc/elements/1.1/",
        "upnp": "urn:schemas-upnp-org:metadata-1-0/upnp/",
        "": "urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/",
    }

    def __init__(self, objects: Optional[List[DidlObject]] = None):
        """
            Initialize a :class:`DidlLitePacket` instance.

            :param objects: Optional list of :class:`DidlObject` instances.
        """
        self._objects = objects if objects is not None else []
        return

    @property
    def objects(self):
        """
            List of contained :class:`DidlObject` instances.

            :returns: Sequence of :class:`DidlObject` instances.
        """
        return self._objects

    def to_xml_lines(self, indent=""):
        """
            Return a list of XML lines representing this DIDL packet.

            :param indent: Optional indentation prefix for each line.

            :returns: List of XML strings.
        """

        attrs_str = ""
        for ak, av in self.xml_namespaces.items():
            attrs_str = "{} {}='{}' ".format(attrs_str, ak, av)

        xlines = ["<DIDL-Lite{}>".format(attrs_str)]

        for obj in self._objects:
            obj_lines = obj.to_xml_lines(indent + "    ")
            xlines.extend(obj_lines)

        xlines.append("</DIDL-Lite>")

        return xlines

    def to_xml(self):
        """
            Return the XML string representation of this DIDL packet.

            :returns: XML string for the packet.
        """

        attrs_str = ""
        for ak, av in self.xml_namespaces.items():
            attrs_str = "{} {}='{}' ".format(attrs_str, ak, av)

        xparts = ["<DIDL-Lite{}>".format(attrs_str)]

        for obj in self._objects:
            xstr = obj.to_xml()
            xparts.append(xstr)

        xparts.append("</DIDL-Lite>")

        xstr = DIDL_LINESEP.join(xparts)

        return xstr


def parse_didl_lite_packet(content, namespaces=DIDL_NAMESPACES):
    """
        Parse a DIDL-Lite XML packet into DIDL object instances.
    """

    root_element: Element = from_xml_string(content)

    obj_items = []

    root_children = [ce for ce in root_element]

    for obj_element in root_children:

        class_element = obj_element.find("upnp:class", namespaces=namespaces)
        didl_class = class_element.text

        obj = None

        if didl_class == "object.container.storageFolder":
            obj = DidlContainerStorageFolder.from_xml(
                obj_element, namespaces=namespaces
            )
        elif didl_class == "object.container.album.photoAlbum":
            obj = DidlContainerPhotoAlbum.from_xml(obj_element, namespaces=namespaces)
        elif didl_class == "object.item.imageItem.photo.vendorAlbumArt":
            obj = DidlItemAlbumArt.from_xml(obj_element, namespaces=namespaces)
        elif didl_class == "object.item.audioItem.musicTrack":
            obj = DidlItemMusicTrack.from_xml(obj_element, namespaces=namespaces)
        elif didl_class == "object.item.imageItem.photo":
            obj = DidlItemPhoto.from_xml(obj_element, namespaces=namespaces)
        else:
            errmsg = "Unknown DIDL object class '{}':".format(didl_class)
            raise ProtocolError(errmsg)

        obj_items.append(obj)

    return obj_items


EXAMPLE_DIDL_PACKET = """
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
           xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
           xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <container id="13" parentID="2" restricted="0" searchable="1">
        <dc:title>Christmas</dc:title>
        <upnp:class>object.container.album.photoAlbum</upnp:class>
        <upnp:searchClass includeDerived="0">
            object.item.imageItem.photo
        </upnp:searchClass>
        <upnp:createClass includeDerived="0">
            object.item.imageItem.photo
        </upnp:createClass>
    </container>
    <container id="1" parentID="0" childCount="2" restricted="0">
        <dc:title>My Music</dc:title>
        <upnp:class>object.container.storageFolder</upnp:class>
        <upnp:storageUsed>730000</upnp:storageUsed>
        <upnp:writeStatus>WRITABLE</upnp:writeStatus>
        <upnp:searchClass includeDerived="0">
            object.container.album.musicAlbum
        </upnp:searchClass>
        <upnp:searchClass includeDerived="0">
            object.item.audioItem.musicTrack
        </upnp:searchClass>
        <upnp:createClass includeDerived="0">
            object.container.album.musicAlbum
        </upnp:createClass>
    </container> 
    <item id="-1" parentID="-1" restricted="true">
        <res protocolInfo="sonos.com-spotify:*:audio/x-spotify:*" duration="0:03:13">x-sonos-spotify:spotify%3atrack%3a7HXBG0W8gFJwHUh5mVF9tf?sid=9&amp;flags=8224&amp;sn=2</res>
        <r:streamContent></r:streamContent>
        <upnp:albumArtURI>/getaa?s=1&amp;u=x-sonos-spotify%3aspotify%253atrack%253a7HXBG0W8gFJwHUh5mVF9tf%3fsid%3d9%26flags%3d8224%26sn%3d2</upnp:albumArtURI>
        <dc:title>Rise</dc:title>
        <upnp:class>object.item.audioItem.musicTrack</upnp:class>
        <dc:creator>Lost Frequencies</dc:creator>
        <upnp:album>Rise</upnp:album>
    </item>
    <item id="31" parentID="30" restricted="0">
        <dc:title>Brand New Day</dc:title>
        <upnp:class name="Vendor Album Art">
            object.item.imageItem.photo.vendorAlbumArt
        </upnp:class>
        <res protocolInfo="http-get:*:image/jpeg:*" size="20000">
            http://10.0.0.1/getcontent.asp?id=31
        </res>
    </item> 
    <item id="14" parentID="12" restricted="0">
        <dc:title>Sunset on the beach</dc:title>
        <dc:date>2001-10-20</dc:date>
        <upnp:class>object.item.imageItem.photo</upnp:class>
        <res protocolInfo="http-get:*:image/jpeg:*" size="20000">
            http://10.0.0.1/getcontent.asp?id=14
        </res>
    </item> 
</DIDL-Lite>
"""

if __name__ == "__main__":
    parse_didl_lite_packet(EXAMPLE_DIDL_PACKET)
