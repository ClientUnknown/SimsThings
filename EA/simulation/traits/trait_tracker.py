import itertoolsimport operatorimport randomfrom protocolbuffers import Commodities_pb2from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom interactions.base.picker_interaction import PickerSuperInteractionfrom objects import ALL_HIDDEN_REASONSfrom objects.mixins import AffordanceCacheMixin, ProvidedAffordanceDatafrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.sim_info_types import Gender, Species, SpeciesExtendedfrom sims.sim_info_utils import apply_super_affordance_commodity_flags, remove_super_affordance_commodity_flagsfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableMapping, TunableEnumEntry, TunableList, TunableTuple, TunableSet, OptionalTunablefrom sims4.utils import flexmethod, classpropertyfrom statistics.commodity_messages import send_sim_commodity_list_update_messagefrom traits.trait_day_night_tracking import DayNightTrackingStatefrom traits.trait_quirks import add_quirksfrom traits.traits import logger, Traitfrom traits.trait_type import TraitTypefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom ui.ui_dialog_picker import ObjectPickerRowfrom vfx.vfx_mask import generate_mask_messageimport game_servicesimport servicesimport sims.ghostimport sims4.telemetryimport telemetry_helperTELEMETRY_GROUP_TRAITS = 'TRAT'TELEMETRY_HOOK_ADD_TRAIT = 'TADD'TELEMETRY_HOOK_REMOVE_TRAIT = 'TRMV'TELEMETRY_FIELD_TRAIT_ID = 'idtr'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_TRAITS)
class HasTraitTrackerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def trait_tracker(self):
        return self._trait_tracker

    def add_trait(self, *args, **kwargs):
        return self._trait_tracker._add_trait(*args, **kwargs)

    def get_traits(self):
        return self._trait_tracker.equipped_traits

    def has_trait(self, *args, **kwargs):
        return self._trait_tracker.has_trait(*args, **kwargs)

    def remove_trait(self, *args, **kwargs):
        return self._trait_tracker._remove_trait(*args, **kwargs)

    def get_initial_commodities(self):
        initial_commodities = set()
        blacklisted_commodities = set()
        for trait in self._trait_tracker:
            initial_commodities.update(trait.initial_commodities)
            blacklisted_commodities.update(trait.initial_commodities_blacklist)
        initial_commodities -= blacklisted_commodities
        return frozenset(initial_commodities)

    def on_all_traits_loaded(self):
        pass

    def _get_trait_ids(self):
        return self._trait_tracker.trait_ids

