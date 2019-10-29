import clockimport enumimport event_testingimport servicesimport sims4.logfrom event_testing.results import TestResult, TestResultNumericfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_test, TestEventfrom interactions import ParticipantType, ParticipantTypeSim, ParticipantTypeSingle, ParticipantTypeSingleSim, ParticipantTypeActorTargetSimfrom objects import ALL_HIDDEN_REASONSfrom objects.components import typesfrom objects.components.stored_object_info_tuning import StoredObjectTypefrom sims.sim_info_gameplay_options import SimInfoGameplayOptions, is_required_pack_installedfrom sims.sim_info_types import Species, SpeciesExtended, Gender, Agefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableFactory, TunableEnumEntry, OptionalTunable, TunableEnumSet, TunableVariant, Tunable, TunableList, TunablePackSafeReference, TunableReference, TunableSet, TunableThreshold, TunableEnumFlags, TunableSimMinute, TunableRange, TunableSkinTonefrom sims4.utils import classpropertyfrom traits.trait_type import TraitTypelogger = sims4.log.Logger('SimInfoTests')
class MatchType(enum.Int):
    MATCH_ALL = 0
    MATCH_ANY = 1

class _SpeciesTestSpecies(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'species': TunableEnumSet(description='\n            The Sim must be one of the specified species. Species are\n            consolidated, e.g. large/small dog are both DOG.\n            ', enum_type=Species, enum_default=Species.HUMAN, invalid_enums=(Species.INVALID,))}

    def __call__(self, sim_info):
        return sim_info.species in self.species

class _SpeciesTestExtendedSpecies(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'species': TunableEnumSet(description='\n            The Sim must be one of the specified species. Species are *not*\n            consolidated, e.g. large/small dog are different species.\n            ', enum_type=SpeciesExtended, enum_default=Species.HUMAN, invalid_enums=(SpeciesExtended.INVALID,))}

    def __call__(self, sim_info):
        return sim_info.extended_species in self.species

class AgeUpTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                Who or what to apply this test to.\n                ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor)}

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call AgeUpTest with a None value in the sims iterable.')
            else:
                if target.is_npc:
                    return TestResult.TRUE
                if target.can_age_up():
                    return TestResult.TRUE
        return TestResult(False, '{} failed AgeUp check. Current age: {}', target, target._age_progress.get_value(), tooltip=self.tooltip)

class SimInfoTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='"\n                Who or what to apply this test to\n                ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'gender': OptionalTunable(tunable=TunableEnumEntry(description='\n                The Sim must be of the specified gender.\n                ', tunable_type=Gender, default=None), enabled_name='specified', disabled_name='unspecified'), 'ages': OptionalTunable(tunable=TunableEnumSet(description='\n                The Sim must be one of the specified ages.\n                ', enum_type=Age, enum_default=Age.ADULT, default_enum_list=[Age.TEEN, Age.YOUNGADULT, Age.ADULT, Age.ELDER]), disabled_name='unspecified', enabled_name='specified'), 'species': TunableVariant(specified=_SpeciesTestSpecies.TunableFactory(), specified_extended=_SpeciesTestExtendedSpecies.TunableFactory(), locked_args={'unspecified': None}, default='unspecified'), 'can_age_up': OptionalTunable(tunable=Tunable(description='\n                Whether the Sim is eligible to advance to the next age.\n                ', tunable_type=bool, default=None), enabled_name='specified', disabled_name='unspecified'), 'npc': OptionalTunable(tunable=Tunable(description="\n                Whether the Sim must be an NPC or Playable Sim.\n                If enabled and true, the sim must be an NPC for this test to pass.\n                If enabled and false, the sim must be playable, non-NPC sim for this test to pass.\n                If disabled, this portion of the Sim Info test will be ignored.\n                \n                Note: NPC in this case means a Sim that is not currently\n                controllable (selectable), or Not Player Controllable. If you\n                need to know if the Sim has ever been played, use 'Has Been\n                Played'\n                ", tunable_type=bool, default=False)), 'has_been_played': OptionalTunable(tunable=Tunable(description='\n                Whether the Sim has ever been played as a Playable Sim.\n                If enabled and true, the Sim must have been played by the player.\n                If enabled and false, the Sim must never have been played.\n                If disabled, this portion of the Sim Info test will be ignored.\n                ', tunable_type=bool, default=False)), 'is_active_sim': OptionalTunable(tunable=Tunable(description='\n                Whether the Sim must be the active selected Sim.\n                If enabled and true, the sim must active for this test to pass.\n                If enabled and false, the sim must not be active for this test to pass.\n                If disabled, this portion of the Sim Info test will be ignored.\n                ', tunable_type=bool, default=True)), 'match_type': TunableEnumEntry(description='\n            When testing multiple participants if MATCH_ALL is set, then all the\n            participants need to pass the test.\n             \n            If MATCH_ANY is set, test will pass as soon as one of them meet the\n            criteria\n            ', tunable_type=MatchType, default=MatchType.MATCH_ALL)}
    __slots__ = ('gender', 'who', 'ages', 'species', 'can_age_up', 'is_active_sim', 'npc', 'has_been_played', 'match_type')

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        if self.match_type == MatchType.MATCH_ANY:
            for target in test_targets:
                result = self._test_sim_info(target)
                if result:
                    return result
            return result
        for target in test_targets:
            result = self._test_sim_info(target)
            if not result:
                return result
        return TestResult.TRUE

    def _test_sim_info(self, sim_info):
        if sim_info is None:
            return TestResult(False, 'Sim Info is None!')
        if self.gender is not None and sim_info.gender != self.gender:
            return TestResult(False, "{}'s gender is {}, must be {}", self.who.name, sim_info.gender, self.gender, tooltip=self.tooltip)
        if self.ages is not None and sim_info.age not in self.ages:
            return TestResult(False, "{}'s age is {}, must be one of the following: {}", self.who.name, sim_info.age, ', '.join(str(age) for age in self.ages), tooltip=self.tooltip)
        if self.species is not None:
            result = self.species(sim_info)
            if not result:
                return TestResult(False, '{} is not of a valid species', sim_info, tooltip=self.tooltip)
        if self.can_age_up is not None and self.can_age_up != sim_info.can_age_up():
            return TestResult(False, '{} {} be able to advance to the next age.', self.who.name, 'must' if self.can_age_up else 'must not', tooltip=self.tooltip)
        if self.npc is not None and sim_info.is_npc != self.npc:
            return TestResult(False, '{} does not meet the npc requirement.', sim_info.full_name, tooltip=self.tooltip)
        if self.has_been_played is not None and sim_info.is_player_sim != self.has_been_played:
            return TestResult(False, '{} does not meet the has_been_played requirement.', sim_info.full_name, tooltip=self.tooltip)
        if self.is_active_sim is not None:
            active_sim = services.get_active_sim()
            if active_sim is None:
                return TestResult(False, 'SimInfoTest: Client returned active Sim as None.', tooltip=self.tooltip)
            if self.is_active_sim:
                if active_sim.sim_info is not sim_info:
                    return TestResult(False, '{} does not meet the active sim requirement.', sim_info.full_name, tooltip=self.tooltip)
            elif active_sim.sim_info is sim_info:
                return TestResult(False, '{} does not meet the active sim requirement.', sim_info.full_name, tooltip=self.tooltip)
        return TestResult.TRUE

class TraitTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.TraitAddEvent, TestEvent.SimTravel, TestEvent.HouseholdChanged)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'subject': TunableEnumEntry(participant_type_enum, participant_type_default, description='Who or what to apply this test to')}

    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that is to be the subject of the test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'whitelist_traits': TunableList(description='\n            The Sim is required to have the specified number of traits from this\n            list in order to pass the test.\n            ', tunable=TunablePackSafeReference(description="\n                A whitelist trait. Please note: for pack-safe entries that are\n                not loaded, the game will behave as if the entry doesn't exist.\n                This allows you to specify a pack trait and required count of 1\n                and always fail the test should the appropriate pack not be\n                installed.\n                ", manager=services.trait_manager()), allow_none=True), 'blacklist_traits': TunableList(description='\n            The is required to not have traits from this list in order to pass\n            this test. Should num_blacklist_allowed be specified, then the Sim\n            is allowed to have up to that amount of blacklisted traits before\n            failing this test.\n            ', tunable=TunableReference(description='\n                A blacklist trait.\n                ', manager=services.trait_manager(), pack_safe=True)), 'whitelist_trait_types': TunableEnumSet(description='\n            The Sim is required to have the specified number of traits with \n            these types in order to pass the test.\n            ', enum_type=TraitType), 'blacklist_trait_types': TunableEnumSet(description='\n            The Sim is required to not have traits of these types to pass this \n            test. Should Num Blacklist Allowed be specified, then the Sim is \n            allowed to have up to that amount of blacklisted traits before \n            failing this test.\n            ', enum_type=TraitType), 'num_whitelist_required': Tunable(description='\n            The number of whitelist traits that the specified Sim is required to\n            have in order to pass this test.\n            ', tunable_type=int, default=1), 'num_blacklist_allowed': Tunable(description='\n            The threshold of blacklist traits owned by the specified Sim that\n            will trigger a test failure.\n            ', tunable_type=int, default=0), 'apply_thresholds_on_individual_basis': Tunable(description="\n            If checked then Num Whitelist Required and Num Blacklist Allowed\n            will be applied to each individual participant from the subject.\n            If unchecked then it will apply the values to the total whitelist\n            and blacklist matches on the group.\n            \n            IMPORTANT!!!\n            In the case of objectives this should probably be set to false\n            since we know that this is coming from only one sim and that we\n            want to use the value that comes out of the test result numeric.\n            This isn't just locked to being this value since there are valid\n            cases within that system when you are looking at a group of sims\n            and could want to test that one of your sims passes.  Ex. Having\n            a ghost sim in the household.\n            ", tunable_type=bool, default=True)}

    def get_test_events_to_register(self):
        if self.subject == ParticipantType.ActiveHousehold:
            return (TestEvent.TraitAddEvent, TestEvent.SimTravel, TestEvent.HouseholdChanged)
        return (TestEvent.TraitAddEvent, TestEvent.SimTravel)

    __slots__ = ('subject', 'whitelist_traits', 'blacklist_traits', 'whitelist_trait_types', 'blacklist_trait_types', 'num_whitelist_required', 'num_blacklist_allowed', 'apply_thresholds_on_individual_basis')

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=()):
        trait_pie_menu_icon = None
        white_count = 0
        black_count = 0
        for target in test_targets:
            trait_tracker = target.trait_tracker
            if self.whitelist_traits or self.whitelist_trait_types:
                if self.apply_thresholds_on_individual_basis:
                    white_count = 0
                pass_white = False
                for trait in self.whitelist_traits:
                    if trait is None:
                        pass
                    elif trait_tracker.has_trait(trait):
                        white_count += 1
                        if white_count >= self.num_whitelist_required:
                            if self.subject == ParticipantType.Actor:
                                trait_pie_menu_icon = trait.pie_menu_icon
                            pass_white = True
                            break
                if not pass_white:
                    for trait_type in self.whitelist_trait_types:
                        traits = trait_tracker.get_traits_of_type(trait_type)
                        white_count += len(traits)
                        if white_count >= self.num_whitelist_required:
                            if self.subject == ParticipantType.Actor:
                                trait_pie_menu_icon = traits[0].pie_menu_icon
                            pass_white = True
                            break
                if pass_white or self.apply_thresholds_on_individual_basis:
                    return TestResult(False, "{} doesn't have any or enough traits in white list", self.subject.name, tooltip=self.tooltip)
            if not self.blacklist_traits:
                if self.blacklist_trait_types:
                    if self.apply_thresholds_on_individual_basis:
                        black_count = 0
                    for trait in self.blacklist_traits:
                        if trait_tracker.has_trait(trait):
                            black_count += 1
                            if black_count > self.num_blacklist_allowed:
                                return TestResult(False, '{} has trait {} in black list', self.subject.name, trait, tooltip=self.tooltip)
                    for trait_type in self.blacklist_trait_types:
                        black_count += len(trait_tracker.get_traits_of_type(trait_type))
                        if black_count > self.num_blacklist_allowed:
                            return TestResult(False, '{} has {} traits that are blacklisted by type.', self.subject.name, black_count, tooltip=self.tooltip)
            if self.apply_thresholds_on_individual_basis:
                black_count = 0
            for trait in self.blacklist_traits:
                if trait_tracker.has_trait(trait):
                    black_count += 1
                    if black_count > self.num_blacklist_allowed:
                        return TestResult(False, '{} has trait {} in black list', self.subject.name, trait, tooltip=self.tooltip)
            for trait_type in self.blacklist_trait_types:
                black_count += len(trait_tracker.get_traits_of_type(trait_type))
                if black_count > self.num_blacklist_allowed:
                    return TestResult(False, '{} has {} traits that are blacklisted by type.', self.subject.name, black_count, tooltip=self.tooltip)
        if self.apply_thresholds_on_individual_basis or white_count < self.num_whitelist_required:
            return TestResultNumeric(False, 'Not enough enough whitelist traits through all participants.', current_value=white_count, goal_value=self.num_whitelist_required, is_money=False)
        return TestResult(True, icon=trait_pie_menu_icon)

    def goal_value(self):
        return self.num_whitelist_required

class BuffTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.BuffBeganEvent,)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'subject': TunableEnumEntry(description='\n                    To whom or what this test should be applied.\n                    ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'whitelist': OptionalTunable(description="\n            If enabled, participant will test for buff's on the whitelist.\n            ", tunable=TunableSet(description='\n                The participant must have at least one buff in this list to pass the\n                test.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True))), 'blacklist': TunableSet(description='\n            The Sim must not have any buff in this list to pass the test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True)), 'apply_whitelist_on_individual_basis': Tunable(description='\n            If checked, will require that each target has at least one\n            whitelisted buff. If unchecked, will require only a single target to\n            have at least one whitelisted trait.\n            ', tunable_type=bool, default=True)}
    __slots__ = ('subject', 'whitelist', 'blacklist', 'apply_whitelist_on_individual_basis')

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=()):
        has_satisfied_whitelist_once = False
        for target in test_targets:
            if self.blacklist and any(target.has_buff(buff_type) for buff_type in self.blacklist):
                return TestResult(False, '{} has buff in blacklist {}', target, self.blacklist, tooltip=self.tooltip)
            if self.whitelist is not None:
                if self.apply_whitelist_on_individual_basis:
                    if not any(target.has_buff(buff_type) for buff_type in self.whitelist):
                        return TestResult(False, "{} doesn't have any buff in whitelist", target, tooltip=self.tooltip)
                        if has_satisfied_whitelist_once or any(target.has_buff(buff_type) for buff_type in self.whitelist):
                            has_satisfied_whitelist_once = True
                elif has_satisfied_whitelist_once or any(target.has_buff(buff_type) for buff_type in self.whitelist):
                    has_satisfied_whitelist_once = True
        if self.apply_whitelist_on_individual_basis:
            return TestResult.TRUE
        if has_satisfied_whitelist_once:
            return TestResult.TRUE
        else:
            return TestResult(False, 'No target has a buff in whitelist', tooltip=self.tooltip)

class BuffAddedTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.BuffBeganEvent,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'acceptable_buffs': TunableSet(description='\n            Buffs that will pass the test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True)), 'check_visibility': Tunable(description='\n            If checked then we will check to make sure that the buff is\n            visible.\n            ', tunable_type=bool, default=False)}

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'buff': event_testing.test_constants.FROM_EVENT_DATA}

    def get_test_events_to_register(self):
        return ()

    def get_custom_event_registration_keys(self):
        keys = [(TestEvent.BuffBeganEvent, buff) for buff in self.acceptable_buffs]
        return keys

    @cached_test
    def __call__(self, buff=None):
        if buff is None:
            return TestResult(False, 'Buff provided is None, valid during zone load.')
        if self.acceptable_buffs and buff not in self.acceptable_buffs:
            return TestResult(False, "{} isn't in acceptable buff list.", buff, tooltip=self.tooltip)
        if self.check_visibility and not buff.visible:
            return TestResult(False, '{} is not visible when we are checking for visibility.', buff, tooltip=self.tooltip)
        return TestResult.TRUE

    def validate_tuning_for_objective(self, objective):
        if self.check_visibility or not self.acceptable_buffs:
            logger.error('Invalid tuning in objective {}.  One of the following must be true: Check Visibility must be true or Acceptable Buffs must have entries.', objective)

class MoodTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.MoodChange, TestEvent.SimTravel)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                    To whom or what this test should be applied.\n                    ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            To whom or what this test should be applied.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'mood': TunablePackSafeReference(description="\n            The mood that must be active (or must be inactive, if 'Disallow' is\n            checked).\n            ", manager=services.get_instance_manager(sims4.resources.Types.MOOD)), 'disallow': Tunable(description="\n            If True, this test will pass if the Sim's mood does NOT match the tuned mood reference.\n            ", tunable_type=bool, default=False)}
    __slots__ = ('who', 'mood', 'disallow')

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        if self.mood is None:
            if self.disallow:
                return TestResult(True)
            return TestResult(False, "Can't match mood as it is None, probably due pack safeness.")
        influence_by_active_mood = False
        for target in test_targets:
            if target is None or not target.is_sim:
                logger.error("Trying to call MoodTest with an invalid Participant Type, {}, in the 'Who' field of tuning. Skipping this participant and attempting to continue.", self)
            else:
                sim_mood = target.get_mood()
                if self.disallow:
                    if self.mood is sim_mood:
                        return TestResult(False, '{} failed mood check for disallowed {}. Current mood: {}', target, self.mood.__name__, sim_mood.__name__ if sim_mood is not None else None, tooltip=self.tooltip)
                        if self.mood is not sim_mood:
                            return TestResult(False, '{} failed mood check for {}. Current mood: {}', target, self.mood.__name__, sim_mood.__name__ if sim_mood is not None else None, tooltip=self.tooltip)
                        if self.who == ParticipantTypeSim.Actor:
                            influence_by_active_mood = True
                else:
                    if self.mood is not sim_mood:
                        return TestResult(False, '{} failed mood check for {}. Current mood: {}', target, self.mood.__name__, sim_mood.__name__ if sim_mood is not None else None, tooltip=self.tooltip)
                    if self.who == ParticipantTypeSim.Actor:
                        influence_by_active_mood = True
        return TestResult(True, influence_by_active_mood=influence_by_active_mood)

class GenealogyRelationType(enum.IntFlags):
    INVALID = 0
    PARENTS = 1
    GRANDPARENTS = 2
    PARENTS_AND_GRANDPARENTS = PARENTS | GRANDPARENTS

class GenealogyTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject who requires to have the genealogy relationship with\n            the target participant. e.g, if PARENTS is selected, then the\n            subject_sim must be a parent of the target_sim.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target_sim': TunableEnumEntry(description='\n            The target sim to test the relationship against.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim), 'required_relationship': TunableEnumEntry(description='\n            The genealogy relationship required from test_participant to\n            target_participant.\n            ', tunable_type=GenealogyRelationType, default=GenealogyRelationType.INVALID, invalid_enums=(GenealogyRelationType.INVALID,))}

    def get_expected_args(self):
        return {'source_participants': self.subject, 'target_participants': self.target_sim}

    def _get_required_ids(self, sim_info):
        genealogy = sim_info.genealogy
        match_ids = set()
        if self.required_relationship & GenealogyRelationType.PARENTS:
            match_ids.update(list(genealogy.get_parent_sim_ids_gen()))
        if self.required_relationship & GenealogyRelationType.GRANDPARENTS:
            match_ids.update(list(genealogy.get_grandparent_sim_ids_gen()))
        return match_ids

    @cached_test
    def __call__(self, source_participants=(), target_participants=()):
        for source_participant in source_participants:
            if not source_participant.is_sim:
                return TestResult(False, 'Source Participant {} is not a sim.', source_participant, tooltip=self.tooltip)
            for target_participant in target_participants:
                target_participant_info = None
                if not target_participant.is_sim:
                    target_participant_info = getattr(target_participant, 'sim_info', None)
                    if target_participant_info is None:
                        return TestResult(False, 'Target Participant {} is not a sim.', target_participant, tooltip=self.tooltip)
                error_message = "Genealogy test fail, {} is not {}'s {}".format(source_participant, target_participant, self.required_relationship)
                match_ids = self._get_required_ids(target_participant_info or target_participant)
                if source_participant.sim_id not in match_ids:
                    return TestResult(False, error_message, tooltip=self.tooltip)
        return TestResult.TRUE

class GenderPreferenceTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    GENDER_PREFERENCE_THRESHOLD = TunableThreshold(description='\n        The threshold in which this sim will consider having an appropriate\n        gender preference.\n        ')
    FACTORY_TUNABLES = {'subject': TunableEnumFlags(description='\n            The subject(s) checking this the gender preference.\n            ', enum_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target_sim': TunableEnumFlags(description='\n            Target(s) of the relationship(s).\n            ', enum_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim), 'fallback_if_no_perference_is_set': Tunable(description='\n            If checked then if no gender preference is set for the sim we will\n            still pass if it is a heterosexual connection.\n            ', tunable_type=bool, default=False), 'override_target_gender_test': OptionalTunable(TunableEnumEntry(description='\n                Required gender to test against as the target gender.\n                ', tunable_type=Gender, default=Gender.FEMALE), disabled_name='test_target_sim_gender', enabled_name='test_specific_gender')}

    def get_expected_args(self):
        return {'subject_participants': self.subject, 'target_participants': self.target_sim}

    def __init__(self, *args, ignore_reciprocal=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._ignore_reciprocal = ignore_reciprocal

    def _check_gender_preference(self, sim_a, sim_b, overide_target_gender=None):
        if overide_target_gender is not None:
            sim_b_gender = overide_target_gender
        else:
            sim_b_gender = sim_b.gender
        if self.fallback_if_no_perference_is_set and not sim_a.has_gender_prefernce_been_set():
            if sim_a.gender == sim_b_gender:
                return TestResult(False, 'GenderPreferenceTest: Sim, {}, has same gender as Sim, {} gender {}, when using fallback.', sim_a, sim_b, sim_b_gender, tooltip=self.tooltip)
            return TestResult.TRUE
        preference_stat = sim_a.get_gender_preference(sim_b_gender)
        if not GenderPreferenceTest.GENDER_PREFERENCE_THRESHOLD.compare(preference_stat.get_value()):
            return TestResult(False, "GenderPreferenceTest: Sim, {}, doesn't have proper gender preference to Sim, {} gender {}.", sim_a, sim_b, sim_b_gender, tooltip=self.tooltip)
        return TestResult.TRUE

    @cached_test
    def __call__(self, subject_participants=None, target_participants=None):
        for subject_participant in subject_participants:
            if not subject_participant.is_sim:
                return TestResult(False, 'GenderPreferenceTest: subject {} is not a sim.', subject_participant, tooltip=self.tooltip)
            if self.override_target_gender_test is not None:
                return self._check_gender_preference(subject_participant, None, self.override_target_gender_test)
            for target_participant in target_participants:
                if not target_participant.is_sim:
                    return TestResult(False, 'GenderPreferenceTest: target {} is not a sim.', target_participant, tooltip=self.tooltip)
                result = self._check_gender_preference(subject_participant, target_participant)
                if not result:
                    return result
                if not self._ignore_reciprocal:
                    result = self._check_gender_preference(target_participant, subject_participant)
                    if not result:
                        return result
        return TestResult.TRUE

class KnowledgeTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of the test. This is the Sim that needs to know\n            information about the target.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'target': TunableEnumEntry(description='\n            The target of the test. This is the Sim whose information needs to\n            be known by the subject.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.TargetSim), 'required_traits': TunableList(description='\n            If there are any traits specified in this list, the test will fail\n            if none of the traits are known.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT))), 'prohibited_traits': TunableSet(description='\n            The test will fail if any of the traits specified in this list are\n            known.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT))), 'career_knowledge_requirement': TunableVariant(description="\n            If enabled, the test will check the subject's knowledge of the\n            target's careers and fail if the knowledge requirement is not met.\n            ", locked_args={'disabled': None, 'knows_about_career': True, 'does_not_know_about_career': False}, default='disabled')}

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.target}

    @cached_test
    def __call__(self, subject=None, target=None):
        subject = next(iter(subject))
        target = next(iter(target))
        if subject is None:
            return TestResult(False, 'Participant {} is None', self.subject, tooltip=self.tooltip)
        if target is None:
            return TestResult(False, 'Participant {} is None', self.target, tooltip=self.tooltip)
        knowledge = subject.relationship_tracker.get_knowledge(target.id)
        known_traits = knowledge.known_traits if knowledge is not None else set()
        if self.required_traits and not any(required_trait in known_traits for required_trait in self.required_traits):
            return TestResult(False, '{} does not know {} has any of these traits: {}', subject, target, self.required_traits, tooltip=self.tooltip)
        if any(prohibited_trait in known_traits for prohibited_trait in self.prohibited_traits):
            return TestResult(False, '{} knows {} has one or more of these traits: {}', subject, target, self.prohibited_traits, tooltip=self.tooltip)
        if self.career_knowledge_requirement is not None:
            knows_career = False if knowledge is None else knowledge.knows_career
            if knows_career != self.career_knowledge_requirement:
                return TestResult(False, '{} knowledge about {} career does not match requirement. Required: {}, Actual: {}', subject, target, self.career_knowledge_requirement, knows_career, tooltip=self.tooltip)
        return TestResult.TRUE

class SatisfactionPointTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.WhimBucksChanged,)
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'threshold': TunableThreshold(description="\n            The threshold to control availability based on the statistic's value\n            ")}

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if not target.is_sim:
                return TestResult(False, 'Cannot test satisfaction points on object other than sim {} as subject {}.', target, self.subject, tooltip=self.tooltip)
            current_satisfaction_points = target.get_whim_bucks()
            if not self.threshold.compare(current_satisfaction_points):
                return TestResult(False, 'No subjects have enough satisfaction points', tooltip=self.tooltip)
        return TestResult.TRUE

class StoredObjectInfoTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that is to be the subject of the test.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'target': TunableEnumEntry(description='\n            The target of the test. This is the Object whose information need \n            to be checked with StoredObjectInfo component from the subject.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'invert': Tunable(description='\n            Whether or not to invert the results of this test.\n            ', tunable_type=bool, default=False), 'stored_object_type': TunableEnumEntry(description='\n            The type of object being stored. This will be used to retrieve the\n            stored object from the Stored Object Info Component of the target.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID, invalid_enums=(StoredObjectType.INVALID,))}

    def get_expected_args(self):
        return {'subject_participant': self.subject, 'target_participant': self.target}

    @cached_test
    def __call__(self, subject_participant=None, target_participant=None):
        if subject_participant is None or target_participant is None:
            return TestResult(False, 'Subject or Target participant is None.', tooltip=self.tooltip)
        subject = next(iter(subject_participant))
        target = next(iter(target_participant))
        if not subject.has_component(types.STORED_OBJECT_INFO_COMPONENT):
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, '{} has no StoredObjectInfo component.', subject, tooltip=self.tooltip)
        stored_object_id = subject.get_stored_object_info_id(self.stored_object_type)
        if stored_object_id is None:
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, '{} has no stored object id info.', subject, tooltip=self.tooltip)
        if stored_object_id != target.id:
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, '{} stored object id is not the same with {} id.', subject, target, tooltip=self.tooltip)
        if self.invert:
            return TestResult(False, '{} stored object id is the same with {} id, but invert is checked.', subject, target, tooltip=self.tooltip)
        return TestResult.TRUE

class StoredObjectInfoExistenceTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that is to be the subject of the test.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'invert': Tunable(description='\n            Whether or not to invert the results of this test.\n            ', tunable_type=bool, default=False), 'stored_object_type': TunableEnumEntry(description='\n            The type of object being stored. This will be used to retrieve the\n            stored object from the Stored Object Info Component of the target.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID, invalid_enums=(StoredObjectType.INVALID,))}

    def get_expected_args(self):
        return {'subject_participant': self.subject}

    @cached_test
    def __call__(self, subject_participant=None):
        if subject_participant is None:
            return TestResult(False, 'Subject participant is None.', tooltip=self.tooltip)
        subject = next(iter(subject_participant))
        if not subject.has_component(types.STORED_OBJECT_INFO_COMPONENT):
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, '{} has no StoredObjectInfo component.', subject, tooltip=self.tooltip)
        stored_object_id = subject.get_stored_object_info_id(self.stored_object_type)
        if stored_object_id is None:
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, '{} has no stored object id info.', subject, tooltip=self.tooltip)
        stored_object = services.object_manager().get(stored_object_id)
        if stored_object is None:
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, '{} stored object is not found on current lot.', subject, tooltip=self.tooltip)
        if self.invert:
            return TestResult(False, '{} stored object {} is found on current lot, but invert is checked', subject, stored_object, tooltip=self.tooltip)
        return TestResult.TRUE

class PregnancyTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant against which to run this pregnancy test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'offspring_gender': OptionalTunable(description="\n            If enabled, test for the offspring's gender.\n            ", tunable=TunableEnumEntry(description='\n                The gender to test for. If the offsrping is not of this gender,\n                the test fails.\n                ', tunable_type=Gender, default=Gender.FEMALE), disabled_name='Dont_Care', enabled_name='Require')}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            pregnancy_tracker = target.pregnancy_tracker
            if not pregnancy_tracker.is_pregnant:
                return TestResult(False, '{} is not pregnant.', target, tooltip=self.tooltip)
            pregnancy_tracker.create_offspring_data()
            first_offspring = next(pregnancy_tracker.get_offspring_data_gen(), None)
            if first_offspring is None:
                return TestResult(False, '{} has no offspring.', target, tooltip=self.tooltip)
            if self.offspring_gender is not None and first_offspring.gender != self.offspring_gender:
                return TestResult(False, "{}'s first offspring should be {} but is {}.", target, self.offspring_gender, first_offspring.gender, tooltip=self.tooltip)
        return TestResult.TRUE

class FilterTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'filter_target': OptionalTunable(tunable=TunableEnumEntry(description='\n                The sim that will have the filter checked against.\n                ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), enabled_by_default=True), 'relative_sim': TunableEnumEntry(description='\n            The sim that will be the relative sim that the filter will\n            check against for relative checks such as relationships or\n            household ids.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'sim_filter': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)), 'duration_available': TunableSimMinute(description='\n            The duration from now that will be used for the start\n            and end time of the filter request.\n            ', default=120, minimum=0), 'threshold_matched': OptionalTunable(description='\n            If enabled, we will require the number of Sims that match the\n            filter pass the threshold requirement. Otherwise we require all\n            Sims that the filter runs on to match.\n            \n            This is useful if you only need one or a number of Sims to match\n            the filter.\n            ', tunable=TunableThreshold(description='\n                A threshold of how many sims should match the filter.\n                ', value=TunableRange(description='\n                    The number that describes the threshold for how many Sims\n                    should match the filter.\n                    ', tunable_type=int, default=1, minimum=0)))}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._duration_available = clock.interval_in_sim_minutes(self.duration_available)

    def get_expected_args(self):
        expected_args = {}
        if self.filter_target is not None:
            expected_args['filter_targets'] = self.filter_target
        expected_args['relative_sims'] = self.relative_sim
        return expected_args

    def _get_sim_filter_gsi_name(self, sim_match_filter_request_type, sim_info=None):
        if sim_match_filter_request_type == True:
            return 'Request to check if {} matches filter from {}'.format(sim_info, self)
        else:
            return 'Tuning: {}'.format(self)

    @cached_test
    def __call__(self, filter_targets=None, relative_sims=None):
        if not relative_sims:
            clients = [client for client in services.client_manager().values()]
            if not clients:
                return TestResult(False, 'FilterTest: No clients found when trying to get the active sim.', tooltip=self.tooltip)
            client = clients[0]
            relative_sim = client.active_sim
            if not relative_sim:
                return TestResult(False, 'FilterTest: No active sim found.', tooltip=self.tooltip)
            relative_sims = {relative_sim.sim_info}
        matches = 0
        if filter_targets is not None:
            for filter_target in filter_targets:
                for relative_sim_info in relative_sims:
                    matched = services.sim_filter_service().does_sim_match_filter(filter_target.id, sim_filter=self.sim_filter, requesting_sim_info=relative_sim_info, household_id=relative_sim_info.household_id, gsi_source_fn=lambda : self._get_sim_filter_gsi_name(True, sim_info=relative_sim_info))
                    if self.threshold_matched is not None:
                        matches = matches + 1 if matched else matches
                    elif not matched:
                        return TestResult(False, 'FilterTest: Sim {} (id {}) does not match filter {}.', filter_target.full_name, filter_target.id, self.sim_filter.__name__, tooltip=self.tooltip)
        else:
            for relative_sim_info in relative_sims:
                results = services.sim_filter_service().submit_filter(self.sim_filter, None, requesting_sim_info=relative_sim_info, allow_yielding=False, start_time=services.time_service().sim_now, end_time=services.time_service().sim_now + self._duration_available, household_id=relative_sim_info.household_id, gsi_source_fn=lambda : self._get_sim_filter_gsi_name(False))
                if self.threshold_matched is not None:
                    matches += len(results)
                elif not results:
                    return TestResult(False, 'FilterTest: Sim {} (id {}) does not match filter {}.', relative_sim_info.full_name, relative_sim_info.id, self.sim_filter.__name__, tooltip=self.tooltip)
        if self.threshold_matched is not None and not self.threshold_matched.compare(matches):
            return TestResult(False, 'FilterTest: {} Sims matched the filter {} but did not meet the threshold {}', matches, self.sim_filter.__name__, self.threshold_matched, tooltip=self.tooltip)
        return TestResult.TRUE

