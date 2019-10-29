import randomfrom audio.primitive import PlaySoundfrom crafting.crafting_interactions import CraftingPhaseSuperInteractionMixin, CraftingPhaseStagingSuperInteractionfrom crafting.music import MusicStylefrom element_utils import build_critical_section_with_finallyfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypeSinglefrom interactions.aop import AffordanceObjectPairfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.interaction_finisher import FinishingTypefrom interactions.social.social_super_interaction import SocialSuperInteractionfrom interactions.utils.interaction_liabilities import CANCEL_INTERACTION_ON_EXIT_LIABILITY, CancelInteractionsOnExitLiabilityfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom sims4.tuning.tunable import Tunable, TunableList, TunableReference, TunableEnumEntry, OptionalTunablefrom sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom ui.ui_dialog_generic import UiDialogTextInputOkimport alarmsimport clockimport event_testing.resultsimport servicesimport simsimport sims4logger = sims4.log.Logger('MusicInteractions', default_owner='rmccord')
class PlayAudioMixin:
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'play_multiple_clips': Tunable(description='\n            If true, the Sim will continue playing until the interaction is\n            cancelled or exit conditions are met. \n            ', needs_tuning=False, tunable_type=bool, default=False), 'music_styles': TunableList(description='\n            List of music styles that are available for this interaction.\n            ', tunable=MusicStyle.TunableReference(description='\n                A music style available for this interaction.\n                ', pack_safe=True)), 'use_buffer': Tunable(description="\n            If true, this interaction will add the buffer tuned on the music\n            track to the length of the track.  This is tunable because some\n            interactions, like Practice, use shorter audio clips that don't\n            require the buffer.\n            ", needs_tuning=False, tunable_type=bool, default=True), 'instrument_participant': TunableEnumEntry(description='\n            The participant that the music will play on.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'audio_start_event': Tunable(description='\n            The script event to listen for from animation so we know when to\n            start the music and vocals.\n            ', tunable_type=int, default=100), 'audio_stop_event': Tunable(description='\n            The script event to listen for from animation so we know when to\n            stop the music and vocals.\n            ', tunable_type=int, default=101), 'mouthpiece_target': OptionalTunable(description='\n            The participant of mine that mouthpieces must target as their mouthpiece\n            target.  e.g. if they are targeting the actor sim of this interaction, \n            their mouthpiece target would be targetsim, my mouthpiece target \n            would be actor.  If all of us are targeting a certain object then\n            both would be object.\n            ', tunable=TunableEnumEntry(description='\n                The participant of mine that mouthpieces must target.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object))}

    def __init__(self, aop, context, track=None, pie_menu_category=None, unlockable_name=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        self._track = track
        self.pie_menu_category = pie_menu_category
        self._unlockable_name = unlockable_name
        self._sound_alarm = None
        self._sound = None
        self._vocals = {}

    def build_basic_content(self, sequence=(), **kwargs):
        self.store_event_handler(self._create_sound_alarm, self.audio_start_event)
        self.store_event_handler(self._cancel_sound_alarm, self.audio_stop_event)
        sequence = super().build_basic_content(sequence, **kwargs)
        return build_critical_section_with_finally(sequence, self._cancel_sound_alarm_no_data)

    def _get_mouthpiece_interaction(self, mouthpiece_object, sim):
        for interaction in sim.get_all_running_and_queued_interactions():
            if isinstance(interaction, PlayAudioMouthpieceSuperInteraction) and (interaction.is_finishing or interaction.is_mouthpiece_target(mouthpiece_object)):
                return interaction

    def _get_required_sims(self, *args, **kwargs):
        required_sims = super()._get_required_sims(*args, **kwargs)
        mouthpiece_target = None if self.mouthpiece_target is None else self.get_participant(self.mouthpiece_target)
        if mouthpiece_target is not None:
            for (musician, _) in self._musicians_and_vocals_gen():
                if self._get_mouthpiece_interaction(mouthpiece_target, musician) is not None:
                    required_sims.add(musician)
        return required_sims

    def _create_sound_alarm(self, event_data, *args, **kwargs):
        if event_data is not None and event_data.event_data['event_actor_id'] != self.sim.id:
            return
        if self._track is None:
            logger.error('Could not find a music track to play for {}', self, owner='rmccord')
            return
        track_length = self._get_track_length()
        if self._sound_alarm is None:
            self._sound_alarm = alarms.add_alarm(self, track_length, self._sound_alarm_callback)
        if self._sound is None and self._track.music_clip is not None:
            instrument = self._get_instrument()
            if instrument is not None:
                self._sound = PlaySound(instrument, self._track.music_clip.instance)
                self._sound.start()
            else:
                logger.error('Instrument is None for participant {} in {}', self.instrument_participant, self, owner='rmccord')
        mouthpiece_target = None if self.mouthpiece_target is None else self.get_participant(self.mouthpiece_target)
        for (musician, vocal_track) in self._musicians_and_vocals_gen():
            interaction = None
            if musician.is_sim and musician is not self.sim and mouthpiece_target is not None:
                interaction = self._get_mouthpiece_interaction(mouthpiece_target, musician)
                if interaction is None:
                    pass
                else:
                    interaction.set_mouthpiece_owner(self)
                    liability = self.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY)
                    if liability is None:
                        liability = CancelInteractionsOnExitLiability()
                        self.add_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY, liability)
                    liability.add_cancel_entry(musician, interaction)
                    vocal = PlaySound(musician, vocal_track.vocal_clip.instance, is_vox=True)
                    vocal.start()
                    self._vocals[musician] = (vocal, interaction)
            vocal = PlaySound(musician, vocal_track.vocal_clip.instance, is_vox=True)
            vocal.start()
            self._vocals[musician] = (vocal, interaction)

    def _sound_alarm_callback(self, handle):
        if self.play_multiple_clips:
            self._cancel_sound_alarm(None)
            styles = self._get_music_styles()
            self._track = PlayAudioMixin._get_next_track(styles, self.sim, self.get_resolver())
            self._create_sound_alarm(None)
        else:
            self.cancel(FinishingType.NATURAL, cancel_reason_msg='Sound alarm triggered and the song finished naturally.')

    def stop_mouthpiece(self, sim):
        if sim in self._vocals:
            (vocal, interaction) = self._vocals.pop(sim)
            vocal.stop()
            if interaction is not None:
                self.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY).remove_cancel_entry(sim, interaction)

    def _cancel_sound_alarm_no_data(self, *args, **kwargs):
        self._cancel_sound_alarm(None)

    def _cancel_sound_alarm(self, event_data, *args, **kwargs):
        if event_data is not None and event_data.event_data['event_actor_id'] != self.sim.id:
            return
        if self._sound_alarm is not None:
            alarms.cancel_alarm(self._sound_alarm)
            self._sound_alarm = None
        if self._sound is not None:
            self._sound.stop()
            self._sound = None
        liability = self.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY)
        for (vocal, interaction) in self._vocals.values():
            vocal.stop()
            if interaction is not None:
                interaction.set_mouthpiece_owner(None)
                liability.remove_cancel_entry(interaction.sim, interaction)
        self._vocals.clear()

    def _get_track_length(self):
        real_seconds = self._track.length
        if self.use_buffer:
            real_seconds += self._track.buffer
        interval = clock.interval_in_real_seconds(real_seconds)
        return interval

    def _get_instrument(self):
        return self.get_participant(self.instrument_participant)

    def _musicians_and_vocals_gen(self):
        resolver = self.get_resolver()
        for (participant_type, vocal_tracks) in self._track.vocals.items():
            for participant in resolver.get_participants(participant_type):
                participant = participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
                if not isinstance(participant, sims.sim_info.SimInfo) or participant is None:
                    logger.warn('Musician participant {} is None for {}', participant_type, self, owner='rmccord')
                else:
                    for track in vocal_tracks:
                        if track.tests.run_tests(resolver):
                            yield (participant, track)
                            break

    def _get_music_styles(self):
        return self.music_styles

    @staticmethod
    def _get_skill_level(skill_type, sim):
        skill = sim.get_statistic(skill_type, add=False)
        if skill is not None:
            return skill.get_user_value()
        elif skill_type.can_add(sim):
            return skill_type.get_user_value()
        return 0

    @staticmethod
    def _get_next_track(styles, sim, resolver):
        valid_tracks = []
        styles = set(styles)
        for (skill_type, level_to_tracks) in MusicStyle.tracks_by_skill.items():
            skill_level = PlayAudioMixin._get_skill_level(skill_type, sim)
            for track in level_to_tracks[skill_level]:
                if not styles & MusicStyle.styles_for_track[track]:
                    pass
                else:
                    valid_tracks.append(track)
        sim_mood = sim.get_mood()
        valid_mood_tracks = [track for track in valid_tracks if sim_mood in track.moods]
        if valid_mood_tracks or not valid_tracks:
            return
        to_consider = valid_mood_tracks or valid_tracks
        random.shuffle(to_consider)
        for track in to_consider:
            if track.check_for_unlock and sim.sim_info.unlock_tracker is not None and sim.sim_info.unlock_tracker.is_unlocked(track):
                return track
            if track.check_for_unlock or track.tests.run_tests(resolver):
                return track

    @classmethod
    def _has_tracks(cls, sim, resolver):
        has_tracker = sim.sim_info.unlock_tracker is not None
        styles = set(cls.music_styles)
        for (skill_type, level_to_tracks) in MusicStyle.tracks_by_skill.items():
            skill_level = PlayAudioMixin._get_skill_level(skill_type, sim)
            for track in level_to_tracks[skill_level]:
                if not styles & MusicStyle.styles_for_track[track]:
                    pass
                else:
                    if track.check_for_unlock and has_tracker and sim.sim_info.unlock_tracker.is_unlocked(track):
                        return True
                    if track.check_for_unlock or track.tests.run_tests(resolver):
                        return True
        return False

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.is_super:
            for affordance in cls._content_sets.all_affordances_gen():
                if isinstance(affordance, PlayAudioMixin):
                    logger.error('{} references another PlayAudio interaction: {} in its content set. This will not properly work as the clip events will collide with one another.', cls, affordance)