class TraitTracker(AffordanceCacheMixin, SimInfoTracker):
    GENDER_TRAITS = TunableMapping(description='\n        A mapping from gender to trait. Any Sim with the specified gender will\n        have the corresponding gender trait.\n        ', key_type=TunableEnumEntry(description="\n            The Sim's gender.\n            ", tunable_type=Gender, default=Gender.MALE), value_type=Trait.TunableReference(description='\n            The trait associated with the specified gender.\n            '))
    DEFAULT_GENDER_OPTION_TRAITS = TunableMapping(description="\n        A mapping from gender to default gender option traits. After loading the\n        sim's trait tracker, if no gender option traits are found (e.g. loading\n        a save created prior to them being added), the tuned gender option traits\n        for the sim's gender will be added.\n        ", key_type=TunableEnumEntry(description="\n            The Sim's gender.\n            ", tunable_type=Gender, default=Gender.MALE), value_type=TunableSet(description='\n            The default gender option traits to be added for this gender.\n            ', tunable=Trait.TunableReference(pack_safe=True)))
    SPECIES_TRAITS = TunableMapping(description='\n        A mapping from species to trait. Any Sim of the specified species will\n        have the corresponding species trait.\n        ', key_type=TunableEnumEntry(description="\n            The Sim's species.\n            ", tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=Trait.TunableReference(description='\n            The trait associated with the specified species.\n            ', pack_safe=True))
    SPECIES_EXTENDED_TRAITS = TunableMapping(description='\n        A mapping from extended species to trait. Any Sim of the specified \n        extended species will have the corresponding extended species trait.\n        ', key_type=TunableEnumEntry(description="\n            The Sim's extended species.\n            ", tunable_type=SpeciesExtended, default=SpeciesExtended.SMALLDOG, invalid_enums=(SpeciesExtended.INVALID,)), value_type=Trait.TunableReference(description='\n            The trait associated with the specified extended species.\n            ', pack_safe=True))
    TRAIT_INHERITANCE = TunableList(description='\n        Define how specific traits are transferred to offspring. Define keys of\n        sets of traits resulting in the assignment of another trait, weighted\n        against other likely outcomes.\n        ', tunable=TunableTuple(description='\n            A set of trait requirements and outcomes. Please note that inverted\n            requirements are not necessary. The game will automatically swap\n            parents A and B to try to fulfill the constraints.\n            \n            e.g. Alien Inheritance\n                Alien inheritance follows a simple set of rules:\n                 Alien+Alien always generates aliens\n                 Alien+None always generates part aliens\n                 Alien+PartAlien generates either aliens or part aliens\n                 PartAlien+PartAlien generates either aliens, part aliens, or regular Sims\n                 PartAlien+None generates either part aliens or regular Sims\n                 \n                Given the specifications involving "None", we need to probably\n                blacklist the two traits to detect a case where only one of the\n                two parents has a meaningful trait:\n                \n                a_whitelist = Alien\n                b_whitelist = Alien\n                outcome = Alien\n                \n                a_whitelist = Alien\n                b_blacklist = Alien,PartAlien\n                outcome = PartAlien\n                \n                etc...\n            ', parent_a_whitelist=TunableList(description='\n                Parent A must have ALL these traits in order to generate this\n                outcome.\n                ', tunable=Trait.TunableReference(pack_safe=True)), parent_a_blacklist=TunableList(description='\n                Parent A must not have ANY of these traits in order to generate this\n                outcome.\n                ', tunable=Trait.TunableReference(pack_safe=True)), parent_b_whitelist=TunableList(description='\n                Parent B must have ALL these traits in order to generate this\n                outcome.\n                ', tunable=Trait.TunableReference(pack_safe=True)), parent_b_blacklist=TunableList(description='\n                Parent B must not have ANY of these traits in order to generate this\n                outcome.\n                ', tunable=Trait.TunableReference(pack_safe=True)), outcomes=TunableList(description='\n                A weighted list of potential outcomes given that the\n                requirements have been satisfied.\n                ', tunable=TunableTuple(description='\n                    A weighted outcome. The weight is relative to other entries\n                    within this outcome set.\n                    ', weight=Tunable(description='\n                        The relative weight of this outcome versus other\n                        outcomes in this same set.\n                        ', tunable_type=float, default=1), trait=Trait.TunableReference(description='\n                        The potential inherited trait.\n                        ', allow_none=True, pack_safe=True)))))

    def __init__(self, sim_info):
        super().__init__()
        self._sim_info = sim_info
        self._sim_info.on_base_characteristic_changed.append(self.add_auto_traits)
        self._equipped_traits = set()
        self._unlocked_equip_slot = 0
        self._buff_handles = {}
        self.trait_vfx_mask = 0
        self._hiding_relationships = False
        self._day_night_state = None
        self._load_in_progress = False

    def __iter__(self):
        return self._equipped_traits.__iter__()

    def __len__(self):
        return len(self._equipped_traits)

    def can_add_trait(self, trait):
        if not self._has_valid_lod(trait):
            return False
        if self.has_trait(trait):
            logger.info('Trying to equip an existing trait {} for Sim {}', trait, self._sim_info)
            return False
        if trait.is_personality_trait and self.empty_slot_number == 0:
            logger.info('Reach max equipment slot number {} for Sim {}', self.equip_slot_number, self._sim_info)
            return False
        if not trait.is_valid_trait(self._sim_info):
            logger.info("Trying to equip a trait {} that conflicts with Sim {}'s age {} or gender {}", trait, self._sim_info, self._sim_info.age, self._sim_info.gender)
            return False
        elif self.is_conflicting(trait):
            logger.info('Trying to equip a conflicting trait {} for Sim {}', trait, self._sim_info)
            return False
        return True

    def add_auto_traits(self):
        for trait in itertools.chain(self.GENDER_TRAITS.values(), self.SPECIES_TRAITS.values(), self.SPECIES_EXTENDED_TRAITS.values()):
            if self.has_trait(trait):
                self._remove_trait(trait)
        auto_traits = (self.GENDER_TRAITS.get(self._sim_info.gender), self.SPECIES_TRAITS.get(self._sim_info.species), self.SPECIES_EXTENDED_TRAITS.get(self._sim_info.extended_species))
        for trait in auto_traits:
            if trait is None:
                pass
            else:
                self._add_trait(trait)

    def remove_invalid_traits(self):
        for trait in tuple(self._equipped_traits):
            if not trait.is_valid_trait(self._sim_info):
                self._sim_info.remove_trait(trait)

    def sort_and_send_commodity_list(self):
        if not self._sim_info.is_selectable:
            return
        final_list = []
        commodities = self._sim_info.get_initial_commodities()
        for trait in self._equipped_traits:
            if not trait.ui_commodity_sort_override:
                pass
            else:
                final_list = [override_commodity for override_commodity in trait.ui_commodity_sort_override if override_commodity in commodities]
                break
        if not final_list:
            final_list = sorted(commodities, key=operator.attrgetter('ui_sort_order'))
        self._send_commodity_list_msg(final_list)

    def _send_commodity_list_msg(self, commodity_list):
        list_msg = Commodities_pb2.CommodityListUpdate()
        list_msg.sim_id = self._sim_info.sim_id
        for commodity in commodity_list:
            stat = self._sim_info.commodity_tracker.get_statistic(commodity)
            if stat and stat.is_visible_commodity():
                with ProtocolBufferRollback(list_msg.commodities) as commodity_msg:
                    stat.populate_commodity_update_msg(commodity_msg, is_rate_change=False)
        send_sim_commodity_list_update_message(self._sim_info, list_msg)

    def _update_initial_commodities(self, trait, previous_initial_commodities):
        should_update_commodity_ui = False
        current_initial_commodities = self._sim_info.get_initial_commodities()
        commodities_to_remove = previous_initial_commodities - current_initial_commodities
        for commodity_to_remove in commodities_to_remove:
            commodity_inst = self._sim_info.commodity_tracker.get_statistic(commodity_to_remove)
            if commodity_inst.is_visible_commodity():
                should_update_commodity_ui = True
            commodity_inst.core = False
            self._sim_info.commodity_tracker.remove_statistic(commodity_to_remove)
        commodities_to_add = current_initial_commodities - previous_initial_commodities
        for commodity_to_add in commodities_to_add:
            commodity_inst = self._sim_info.commodity_tracker.add_statistic(commodity_to_add)
            commodity_inst.core = True
            if should_update_commodity_ui or commodity_inst.is_visible_commodity():
                should_update_commodity_ui = True
        if should_update_commodity_ui:
            self.sort_and_send_commodity_list()

    def _add_trait(self, trait, from_load=False):
        if not self.can_add_trait(trait):
            return False
        initial_commodities_modified = trait.initial_commodities or trait.initial_commodities_blacklist
        if initial_commodities_modified:
            previous_initial_commodities = self._sim_info.get_initial_commodities()
        self._equipped_traits.add(trait)
        if initial_commodities_modified:
            self._update_initial_commodities(trait, previous_initial_commodities)
        if trait.buffs_add_on_spawn_only and self._sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            try:
                self._add_buffs(trait)
            except Exception as e:
                logger.exception('Error adding buffs while adding trait: {0}. {1}.', trait.__name__, e, owner='asantos')
        self._add_vfx_mask(trait, send_op=not from_load)
        self._add_day_night_tracking(trait)
        self.update_trait_effects()
        if trait.is_ghost_trait:
            sims.ghost.Ghost.enable_ghost_routing(self._sim_info)
        if trait.disable_aging:
            self._sim_info.update_age_callbacks()
        sim = self._sim_info.get_sim_instance()
        provided_affordances = []
        for provided_affordance in trait.target_super_affordances:
            provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
            provided_affordances.append(provided_affordance_data)
        self.add_to_affordance_caches(trait.super_affordances, provided_affordances)
        self.add_to_actor_mixer_cache(trait.actor_mixers)
        self.add_to_provided_mixer_cache(trait.provided_mixers)
        apply_super_affordance_commodity_flags(sim, trait, trait.super_affordances)
        self._hiding_relationships |= trait.hide_relationships
        if sim is not None:
            teleport_style_interaction = trait.get_teleport_style_interaction_to_inject()
            if teleport_style_interaction is not None:
                sim.add_teleport_style_interaction_to_inject(teleport_style_interaction)
        if not from_load:
            if trait.is_personality_trait:
                if self._sim_info.household is not None:
                    for household_sim in self._sim_info.household:
                        if household_sim is self._sim_info:
                            pass
                        else:
                            household_sim.relationship_tracker.add_known_trait(trait, self._sim_info.sim_id)
                else:
                    logger.error("Attempting to add a trait to a Sim that doesn't have a household. This shouldn't happen. Sim={}, trait={}", self._sim_info, trait)
            self._sim_info.resend_trait_ids()
            if trait.disable_aging is not None:
                self._sim_info.resend_age_progress_data()
            if sim is not None:
                with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ADD_TRAIT, sim=sim) as hook:
                    hook.write_int(TELEMETRY_FIELD_TRAIT_ID, trait.guid64)
            if trait.always_send_test_event_on_add or sim is not None:
                services.get_event_manager().process_event(test_events.TestEvent.TraitAddEvent, sim_info=self._sim_info)
            if trait.loot_on_trait_add is not None:
                resolver = SingleSimResolver(self._sim_info)
                for loot_action in trait.loot_on_trait_add:
                    loot_action.apply_to_resolver(resolver)
        return True

    def _remove_trait(self, trait):
        if not self.has_trait(trait):
            return False
        initial_commodities_modified = trait.initial_commodities or trait.initial_commodities_blacklist
        if initial_commodities_modified:
            previous_initial_commodities = self._sim_info.get_initial_commodities()
        self._equipped_traits.remove(trait)
        if initial_commodities_modified:
            self._update_initial_commodities(trait, previous_initial_commodities)
        self._remove_buffs(trait)
        self._remove_vfx_mask(trait)
        self._remove_day_night_tracking(trait)
        self.update_trait_effects()
        self.update_affordance_caches()
        if trait.disable_aging:
            self._sim_info.update_age_callbacks()
        self._sim_info.resend_trait_ids()
        if trait.disable_aging is not None:
            self._sim_info.resend_age_progress_data()
        if not any(t.is_ghost_trait for t in self._equipped_traits):
            sims.ghost.Ghost.remove_ghost_from_sim(self._sim_info)
        sim = self._sim_info.get_sim_instance()
        if sim is not None:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_REMOVE_TRAIT, sim=sim) as hook:
                hook.write_int(TELEMETRY_FIELD_TRAIT_ID, trait.guid64)
            services.get_event_manager().process_event(test_events.TestEvent.TraitRemoveEvent, sim_info=self._sim_info)
            teleport_style_interaction = trait.get_teleport_style_interaction_to_inject()
            if teleport_style_interaction is not None:
                sim.try_remove_teleport_style_interaction_to_inject(teleport_style_interaction)
        remove_super_affordance_commodity_flags(sim, trait)
        self._hiding_relationships = any(trait.hide_relationships for trait in self)
        return True

    def get_traits_of_type(self, trait_type):
        return [t for t in self._equipped_traits if t.trait_type == trait_type]

    def remove_traits_of_type(self, trait_type):
        for trait in list(self._equipped_traits):
            if trait.trait_type == trait_type:
                self._remove_trait(trait)

    def clear_traits(self):
        for trait in list(self._equipped_traits):
            self._remove_trait(trait)

    def has_trait(self, trait):
        return trait in self._equipped_traits

    def has_any_trait(self, traits):
        return any(t in traits for t in self._equipped_traits)

    def is_conflicting(self, trait):
        return any(t.is_conflicting(trait) for t in self._equipped_traits)

    @staticmethod
    def _get_inherited_traits_internal(traits_a, traits_b, trait_entry):
        if trait_entry.parent_a_whitelist and not all(t in traits_a for t in trait_entry.parent_a_whitelist):
            return False
        if any(t in traits_a for t in trait_entry.parent_a_blacklist):
            return False
        if trait_entry.parent_b_whitelist and not all(t in traits_b for t in trait_entry.parent_b_whitelist):
            return False
        elif any(t in traits_b for t in trait_entry.parent_b_blacklist):
            return False
        return True

    def get_inherited_traits(self, other_sim):
        traits_a = list(self)
        traits_b = list(other_sim.trait_tracker)
        inherited_entries = []
        for trait_entry in TraitTracker.TRAIT_INHERITANCE:
            if not self._get_inherited_traits_internal(traits_a, traits_b, trait_entry):
                if self._get_inherited_traits_internal(traits_b, traits_a, trait_entry):
                    inherited_entries.append(tuple((outcome.weight, outcome.trait) for outcome in trait_entry.outcomes))
            inherited_entries.append(tuple((outcome.weight, outcome.trait) for outcome in trait_entry.outcomes))
        return inherited_entries

    def get_leave_lot_now_interactions(self, must_run=False):
        interactions = set()
        for trait in self:
            if trait.npc_leave_lot_interactions:
                if must_run:
                    interactions.update(trait.npc_leave_lot_interactions.leave_lot_now_must_run_interactions)
                else:
                    interactions.update(trait.npc_leave_lot_interactions.leave_lot_now_interactions)
        return interactions

    @property
    def personality_traits(self):
        return tuple(trait for trait in self if trait.is_personality_trait)

    @property
    def gender_option_traits(self):
        return tuple(trait for trait in self if trait.is_gender_option_trait)

    @property
    def aspiration_traits(self):
        return tuple(trait for trait in self if trait.is_aspiration_trait)

    @property
    def trait_ids(self):
        return [t.guid64 for t in self._equipped_traits]

    @property
    def equipped_traits(self):
        return self._equipped_traits

    def get_default_trait_asm_params(self, actor_name):
        asm_param_dict = {}
        for trait_asm_param in Trait.default_trait_params:
            asm_param_dict[(trait_asm_param, actor_name)] = False
        return asm_param_dict

    @property
    def equip_slot_number(self):
        age = self._sim_info.age
        slot_number = self._unlocked_equip_slot
        slot_number += self._sim_info.get_aging_data().get_personality_trait_count(age)
        return slot_number

    @property
    def empty_slot_number(self):
        equipped_personality_traits = sum(1 for trait in self if trait.is_personality_trait)
        empty_slot_number = self.equip_slot_number - equipped_personality_traits
        return max(empty_slot_number, 0)

    def _add_buffs(self, trait):
        if trait.guid64 in self._buff_handles:
            return
        buff_handles = []
        for buff in trait.buffs:
            buff_handle = self._sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason, remove_on_zone_unload=trait.buffs_add_on_spawn_only)
            if buff_handle is not None:
                buff_handles.append(buff_handle)
        if buff_handles:
            self._buff_handles[trait.guid64] = buff_handles

    def _remove_buffs(self, trait):
        if trait.guid64 in self._buff_handles:
            for buff_handle in self._buff_handles[trait.guid64]:
                self._sim_info.remove_buff(buff_handle)
            del self._buff_handles[trait.guid64]

    def _add_vfx_mask(self, trait, send_op=False):
        if trait.vfx_mask is None:
            return
        for mask in trait.vfx_mask:
            self.trait_vfx_mask |= mask
        if send_op and self._sim_info is services.active_sim_info():
            generate_mask_message(self.trait_vfx_mask, self._sim_info)

    def _remove_vfx_mask(self, trait):
        if trait.vfx_mask is None:
            return
        for mask in trait.vfx_mask:
            self.trait_vfx_mask ^= mask
        if self._sim_info is services.active_sim_info():
            generate_mask_message(self.trait_vfx_mask, self._sim_info)

    def update_trait_effects(self):
        if self._load_in_progress:
            return
        self._update_voice_effect()
        self._update_plumbbob_override()

    def _update_voice_effect(self):
        try:
            voice_effect_request = max((trait.voice_effect for trait in self if trait.voice_effect is not None), key=operator.attrgetter('priority'))
            self._sim_info.voice_effect = voice_effect_request.voice_effect
        except ValueError:
            self._sim_info.voice_effect = None

    def _update_plumbbob_override(self):
        try:
            plumbbob_override_request = max((trait.plumbbob_override for trait in self if trait.plumbbob_override is not None), key=operator.attrgetter('priority'))
            self._sim_info.plumbbob_override = (plumbbob_override_request.active_sim_plumbbob, plumbbob_override_request.active_sim_club_leader_plumbbob)
        except ValueError:
            self._sim_info.plumbbob_override = None

    def _add_default_gender_option_traits(self):
        gender_option_traits = self.DEFAULT_GENDER_OPTION_TRAITS.get(self._sim_info.gender)
        for gender_option_trait in gender_option_traits:
            if not self.has_trait(gender_option_trait):
                self._add_trait(gender_option_trait)

    def on_sim_startup(self):
        sim = self._sim_info.get_sim_instance()
        for trait in tuple(self):
            if trait in self:
                if trait.buffs_add_on_spawn_only:
                    self._add_buffs(trait)
                apply_super_affordance_commodity_flags(sim, trait, trait.super_affordances)
                teleport_style_interaction = trait.get_teleport_style_interaction_to_inject()
                if teleport_style_interaction is not None:
                    sim.add_teleport_style_interaction_to_inject(teleport_style_interaction)
                    logger.error('Trait:{} was removed during startup', trait)
            else:
                logger.error('Trait:{} was removed during startup', trait)
        if any(trait.is_ghost_trait for trait in self):
            sims.ghost.Ghost.enable_ghost_routing(self._sim_info)

    def on_zone_unload(self):
        if game_services.service_manager.is_traveling:
            for trait in tuple(self):
                if not trait.buffs_add_on_spawn_only:
                    self._remove_buffs(trait)
                if not (trait in self and trait.persistable):
                    self._remove_trait(trait)

    def on_zone_load(self):
        if game_services.service_manager.is_traveling:
            for trait in tuple(self):
                if trait in self and not trait.buffs_add_on_spawn_only:
                    self._add_buffs(trait)

    def on_sim_removed(self):
        for trait in tuple(self):
            if trait.buffs_add_on_spawn_only:
                self._remove_buffs(trait)
            if not trait.persistable:
                self._remove_trait(trait)

    def save(self):
        data = protocols.PersistableTraitTracker()
        trait_ids = [trait.guid64 for trait in self._equipped_traits if trait.persistable]
        data.trait_ids.extend(trait_ids)
        return data

    def load(self, data, skip_load):
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        try:
            self._load_in_progress = True
            self._sim_info._update_age_trait(self._sim_info.age)
            for trait_instance_id in data.trait_ids:
                trait = trait_manager.get(trait_instance_id)
                if trait is not None:
                    if not self._has_valid_lod(trait):
                        pass
                    elif skip_load and not trait.allow_from_gallery:
                        pass
                    else:
                        self._sim_info.add_trait(trait, from_load=True)
            if self.personality_traits or not self._sim_info.is_baby:
                possible_traits = [trait for trait in trait_manager.types.values() if trait.is_personality_trait and self.can_add_trait(trait)]
                if possible_traits:
                    chosen_trait = random.choice(possible_traits)
                    self._add_trait(chosen_trait, from_load=True)
            if not any(trait.is_gender_option_trait for trait in self):
                self._add_default_gender_option_traits()
            add_quirks(self._sim_info)
            self._sim_info.on_all_traits_loaded()
        finally:
            self._load_in_progress = False

    def _has_any_trait_with_day_night_tracking(self):
        return any(trait for trait in self if trait.day_night_tracking is not None)

    def _add_day_night_tracking(self, trait):
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        if trait.day_night_tracking is not None and not sim.is_on_location_changed_callback_registered(self._day_night_tracking_callback):
            sim.register_on_location_changed(self._day_night_tracking_callback)
        self.update_day_night_tracking_state(force_update=True)

    def _remove_day_night_tracking(self, trait):
        self._day_night_state = None
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        if trait.day_night_tracking is None or self._has_any_trait_with_day_night_tracking():
            return
        sim.unregister_on_location_changed(self._day_night_tracking_callback)

    def _day_night_tracking_callback(self, *_, **__):
        self.update_day_night_tracking_state()

    def update_day_night_tracking_state(self, force_update=False, full_reset=False):
        if not self._has_any_trait_with_day_night_tracking():
            return
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        if full_reset:
            self._clear_all_day_night_buffs()
        time_service = services.time_service()
        is_day = time_service.is_day_time()
        in_sunlight = time_service.is_in_sunlight(sim)
        new_state = self._day_night_state is None
        if new_state:
            self._day_night_state = DayNightTrackingState(is_day, in_sunlight)
        update_day_night = new_state or self._day_night_state.is_day != is_day
        update_sunlight = new_state or self._day_night_state.in_sunlight != in_sunlight
        if force_update or update_day_night or not update_sunlight:
            return
        self._day_night_state.is_day = is_day
        self._day_night_state.in_sunlight = in_sunlight
        for trait in self:
            if not trait.day_night_tracking:
                pass
            else:
                day_night_tracking = trait.day_night_tracking
                if update_day_night or force_update:
                    self._add_remove_day_night_buffs(day_night_tracking.day_buffs, add=is_day)
                    self._add_remove_day_night_buffs(day_night_tracking.night_buffs, add=not is_day)
                if not update_sunlight:
                    if force_update:
                        self._add_remove_day_night_buffs(day_night_tracking.sunlight_buffs, add=in_sunlight)
                        self._add_remove_day_night_buffs(day_night_tracking.shade_buffs, add=not in_sunlight)
                self._add_remove_day_night_buffs(day_night_tracking.sunlight_buffs, add=in_sunlight)
                self._add_remove_day_night_buffs(day_night_tracking.shade_buffs, add=not in_sunlight)

    def update_day_night_buffs_on_buff_removal(self, buff_to_remove):
        if not self._has_any_trait_with_day_night_tracking():
            return
        for trait in self:
            if trait.day_night_tracking:
                if not trait.day_night_tracking.force_refresh_buffs:
                    pass
                else:
                    force_refresh_buffs = trait.day_night_tracking.force_refresh_buffs
                    if any(buff.buff_type is buff_to_remove.buff_type for buff in force_refresh_buffs):
                        self.update_day_night_tracking_state(full_reset=True, force_update=True)
                        return

    def _clear_all_day_night_buffs(self):
        for trait in self:
            if not trait.day_night_tracking:
                pass
            else:
                day_night_tracking = trait.day_night_tracking
                self._add_remove_day_night_buffs(day_night_tracking.day_buffs, add=False)
                self._add_remove_day_night_buffs(day_night_tracking.night_buffs, add=False)
                self._add_remove_day_night_buffs(day_night_tracking.sunlight_buffs, add=False)
                self._add_remove_day_night_buffs(day_night_tracking.shade_buffs, add=False)

    def _add_remove_day_night_buffs(self, buffs, add=True):
        for buff in buffs:
            if add:
                self._sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason)
            else:
                self._sim_info.remove_buff_by_type(buff.buff_type)

    def on_sim_ready_to_simulate(self):
        for trait in self:
            self._add_day_night_tracking(trait)

    def get_provided_super_affordances(self):
        affordances = set()
        target_affordances = list()
        for trait in self._equipped_traits:
            affordances.update(trait.super_affordances)
            for provided_affordance in trait.target_super_affordances:
                provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
                target_affordances.append(provided_affordance_data)
        return (affordances, target_affordances)

    def get_actor_and_provided_mixers_list(self):
        actor_mixers = [trait.actor_mixers for trait in self._equipped_traits]
        provided_mixers = [trait.provided_mixers for trait in self._equipped_traits]
        return (actor_mixers, provided_mixers)

    def get_sim_info_from_provider(self):
        return self._sim_info

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.MINIMUM

    def on_lod_update(self, old_lod, new_lod):
        if new_lod >= old_lod:
            return
        for trait in tuple(self._equipped_traits):
            if not self._has_valid_lod(trait):
                self._sim_info.remove_trait(trait)

    def _has_valid_lod(self, trait):
        if self._sim_info.lod < trait.min_lod_value:
            return False
        return True

    @property
    def hide_relationships(self):
        return self._hiding_relationships

class TraitPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'is_add': Tunable(description='\n            If this interaction is trying to add a trait to the sim or to\n            remove a trait from the sim.\n            ', tunable_type=bool, default=True), 'already_equipped_tooltip': OptionalTunable(description='\n            If tuned, we show this tooltip if row is disabled when trait is \n            already equipped.\n            ', tunable=TunableLocalizedStringFactory(description='\n                Tooltip to display.\n                ')), 'filter_by_types': OptionalTunable(description='\n            If specified, limits the traits that appear in this picker to specific types of traits.\n            If disabled, all traits are available.\n            ', tunable=TunableWhiteBlackList(tunable=TunableEnumEntry(default=TraitType.PERSONALITY, tunable_type=TraitType)))}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.target, target_sim=self.target)
        return True

    @classmethod
    def _match_trait_type(cls, trait):
        if cls.filter_by_types is None:
            return True
        return cls.filter_by_types.test_item(trait.trait_type)

    @classmethod
    def _trait_selection_gen(cls, target):
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        trait_tracker = target.sim_info.trait_tracker
        if cls.is_add:
            for trait in trait_manager.types.values():
                if not cls._match_trait_type(trait):
                    pass
                elif trait_tracker.can_add_trait(trait):
                    yield trait
        else:
            for trait in trait_tracker.equipped_traits:
                if not cls._match_trait_type(trait):
                    pass
                else:
                    yield trait

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        trait_tracker = target.sim_info.trait_tracker
        for trait in cls._trait_selection_gen(target):
            if trait.display_name:
                display_name = trait.display_name(target)
                is_enabled = True
                row_tooltip = None
                is_enabled = not trait_tracker.has_trait(trait)
                row_tooltip = None if is_enabled or cls.already_equipped_tooltip is None else lambda *_: cls.already_equipped_tooltip(target)
                row = ObjectPickerRow(name=display_name, row_description=trait.trait_description(target), icon=trait.icon, tag=trait, is_enable=is_enabled, row_tooltip=row_tooltip)
                yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        trait = choice_tag
        if trait is not None:
            if self.is_add:
                self.target.sim_info.add_trait(trait)
            else:
                self.target.sim_info.remove_trait(trait)

class AgentPickerSuperInteraction(TraitPickerSuperInteraction):

    @classmethod
    def _trait_selection_gen(cls, target):
        career_tracker = target.sim_info.career_tracker
        for career in career_tracker:
            for trait in career.current_level_tuning.agents_available:
                yield trait
