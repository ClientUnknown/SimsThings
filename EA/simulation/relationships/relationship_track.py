import collectionsimport operatorfrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom interactions.utils.tunable_icon import TunableIconfrom relationships.tunable import TunableRelationshipBitData, TunableRelationshipTrack2dLinkfrom sims.sim_info_types import Speciesfrom sims4.math import Thresholdfrom sims4.tuning.geometric import TunableVector2, TunableWeightedUtilityCurveAndWeightfrom sims4.tuning.instances import HashedTunedInstanceMetaclass, lock_instance_tunablesfrom sims4.tuning.tunable import TunableVariant, TunableList, TunableReference, TunableRange, HasTunableReference, Tunable, TunableSet, OptionalTunable, TunableTuple, TunableThreshold, TunableInterval, TunablePackSafeReference, TunableEnumEntry, TunableMappingfrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom sims4.utils import classpropertyfrom singletons import DEFAULTfrom statistics.continuous_statistic_tuning import TunedContinuousStatisticfrom tunable_multiplier import TestedSumimport alarmsimport date_and_timeimport event_testing.testsimport servicesimport simsimport sims4.logimport sims4.resourcesimport sims4.tuninglogger = sims4.log.Logger('Relationship', default_owner='msantander')
class BaseRelationshipTrack:
    INSTANCE_TUNABLES = {'bit_data_tuning': TunableVariant(description='\n            Bit tuning for all the bits that compose this relationship \n            track.\n            The structure tuned here, either 2d or simple track should include \n            bits for all the possible range of the track.\n            ', bit_set=TunableRelationshipBitData(), _2dMatrix=TunableRelationshipTrack2dLink()), '_neutral_bit': TunableReference(description="\n            The neutral bit for this relationship track.  This is the bit\n            that is displayed when there are holes in the relationship\n            track's bit data.\n            ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), tuning_group=GroupNames.CORE), 'ad_data': TunableList(description='\n            A list of Vector2 points that define the desire curve for this \n            relationship track.\n            ', tunable=TunableVector2(description='\n                Point on a Curve.\n                ', default=sims4.math.Vector2(0, 0)), tuning_group=GroupNames.SPECIAL_CASES), '_add_bit_on_threshold': OptionalTunable(description='\n            If enabled, the referenced bit will be added this track reaches the\n            threshold.\n            ', tunable=TunableTuple(description='\n                The bit & threshold pair.\n                ', bit=TunableReference(description='\n                    The bit to add.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), threshold=TunableThreshold(description='\n                    The threshold at which to add this bit.\n                    ')), tuning_group=GroupNames.CORE), 'causes_delayed_removal_on_convergence': Tunable(description='\n            If True, this track may cause the relationship to get culled\n            when it reaches convergence.  This is not guaranteed, based on\n            the culling rules.  Sim relationships will NOT be culled if any\n            of the folling conditions are met: \n            - Sim has any relationship bits that are tuned to prevent this. \n            - The sims are in the same household\n            \n            Note: This value is ignored by the Relationship Culling Story\n            Progression Action.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CORE), 'tested_initial_modifier': OptionalTunable(description='\n            If enabled, a modifier will be applied to the initial value when\n            the track is created.\n            ', tunable=TestedSum.TunableFactory(description='\n                The test to run and the outcome if test passes.\n                '), tuning_group=GroupNames.CORE), 'visible_test_set': OptionalTunable(event_testing.tests.TunableTestSet(description='\n                If set, tests whether relationship should be sent to client. If\n                no test given, then as soon as track is added to the\n                relationship, it will be visible to client.\n                '), disabled_value=DEFAULT, disabled_name='always_visible', enabled_name='run_test', tuning_group=GroupNames.SPECIAL_CASES), 'delay_until_decay_is_applied': OptionalTunable(description='\n            If enabled, the decay for this track will be disabled whenever\n            the value changes by any means other than decay.  It will then \n            be re-enabled after this amount of time (in sim minutes) passes.\n            ', tunable=TunableRange(description='\n                The amount of time, in sim minutes, that it takes before \n                decay is enabled.\n                ', tunable_type=int, default=10, minimum=1), tuning_group=GroupNames.DECAY), 'display_priority': TunableRange(description='\n            The display priority of this relationship track.  Tracks with a\n            display priority greater than zero will be displayed in ascending\n            order in the UI.\n            \n            So a relationship track with a display priority of 1 will show\n            above a relationship track with a display priority of 2.\n            Relationship tracks with the same display priority will show up\n            in potentially non-deterministic ways.  Relationship tracks\n            with display priorities of 0 will not be shown.\n            ', tunable_type=int, default=0, minimum=0, tuning_group=GroupNames.UI), 'headline': OptionalTunable(description='\n            If enabled when this relationship track updates we will display\n            a headline update to the UI.\n            ', tunable=TunableReference(description='\n                The headline that we want to send down.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HEADLINE)), tuning_group=GroupNames.UI), 'display_popup_priority': TunableRange(description='\n            The display popup priority.  This is the priority that the\n            relationship score increases will display if there are multiple\n            relationship changes at the same time.\n            ', tunable_type=int, default=0, minimum=0, tuning_group=GroupNames.UI), 'persist_at_convergence': Tunable(description='\n            If unchecked, this track will not be persisted if it is at\n            convergence. This prevents a ton of tracks, in particular short\n            term context tracks, from piling up on relationships with a value\n            of 0.\n            \n            If checked, the track will be persisted even if it is at 0. This\n            should only used on tracks where its presence matters.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES)}

    def __init__(self, tracker):
        super().__init__(tracker, self.initial_value)
        self._per_instance_data = self.bit_data.get_track_instance_data(self)
        self.visible_to_client = True if self.visible_test_set is DEFAULT else False
        self._decay_alarm_handle = None
        self._cached_ticks_until_decay_begins = -1
        self._convergence_callback_data = None
        self._set_initial_decay()
        if not self._tracker.suppress_callback_setup_during_load:
            self._create_convergence_callback()

    def on_add(self):
        if not self.tracker.suppress_callback_setup_during_load:
            self._per_instance_data.setup_callbacks()
            (old_bit, new_bit) = self.update_instance_data()
            if not self.tracker.load_in_progress:
                sim_id_a = self.tracker.rel_data.relationship.sim_id_a
                sim_id_b = self.tracker.rel_data.relationship.sim_id_b
                if old_bit is not None and old_bit is not new_bit:
                    self.tracker.rel_data.relationship.remove_bit(sim_id_a, sim_id_b, old_bit)
                if new_bit is not None and not self.tracker.rel_data.relationship.has_bit(sim_id_a, new_bit):
                    self.tracker.rel_data.relationship.add_relationship_bit(sim_id_a, sim_id_b, new_bit)
        if self._add_bit_on_threshold is not None:
            self.create_and_add_callback_listener(self._add_bit_on_threshold.threshold, self._on_add_bit_from_threshold_callback)

    def _set_initial_decay(self):
        if self._should_decay():
            self.decay_enabled = True

    def _should_decay(self):
        if self.decay_rate == 0:
            return False
        if self.tracker.is_track_locked(self):
            return False
        if self.tracker.rel_data.relationship.is_object_rel():
            return True
        if self.decay_only_affects_played_sims:
            if not services.sim_info_manager():
                return False
            sim_info = self.tracker.rel_data.relationship.find_sim_info_a()
            target_sim_info = self.tracker.rel_data.relationship.find_sim_info_b()
            if sim_info is None or target_sim_info is None:
                return False
            active_household = services.active_household()
            if active_household is None:
                return False
            if sim_info in active_household or target_sim_info in active_household:
                return True
            if sim_info.is_player_sim or target_sim_info.is_player_sim:
                if not self.tracker.rel_data.relationship.can_cull_relationship(consider_convergence=False):
                    return False
                current_value = self.get_value()
                if self.decay_affecting_played_sims.range_decay_threshold.lower_bound < current_value and current_value < self.decay_affecting_played_sims.range_decay_threshold.upper_bound:
                    return True
        else:
            return True
        return False

    def _create_convergence_callback(self):
        if self._convergence_callback_data is None:
            self._convergence_callback_data = self.create_and_add_callback_listener(Threshold(self.convergence_value, operator.eq), self._on_convergence_callback)
        else:
            logger.error('Track {} attempted to create convergence callback twice.'.format(self))

    def _on_convergence_callback(self, _):
        logger.debug('Track {} reached convergence; rel might get culled for {}', self, self.tracker.rel_data)
        self.tracker.rel_data.track_reached_convergence(self)

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        cls.bit_data = cls.bit_data_tuning()
        cls.bit_data.build_track_data()
        cls._build_utility_curve_from_tuning_data(cls.ad_data)

    def fixup_callbacks_during_load(self):
        self._create_convergence_callback()
        super().fixup_callbacks_during_load()
        self._per_instance_data.setup_callbacks()

    def update_instance_data(self):
        return self._per_instance_data.request_full_update()

    def reset_decay_alarm(self, use_cached_time=False):
        self._destroy_decay_alarm()
        if self._should_decay():
            delay_time_span = None
            if use_cached_time:
                if self._cached_ticks_until_decay_begins > 0:
                    delay_time_span = date_and_time.TimeSpan(self._cached_ticks_until_decay_begins)
                elif self._cached_ticks_until_decay_begins == 0:
                    self.decay_enabled = True
                    return
            if delay_time_span is None:
                delay_time_span = date_and_time.create_time_span(minutes=self.delay_until_decay_is_applied)
            self._decay_alarm_handle = alarms.add_alarm(self, delay_time_span, self._decay_alarm_callback, cross_zone=True)
            self.decay_enabled = False

    def get_bit_for_client(self):
        active_bit = self.get_active_bit()
        if active_bit is None:
            return self._neutral_bit
        return active_bit

    def get_active_bit(self):
        return self._per_instance_data.get_active_bit()

    def _destroy_decay_alarm(self):
        if self._decay_alarm_handle is not None:
            alarms.cancel_alarm(self._decay_alarm_handle)
            self._decay_alarm_handle = None

    def get_saved_ticks_until_decay_begins(self):
        if self.decay_enabled:
            return 0
        if self._decay_alarm_handle:
            return self._decay_alarm_handle.get_remaining_time().in_ticks()
        return self._cached_ticks_until_decay_begins

    def set_time_until_decay_begins(self, ticks_until_decay_begins):
        if self.delay_until_decay_is_applied is None:
            self._cached_ticks_until_decay_begins = ticks_until_decay_begins
            if self._cached_ticks_until_decay_begins != 0.0 and self._cached_ticks_until_decay_begins != -1.0:
                logger.error('Rel Track {} loaded with bad persisted value {}', self, self._cached_ticks_until_decay_begins)
            return
        max_tuning = date_and_time.create_time_span(minutes=self.delay_until_decay_is_applied).in_ticks()
        self._cached_ticks_until_decay_begins = min(ticks_until_decay_begins, max_tuning)
        if self._cached_ticks_until_decay_begins < -1.0:
            logger.error('Rel Track {} loaded with bad persisted value {}', self, self._cached_ticks_until_decay_begins)

    def update_track_index(self, relationship):
        self._per_instance_data.full_load_update(relationship)

class RelationshipTrack(BaseRelationshipTrack, TunedContinuousStatistic, HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.statistic_manager()):
    FRIENDSHIP_TRACK = TunableReference(description='\n        A reference to the friendship track so that the client knows which\n        track is the friendship one.\n        ', manager=services.statistic_manager(), class_restrictions='RelationshipTrack', export_modes=sims4.tuning.tunable_base.ExportModes.ClientBinary)
    FRIENDSHIP_TRACK_FILTER_THRESHOLD = Tunable(description='\n        Value that the client will use when filtering friendship on the Sim\n        Picker.  Sims that have a track value equal to or above this value will\n        be shown with the friendship filter.\n        ', tunable_type=int, default=0, export_modes=ExportModes.ClientBinary)
    ROMANCE_TRACK = TunableReference(description='\n        A reference to the romance track so that the client knows which\n        track is the romance one.\n        ', manager=services.statistic_manager(), class_restrictions='RelationshipTrack', export_modes=ExportModes.All)
    ROMANCE_TRACK_FILTER_THRESHOLD = Tunable(description='\n        Value that the client will use when filtering romance on the Sim\n        Picker.  Sims that have a track value equal to or above this value will\n        be shown with the romance filter.\n        ', tunable_type=int, default=0, export_modes=ExportModes.ClientBinary)
    ROMANCE_TRACK_FILTER_BITS = TunableSet(description='\n        A set of relationship bits that will be used in the Sim Picker for\n        filtering based on romance.  If a Sim has any of these bits then they\n        will be displayed in the Sim Picker when filtering for romance.\n        ', tunable=TunableReference(description='\n            A specific bit used for filtering romance in the Sim Picker.\n            ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), export_modes=ExportModes.ClientBinary)
    FRIENDSHIP_TRACK_FILTER_BITS = TunableSet(description='\n        A set of relationship bits that will be used in the Sim Picker for\n        filtering based on friendship.  If a Sim has any of these bits then\n        they will be displayed in the Sim Picker when filtering for romance.\n        ', tunable=TunableReference(description='\n            A specific bit used for filtering romance in the Sim Picker.\n            ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), export_modes=ExportModes.ClientBinary)
    COWORKER_TRACK_FILTER_BITS = TunableSet(description='\n        A set of relationship bits that will be used in the Sim Picker and\n        the Relationship Panel for filtering sims met through careers.\n        If a Sim has any of these bits then they will be displayed when the\n        filter is active.\n        ', tunable=TunableReference(description='\n            A specific bit used for filtering coworkers in the Sim Picker.\n            ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True), export_modes=ExportModes.ClientBinary)
    SIM_TO_PET_FRIENDSHIP_TRACK = TunablePackSafeReference(description='\n        A reference to the sim_to_pet_friendship track so that the client knows which\n        track is the sim to pet friendship track.\n        ', manager=services.statistic_manager(), class_restrictions='RelationshipTrack', export_modes=ExportModes.ClientBinary)
    SIM_TO_PET_FRIENDSHIP_TRACK_FILTER_THRESHOLD = Tunable(description='\n        Value that the client will use when filtering friendship on the Sim\n        Picker.  Pets that have a track value equal to or above this value will\n        be shown with the friendship filter.\n        ', tunable_type=int, default=0, export_modes=ExportModes.ClientBinary)
    REMOVE_INSTANCE_TUNABLES = ('stat_asm_param', 'persisted_tuning')
    INSTANCE_TUNABLES = {'relationship_obj_prefence_curve': TunableWeightedUtilityCurveAndWeight(description="\n            This curve lets you modify autonomous desire to interact with an \n            object if you have a relationship of this type with the object's\n            crafter.\n            ", tuning_group=GroupNames.SPECIAL_CASES), 'decay_affecting_played_sims': OptionalTunable(description='\n            If enabled, the decay is only enabled if one or both of the sims in\n            the relationship are played sims.\n            ', tunable=TunableTuple(range_decay_threshold=TunableInterval(description='\n                    If relationship value is outside the interval, then decay is\n                    disabled.\n                    ', tunable_type=float, default_lower=-20, default_upper=35)), tuning_group=GroupNames.DECAY), 'species_requirements': OptionalTunable(description='\n            If enabled then this relationship track will have species\n            requirements if it is attempting to be given to a pair of Sims.\n            ', tunable=TunableTuple(description='\n                Two sets of species that determine if a pair of Sims can be given\n                this relationship track.  Each pair of Sims must match themselves\n                to the opposite species lists.\n                Example 1:\n                species_list_one = { HUMAN }\n                species_list_two = { DOG }\n                \n                Will pass if a Human and a Dog Sim are being attempted to give this\n                relationship track.  This will not be allowed if two Humans or two\n                Dogs are attempted to be given this track.\n                \n                Example 2:\n                species_list_one = { HUMAN }\n                species_list_two = { HUMAN, DOG }\n                \n                Will pass for a relationship between two Humans or a Dog and a\n                Human are attempted to be given this track.\n                ', species_list_one=TunableSet(description='\n                    A set of species that one of the Sims must have to be\n                    given this relationship track.\n                    ', tunable=TunableEnumEntry(description='\n                        A species that one of the Sims must have to be given\n                        this relationship track.\n                        ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,))), species_list_two=TunableSet(description='\n                    A set of species that one of the Sims must have to be\n                    given this relationship track.\n                    ', tunable=TunableEnumEntry(description='\n                        A species that one of the Sims must have to be given\n                        this relationship track.\n                        ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)))))}
    bit_data = None

    def __init__(self, tracker):
        super().__init__(tracker)
        self._first_same_sex_relationship_callback_data = None

    @classproperty
    def is_short_term_context(cls):
        return False

    @classproperty
    def decay_only_affects_played_sims(cls):
        return cls.decay_affecting_played_sims is not None

    def on_add(self):
        super().on_add()
        if self._should_initialize_first_same_sex_relationship_callback():
            self._first_same_sex_relationship_callback_data = self.create_and_add_callback_listener(Threshold(sims.global_gender_preference_tuning.GlobalGenderPreferenceTuning.ENABLE_AUTOGENERATION_SAME_SEX_PREFERENCE_THRESHOLD, operator.ge), self._first_same_sex_relationship_callback)

    def on_remove(self, on_destroy=False):
        self.remove_callback_listener(self._first_same_sex_relationship_callback_data)
        super().on_remove(on_destroy=on_destroy)
        self._destroy_decay_alarm()

    def set_value(self, value, *args, headline_icon_modifier=None, **kwargs):
        self._update_value()
        if self.tracker.is_track_locked(self):
            return
        old_value = self._value
        delta = value - old_value
        sim_info_a = self.tracker.rel_data.relationship.find_sim_info_a()
        sim_info_b = self.tracker.rel_data.relationship.find_sim_info_b()
        if sim_info_a is not None and sim_info_b is not None:
            event_manager = services.get_event_manager()
            event_manager.process_event(event_testing.test_events.TestEvent.PrerelationshipChanged, sim_info=sim_info_a, sim_id=sim_info_a.sim_id, target_sim_id=sim_info_b.sim_id)
            event_manager.process_event(event_testing.test_events.TestEvent.PrerelationshipChanged, sim_info=sim_info_b, sim_id=sim_info_b.sim_id, target_sim_id=sim_info_a.sim_id)
        super().set_value(value, *args, **kwargs)
        self._update_visiblity()
        self.reset_decay_alarm()
        self.tracker.rel_data.relationship.send_relationship_info(deltas={self: delta}, headline_icon_modifier=headline_icon_modifier)
        if sim_info_a is not None and sim_info_b is not None:
            event_manager.process_event(event_testing.test_events.TestEvent.RelationshipChanged, sim_info=sim_info_a, sim_id=sim_info_a.sim_id, target_sim_id=sim_info_b.sim_id)
            event_manager.process_event(event_testing.test_events.TestEvent.RelationshipChanged, sim_info=sim_info_b, sim_id=sim_info_b.sim_id, target_sim_id=sim_info_a.sim_id)

    @property
    def is_visible(self):
        return self.visible_to_client

    def apply_social_group_decay(self):
        pass

    def remove_social_group_decay(self):
        pass

    def _on_statistic_modifier_changed(self, notify_watcher=True):
        super()._on_statistic_modifier_changed(notify_watcher=notify_watcher)
        if self._statistic_modifier == 0:
            self.reset_decay_alarm()
        self.tracker.rel_data.relationship.send_relationship_info()

    def _update_visiblity(self):
        if not self.visible_to_client:
            sim_info_manager = services.sim_info_manager()
            sim_info_a = sim_info_manager.get(self.tracker.rel_data.sim_id_a)
            if sim_info_a is None:
                return
            sim_info_b = sim_info_manager.get(self.tracker.rel_data.sim_id_b)
            if sim_info_b is None:
                return
            resolver = DoubleSimResolver(sim_info_a, sim_info_b)
            self.visible_to_client = True if self.visible_test_set.run_tests(resolver) else False

    @staticmethod
    def check_relationship_track_display_priorities(statistic_manager):
        return

    @classmethod
    def type_id(cls):
        return cls.guid64

    @classmethod
    def get_bit_track_node_for_bit(cls, relationship_bit):
        for node in cls.bit_data.bit_track_node_gen():
            if node.bit is relationship_bit:
                return node

    @classmethod
    def bit_track_node_gen(cls):
        for node in cls.bit_data.bit_track_node_gen():
            yield node

    @classmethod
    def get_bit_at_relationship_value(cls, value):
        track_notes = tuple(cls.bit_track_node_gen())
        if value >= 0:
            for bit_node in reversed(track_notes):
                if value >= bit_node.add_value:
                    return bit_node.bit or cls._neutral_bit
        else:
            for bit_node in track_notes:
                if value < bit_node.add_value:
                    return bit_node.bit or cls._neutral_bit
        return cls._neutral_bit

    @classproperty
    def persisted(cls):
        return True

    def get_bit_data_set(self):
        return self._per_instance_data.bit_data_set

    def get_active_bit_by_value(self):
        return self._per_instance_data.get_active_bit_by_value()

    def _decay_alarm_callback(self, handle):
        self._destroy_decay_alarm()
        self.decay_enabled = True
        self._cached_ticks_until_decay_begins = 0
        sim_info_a = self.tracker.rel_data.relationship.find_sim_info_a()
        sim_info_b = self.tracker.rel_data.relationship.find_sim_info_b()
        if sim_info_a is not None and sim_info_b is not None and (sim_info_a.is_selectable or sim_info_b.is_selectable):
            self.tracker.rel_data.relationship.send_relationship_info()

    def _on_add_bit_from_threshold_callback(self, _):
        logger.debug('Track {} is adding its extra bit: {}'.format(self, self._add_bit_on_threshold.bit))
        self.tracker.rel_data.relationship.add_relationship_bit(self.tracker.rel_data.sim_id_a, self.tracker.rel_data.sim_id_b, self._add_bit_on_threshold.bit)

    def _should_initialize_first_same_sex_relationship_callback(self):
        if self.stat_type is not self.ROMANCE_TRACK:
            return False
        if sims.global_gender_preference_tuning.GlobalGenderPreferenceTuning.enable_autogeneration_same_sex_preference:
            return False
        sim_info_a = self.tracker.rel_data.relationship.find_sim_info_a()
        sim_info_b = self.tracker.rel_data.relationship.find_sim_info_b()
        if sim_info_a is None or sim_info_b is None:
            return False
        if sim_info_a.gender is not sim_info_b.gender:
            return False
        elif sim_info_a.is_npc and sim_info_b.is_npc:
            return False
        return True

    def _first_same_sex_relationship_callback(self, _):
        sims.global_gender_preference_tuning.GlobalGenderPreferenceTuning.enable_autogeneration_same_sex_preference = True
        self.remove_callback_listener(self._first_same_sex_relationship_callback_data)
services.get_instance_manager(sims4.resources.Types.STATISTIC).add_on_load_complete(RelationshipTrack.check_relationship_track_display_priorities)
class ShortTermContextRelationshipTrack(RelationshipTrack):
    INSTANCE_TUNABLES = {'socialization_decay_modifier': TunableRange(description='\n            A multiplier to apply to the decay rate if the two Sims that this\n            relationship track applies to are socializing.\n            ', tunable_type=float, default=1, minimum=0, tuning_group=GroupNames.DECAY), 'decay_to_initial_modifier': Tunable(description='\n            If True, this track will converge to the tested modifier calculated\n            at the time the sims last left a social group.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CORE)}

    @classproperty
    def is_short_term_context(cls):
        return True

    def on_add(self):
        super().on_add()
        sim_a = self.tracker.rel_data.relationship.find_sim_a()
        sim_b = self.tracker.rel_data.relationship.find_sim_b()
        if sim_a is not None and sim_b is not None and sim_a.is_in_group_with(sim_b):
            self.apply_social_group_decay()

    def apply_social_group_decay(self):
        if self.socialization_decay_modifier != 1:
            self.add_decay_rate_modifier(self.socialization_decay_modifier)

    def remove_social_group_decay(self):
        if self.socialization_decay_modifier != 1:
            self.remove_decay_rate_modifier(self.socialization_decay_modifier)
        if self.tested_initial_modifier is not None:
            sim_info_a = self.tracker.rel_data.relationship.find_sim_info_a()
            sim_info_b = self.tracker.rel_data.relationship.find_sim_info_b()
            if sim_info_a is None or sim_info_b is None:
                return
            self.convergence_value = self._default_convergence_value + self.tested_initial_modifier.get_max_modifier(DoubleSimResolver(sim_info_a, sim_info_b))
lock_instance_tunables(ShortTermContextRelationshipTrack, visible_test_set=DEFAULT)
class ObjectRelationshipTrack(BaseRelationshipTrack, TunedContinuousStatistic, HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.statistic_manager()):
    OBJECT_BASED_FRIENDSHIP_TRACKS = TunableMapping(description='\n        A mapping of sets of objects with a specific tag to a friendship track.\n        Any value added to the tuned track will apply to all objects within the set.\n        ', key_type=TunableReference(description='\n            This track can be referenced by all objects with the tuned tag.\n            ', manager=services.statistic_manager(), class_restrictions='ObjectRelationshipTrack', pack_safe=True), value_type=TunableReference(description='\n            Tags that define the objects in the track.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TAG_SET), pack_safe=True), tuple_name='ObjectBasedFriendshipTrackTuple', export_modes=ExportModes.All)
    INSTANCE_TUNABLES = {'can_name_object': Tunable(description='\n            If enabled, then the relationship between Sim and an object can be \n            assigned a name by the player, which can be treated as the name\n            of the object(s).\n            ', tunable_type=bool, default=False)}
    bit_data = None

    def on_remove(self, on_destroy=False):
        super().on_remove(on_destroy=on_destroy)
        self._destroy_decay_alarm()

    def set_value(self, value, *args, headline_icon_modifier=None, **kwargs):
        self._update_value()
        if self.tracker.is_track_locked(self):
            return
        old_value = self._value
        delta = value - old_value
        super().set_value(value, *args, **kwargs)
        self._update_visiblity()
        self.reset_decay_alarm()
        self.tracker.rel_data.relationship.send_object_relationship_info(deltas={self: delta}, headline_icon_modifier=headline_icon_modifier)

    def set_name_override(self, name_override_obj):
        self.tracker.rel_data.relationship.send_object_relationship_info(name_override_obj=name_override_obj)

    def _update_visiblity(self):
        if not self.visible_to_client:
            sim_info_manager = services.sim_info_manager()
            sim_info_a = sim_info_manager.get(self.tracker.rel_data.sim_id_a)
            if sim_info_a is None:
                return
            resolver = SingleSimResolver(sim_info_a)
            self.visible_to_client = True if self.visible_test_set.run_tests(resolver) else False

    @classmethod
    def get_object_definitions(cls, track):
        tags = cls.OBJECT_BASED_FRIENDSHIP_TRACKS[track]
        return services.definition_manager().get_definitions_for_tags_gen(tags.tags)
