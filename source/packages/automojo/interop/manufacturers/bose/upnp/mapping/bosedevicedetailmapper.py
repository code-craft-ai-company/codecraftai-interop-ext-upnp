"""
    .. module:: bosedevicedetailmapper
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing data description classes that describe Bose UPNP devices.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Any, Dict, Optional

from xml.etree.ElementTree import Element

from automojo.interop.manufacturers.bose.constants import BOSE_MANUFACTURER_NAME

from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import EmbeddedDeviceDesc
from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion
from automojo.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper

from automojo.interop.manufacturers.bose.constants import BOSE_XML_NAMESPACES, BOSE_NAMESPACE_PREFIX_END


from automojo.interop.manufacturers.bose.upnp.description.bosedevicedetail import BoseDeviceDetail
from automojo.interop.manufacturers.bose.upnp.description.boseembeddeddevicedetail import BoseEmbeddedDeviceDetail
from automojo.interop.manufacturers.bose.upnp.description.bosemultiroomversions import BoseMultiRoomVersions
from automojo.interop.manufacturers.bose.upnp.description.bosefeatureversion import BoseFeatureVersion


class BoseDeviceDetailMapper(DeviceDetailMapper):
    """
        The :class:`BoseDeviceDetailMapper` provides customized processing of Bose specific device descriptions for the purpose of
        mapping device description content to a common device description model.
    """


    @classmethod
    def get_manufacturer(cls):
        return BOSE_MANUFACTURER_NAME

    @classmethod
    def create_root_device_description(cls, root_el: Element, namespaces: Dict[str, str], specVersion: SpecVersion,
                                       locationURL: Optional[str] = None) -> BoseDeviceDetail:
        """
            Creates a device description object from the root device element.

            :param root_el: Root element from the device description document.
            :param namespaces: Namespace mapping for XML parsing.
            :param specVersion: Parsed :class:`SpecVersion` information.
            :param locationURL: Optional location URL for the device.

            :returns: Newly created :class:`Basic1DeviceDesc` instance.
        """

        device_el: Element = root_el.find("device", namespaces=namespaces)

        device_desc = cls._process_device(root_el, device_el, namespaces, specVersion, locationURL=locationURL, is_embedded=False)

        return device_desc


    @classmethod
    def _create_basic1_device_desc(cls, root_el: Element, device_el: Element, namespaces: Dict[str, str], specVersion: SpecVersion,
                                  locationURL: str, params: Dict[str, Any]) -> BoseDeviceDetail:
        """
            Creates a :class:`BoseDeviceDetail` from a basic device description element.

            :param cls: The class type this method is bound to.
            :param root_el: Root XML element.
            :param device_el: Device element to process.
            :param namespaces: XML namespace mappings.
            :param specVersion: UPnP specification version object.
            :param locationURL: URL where the device description was retrieved.
            :param params: Dictionary of parsed parameters.

            :returns: A populated :class:`BoseDeviceDetail` instance.
        """

        ext_params = {
            "mac_addr": None,
            "generation":  None,
            "codename":  None,
            "color": None,
            "software_version": None,
            "multi_room": None
        }

        params.update(ext_params)

        all_namespaces = {}
        all_namespaces.update(namespaces)
        all_namespaces.update(BOSE_XML_NAMESPACES)

        for child_el in device_el.iterfind("./bose:*", namespaces=BOSE_XML_NAMESPACES):
            full_tag = child_el.tag
            tag = full_tag[BOSE_NAMESPACE_PREFIX_END:]
            txtval = child_el.text

            if tag == "X_MAC":
                params['mac_addr'] = txtval if txtval is not None else ""
            elif tag == "X_ecoSystem":
                params['generation'] = txtval if txtval is not None else ""
            elif tag == "X_productType":
                params['codename'] = txtval if txtval is not None else ""
            elif tag == "X_productColor":
                params['color'] = txtval if txtval is not None else ""
            elif tag == "X_softwareVersion":
                params['software_version'] = txtval if txtval is not None else ""
            elif tag == "X_multiroomVersions":
                params['multi_room'] = BoseDeviceDetailMapper.process_device_multiroom_versions(child_el, all_namespaces)
        
        try:
            device = BoseDeviceDetail(specVersion=specVersion, locationURL=locationURL, **params)
        except Exception as err:
            err_msg = f"Error creating Bose device description: {err}"
            raise RuntimeError(err_msg) from err

        return device

    @classmethod
    def _create_embedded_device_desc(cls, root_el: Element, device_el: Element, namespaces: Dict[str, str], specVersion: SpecVersion,
                                   params: Dict[str, Any]) -> EmbeddedDeviceDesc:
        """
            Creates an :class:`EmbeddedDeviceDesc` for a Bose embedded device.

            :param root_el: Root XML element.
            :param device_el: Device element to process.
            :param namespaces: XML namespace mappings.
            :param specVersion: UPnP specification version object.
            :param params: Dictionary of parsed parameters.

            :returns: A populated :class:`EmbeddedDeviceDesc` instance.
        """
        ext_params = {
            "mac_addr": None,
            "generation":  None,
            "codename":  None,
            "color": None,
            "software_version": None,
            "multi_room": None
        }

        params.update(ext_params)
        
        all_namespaces = {}
        all_namespaces.update(namespaces)
        all_namespaces.update(BOSE_XML_NAMESPACES)

        for child_el in device_el.iterfind("./bose:*", namespaces=BOSE_XML_NAMESPACES):            
            full_tag = child_el.tag
            tag = full_tag[BOSE_NAMESPACE_PREFIX_END:]
            txtval = child_el.text

            if tag == "X_MAC":
                params['mac_addr'] = txtval if txtval is not None else ""
            elif tag == "X_ecoSystem":
                params['generation'] = txtval if txtval is not None else ""
            elif tag == "X_productType":
                params['codename'] = txtval if txtval is not None else ""
            elif tag == "X_productColor":
                params['color'] = txtval if txtval is not None else ""
            elif tag == "X_softwareVersion":
                params['software_version'] = txtval if txtval is not None else ""
            elif tag == "X_multiroomVersions":
                params['multi_room'] = BoseDeviceDetailMapper.process_device_multiroom_versions(child_el, all_namespaces)

        try:
            device = BoseEmbeddedDeviceDetail(specVersion=specVersion, locationURL=None, **params)
        except Exception as err:
            err_msg = f"Error creating Bose embedded device description: {err}"
            raise RuntimeError(err_msg) from err

        return device

    @classmethod
    def process_device_multiroom_versions(cls, multiroom_el: Element, namespaces: Dict[str, str] ) -> BoseMultiRoomVersions:
        """
            Processes the Bose multi-room version section of a device description.

            :param multiroom_el: Element containing multi-room version data.
            :param namespaces: XML namespace mappings.

            :returns: A :class:`BoseMultiRoomVersions` instance.
        """

        bmrv = None

        audio_control_ver = None
        audio_payload_ver = None
        clock_sync_ver = None
        nowplaying_ver = None
        playback_request_ver = None
        zonecontrol_ver = None
        
        # Bose BUG: There is a bug in the Bose specific device description content.  The base elements specific to bose are
        # in a 'bose' namespace, but the child elements are in the default namespace.  Not the 'bose' namespace.

        next_ver_el = multiroom_el.find("./AudioControl_Protocol_Version", namespaces=namespaces)
        if next_ver_el is not None:
            audio_control_ver = BoseDeviceDetailMapper.process_bose_feature_version(next_ver_el, namespaces=namespaces)
        
        next_ver_el = multiroom_el.find("./ClockSync_Protocol_Version", namespaces=namespaces)
        if next_ver_el is not None:
            clock_sync_ver = BoseDeviceDetailMapper.process_bose_feature_version(next_ver_el, namespaces=namespaces)
        
        next_ver_el = multiroom_el.find("./Audio_Payload_Version", namespaces=namespaces)
        if next_ver_el is not None:
            audio_payload_ver = BoseDeviceDetailMapper.process_bose_feature_version(next_ver_el, namespaces=namespaces)

        next_ver_el = multiroom_el.find("./NowPlaying_Version", namespaces=namespaces)
        if next_ver_el is not None:
            nowplaying_ver = BoseDeviceDetailMapper.process_bose_feature_version(next_ver_el, namespaces=namespaces)
        
        next_ver_el = multiroom_el.find("./bose:PlaybackRequest_Version", namespaces=namespaces)
        if next_ver_el is not None:
            playback_request_ver = BoseDeviceDetailMapper.process_bose_feature_version(next_ver_el, namespaces=namespaces)
        
        next_ver_el = multiroom_el.find("./ZoneControl_Version", namespaces=namespaces)
        if next_ver_el is not None:
            zonecontrol_ver = BoseDeviceDetailMapper.process_bose_feature_version(next_ver_el, namespaces=namespaces)
        

        bmrv = BoseMultiRoomVersions(audio_control=audio_control_ver, audio_payload=audio_payload_ver, clock_sync=clock_sync_ver,
                                     now_playing=nowplaying_ver, playback_request=playback_request_ver, zone_control=zonecontrol_ver)

        return bmrv
    
    @classmethod
    def process_bose_feature_version(cls, version_el: Element, namespaces: Dict[str, str] ) -> BoseFeatureVersion:
        """
            Processes a Bose feature version element.

            :param version_el: XML element describing the version.
            :param namespaces: XML namespace mappings.

            :returns: A :class:`BoseFeatureVersion` instance.
        """

        major = None
        minor = None

        next_el = version_el.find("./major_version", namespaces=namespaces)
        if next_el is not None and next_el.text is not None:
            try:
                major = int(next_el.text.strip())
            except ValueError:
                major = None
        
        next_el = version_el.find("./minor_version", namespaces=namespaces)
        if next_el is not None and next_el.text is not None:
            try:
                minor = int(next_el.text.strip())
            except ValueError:
                minor = None
        
        verobj = BoseFeatureVersion(major, minor)

        return verobj
