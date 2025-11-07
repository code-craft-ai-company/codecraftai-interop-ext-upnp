

"""
    .. module:: upnpdevicehint
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: upnpdevicehint module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from automojo.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence

class UpnpDeviceHint:
    """
        A class to represent a UPnP device hint.
    """

    def __init__(self, hint: str):
        """
            Initialize the UPnP device hint.

            :param hint: The configured hint string.
        """
        self._hint = hint
        return
    
    def get_hint(self) -> str:
        """
            Get the hint that can be used to identify a Upnp device.

            :returns: The hint for the UPnP device.
        """
        return self._hint

    def matches(self, exhibit: DeviceEvidence) -> bool:
        """
            Check if the hint provided by the user configuration matches the device exhibit.

            :param exhibit: The UPnP device exhibit to check against.

            :returns: ``True`` if the hint matches the device exhibit, ``False`` otherwise.
        """
        rtnval = False

        if self._hint in exhibit.usn:
            rtnval = True

        return rtnval
