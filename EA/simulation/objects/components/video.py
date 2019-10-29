from protocolbuffers import DistributorOps_pb2 as protocols, ResourceKey_pb2from animation.awareness.awareness_enums import AwarenessChannelfrom animation.awareness.awareness_tuning import AwarenessSourceRequestfrom clock import ClockSpeedModefrom objects.components import types, componentmethodfrom objects.components.types import NativeComponentfrom sims4.tuning.tunable import HasTunableFactory, TunableEnumEntry, OptionalTunable, TunableResourceKeyimport enumimport sims4.hash_utilRESOURCE_TYPE_VP6 = 929579223RESOURCE_GROUP_PLAYLIST = 12535179
class VideoDisplayType(enum.Int):
    NORMAL = ...
    LIGHT_OVERLAY = ...

class VideoPlaylist:

    def __init__(self, version_id, clip_names, loop_last, display_type, mute_speed, distortion_speed, speed_audio_clip_replacement, append_clip):
        self.version_id = version_id
        self.clip_keys = VideoPlaylist._encode_clip_names(clip_names)
        self.loop_last = loop_last
        self.display_type = display_type
        self.mute_speed = mute_speed
        self.distortion_speed = distortion_speed
        self.speed_audio_clip_replacement = speed_audio_clip_replacement
        self.append_clip = append_clip

    def __str__(self):
        return 'version({}): {} clips, loop={}, display={}, mute speed={}, distortion speed = {}'.format(self.version_id, len(self.clip_keys), self.loop_last, self.display_type, self.mute_speed, self.distortion_speed, self.speed_audio_clip_replacement)

    def append_clips(self, clip_names, loop_last):
        if clip_names:
            self.clip_keys += VideoPlaylist._encode_clip_names(clip_names)
            self.loop_last = loop_last

    def get_protocol_msg(self):
        msg = protocols.VideoSetPlaylist()
        msg.version_id = self.version_id
        msg.clip_keys.extend(self.clip_keys)
        msg.final_loop = self.loop_last
        msg.video_overlay = self.display_type == VideoDisplayType.LIGHT_OVERLAY
        msg.mute_speed = self.mute_speed
        msg.distortion_speed = self.distortion_speed
        if self.speed_audio_clip_replacement is not None:
            msg.speed_audio_clip_replacement = self.speed_audio_clip_replacement.instance
        msg.append_clip = self.append_clip
        return msg

    @staticmethod
    def _encode_clip_names(clip_names):
        return [VideoPlaylist._encode_clip_name(clip_name) for clip_name in clip_names]

    @staticmethod
    def _encode_clip_name(clip_name):
        key = ResourceKey_pb2.ResourceKey()
        if type(clip_name) is sims4.resources.Key:
            key.type = clip_name.type
            key.group = clip_name.group
            key.instance = clip_name.instance
            if key.type == sims4.resources.Types.PLAYLIST:
                key.group = RESOURCE_GROUP_PLAYLIST
        else:
            split_index = clip_name.find('.')
            key.type = RESOURCE_TYPE_VP6
            key.group = 0
            if split_index < 0:
                key.instance = sims4.hash_util.hash64(clip_name)
            else:
                key.instance = sims4.hash_util.hash64(clip_name[:split_index])
                ext = clip_name[split_index + 1:]
                if ext == 'playlist':
                    key.group = RESOURCE_GROUP_PLAYLIST
                elif ext != 'vp6':
                    raise ValueError('Unknown clip name extension: ' + ext)
        return key

class VideoComponent(HasTunableFactory, NativeComponent, component_name=types.VIDEO_COMPONENT, key=2982943478):
    FACTORY_TUNABLES = {'video_display_type': TunableEnumEntry(description="\n            How videos should be played. This option should be kept in line\n            with what the model expects. If you're unsure what that is, please\n            consult the modeler. Setting this to the wrong value will result in\n            broken behavior such as videos not playing, broken shaders, etc.\n            \n            NORMAL: Videos appear as if being played from a screen on the\n            object, e.g. TVs, computer, tablets.\n            \n            LIGHT_OVERLAY: Videos appear as if they are being projected onto\n            the object by a video projector.\n            ", tunable_type=VideoDisplayType, default=VideoDisplayType.NORMAL), 'mute_speed': TunableEnumEntry(description='\n            Game Speed at or above the mute speed will have the audio muted\n            when that speed is selected. \n            Pause(0) is always muted.\n            ', tunable_type=ClockSpeedMode, default=ClockSpeedMode.PAUSED), 'speed_audio_clip_replacement': OptionalTunable(description='\n            If enabled, when the speed changes to the value tuned on MUTE SPEED\n            the audio of the video will be muted but additionally this audio\n            clip will be played.\n            ', tunable=TunableResourceKey(description='\n                Audio clip name to play when mute speed crosses its threshold\n                ', default=None, resource_types=(sims4.resources.Types.PROPX,)), enabled_name='play_clip_on_speed_change', disabled_name='no_replacement'), 'distortion_speed': TunableEnumEntry(description='\n            Game Speed at or above the distortion speed will have a distortion\n            effect applied to the video when that speed is selected. \n            Pause(0) will never distort.\n            ', tunable_type=ClockSpeedMode, default=ClockSpeedMode.PAUSED)}

    def __init__(self, *args, video_display_type=VideoDisplayType.NORMAL, mute_speed=ClockSpeedMode.PAUSED, distortion_speed=ClockSpeedMode.PAUSED, speed_audio_clip_replacement=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_display_type = video_display_type
        self.mute_speed = mute_speed
        self.distortion_speed = distortion_speed
        self.speed_audio_clip_replacement = speed_audio_clip_replacement
        self._awareness_request = None

    def __repr__(self):
        if self.owner.video_playlist is None:
            return 'No clips queued'
        else:
            return repr(self.owner.video_playlist)

    @property
    def video_playlist_looping(self):
        return self.owner.video_playlist

    @video_playlist_looping.setter
    def video_playlist_looping(self, value):
        if value is None:
            self.set_video_clips()
        else:
            self.set_video_clips([value], loop_last=True)

    @property
    def video_playlist(self):
        return self.owner.video_playlist

    @video_playlist.setter
    def video_playlist(self, value):
        if value is None:
            self.set_video_clips()
        else:
            self.set_video_clips(value.clip_list, loop_last=value.loop_last, append_clip=value.append_clip)

    def on_add(self):
        self._awareness_request = AwarenessSourceRequest(self.owner, awareness_sources={AwarenessChannel.AUDIO_VOLUME: 1})
        self._awareness_request.start()

    def on_remove(self):
        if self._awareness_request is not None:
            self._awareness_request.stop()
            self._awareness_request = None

    @componentmethod
    def set_video_clips(self, clip_names=[], loop_last=False, append_clip=False):
        if self.owner.video_playlist:
            version_id = self._next_version(self.owner.video_playlist.version_id)
        else:
            version_id = 0
        self.owner.video_playlist = VideoPlaylist(version_id, clip_names, loop_last, self.video_display_type, self.mute_speed, self.distortion_speed, self.speed_audio_clip_replacement, append_clip)

    @componentmethod
    def add_video_clips(self, clip_names, loop_last=False):
        if not clip_names:
            return
        if self.owner.video_playlist is None:
            self.set_video_clips(clip_names, loop_last)
        else:
            self.owner.video_playlist.append_clips(clip_names, loop_last)
            self.owner._resend_video_playlist()

    @staticmethod
    def _next_version(version_id):
        if version_id >= 65535:
            return 0
        else:
            return version_id + 1
