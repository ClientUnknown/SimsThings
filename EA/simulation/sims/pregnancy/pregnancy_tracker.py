import itertoolsimport operatorimport randomfrom protocolbuffers import SimObjectAttributes_pb2from event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableGlobalTestSetfrom objects import ALL_HIDDEN_REASONSfrom relationships.relationship_bit import RelationshipBitfrom relationships.relationship_tracker_tuning import DefaultGenealogyLinkfrom services.relgraph_service import RelgraphServicefrom sims.aging.aging_tuning import AgingTuningfrom sims.pregnancy.pregnancy_enums import PregnancyOriginfrom sims.pregnancy.pregnancy_offspring_data import PregnancyOffspringDatafrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.sim_info_types import Gender, Speciesfrom sims.sim_spawner import SimCreator, SimSpawnerfrom sims4.common import Pack, is_available_packfrom sims4.math import MAX_UINT32, EPSILONfrom sims4.random import pop_weightedfrom sims4.tuning.tunable import TunableReference, TunableMapping, TunableTuple, TunableSet, TunableEnumEntry, TunableList, Tunable, OptionalTunable, TunablePercent, TunableRangefrom traits.traits import Trait, get_possible_traitsfrom tunable_multiplier import TunableMultiplierfrom ui.screen_slam import TunableScreenSlamSnippetfrom ui.ui_dialog import UiDialogOkimport alarmsimport clockimport servicesimport sims4.loglogger = sims4.log.Logger('Pregnancy', default_owner='epanero')
class PregnancyTracker(SimInfoTracker):
    PREGNANCY_COMMODITY_MAP = TunableMapping(description='\n        The commodity to award if conception is successful.\n        ', key_type=TunableEnumEntry(description='\n            Species these commodities are intended for.\n            ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunableReference(description='\n            The commodity reference controlling pregnancy.\n            ', pack_safe=True, manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)))
    PREGNANCY_TRAIT = TunableReference(description='\n        The trait that all pregnant Sims have during pregnancy.\n        ', manager=services.trait_manager())
    PREGNANCY_ORIGIN_TRAIT_MAPPING = TunableMapping(description='\n        A mapping from PregnancyOrigin to a set of traits to be added at the\n        start of the pregnancy, and removed at the end of the pregnancy.\n        ', key_type=PregnancyOrigin, value_type=TunableTuple(description='\n            A tuple of the traits that should be added/removed with a pregnancy\n            that has this origin, and the content pack they are associated with.\n            ', traits=TunableSet(description='\n                The traits to be added/removed.\n                ', tunable=Trait.TunablePackSafeReference()), pack=TunableEnumEntry(description='\n                The content pack associated with this set of traits. If the pack\n                is uninstalled, the pregnancy will be auto-completed.\n                ', tunable_type=Pack, default=Pack.BASE_GAME)))
    PREGNANCY_RATE = TunableRange(description='\n        The rate per Sim minute of pregnancy.\n        ', tunable_type=float, default=0.001, minimum=EPSILON)
    MULTIPLE_OFFSPRING_CHANCES = TunableList(description='\n        A list defining the probabilities of multiple births.\n        ', tunable=TunableTuple(size=Tunable(description='\n                The number of offspring born.\n                ', tunable_type=int, default=1), weight=Tunable(description='\n                The weight, relative to other outcomes.\n                ', tunable_type=float, default=1), npc_dialog=UiDialogOk.TunableFactory(description='\n                A dialog displayed when a NPC Sim gives birth to an offspring\n                that was conceived by a currently player-controlled Sim. The\n                dialog is specifically used when this number of offspring is\n                generated.\n                \n                Three tokens are passed in: the two parent Sims and the\n                offspring\n                ', locked_args={'text_tokens': None}), modifiers=TunableMultiplier.TunableFactory(description='\n                A tunable list of test sets and associated multipliers to apply\n                to the total chance of this number of potential offspring.\n                '), screen_slam_one_parent=OptionalTunable(description='\n                Screen slam to show when only one parent is available.\n                Localization Tokens: Sim A - {0.SimFirstName}\n                ', tunable=TunableScreenSlamSnippet()), screen_slam_two_parents=OptionalTunable(description='\n                Screen slam to show when both parents are available.\n                Localization Tokens: Sim A - {0.SimFirstName}, Sim B -\n                {1.SimFirstName}\n                ', tunable=TunableScreenSlamSnippet())))
    MONOZYGOTIC_OFFSPRING_CHANCE = TunablePercent(description='\n        The chance that each subsequent offspring of a multiple birth has the\n        same genetics as the first offspring.\n        ', default=50)
    GENDER_CHANCE_STAT = TunableReference(description='\n        A commodity that determines the chance that an offspring is female. The\n        minimum value guarantees the offspring is male, whereas the maximum\n        value guarantees it is female.\n        ', manager=services.statistic_manager())
    BIRTHPARENT_BIT = RelationshipBit.TunableReference(description='\n        The bit that is added on the relationship from the Sim to any of its\n        offspring.\n        ')
    AT_BIRTH_TESTS = TunableGlobalTestSet(description='\n        Tests to run between the pregnant sim and their partner, at the time of\n        birth. If any test fails, the the partner sim will not be set as the\n        other parent. This is intended to prevent modifications to the partner\n        sim during the time between impregnation and birth that would make the\n        partner sim an invalid parent (age too young, relationship incestuous, etc).\n        ')
    PREGNANCY_ORIGIN_MODIFIERS = TunableMapping(description='\n        Define any modifiers that, given the origination of the pregnancy,\n        affect certain aspects of the generated offspring.\n        ', key_type=TunableEnumEntry(description='\n            The origin of the pregnancy.\n            ', tunable_type=PregnancyOrigin, default=PregnancyOrigin.DEFAULT, pack_safe=True), value_type=TunableTuple(description='\n            The aspects of the pregnancy modified specifically for the specified\n            origin.\n            ', default_relationships=TunableTuple(description='\n                Override default relationships for the parents.\n                ', father_override=OptionalTunable(description='\n                    If set, override default relationships for the father.\n                    ', tunable=TunableEnumEntry(description='\n                        The default relationships for the father.\n                        ', tunable_type=DefaultGenealogyLink, default=DefaultGenealogyLink.FamilyMember)), mother_override=OptionalTunable(description='\n                    If set, override default relationships for the mother.\n                    ', tunable=TunableEnumEntry(description='\n                        The default relationships for the mother.\n                        ', tunable_type=DefaultGenealogyLink, default=DefaultGenealogyLink.FamilyMember))), trait_entries=TunableList(description='\n                Sets of traits that might be randomly applied to each generated\n                offspring. Each group is individually randomized.\n                ', tunable=TunableTuple(description='\n                    A set of random traits. Specify a chance that a trait from\n                    the group is selected, and then specify a set of traits.\n                    Only one trait from this group may be selected. If the\n                    chance is less than 100%, no traits could be selected.\n                    ', chance=TunablePercent(description='\n                        The chance that a trait from this set is selected.\n                        ', default=100), traits=TunableList(description='\n                        The set of traits that might be applied to each\n                        generated offspring. Specify a weight for each trait\n                        compared to other traits in the same set.\n                        ', tunable=TunableTuple(description='\n                            A weighted trait that might be applied to the\n                            generated offspring. The weight is relative to other\n                            entries within the same set.\n                            ', weight=Tunable(description='\n                                The relative weight of this trait compared to\n                                other traits within the same set.\n                                ', tunable_type=float, default=1), trait=Trait.TunableReference(description='\n                                A trait that might be applied to the generated\n                                offspring.\n                                ', pack_safe=True)))))))

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._clear_pregnancy_data()
        self._completion_callback_listener = None
        self._completion_alarm_handle = None

    @property
    def account(self):
        return self._sim_info.account

    @property
    def is_pregnant(self):
        if self._seed:
            return True
        return False

    @property
    def offspring_count(self):
        return max(len(self._offspring_data), 1)

    @property
    def offspring_count_override(self):
        return self._offspring_count_override

    @offspring_count_override.setter
    def offspring_count_override(self, value):
        self._offspring_count_override = value

    def _get_parent(self, sim_id):
        sim_info_manager = services.sim_info_manager()
        if sim_id in sim_info_manager:
            return sim_info_manager.get(sim_id)

    def get_parents(self):
        if self._parent_ids:
            parent_a = self._get_parent(self._parent_ids[0])
            parent_b = self._get_parent(self._parent_ids[1]) or parent_a
            return (parent_a, parent_b)
        return (None, None)

    def get_partner(self):
        (owner, partner) = self.get_parents()
        if partner is not owner:
            return partner

    def start_pregnancy(self, parent_a, parent_b, pregnancy_origin=PregnancyOrigin.DEFAULT):
        if self.is_pregnant:
            return
        if not parent_a.incest_prevention_test(parent_b):
            return
        self._seed = random.randint(1, MAX_UINT32)
        self._parent_ids = (parent_a.id, parent_b.id)
        self._offspring_data = []
        self._origin = pregnancy_origin
        self.enable_pregnancy()

    def enable_pregnancy(self):
        if not self._is_enabled:
            pregnancy_commodity_type = self.PREGNANCY_COMMODITY_MAP.get(self._sim_info.species)
            tracker = self._sim_info.get_tracker(pregnancy_commodity_type)
            pregnancy_commodity = tracker.get_statistic(pregnancy_commodity_type, add=True)
            pregnancy_commodity.add_statistic_modifier(self.PREGNANCY_RATE)
            threshold = sims4.math.Threshold(pregnancy_commodity.max_value, operator.ge)
            self._completion_callback_listener = tracker.create_and_add_listener(pregnancy_commodity.stat_type, threshold, self._on_pregnancy_complete)
            if threshold.compare(pregnancy_commodity.get_value()):
                self._on_pregnancy_complete()
            tracker = self._sim_info.get_tracker(self.GENDER_CHANCE_STAT)
            tracker.add_statistic(self.GENDER_CHANCE_STAT)
            self._sim_info.add_trait(self.PREGNANCY_TRAIT)
            traits_pack_tuple = self.PREGNANCY_ORIGIN_TRAIT_MAPPING.get(self._origin)
            if traits_pack_tuple is not None:
                for trait in traits_pack_tuple.traits:
                    self._sim_info.add_trait(trait)
            self._is_enabled = True

    def _on_pregnancy_complete(self, *_, **__):
        if not self.is_pregnant:
            return
        if self._sim_info.is_npc:
            current_zone = services.current_zone()
            if current_zone.is_zone_running and self._sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if self._completion_alarm_handle is None:
                    self._completion_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(1), self._on_pregnancy_complete, repeating=True, cross_zone=True)
            else:
                self._create_and_name_offspring()
                self._show_npc_dialog()
                self.clear_pregnancy()

    def complete_pregnancy(self):
        services.get_event_manager().process_event(TestEvent.OffspringCreated, sim_info=self._sim_info, offspring_created=self.offspring_count)
        for tuning_data in self.MULTIPLE_OFFSPRING_CHANCES:
            if tuning_data.size == self.offspring_count:
                (parent_a, parent_b) = self.get_parents()
                if parent_a is parent_b:
                    screen_slam = tuning_data.screen_slam_one_parent
                else:
                    screen_slam = tuning_data.screen_slam_two_parents
                if screen_slam is not None:
                    screen_slam.send_screen_slam_message(self._sim_info, parent_a, parent_b)
                break

    def _clear_pregnancy_data(self):
        self._seed = 0
        self._parent_ids = []
        self._offspring_data = []
        self._offspring_count_override = None
        self._origin = PregnancyOrigin.DEFAULT
        self._is_enabled = False

    def clear_pregnancy_visuals(self):
        if self._sim_info.pregnancy_progress:
            self._sim_info.pregnancy_progress = 0

    def clear_pregnancy(self):
        pregnancy_commodity_type = self.PREGNANCY_COMMODITY_MAP.get(self._sim_info.species)
        tracker = self._sim_info.get_tracker(pregnancy_commodity_type)
        if tracker is not None:
            stat = tracker.get_statistic(pregnancy_commodity_type, add=True)
            if stat is not None:
                stat.set_value(stat.min_value)
                stat.remove_statistic_modifier(self.PREGNANCY_RATE)
            if self._completion_callback_listener is not None:
                tracker.remove_listener(self._completion_callback_listener)
                self._completion_callback_listener = None
        tracker = self._sim_info.get_tracker(self.GENDER_CHANCE_STAT)
        if tracker is not None:
            tracker.remove_statistic(self.GENDER_CHANCE_STAT)
        if self._sim_info.has_trait(self.PREGNANCY_TRAIT):
            self._sim_info.remove_trait(self.PREGNANCY_TRAIT)
        traits_pack_tuple = self.PREGNANCY_ORIGIN_TRAIT_MAPPING.get(self._origin)
        if traits_pack_tuple is not None:
            for trait in traits_pack_tuple.traits:
                if self._sim_info.has_trait(trait):
                    self._sim_info.remove_trait(trait)
        if self._completion_alarm_handle is not None:
            alarms.cancel_alarm(self._completion_alarm_handle)
            self._completion_alarm_handle = None
        self.clear_pregnancy_visuals()
        self._clear_pregnancy_data()

    def _create_and_name_offspring(self, on_create=None):
        self.create_offspring_data()
        for offspring_data in self.get_offspring_data_gen():
            offspring_data.first_name = self._get_random_first_name(offspring_data)
            sim_info = self.create_sim_info(offspring_data)
            if on_create is not None:
                on_create(sim_info)

    def validate_partner(self):
        impregnator = self.get_partner()
        if impregnator is None:
            return
        resolver = DoubleSimResolver(self._sim_info, impregnator)
        if not self.AT_BIRTH_TESTS.run_tests(resolver):
            self._parent_ids = (self._sim_info.id, self._sim_info.id)

    def create_sim_info(self, offspring_data):
        self.validate_partner()
        (parent_a, parent_b) = self.get_parents()
        sim_creator = SimCreator(age=offspring_data.age, gender=offspring_data.gender, species=offspring_data.species, first_name=offspring_data.first_name, last_name=offspring_data.last_name)
        household = self._sim_info.household
        zone_id = household.home_zone_id
        (sim_info_list, _) = SimSpawner.create_sim_infos((sim_creator,), household=household, account=self.account, zone_id=zone_id, generate_deterministic_sim=True, creation_source='pregnancy')
        sim_info = sim_info_list[0]
        sim_info.world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
        for trait in tuple(sim_info.trait_tracker.personality_traits):
            sim_info.remove_trait(trait)
        for trait in offspring_data.traits:
            sim_info.add_trait(trait)
        sim_info.apply_genetics(parent_a, parent_b, seed=offspring_data.genetics)
        sim_info.resend_extended_species()
        sim_info.resend_physical_attributes()
        default_track_overrides = {}
        mother = parent_a if parent_a.gender == Gender.FEMALE else parent_b
        father = parent_a if parent_a.gender == Gender.MALE else parent_b
        if self._origin in self.PREGNANCY_ORIGIN_MODIFIERS:
            father_override = self.PREGNANCY_ORIGIN_MODIFIERS[self._origin].default_relationships.father_override
            if father_override is not None:
                default_track_overrides[father] = father_override
            mother_override = self.PREGNANCY_ORIGIN_MODIFIERS[self._origin].default_relationships.mother_override
            if mother_override is not None:
                default_track_overrides[mother] = mother_override
        self.initialize_sim_info(sim_info, parent_a, parent_b, default_track_overrides=default_track_overrides)
        self._sim_info.relationship_tracker.add_relationship_bit(sim_info.id, self.BIRTHPARENT_BIT)
        return sim_info

    @staticmethod
    def initialize_sim_info(sim_info, parent_a, parent_b, default_track_overrides=None):
        sim_info.add_parent_relations(parent_a, parent_b)
        if sim_info.household is not parent_a.household:
            parent_a.household.add_sim_info_to_household(sim_info)
        sim_info.set_default_relationships(reciprocal=True, default_track_overrides=default_track_overrides)
        services.sim_info_manager().set_default_genealogy(sim_infos=(sim_info,))
        parent_generation = max(parent_a.generation, parent_b.generation if parent_b is not None else 0)
        sim_info.generation = parent_generation + 1 if sim_info.is_played_sim else parent_generation
        services.get_event_manager().process_event(TestEvent.GenerationCreated, sim_info=sim_info)
        client = services.client_manager().get_client_by_household_id(sim_info.household_id)
        if client is not None:
            client.add_selectable_sim_info(sim_info)
        parent_b_sim_id = parent_b.sim_id if parent_b is not None else 0
        RelgraphService.relgraph_add_child(parent_a.sim_id, parent_b_sim_id, sim_info.sim_id)

    @classmethod
    def select_traits_for_offspring(cls, offspring_data, parent_a, parent_b, num_traits, origin=PregnancyOrigin.DEFAULT, random=random):
        traits = []
        personality_trait_slots = num_traits

        def _add_trait_if_possible(selected_trait):
            nonlocal personality_trait_slots
            if selected_trait in traits:
                return False
            if any(t.is_conflicting(selected_trait) for t in traits):
                return False
            if selected_trait.is_personality_trait:
                if not personality_trait_slots:
                    return False
                personality_trait_slots -= 1
            traits.append(selected_trait)
            return True

        if origin in cls.PREGNANCY_ORIGIN_MODIFIERS:
            trait_entries = cls.PREGNANCY_ORIGIN_MODIFIERS[origin].trait_entries
            for trait_entry in trait_entries:
                if random.random() >= trait_entry.chance:
                    pass
                else:
                    selected_trait = pop_weighted([(t.weight, t.trait) for t in trait_entry.traits if t.trait.is_valid_trait(offspring_data)], random=random)
                    if selected_trait is not None:
                        _add_trait_if_possible(selected_trait)
        if parent_b is not None:
            for inherited_trait_entries in parent_a.trait_tracker.get_inherited_traits(parent_b):
                selected_trait = pop_weighted(list(inherited_trait_entries), random=random)
                if selected_trait is not None:
                    _add_trait_if_possible(selected_trait)
        if not (parent_a is not None and personality_trait_slots):
            return traits
        personality_traits = get_possible_traits(offspring_data)
        random.shuffle(personality_traits)
        while True:
            current_trait = personality_traits.pop()
            if _add_trait_if_possible(current_trait):
                break
            if not personality_traits:
                return traits
        if not personality_trait_slots:
            return traits
        traits_a = set(parent_a.trait_tracker.personality_traits)
        traits_b = set(parent_b.trait_tracker.personality_traits)
        shared_parent_traits = list(traits_a.intersection(traits_b) - set(traits))
        random.shuffle(shared_parent_traits)
        while personality_trait_slots and shared_parent_traits:
            current_trait = shared_parent_traits.pop()
            if current_trait in personality_traits:
                personality_traits.remove(current_trait)
            did_add_trait = _add_trait_if_possible(current_trait)
            if did_add_trait and not personality_trait_slots:
                return traits
        remaining_parent_traits = list(traits_a.symmetric_difference(traits_b) - set(traits))
        random.shuffle(remaining_parent_traits)
        while personality_trait_slots and remaining_parent_traits:
            current_trait = remaining_parent_traits.pop()
            if current_trait in personality_traits:
                personality_traits.remove(current_trait)
            did_add_trait = _add_trait_if_possible(current_trait)
            if did_add_trait and not personality_trait_slots:
                return traits
        while personality_trait_slots and personality_traits:
            current_trait = personality_traits.pop()
            _add_trait_if_possible(current_trait)
        return traits

    def create_offspring_data(self):
        r = random.Random()
        r.seed(self._seed)
        if self._offspring_count_override is not None:
            offspring_count = self._offspring_count_override
        else:
            offspring_count = pop_weighted([(p.weight*p.modifiers.get_multiplier(SingleSimResolver(self._sim_info)), p.size) for p in self.MULTIPLE_OFFSPRING_CHANCES], random=r)
        offspring_count = min(self._sim_info.household.free_slot_count + 1, offspring_count)
        species = self._sim_info.species
        age = self._sim_info.get_birth_age()
        aging_data = AgingTuning.get_aging_data(species)
        num_personality_traits = aging_data.get_personality_trait_count(age)
        self._offspring_data = []
        for offspring_index in range(offspring_count):
            if offspring_index and r.random() < self.MONOZYGOTIC_OFFSPRING_CHANCE:
                gender = self._offspring_data[offspring_index - 1].gender
                genetics = self._offspring_data[offspring_index - 1].genetics
            else:
                gender_chance_stat = self._sim_info.get_statistic(self.GENDER_CHANCE_STAT)
                if gender_chance_stat is None:
                    gender_chance = 0.5
                else:
                    gender_chance = (gender_chance_stat.get_value() - gender_chance_stat.min_value)/(gender_chance_stat.max_value - gender_chance_stat.min_value)
                gender = Gender.FEMALE if r.random() < gender_chance else Gender.MALE
                genetics = r.randint(1, MAX_UINT32)
            last_name = SimSpawner.get_last_name(self._sim_info.last_name, gender, species)
            offspring_data = PregnancyOffspringData(age, gender, species, genetics, last_name=last_name)
            (parent_a, parent_b) = self.get_parents()
            offspring_data.traits = self.select_traits_for_offspring(offspring_data, parent_a, parent_b, num_personality_traits, origin=self._origin)
            self._offspring_data.append(offspring_data)

    def get_offspring_data_gen(self):
        for offspring_data in self._offspring_data:
            yield offspring_data

    def _get_random_first_name(self, offspring_data):
        tries_left = 10

        def is_valid(first_name):
            nonlocal tries_left
            if not first_name:
                return False
            tries_left -= 1
            if tries_left and any(sim.first_name == first_name for sim in self._sim_info.household):
                return False
            elif any(sim.first_name == first_name for sim in self._offspring_data):
                return False
            return True

        first_name = None
        while not is_valid(first_name):
            first_name = SimSpawner.get_random_first_name(offspring_data.gender, offspring_data.species)
        return first_name

    def assign_random_first_names_to_offspring_data(self):
        for offspring_data in self.get_offspring_data_gen():
            offspring_data.first_name = self._get_random_first_name(offspring_data)

    def _show_npc_dialog(self):
        for tuning_data in self.MULTIPLE_OFFSPRING_CHANCES:
            if tuning_data.size == self.offspring_count:
                npc_dialog = tuning_data.npc_dialog
                if npc_dialog is not None:
                    for parent in self.get_parents():
                        if parent is None:
                            logger.error('Pregnancy for {} has a None parent for IDs {}. Please file a DT with a save attached.', self._sim_info, ','.join(str(parent_id) for parent_id in self._parent_ids))
                            return
                        parent_instance = parent.get_sim_instance()
                        if parent_instance is not None and parent_instance.client is not None:
                            additional_tokens = list(itertools.chain(self.get_parents(), self._offspring_data))
                            dialog = npc_dialog(parent_instance, DoubleSimResolver(additional_tokens[0], additional_tokens[1]))
                            dialog.show_dialog(additional_tokens=additional_tokens)
                return

    def save(self):
        data = SimObjectAttributes_pb2.PersistablePregnancyTracker()
        data.seed = self._seed
        data.origin = self._origin
        data.parent_ids.extend(self._parent_ids)
        return data

    def load(self, data):
        self._seed = int(data.seed)
        try:
            self._origin = PregnancyOrigin(data.origin)
        except KeyError:
            self._origin = PregnancyOrigin.DEFAULT
        self._parent_ids.clear()
        self._parent_ids.extend(data.parent_ids)

    def refresh_pregnancy_data(self, on_create=None):
        if not self.is_pregnant:
            self.clear_pregnancy()
            return
        traits_pack_tuple = self.PREGNANCY_ORIGIN_TRAIT_MAPPING.get(self._origin)
        if traits_pack_tuple is not None and not is_available_pack(traits_pack_tuple.pack):
            self._create_and_name_offspring(on_create=on_create)
            self.clear_pregnancy()
        self.enable_pregnancy()

    def on_lod_update(self, old_lod, new_lod):
        if new_lod == SimInfoLODLevel.MINIMUM:
            self.clear_pregnancy()
