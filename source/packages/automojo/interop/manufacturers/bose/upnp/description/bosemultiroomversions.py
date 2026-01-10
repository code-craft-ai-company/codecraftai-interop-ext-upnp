"""
    .. module:: bosemultiroomversions
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the BoseMultiRoomVersions class which describes the various feature versions
        associated with a bose player.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Optional

from automojo.interop.manufacturers.bose.upnp.description.bosefeatureversion import (
    BoseFeatureVersion,
)


class BoseMultiRoomVersions:
    """
        Collection of multi-room protocol versions for a Bose device.
    """

    def __init__(
        self,
        audio_control: Optional[BoseFeatureVersion],
        audio_payload: Optional[BoseFeatureVersion],
        clock_sync: Optional[BoseFeatureVersion],
        now_playing: Optional[BoseFeatureVersion],
        playback_request: Optional[BoseFeatureVersion],
        zone_control: Optional[BoseFeatureVersion],
    ):
        """
            Stores a collection of Bose feature versions for multi-room support.

            :param audio_control: Audio control protocol version or None if not available.
            :param audio_payload: Audio payload protocol version or None if not available.
            :param clock_sync: Clock synchronization protocol version or None if not available.
            :param now_playing: Now playing protocol version or None if not available.
            :param playback_request: Playback request protocol version or None if not available.
            :param zone_control: Zone control protocol version or None if not available.

            :returns: None
        """

        self._audio_control = audio_control
        self._audio_payload = audio_payload
        self._clock_sync = clock_sync
        self._now_playing = now_playing
        self._playback_request = playback_request
        self._zone_control = zone_control
        return

    @property
    def audio_control(self) -> Optional[BoseFeatureVersion]:
        """
            Returns the audio control protocol version.

            :returns: The audio control :class:`BoseFeatureVersion` or None if not available.
        """
        return self._audio_control

    @property
    def audio_payload(self) -> Optional[BoseFeatureVersion]:
        """
            Returns the audio payload protocol version.

            :returns: The audio payload :class:`BoseFeatureVersion` or None if not available.
        """
        return self._audio_payload

    @property
    def clock_sync(self) -> Optional[BoseFeatureVersion]:
        """
            Returns the clock synchronization protocol version.

            :returns: The clock synchronization :class:`BoseFeatureVersion` or None if not available.
        """
        return self._clock_sync

    @property
    def now_playing(self) -> Optional[BoseFeatureVersion]:
        """
            Returns the now playing protocol version.

            :returns: The now playing :class:`BoseFeatureVersion` or None if not available.
        """
        return self._now_playing

    @property
    def playback_request(self) -> Optional[BoseFeatureVersion]:
        """
            Returns the playback request protocol version.

            :returns: The playback request :class:`BoseFeatureVersion` or None if not available.
        """
        return self._playback_request

    @property
    def zone_control(self) -> Optional[BoseFeatureVersion]:
        """
            Returns the zone control protocol version.

            :returns: The zone control :class:`BoseFeatureVersion` or None if not available.
        """
        return self._zone_control