class PlayAudioTieredMenuMixin(PlayAudioMixin):
    INSTANCE_SUBCLASSES_ONLY = True

    @flexmethod
    def get_pie_menu_category(cls, inst, pie_menu_category=None, **interaction_parameters):
        if inst is not None:
            return inst.pie_menu_category
        return pie_menu_category

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, track=None, unlockable_name=None, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if track is not None and track.music_track_name is not None:
            name = track.music_track_name(unlockable_name)
            return name
        return super(__class__, inst_or_cls)._get_name(target=target, context=context, **kwargs)

    @classmethod
    def potential_interactions(cls, *args, **kwargs):
        raise NotImplementedError

class PlayAudioNonTieredMenuMixin(PlayAudioMixin):
    INSTANCE_SUBCLASSES_ONLY = True

    def __init__(self, aop_or_target, context, **kwargs):
        super().__init__(aop_or_target, context, **kwargs)
        if 'phase' in kwargs:
            phase = kwargs['phase']
            styles = [phase.recipe.get_crafting_music_style(affordance=self.affordance)]
        else:
            styles = self.music_styles
        self._track = PlayAudioMixin._get_next_track(styles, context.sim, self.get_resolver())

    @classproperty
    def validate_tracks(cls):
        return True

    @flexmethod
    def test(cls, inst, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst is not None:
            if inst._track is None:
                return event_testing.results.TestResult(False, 'No available songs to play.')
        else:
            context = cls.context if context is DEFAULT else context
            sim = context.sim
            if sim is None:
                return event_testing.results.TestResult(False, 'Sim is None in interaction context.')
            if not cls._has_tracks(sim, sim.get_resolver()):
                return event_testing.results.TestResult(False, 'No available songs to play.')
        return super(__class__, inst_or_cls).test(context=context, **kwargs)

class PlayAudioSuperInteractionTieredMenu(PlayAudioTieredMenuMixin, SuperInteraction):

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        sim = context.sim
        if sim is None:
            return
        resolver = SingleSimResolver(sim.sim_info)
        for style in cls.music_styles:
            for track in style.music_tracks:
                if track.tests.run_tests(resolver):
                    if not track.check_for_unlock:
                        yield AffordanceObjectPair(cls, target, cls, None, track=track, pie_menu_category=style.pie_menu_category, **kwargs)
                    else:
                        unlocks = sim.sim_info.unlock_tracker.get_unlocks(track) if sim.sim_info.unlock_tracker is not None else None
                        if unlocks:
                            for unlock in unlocks:
                                yield AffordanceObjectPair(cls, target, cls, None, track=unlock.tuning_class, pie_menu_category=style.pie_menu_category, unlockable_name=unlock.name, **kwargs)

class PlayAudioSuperInteractionNonTieredMenu(PlayAudioNonTieredMenuMixin, SuperInteraction):
    pass

class PlayAudioMouthpieceSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'audio_stop_event': Tunable(description='\n            The script event to listen for from animation so we know when to\n            stop the music and vocals.\n            ', tunable_type=int, default=101), 'mouthpiece_target': TunableEnumEntry(description='\n            The participant of mine that owning music interaction must target \n            as its mouthpiece target.  e.g. if we are targeting the sim running\n            the music interaction their mouthpiece target would be actor, our\n            mouthpiece target would be targetsim.  If all of us are targeting \n            a certain object then both would be object.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mouthpiece_owner = None

    def set_mouthpiece_owner(self, owner):
        self._mouthpiece_owner = owner

    def is_mouthpiece_target(self, target):
        return target is self.get_participant(self.mouthpiece_target)

    def build_basic_content(self, sequence=(), **kwargs):
        self.store_event_handler(self._cancel_sound_alarm, self.audio_stop_event)
        sequence = super().build_basic_content(sequence, **kwargs)
        return build_critical_section_with_finally(sequence, self._cancel_sound_alarm)

    def _cancel_sound_alarm(self, *args, **kwargs):
        if self._mouthpiece_owner is not None:
            self._mouthpiece_owner.stop_mouthpiece(self.sim)
            self._mouthpiece_owner = None

class PlayAudioSocialSuperInteraction(PlayAudioNonTieredMenuMixin, SocialSuperInteraction):
    pass

class PlayAudioCraftingPhaseStagingSuperInteraction(PlayAudioNonTieredMenuMixin, CraftingPhaseStagingSuperInteraction):

    @classproperty
    def validate_tracks(cls):
        return False

    def _get_music_styles(self):
        crafting_music_style = self.recipe.get_crafting_music_style(affordance=self.affordance)
        if crafting_music_style is None:
            logger.error('Music style is None for {}, cannot play music during {}.', self.recipe, self)
            return self.music_styles
        return [crafting_music_style]

class PlayAudioMixerInteractionNonTieredMenu(PlayAudioNonTieredMenuMixin, MixerInteraction):
    pass
TEXT_INPUT_SONG_NAME = 'song_name'
class UnluckMusicTrackSuperInteraction(CraftingPhaseSuperInteractionMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'dialog': UiDialogTextInputOk.TunableFactory(description='\n            Text entry dialog to name the song the Sim wrote.\n            ', text_inputs=(TEXT_INPUT_SONG_NAME,))}

    @classproperty
    def tuning_tags(cls):
        return cls.get_category_tags()

    def _run_interaction_gen(self, timeline):

        def on_response(dialog):
            if not dialog.accepted:
                self.cancel(FinishingType.DIALOG, cancel_reason_msg='Name Song dialog timed out from client.')
                return
            name = dialog.text_input_responses.get(TEXT_INPUT_SONG_NAME)
            for music_track in self.phase.recipe.music_track_unlocks:
                self.sim.sim_info.unlock_tracker.add_unlock(music_track, name)

        dialog = self.dialog(self.sim, self.get_resolver())
        dialog.show_dialog(on_response=on_response)

        def _destroy_target():
            self.process.current_ico.destroy(source=self, cause='Destroying target of unlock music track SI')

        self.add_exit_function(_destroy_target)
        return True

class LicenseSongSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'music_styles': TunableList(TunableReference(description='\n            Which music styles are available for this interaction.  This\n            should be only the Written Music Style for the particular\n            instrument.\n            ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=(MusicStyle,), reload_dependent=True))}

    @classmethod
    def _verify_tuning_callback(cls):
        for style in cls.music_styles:
            for track in style.music_tracks:
                if not track.check_for_unlock:
                    logger.error("MusicTrack {} does not have check_for_unlock set to False.  This is required for MusicTracks that can be 'Licensed'.", track.__name__)

    def __init__(self, aop, context, track=None, unlockable_name=None, **kwargs):
        super().__init__(aop, context, unlockable_name=unlockable_name, **kwargs)
        self._track = track
        self._unlockable_name = unlockable_name

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, track=None, unlockable_name=None, **kwargs):
        if unlockable_name is not None and track.music_track_name is not None:
            return track.music_track_name(unlockable_name)
        inst_or_cls = inst if inst is not None else cls
        return super(SuperInteraction, inst_or_cls)._get_name(target=target, context=context, **kwargs)

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if context.sim is None:
            return
        if context.sim.sim_info.unlock_tracker is None:
            return
        for style in cls.music_styles:
            for track in style.music_tracks:
                unlocks = context.sim.sim_info.unlock_tracker.get_unlocks(track)
                if unlocks:
                    for unlock in unlocks:
                        yield AffordanceObjectPair(cls, target, cls, None, track=unlock.tuning_class, pie_menu_category=style.pie_menu_category, unlockable_name=unlock.name, **kwargs)
