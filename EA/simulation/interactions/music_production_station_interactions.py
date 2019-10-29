from distributor.shared_messages import IconInfoDatafrom element_utils import build_critical_section_with_finallyfrom event_testing.tests import TunableTestSetfrom interactions.aop import AffordanceObjectPairfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.utils.tunable_icon import TunableIconfrom objects.components.stored_audio_component import ChannelFlagsfrom objects.components.types import STORED_AUDIO_COMPONENTfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableResourceKey, Tunable, TunableMapping, TunableEnumEntry, TunableTuple, OptionalTunable, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom snippets import define_snippet, MUSIC_TRACK_DATAimport sims4.loglogger = sims4.log.Logger('MusicProductionStationInteraction', default_owner='skorman')
class MusicTrackData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'looping_audio': TunableResourceKey(description='\n            The looping propx file of the music track.\n            ', resource_types=(Types.PROPX,)), 'fixed_length_audio': TunableResourceKey(description='\n            The fixed-length propx file of the music track.\n            ', resource_types=(Types.PROPX,))}
(TunableMusicTrackDataReference, TunableMusicTrackDataSnippet) = define_snippet(MUSIC_TRACK_DATA, MusicTrackData.TunableFactory())
class UseMusicProductionStationSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'music_track_data_snippet': TunableMusicTrackDataSnippet(description='\n            The reference to looping and fixed-length .propx files for the associated\n            music track.\n            '), 'channels': TunableMapping(description='\n            A map of channel enums and their associated data. \n            ', key_type=TunableEnumEntry(description='\n                The enum for a channel.\n                ', tunable_type=ChannelFlags, default=ChannelFlags.CHANNEL1), value_type=TunableTuple(description='\n                Channel specific data.\n                ', channel_name=TunableLocalizedString(description='\n                    The name to display for this channel. \n                    '), channel_tests=TunableTestSet(description="\n                   The tests to display this channel's remix mixer\n                   "))), 'turn_on_channel_display_name': TunableLocalizedStringFactory(description='\n            The name to display for remix mixers that turn on a channel.\n            '), 'turn_on_channel_icon': TunableIcon(description='\n            The icon to display in the pie menu for remix mixers that turn on a channel. \n            ', tuning_group=GroupNames.UI), 'turn_off_channel_display_name': TunableLocalizedStringFactory(description='\n            The name to display for remix mixers that turn off a channel. \n            '), 'turn_off_channel_icon': TunableIcon(description='\n            The icon to display in the pie menu for remix mixers that turn off a channel. \n            ', tuning_group=GroupNames.UI), 'audio_start_event': Tunable(description='\n            The script event to listen for from animation so we know when to\n            start the music.\n            ', tunable_type=int, default=520), 'audio_stop_event': Tunable(description='\n            The script event to listen for from animation so we know when to\n            stop the music.\n            ', tunable_type=int, default=521)}

    def __init__(self, aop, context, *args, **kwargs):
        super().__init__(aop, context, *args, exit_functions=(), force_inertial=False, additional_post_run_autonomy_commodities=None, **kwargs)
        self._sound = None
        self._stored_audio_component = None

    def build_basic_content(self, sequence=(), **kwargs):
        self.store_event_handler(self._play_music_track, self.audio_start_event)
        self.store_event_handler(self._stop_music_track, self.audio_stop_event)
        sequence = super().build_basic_content(sequence, **kwargs)
        return build_critical_section_with_finally(sequence, self._stop_music_track)

    def _play_music_track(self, event_data, *args, **kwargs):
        self._stored_audio_component = self.target.get_component(STORED_AUDIO_COMPONENT)
        if self._stored_audio_component is None:
            logger.error('{} has no Stored Audio Component, which UseMusicProductionStationSuperInteraction requires for proper use.', self.target)
            return
        if self._sound is None:
            self._stored_audio_component.store_track(music_track_snippet=self.music_track_data_snippet)
            self._sound = self._stored_audio_component.play_looping_music_track(self.target)

    def _stop_music_track(self, event_data, *args, **kwargs):
        if self._sound is not None:
            self._sound.stop()
            self._sound = None

    def _exited_pipeline(self, *args, **kwargs):
        if self._stored_audio_component is not None:
            self._stored_audio_component.clear()
            self._stored_audio_component = None
        super()._exited_pipeline(*args, **kwargs)

class RemixTrackMixerInteraction(MixerInteraction):
    INSTANCE_TUNABLES = {'remix_track_event': OptionalTunable(description='\n            If enabled, The script event to listen for from animation so we\n            know when to mute/unmute a specific channel on the propx. \n            If disabled, the interaction will mute/unmute channels immediately\n            on run. \n            ', tunable=Tunable(description='\n                The remix track event to listen for.\n                ', tunable_type=int, default=522), enabled_name='Set_Script_Event', disabled_name='Run_Content_Immediately')}

    @classmethod
    def potential_interactions(cls, target, sa, si, **kwargs):
        if not target.has_component(STORED_AUDIO_COMPONENT):
            return
        resolver = si.get_resolver()
        for (channel, channel_data) in si.channels.items():
            if channel_data.channel_tests.run_tests(resolver) and channel is not ChannelFlags.CHANNEL1:
                stored_audio_component = target.get_component(STORED_AUDIO_COMPONENT)
                if not stored_audio_component.get_channel_value(channel):
                    display_name = si.turn_on_channel_display_name(channel_data.channel_name)
                    yield AffordanceObjectPair(cls, target, sa, si, display_name=display_name, channel_name=channel_data.channel_name, icon=si.turn_on_channel_icon, channel=channel, channel_value=1)
                else:
                    display_name = si.turn_off_channel_display_name(channel_data.channel_name)
                    yield AffordanceObjectPair(cls, target, sa, si, display_name=display_name, channel_name=channel_data.channel_name, icon=si.turn_off_channel_icon, channel=channel, channel_value=0)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, display_name=None, **interaction_parameters):
        if inst.display_name_in_queue is not None:
            display_name = inst.display_name_in_queue(inst._kwargs['channel_name'])
        return display_name

    @flexmethod
    def get_pie_menu_icon_info(cls, inst, target=DEFAULT, context=DEFAULT, icon=None, **interaction_parameters):
        return IconInfoData(icon)

    def __init__(self, *args, channel=None, channel_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = channel
        self._channel_value = channel_value
        self._stored_audio_component = None

    def build_basic_content(self, sequence=(), **kwargs):
        sequence = super().build_basic_content(sequence, **kwargs)
        if self.remix_track_event is not None:
            self.store_event_handler(self._play_audio, self.remix_track_event)
        else:
            sequence = (self._play_audio, sequence)
        return sequence

    def _play_audio(self, event_data, *args, **kwargs):
        self._stored_audio_component = self.target.get_component(STORED_AUDIO_COMPONENT)
        self._stored_audio_component.update_channel_value(self._channel, self._channel_value)
        self._stored_audio_component.apply_audio_effect(self.target)
