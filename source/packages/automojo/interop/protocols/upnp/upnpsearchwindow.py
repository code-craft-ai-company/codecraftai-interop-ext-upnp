
"""
    .. module:: upnpsearchwindow
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: upnpsearchwindow module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Dict, List, TYPE_CHECKING


import threading
import time
import weakref

from datetime import datetime, timedelta

from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from automojo.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint


if TYPE_CHECKING:
    from automojo.interop.protocols.upnp.upnppresence import UpnpPresence


class UpnpSearchWindowState:
    """
        Enumeration describing the lifecycle of a UPNP search window.
    """
    INACTIVE = 0
    ACTIVE = 1
    COMPLETED = 2
    TIMEOUT = 3


class UpnpSearchWindow:
    """
        The UpnpSearchWindow class provides a synchronization and state managment device for synchronizing the state of SSDP search
        activities on the network.
    """

    def __init__(self, presence: "UpnpPresence", id: str, start: datetime, end: datetime, monitor_interval: float, limit_to: List[UpnpDeviceHint]=None):
        """
            :param presence: The owning :class:`UpnpPresence` instance.
            :param id: Identifier for this search window.
            :param start: Start time of the search window.
            :param end: End time of the search window.
            :param monitor_interval: Polling interval for window monitoring.
            :param limit_to: Optional list of device hints to limit the search.
        """

        self._presence_ref = weakref.ref(presence)
        self._id = id
        self._start = start
        self._end = end
        self._monitor_interval = monitor_interval
        self._limit_to = limit_to

        self._still_waiting_for = None
        if limit_to is not None:
            self._still_waiting_for = [hint for hint in limit_to]

        self._window_state = UpnpSearchWindowState.INACTIVE

        self._lock = threading.Lock()
        self._wait_gate = threading.Event()
        self._monitor_thread = None

        self._devices_found = {}
        self._matching_devices = {}
        
        return

    @property
    def devices_found(self) -> Dict[str, UpnpDeviceDetail]:
        """
            The dictionary of devices found during the search window.  The keys are the USN identifiers of the devices and the values
            are the :class:`UpnpDeviceDetail` objects that represent the devices.

            :returns: Copy of the devices found mapping.
        """
        rtnval = self._devices_found.copy()
        return rtnval

    @property
    def id(self) -> str:
        """
            The ID of the search window.  This is a unique identifier for the search window.

            :returns: Identifier string for this search window.
        """
        return self._id
    
    @property
    def matching_devices(self) -> Dict[str, UpnpDeviceDetail]:
        """
            The dictionary of devices that matched the search window.  The keys are the USN identifiers of the devices and the values
            are the :class:`UpnpDeviceDetail` objects that represent the devices.

            :returns: Mapping of device hints to matching device details.
        """
        rtnval = self._matching_devices.copy()
        return rtnval

    @property
    def presence(self) -> "UpnpPresence":
        """
            The :class:`UpnpPresence` object that is associated with this search window.

            :returns: The owning :class:`UpnpPresence` instance.
        """
        return self._presence_ref()


    def add_device(self, identifier: str, device_detail: UpnpDeviceDetail):
        """
            Add a device to the list of devices found during the search window.

            :param identifier: The USN identifier for the device being added.
            :param device_detail: The :class:`UpnpDeviceDetail` object describing the device.
        """

        self._lock.acquire()
        try:
            self._devices_found[identifier] = device_detail
        finally:
            self._lock.release()

        return


    def is_active(self) -> bool:
        """
            Check if the search window is active.  This method will return True if the search window is active, otherwise False.
        """

        rtnval = False

        self._lock.acquire()
        try:
            rtnval = self._window_state == UpnpSearchWindowState.ACTIVE
        finally:
            self._lock.release()

        return rtnval


    def start(self):
        """
            Begin monitoring for search results in a background thread.
        """
        self._lock.acquire()
        try:
            start_gate = threading.Event()
            start_gate.clear()

            self._monitor_thread = threading.Thread(target=self._monitor_thread_entry, name="am-msearch-window-mon", args=(start_gate,), daemon=True)
            self._monitor_thread.start()

            start_gate.wait()
        finally:
            self._lock.release()

        return


    def wait(self, timeout: float = None) -> bool:
        """
            Wait for the search window to close or for all the devices to be found that were presented in the 'limit_to' list.
            This method will block until the search window has closed or the timeout has been reached.

            :param timeout: The time in seconds to wait for the search window to close.  If None, then wait indefinitely.

            :returns: ``True`` if the window closed before timeout, otherwise ``False``.
        """

        try:
            self._lock.acquire()

            if self._window_state == UpnpSearchWindowState.INACTIVE:
                raise RuntimeError("The search window is not active.")

            if self._window_state == UpnpSearchWindowState.ACTIVE:
                try:
                    self._lock.release()
                
                    self._wait_gate.wait(timeout=timeout)
                finally:
                    self._lock.acquire()

        finally:
            self._lock.release()

        return


    def _monitor_thread_entry(self, sgate: threading.Event):
        """
            The monitor thread entry point.  This thread is responsible for monitoring the state of the search window and
            notifying the calling thread when the search window has closed.
        """

        self._window_state = UpnpSearchWindowState.ACTIVE
        self._wait_gate.clear()

        sgate.set()

        while self._window_state == UpnpSearchWindowState.ACTIVE:
            
            now = datetime.now()

            if now > self._end:
                self._window_state = UpnpSearchWindowState.TIMEOUT
                break

            try:
                self._lock.acquire()

                if self._still_waiting_for is not None:

                    checking_for = [hint for hint in self._still_waiting_for]
                    recheck_for = []
                    current_found = self._devices_found.copy()

                    try:
                        self._lock.release()

                        while len(checking_for) > 0:
                            nxt_hint = checking_for.pop()

                            hint_matched = False
                            for device in current_found.values():
                                if nxt_hint.matches(device):
                                    self._matching_devices[nxt_hint.get_hint()] = device
                                    hint_matched = True
                                    break
                            
                            if not hint_matched:
                                recheck_for.append(nxt_hint)

                    finally:
                        self._lock.acquire()

                    self._still_waiting_for = recheck_for

                    # If we had a wait list and we found all the devices, then we can break out of the thread loop
                    # and notify any waiting thread that the search is completed and the windows closed.
                    if len(self._still_waiting_for) == 0:
                        self._window_state = UpnpSearchWindowState.COMPLETED
                        break

            finally:
                self._lock.release()

            time.sleep(self._monitor_interval)


        # The search window has closed, so we need to notify any waiting threads
        self._wait_gate.set()

        presence = self._presence_ref()
        if presence is not None:
            presence.search_window_closed(self._id)

        return
