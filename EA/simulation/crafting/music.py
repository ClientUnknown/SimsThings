import collectionsfrom crafting.recipe import Recipefrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypeSimfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import TunedInstanceMetaclass, HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableResourceKey, TunableRealSecond, TunableList, TunableReference, Tunable, OptionalTunable, HasTunableReference, TunableEnumEntry, TunableMapping, TunableVariant, TunableTuplefrom statistics.skill_tests import SkillRangeTestimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Music')
class VocalTrack(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RECIPE)):
    INSTANCE_TUNABLES = {'vocal_clip': TunableResourceKey(description='\n            The propx file of the vox to play.\n            ', default=None, resource_types=(sims4.resources.Types.PROPX,)), 'tests': TunableTestSet(description='\n            Tests to verify if this song is available for the Sim to play.\n            ')}

class MusicTrack(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RECIPE)):
    INSTANCE_TUNABLES = {'music_clip': OptionalTunable(description='\n            If enabled, the music clip for music interactions. If disabled,\n            make sure you have vocals tuned.\n            ', tunable=TunableResourceKey(description='\n                The propx file of the music clip to play.\n                ', needs_tuning=False, resource_types=(sims4.resources.Types.PROPX,))), 'length': TunableRealSecond(description="\n            The length of the clip in real seconds.  This should be a part of\n            the propx's file name.\n            ", needs_tuning=False, default=30, minimum=0), 'buffer': TunableRealSecond(description="\n            A buffer added to the track length.  This is used to prevent the\n            audio from stopping before it's finished.\n            ", needs_tuning=False, default=0), 'check_for_unlock': Tunable(description="\n            Whether or not to check the Sim's Unlock Component to determine if\n            they can play the song.  Currently, only clips that are meant to be\n            unlocked by the Write Song interaction should have this set to true.\n            ", needs_tuning=False, tunable_type=bool, default=False), 'music_track_name': OptionalTunable(description="\n            If the clip is of a song, this is its name. The name is shown in the\n            Pie Menu when picking specific songs to play.\n            \n            If the clip isn't a song, like clips used for the Practice or Write\n            Song interactions, this does not need to be tuned.\n            ", tunable=TunableLocalizedStringFactory(description="\n                The track's name.\n                "), enabled_by_default=True), 'tests': TunableTestSet(description='\n            Tests to verify if this song is available for the Sim to play.\n            '), 'moods': TunableList(description="\n            A list of moods that will be used to determine which song a Sim will\n            play autonomously.  If a Sim doesn't know any songs that their\n            current mood, they'll play anything.\n            ", tunable=TunableReference(manager=services.mood_manager()), needs_tuning=True), 'vocals': TunableMapping(description="\n            A mapping of participants and their potential vocal tracks. Each\n            participant that has a vocal track that tests successfully will\n            sing when the music starts.\n            \n            Note: The interaction's resolver will be passed into the vocal\n            track tests, so use the same participant in those tests.\n            ", key_name='participant', value_name='vocal_tracks', key_type=TunableEnumEntry(description='\n                The participant who should sing vocals when the music starts.\n                ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), value_type=TunableList(description='\n                If this music track has vocals, add them here.  The first track that\n                passes its test will be used.  If no tracks pass their test, none\n                will be used.\n                ', tunable=VocalTrack.TunableReference()))}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.music_clip is None and not cls.vocals:
            logger.error('{} does not have music or vocals tuned.', cls, owner='rmccord')

class MusicStyle(HasTunableReference, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RECIPE)):
    INSTANCE_TUNABLES = {'music_tracks': TunableList(TunableReference(description='\n            A particular music track to use as part of this\n            style.\n            ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), pack_safe=True, class_restrictions=(MusicTrack,))), 'pie_menu_category': TunableReference(description='\n            The pie menu category for this music style.\n            This can be used to break styles up into genres.\n            ', manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True)}
    tracks_by_skill = collections.defaultdict(lambda : collections.defaultdict(set))
    styles_for_track = collections.defaultdict(set)

    @classmethod
    def _tuning_loaded_callback(cls):
        services.get_instance_manager(sims4.resources.Types.RECIPE).add_on_load_complete(cls._set_up_dictionaries)

    @classmethod
    def _set_up_dictionaries(cls, _):
        for track in cls.music_tracks:
            cls.styles_for_track[track].add(cls)
            if not track.tests:
                logger.error('{} has no tuned test groups. This makes it hard to optimize music track choosing. Please tune at least one test group and one skill test in every test group.', cls, owner='rmccord')
            for test_group in track.tests:
                has_skill_test = False
                for test in test_group:
                    if not isinstance(test, SkillRangeTest):
                        pass
                    else:
                        has_skill_test = True
                        for level in range(test.skill_range_min, test.skill_range_max + 1):
                            cls.tracks_by_skill[test.skill][level].add(track)
                if not has_skill_test:
                    logger.error('{} has no tuned skill test in one of its test groups. This makes it hard to optimize music track choosing. Please tune at least one skill test in every test group.', cls, owner='rmccord')

class MusicRecipe(Recipe):
    MUSIC_STYLE_SINGLE = 0
    MUSIC_STYLE_AFFORDANCE_MAP = 1
    INSTANCE_TUNABLES = {'music_track_unlocks': TunableList(description='\n            The music tracks that will be unlocked when the crafting process is\n            complete.\n            ', tunable=TunableReference(description='\n                The music track that will be unlocked when the crafting process\n                is complete.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=('MusicTrack',))), 'music_style_while_crafting': TunableVariant(description='\n            Tuning that decides which music style to play while crafting this\n            recipe.\n            ', single_music_style=TunableTuple(description='\n                A single music style to use while crafting.\n                ', music_style=TunableReference(description='\n                    Which music style the Sim will pull tracks from while writing\n                    the song.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=('MusicStyle',)), locked_args={'variant_music_type': MUSIC_STYLE_SINGLE}), affordance_to_style_mapping=TunableTuple(description='\n                A mapping from affordance to music style, so that we can craft\n                this recipe on multiple instruments. the affordances in this\n                list should be some part of the phases of the recipe, so they\n                can pull from this list.\n                ', mapping=TunableMapping(description='\n                    A mapping from affordance to music style, so that we can craft\n                    this recipe on multiple instruments. the affordances in this\n                    list should be some part of the phases of the recipe, so they\n                    can pull from this list.\n                    ', key_type=TunableReference(description='\n                        The affordance used to craft this recipe.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('PlayAudioCraftingPhaseStagingSuperInteraction',)), value_type=TunableReference(description='\n                        Which music style the Sim will pull tracks from while writing\n                        the song.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=('MusicStyle',)), key_name='affordance', value_name='music_style'), locked_args={'variant_music_type': MUSIC_STYLE_AFFORDANCE_MAP}), default='single_music_style')}

    @classmethod
    def get_crafting_music_style(cls, affordance=None):
        if cls.music_style_while_crafting.variant_music_type == MusicRecipe.MUSIC_STYLE_SINGLE:
            return cls.music_style_while_crafting.music_style
        elif cls.music_style_while_crafting.variant_music_type == MusicRecipe.MUSIC_STYLE_AFFORDANCE_MAP and affordance is not None:
            return cls.music_style_while_crafting.mapping.get(affordance, None)
        else:
            return
        return
