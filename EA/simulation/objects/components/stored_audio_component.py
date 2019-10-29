from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom audio.audio_effect_data import AudioEffectDatafrom audio.primitive import PlaySoundfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects.components import Component, typesfrom objects.components.types import STORED_AUDIO_COMPONENTfrom sims4.resources import get_protobuff_for_key, get_key_from_protobufffrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, TunableTuple, OptionalTunablefrom sims4.tuning.tunable_hash import TunableStringHash64import enumimport servicesimport sims4logger = sims4.log.Logger('StoredAudioComponent', default_owner='skorman')
class ChannelFlags(enum.IntFlags):
    CHANNEL1 = 1
    CHANNEL2 = 2
    CHANNEL3 = 4
    CHANNEL4 = 8
    CHANNEL5 = 16
    CHANNEL6 = 32
    CHANNEL7 = 64
    CHANNEL8 = 128

class StoredAudioComponent(Component, AutoFactoryInit, HasTunableFactory, component_name=types.STORED_AUDIO_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.StoredAudioComponent):
    FACTORY_TUNABLES = {'audio_effect': OptionalTunable(description='\n            If enabled, the audio effect is applied to the stored sound. If disabled,\n            no audio effect will occur.\n            ', tunable=TunableTuple(tag_name=TunableStringHash64(description="\n                    The tag used as a key for the music track's audio effect data.\n                    Any effect of the same key will be removed and replaced.\n                    ", default=''), effect_id=TunableStringHash64(description="\n                    ID that corresponds to the music track's audio effect.\n                    ", default='')))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sound = None
        self._music_track_snippet = None
        if self.audio_effect is not None:
            self._channel_values_int = 0
        else:
            self._channel_values_int = None

    @property
    def channel_values(self):
        if self._channel_values_int is None:
            logger.error('Attempting to retrieve Audio Effect off of the Stored Audio Component of {} when None is tuned'.format(self.owner))
            return
        return self._channel_values_int

    @property
    def sound(self):
        return self._sound

    @property
    def music_track_snippet(self):
        return self._music_track_snippet

    def get_channel_value(self, channel):
        if self._channel_values_int is None:
            logger.error('Attempting to retrieve Audio Effect off of the Stored Audio Component of {} when None is tuned'.format(self.owner))
            return
        return self._channel_values_int & channel

    def store_track(self, sound=None, music_track_snippet=None):
        if sound is not None:
            self._sound = sound
        if music_track_snippet is not None:
            self._music_track_snippet = music_track_snippet
        self._channel_values_int |= ChannelFlags.CHANNEL1

    def set_channel_values(self, value):
        self._channel_values_int = value

    def update_channel_value(self, channel, value):
        if value:
            self._channel_values_int |= channel
        else:
            self._channel_values_int &= ~channel

    def clear(self):
        self._channel_values_int = 0
        self._sound = None
        self._music_track_snippet = None

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.StoredAudioComponent
        stored_audio_component_data = persistable_data.Extensions[protocols.PersistableStoredAudioComponent.persistable_data]
        if self._sound is not None:
            stored_audio_component_data.sound_resource.sound = get_protobuff_for_key(self._sound)
        if self._music_track_snippet is not None:
            stored_audio_component_data.sound_resource.music_track_snippet = get_protobuff_for_key(self._music_track_snippet.resource_key)
        channel_values_int = self._channel_values_int
        if channel_values_int is not None:
            stored_audio_component_data.channel_values_int = channel_values_int
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        stored_audio_component_data = persistable_data.Extensions[protocols.PersistableStoredAudioComponent.persistable_data]
        if stored_audio_component_data.HasField('sound_resource'):
            self._sound = get_key_from_protobuff(stored_audio_component_data.sound_resource.sound)
            music_track_resource_key = get_key_from_protobuff(stored_audio_component_data.sound_resource.music_track_snippet)
            if music_track_resource_key is not None:
                snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
                self._music_track_snippet = snippet_manager.get(music_track_resource_key)
        if stored_audio_component_data.HasField('channel_values_int'):
            self._channel_values_int = stored_audio_component_data.channel_values_int

    def play_sound(self, target_object):
        if self._sound is None:
            return
        sound = PlaySound(target_object, self._sound.instance)
        sound.start()
        self.apply_audio_effect(target_object)
        return sound

    def play_looping_music_track(self, target_object):
        if self._music_track_snippet is None:
            return
        sound = PlaySound(target_object, self._music_track_snippet.looping_audio.instance)
        sound.start()
        self.apply_audio_effect(target_object)
        return sound

    def play_fixed_length_music_track(self, target_object):
        if self._music_track_snippet is None:
            return
        sound = PlaySound(target_object, self._music_track_snippet.fixed_length_audio.instance)
        sound.start()
        self.apply_audio_effect(target_object)
        return sound

    def apply_audio_effect(self, target_object):
        audio_effect = self.audio_effect
        if audio_effect is not None:
            audio_effect_data = AudioEffectData(audio_effect.effect_id, self._channel_values_int)
            target_object.append_audio_effect(audio_effect.tag_name, audio_effect_data)

class TransferStoredAudioComponent(XevtTriggeredElement, HasTunableFactory):
    FACTORY_TUNABLES = {'source_participant': TunableEnumEntry(description='\n            The participant of the interaction whose stored audio component\n            will be copied and moved to the target participant. \n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'target_participant': TunableEnumEntry(description='\n            The participant of the interaction who will populate its stored \n            audio component with data from the source participant. \n            ', tunable_type=ParticipantType, default=ParticipantType.CreatedObject)}

    def _do_behavior(self):
        source = self.interaction.get_participant(self.source_participant)
        if source is None or not source.has_component(STORED_AUDIO_COMPONENT):
            logger.error('TransferStoredAudioComponent attempting to copy the Stored Audio Component on {}, but the component is not enabled.', source)
            return
        source_component = source.get_component(STORED_AUDIO_COMPONENT)
        for target in self.interaction.get_participants(self.target_participant):
            if target is None or not target.has_component(STORED_AUDIO_COMPONENT):
                logger.error('TransferStoredAudioComponent attempting to transfer Stored Audio Component to {}, but the component is not enabled.', target)
                return
            target_component = target.get_component(STORED_AUDIO_COMPONENT)
            if source_component.sound is not None:
                target_component.store_track(sound=source_component.sound)
            if source_component.music_track_snippet is not None:
                target_component.store_track(music_track_snippet=source_component.music_track_snippet)
            if source_component.audio_effect is not None:
                target_component.set_channel_values(source_component.channel_values)