class _AppropriatenessTestBase(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The subject of this situation data test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}
    __slots__ = ('participant', 'is_appropriate')

    def get_expected_args(self):
        return {'test_targets': self.participant, 'affordance': ParticipantType.Affordance}

    @cached_test
    def __call__(self, test_targets=None, affordance=None):
        if not test_targets:
            return TestResult(False, 'AppropriatenessTest: There are no participants.', tooltip=self.tooltip)
        if not affordance:
            return TestResult(False, 'AppropriatenessTest: There is no affordance.', tooltip=self.tooltip)
        for target in test_targets:
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'AppropriatenessTest: {} is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if target.Buffs.is_appropriate(affordance.appropriateness_tags) != self.is_appropriate:
                return TestResult(False, 'AppropriatenessTest: This interaction is not appropriate for Sim of id {}. appropriateness tags {}.', target.id, affordance.appropriateness_tags, tooltip=self.tooltip)
        return TestResult.TRUE

class AppropriatenessTest(_AppropriatenessTestBase):
    __slots__ = ()

    @classproperty
    def is_appropriate(self):
        return True

class InappropriatenessTest(_AppropriatenessTestBase):
    __slots__ = ()

    @classproperty
    def is_appropriate(self):
        return False

class SimInfoGameplayOptionsTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The subject of the test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'gameplay_option': TunableEnumEntry(description='\n            The gameplay option to test. This test will pass if this option is\n            set.\n            ', tunable_type=SimInfoGameplayOptions, default=SimInfoGameplayOptions.ALLOW_FAME), 'invert': Tunable(description='\n            If enabled, requires the option to be unset for the test to pass.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=None):
        subject = next(iter(test_targets))
        if not is_required_pack_installed(self.gameplay_option):
            return TestResult(False, '{} option missing required pack', self.gameplay_option, self.tooltip)
        option_result = subject.sim_info.get_gameplay_option(self.gameplay_option)
        if self.invert or option_result or not (self.invert and option_result):
            return TestResult.TRUE
        return TestResult(False, "{}'s option {} is set to {}", subject, self.gameplay_option, option_result, tooltip=self.tooltip)

class SkinToneTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of the test.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'skin_tones': TunableList(description="\n            The Sim's skin tone must be one of the specified skin tones.\n            ", tunable=TunableSkinTone(description='\n                A skin tone to test.\n                ', pack_safe=True), minlength=1), 'invert': Tunable(description='\n            If true, invert the result of this test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subject': self.subject}

    @cached_test
    def __call__(self, subject=None):
        subject = next(iter(subject))
        if subject.skin_tone in self.skin_tones:
            if self.invert:
                return TestResult(False, "{}'s skin tone is {} which is one of the following: {}, but invert is checked", subject, subject.skin_tone, ', '.join(str(skin_tone) for skin_tone in self.skin_tones), tooltip=self.tooltip)
            return TestResult.TRUE
        if self.invert:
            return TestResult.TRUE
        return TestResult(False, "{}'s skin tone is {} which is not one of the following: {}", subject, subject.skin_tone, ', '.join(str(skin_tone) for skin_tone in self.skin_tones), tooltip=self.tooltip)

class BirthdayTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant against which to run this birthday test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'invert': Tunable(description='\n            If true, invert the result of this test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if not target.is_birthday():
                if self.invert:
                    return TestResult.TRUE
                return TestResult(False, "It is not {}'s birthday.", target, tooltip=self.tooltip)
        if self.invert:
            return TestResult(False, "Test inverted, it is {}'s birthday.", target, tooltip=self.tooltip)
        return TestResult.TRUE
