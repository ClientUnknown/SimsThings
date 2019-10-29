from audio.audio_effect_data import AudioEffectDatafrom audio.primitive import TunablePlayAudio, play_tunable_audiofrom element_utils import CleanupType, build_element, build_critical_section_with_finallyfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects.components.state_change import StateChangefrom objects.components.types import STORED_AUDIO_COMPONENTfrom sims4.tuning.tunable import TunableFactory, TunableEnumFlags, Tunable, HasTunableFactory, AutoFactoryInit, TunableEnumEntry, TunableTuple, OptionalTunablefrom sims4.tuning.tunable_hash import TunableStringHash64import sims4.loglogger = sims4.log.Logger('Audio')
class TunableAudioModificationElement(TunableFactory):

    @staticmethod
    def factory(interaction, subject, tag_name, effect_name, sequence=(), **kwargs):
        target = interaction.get_participant(subject)
        audio_effect_data = AudioEffectData(effect_name)
        if target is not None:

            def start(*_, **__):
                target.append_audio_effect(tag_name, audio_effect_data)

            def stop(*_, **__):
                target.remove_audio_effect(tag_name)

        return build_critical_section_with_finally(start, sequence, stop)

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(subject=TunableEnumFlags(ParticipantType, ParticipantType.Actor, description='Object the audio effect will be placed on.'), tag_name=TunableStringHash64(description='\n                             Name of the animation tag this effect will trigger on.\n                             ', default='x'), effect_name=TunableStringHash64(description='\n                             Name of the audio modification that will be applied\n                             ', default=''), **kwargs)

class ApplyAudioEffect(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'effect_name': TunableStringHash64(description='\n            Name of the audio modification that will be applied.\n            ', default='', allow_empty=False), 'tag_name': TunableStringHash64(description='\n            The tag name is the key that will be used for the effects. Any\n            effect of the same key will remove a previous effect.\n            ', default='x', allow_empty=False)}

    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self._audio_effect_data = AudioEffectData(self.effect_name)
        if target.inventoryitem_component is not None:
            forward_to_owner_list = target.inventoryitem_component.forward_client_state_change_to_inventory_owner
            if StateChange.AUDIO_EFFECT_STATE in forward_to_owner_list:
                self.target = target.inventoryitem_component.inventory_owner
        self._running = False

    def _run(self):
        self.start()
        return True

    @property
    def running(self):
        return self._running

    @property
    def is_attached(self):
        return self._running

    def start(self):
        if self.target is not None:
            self.target.append_audio_effect(self.tag_name, self._audio_effect_data)
            self._running = True

    def stop(self, *_, **__):
        if self.target is not None:
            self.target.remove_audio_effect(self.tag_name)
            self._running = False

class TunableAudioSting(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': 'Play an Audio Sting at the beginning/end of an interaction or on XEvent.', 'audio_sting': TunablePlayAudio(description='\n            The audio sting that gets played on the subject.\n            '), 'stop_audio_on_end': Tunable(description="\n            If checked AND the timing is not set to END, the audio sting will\n            turn off when the interaction finishes. Otherwise, the audio will\n            play normally and finish when it's done.\n            ", tunable_type=bool, default=False), 'subject': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='The participant who the audio sting will be played on.')}

    def _build_outer_elements(self, sequence):

        def stop_audio(e):
            if hasattr(self, '_sound'):
                self._sound.stop()

        if self.stop_audio_on_end and self.timing is not self.AT_END:
            return build_element([sequence, stop_audio], critical=CleanupType.OnCancelOrException)
        return sequence

    def _do_behavior(self):
        subject = self.interaction.get_participant(self.subject)
        if subject is not None or not self.stop_audio_on_end:
            self._sound = play_tunable_audio(self.audio_sting, subject)
        else:
            logger.error('Expecting to start and stop a TunableAudioSting during {} on a subject that is None.'.format(self.interaction), owner='rmccord')

class TunablePlayStoredAudioFromSource(XevtTriggeredElement, HasTunableFactory):
    FACTORY_TUNABLES = {'target_object': TunableEnumEntry(description='\n            The participant who the audio sting will be played on.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'stored_audio_source': TunableEnumEntry(description='\n            The participant who sources the stored audio component.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'stop_audio_on_end': Tunable(description="\n            If checked AND the timing is not set to END, the audio sting will\n            turn off when the interaction finishes. Otherwise, the audio will\n            play normally and finish when it's done.\n            ", tunable_type=bool, default=False), 'play_from_music_track_data': OptionalTunable(description="\n            If enabled, then instead of playing from a single sound on the \n            Stored Audio Component, sound will be played from the\n            Stored Audio Component's music track data.\n            ", tunable=Tunable(description='\n                If set to True, the audio from the fixed length audio field will play.\n                If set to False, the audio from the looping audio field will play.\n                ', tunable_type=bool, default=True), disabled_name='play_from_sound', enabled_name='play_from_music_track_snippet')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sound = None

    def _build_outer_elements(self, sequence):

        def stop_audio(e):
            if self._sound is not None:
                self._sound.stop()

        if self.stop_audio_on_end and self.timing is not self.AT_END:
            return build_element([sequence, stop_audio], critical=CleanupType.OnCancelOrException)
        return sequence

    def _do_behavior(self):
        stored_audio_source = self.interaction.get_participant(self.stored_audio_source)
        if stored_audio_source is None:
            logger.error("Interaction:'{}' has a Play Stored Audio from Source Basic Extra where the stored audio source is None.".format(self.interaction), owner='shipark')
            return
        stored_audio_source_component = stored_audio_source.get_component(STORED_AUDIO_COMPONENT)
        if stored_audio_source_component is None:
            logger.error("Interaction:'{}' has a Play Stored Audio from Source Basic Extra with a disabled Stored Audio Component on the stored audio source.".format(self.interaction.name), owner='shipark')
            return
        for target_object in self.interaction.get_participants(self.target_object):
            if target_object is None:
                logger.error("Interaction:'{}' has a Play Stored Audio from Source Basic extra where the target object in None.".format(self.interaction))
                return
            if self.play_from_music_track_data is not None:
                if self.play_from_music_track_data:
                    self._sound = stored_audio_source_component.play_fixed_length_music_track(target_object)
                    return
                self._sound = stored_audio_source_component.play_looping_music_track(target_object)
                return
            self._sound = stored_audio_source_component.play_sound(target_object)
