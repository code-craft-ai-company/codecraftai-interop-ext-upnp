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

from automojo.interop.manufacturers.bose.upnp.description.bosefeatureversion import (
    BoseFeatureVersion,
)


class BoseMultiRoomVersions:
    """
        Collection of multi-room protocol versions for a Bose device.
    """

    def __init__(
        self,
        audio_control: BoseFeatureVersion,
        audio_payload: BoseFeatureVersion,
        clock_sync: BoseFeatureVersion,
        now_playing: BoseFeatureVersion,
        playback_request: BoseFeatureVersion,
        zone_control: BoseFeatureVersion,
    ):
        """
            Stores a collection of Bose feature versions for multi-room support.

            :param audio_control: Audio control protocol version.
            :param audio_payload: Audio payload protocol version.
            :param clock_sync: Clock synchronization protocol version.
            :param now_playing: Now playing protocol version.
            :param playback_request: Playback request protocol version.
            :param zone_control: Zone control protocol version.

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
    def audio_control(self) -> BoseFeatureVersion:
        """
            Returns the audio control protocol version.

            :returns: The audio control :class:`BoseFeatureVersion`.
        """
        return self._audio_control

    @property
    def audio_payload(self) -> BoseFeatureVersion:
        """
            Returns the audio payload protocol version.

            :returns: The audio payload :class:`BoseFeatureVersion`.
        """
        return self._audio_payload

    @property
    def clock_sync(self) -> BoseFeatureVersion:
        """
            Returns the clock synchronization protocol version.

            :returns: The clock synchronization :class:`BoseFeatureVersion`.
        """
        return self._clock_sync

    @property
    def now_playing(self) -> BoseFeatureVersion:
        """
            Returns the now playing protocol version.

            :returns: The now playing :class:`BoseFeatureVersion`.
        """
        return self._now_playing

    @property
    def playback_request(self) -> BoseFeatureVersion:
        """
            Returns the playback request protocol version.

            :returns: The playback request :class:`BoseFeatureVersion`.
        """
        return self._playback_request

    @property
    def zone_control(self) -> BoseFeatureVersion:
        """
            Returns the zone control protocol version.

            :returns: The zone control :class:`BoseFeatureVersion`.
        """
        return self._zone_control
