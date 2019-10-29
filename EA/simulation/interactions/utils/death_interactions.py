from event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import ObjectJigConstraintfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom interactions.utils.creation import ObjectCreationElementfrom interactions.utils.death import DeathType, is_death_enabled, DEATH_INTERACTION_MARKER_ATTRIBUTEfrom interactions.utils.interaction_liabilities import RESERVATION_LIABILITYfrom interactions.utils.outcome_enums import OutcomeResultfrom objects.components import typesfrom objects.object_creation import CreationDataBase, ObjectCreationParamsfrom sims.ghost import Ghostfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.localization.localization_tunables import LocalizedStringHouseholdNameSelectorfrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom ui.ui_dialog_generic import UiDialogfrom ui.ui_dialog_notification import UiDialogNotificationimport build_buyimport element_utilsimport servicesimport sims4.telemetryimport telemetry_helperTELEMETRY_GROUP_DEATH = 'DEAD'TELEMETRY_HOOK_SIM_DIES = 'SDIE'TELEMETRY_DEATH_TYPE = 'dety'death_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_DEATH)logger = sims4.log.Logger('Death Interactions')
class DeathElement(ObjectCreationElement):
    FACTORY_TUNABLES = {'create_urnstone': Tunable(description="\n            If checked, an urnstone is spawned at the Sim's location.\n            ", tunable_type=bool, default=True)}

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(interaction, *args, **kwargs)
        self._on_lot_placement_failed = False
        self._interaction = interaction

    @property
    def definition(self):
        if not self.create_urnstone:
            return
        return super().definition

    @property
    def placement_failed(self):
        return self._on_lot_placement_failed

    def _get_ignored_object_ids(self):
        jig_liability = self._interaction.get_liability(ObjectJigConstraint.JIG_CONSTRAINT_LIABILITY)
        if jig_liability is not None and jig_liability.jig is not None:
            return (jig_liability.jig.id, self._interaction.sim.id)
        return (self._interaction.sim.id,)

    def _place_object(self, created_object):
        if created_object is None:
            return False
        if not self._place_object_no_fallback(created_object):
            self._on_lot_placement_failed = True
        return True

    def _do_behavior(self, *args, **kwargs):
        if self.definition is not None:
            super()._do_behavior(*args, **kwargs)
        object_data = None if self._object_helper.is_object_none else (self._object_helper.object, self.placement_failed)
        self._interaction.run_death_behavior(death_object_data=object_data)

    def _build_outer_elements(self, sequence):
        if self.definition is None:
            return sequence
        return super()._build_outer_elements(sequence)

    def create_object(self):
        if self.definition is None:
            return
        return super().create_object(self._interaction.get_resolver())

class DeathSuperInteraction(SuperInteraction):

    class UrnstoneCreationData(CreationDataBase):

        def get_definition(*args, **kwargs):
            return Ghost.URNSTONE_DEFINITION.get_definition(*args, **kwargs)

        def get_creation_params(*args, **kwargs):
            return ObjectCreationParams(Ghost.URNSTONE_DEFINITION.get_definition(*args, **kwargs), {})

        def setup_created_object(*args, **kwargs):
            return Ghost.URNSTONE_DEFINITION.setup_created_object(*args, **kwargs)

        def get_source_object(*args, **kwargs):
            return Ghost.URNSTONE_DEFINITION.get_source_object(*args, **kwargs)

    INSTANCE_TUNABLES = {'death_element': DeathElement.TunableFactory(description='\n            Define what object is created by the dying Sim.\n            ', locked_args={'creation_data': UrnstoneCreationData, 'destroy_on_placement_failure': False}, tuning_group=GroupNames.DEATH), 'death_subject': TunableEnumEntry(description='\n            The participant whose death will be occurring.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor, tuning_group=GroupNames.DEATH), 'death_type': OptionalTunable(description="\n            If enabled, this is a regular Death interactions: the Sim will have\n            its death type set to this value, and it will effectively become a\n            ghost.\n            \n            If disabled, the interaction behavior is mostly the same, except\n            that the Sim won't become a ghost. Instead, they'll be split out of\n            this household (into a hidden household) and its LOD set to MINIMUM.\n            ", tunable=TunableEnumEntry(description="\n                The subject's death type will be set to this value.\n                ", tunable_type=DeathType, default=DeathType.NONE, tuning_group=GroupNames.DEATH), enabled_by_default=True, disabled_name='Set_To_Minimum_LOD'), 'death_dialog': UiDialog.TunableFactory(description='\n            A dialog informing the Player that their last selectable Sim is\n            dead, prompting them to either save and quit, or quit.\n            ', text=LocalizedStringHouseholdNameSelector.TunableFactory(), tuning_group=GroupNames.DEATH), 'off_lot_death_notification': OptionalTunable(description='\n            If enabled, show a notification when Sims die off-lot.\n            ', tunable=UiDialogNotification.TunableFactory(description='\n                The notification that is displayed when sim has died off lot and\n                then switching to sim that is not on current lot the sim died\n                on.\n                \n                Tokens:\n                0 - Sim that has died\n                1 - Zone Name the sim died on.\n                '), tuning_group=GroupNames.DEATH), 'save_lock_tooltip': TunableLocalizedStringFactory(description='\n            The tooltip/message to show when the player tries to save the game\n            while the death interaction is happening\n            ', tuning_group=GroupNames.UI)}

    def __init__(self, *args, **kwargs):
        self._removed_sim = None
        self._client = None
        super().__init__(*args, **kwargs)
        self._priority = Priority.Critical
        self._run_priority = self._priority
        self._death_object_data = None
        self._has_completed_death = False
        self._has_finalized_death = False

    @flexmethod
    def test(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        context = inst.context if context is DEFAULT else context
        running_death_interaction = getattr(context.sim, DEATH_INTERACTION_MARKER_ATTRIBUTE, None)
        if running_death_interaction is not None and running_death_interaction is not inst:
            return TestResult(False, '{} is already dying.', context.sim)
        if cls.death_type is not None:
            if not is_death_enabled():
                return TestResult(False, 'Death is disabled.')
            sim_info = context.sim.sim_info
            if sim_info.is_death_disabled():
                return TestResult(False, '{} is not allowed to die.', sim_info)
        return super(__class__, inst if inst is not None else cls).test(target=target, context=context, **kwargs)

    @property
    def sim(self):
        if self._removed_sim is not None:
            return self._removed_sim
        return super().sim

    @property
    def should_die_on_transition_failure(self):
        return self.target is self.sim or self.target is None

    def on_added_to_queue(self, *args, **kwargs):
        services.get_persistence_service().lock_save(self)
        setattr(self.sim, DEATH_INTERACTION_MARKER_ATTRIBUTE, self)
        return super().on_added_to_queue(*args, **kwargs)

    def _exited_pipeline(self, *args, **kwargs):
        try:
            should_die_on_transition_failure = self.should_die_on_transition_failure
            super()._exited_pipeline(*args, **kwargs)
        finally:
            try:
                if (self.finishing_type == FinishingType.TRANSITION_FAILURE or self.finishing_type == FinishingType.USER_CANCEL or self.finishing_type == FinishingType.FAILED_TESTS) and not should_die_on_transition_failure:
                    return
                if self.global_outcome_result != OutcomeResult.SUCCESS:
                    self.run_death_behavior(from_reset=True)
            finally:
                services.get_persistence_service().unlock_save(self)
                delattr(self.sim, DEATH_INTERACTION_MARKER_ATTRIBUTE)

    def build_outcome(self, *args, **kwargs):
        outcome_sequence = super().build_outcome(*args, **kwargs)

        def _do(timeline):
            nonlocal outcome_sequence
            self.outcome.decide(self, update_global_outcome_result=True)
            if self.global_outcome_result == OutcomeResult.FAILURE:
                outcome_sequence = self.death_element(self, sequence=outcome_sequence)
            result = yield from element_utils.run_child(timeline, outcome_sequence)
            return result

        return (_do,)

    def _get_cancel_replacement_aops_contexts_postures(self, *args, **kwargs):
        return []

    def run_death_behavior(self, death_object_data=None, from_reset=False):
        if self._death_object_data is not None:
            return
        if death_object_data is None:
            death_element = self.death_element(self)
            death_object_data = (death_element.create_object(), death_element.placement_failed)
        self._death_object_data = death_object_data
        self.sim.sim_info.career_tracker.on_death()
        self.sim.sim_info.Buffs.remove_all_buffs_with_temporary_commodities()
        if not self.sim.is_npc:
            self.sim.inventory_component.push_items_to_household_inventory()
        self.sim.inventory_component.purge_inventory()
        self.sim.sim_info.inventory_data = self.sim.inventory_component.save_items()
        if self.death_type is not None:
            with telemetry_helper.begin_hook(death_telemetry_writer, TELEMETRY_HOOK_SIM_DIES, sim_info=self.sim.sim_info) as hook:
                hook.write_int(TELEMETRY_DEATH_TYPE, self.death_type)
        for si in list(self.sim.interaction_refs):
            si.refresh_conditional_actions()
            si.set_target(None)
            si.remove_liability(RESERVATION_LIABILITY)
        self.sim.remove_from_client()
        self._removed_sim = self.sim
        self._client = self.sim.household.client
        if from_reset:
            self._finalize_death()
            self.sim.schedule_destroy_asap(source=self.sim, cause='Sim reset during death.')
        else:
            self.add_exit_function(self.run_post_death_behavior)

    def _finalize_death(self):
        if self._has_finalized_death:
            return
        self._has_finalized_death = True
        sim_info = self.sim.sim_info
        current_household = sim_info.household
        death_object = self._death_object_data[0]
        if death_object is not None:
            death_object.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=sim_info.id)
            death_object.update_object_tooltip()
            active_household = services.active_household()
            death_object.set_household_owner_id(active_household.id)
            if self._death_object_data[1]:
                try:
                    if not build_buy.move_object_to_household_inventory(death_object):
                        logger.error('Failed to place an urnstone for {} in household inventory: {}', sim_info, sim_info.household.id)
                except KeyError:
                    logger.exception('Failed to place an urnstone for {} in household inventory: {}', sim_info, sim_info.household.id)
        death_tracker = sim_info.death_tracker
        death_tracker.set_death_type(self.death_type)
        if self.death_type is None:
            sim_info.request_lod(SimInfoLODLevel.MINIMUM)
        if self._client is not None:
            self._client.set_next_sim_or_none(only_if_this_active_sim_info=sim_info)
            self._client.selectable_sims.remove_selectable_sim_info(sim_info)
            kill_all_fires = False
            if any(sim.can_live_alone for sim in self._client.selectable_sims):
                if self._show_off_lot_death_notification():
                    kill_all_fires = True
            else:
                kill_all_fires = True
                self._disband_travel_group()
                self._show_death_dialog()
                self._client.clear_selectable_sims()
            if kill_all_fires:
                fire_service = services.get_fire_service()
                if fire_service is not None:
                    fire_service.kill()
        current_household.handle_adultless_household()
        services.daycare_service().refresh_household_daycare_nanny_status(sim_info)

    def run_post_death_behavior(self):
        if self._has_completed_death:
            return
        self._has_completed_death = True
        self.sim.schedule_destroy_asap(post_delete_func=self._finalize_death, source=self.sim, cause='Sim died.')

    def _disband_travel_group(self):
        dead_sim_info = self.sim.sim_info
        travel_group = dead_sim_info.travel_group
        if travel_group is not None:
            services.travel_group_manager().destroy_travel_group_and_release_zone(travel_group)

    def _show_death_dialog(self):
        if self._client is not None:
            dialog = self.death_dialog(self.sim, text=lambda *args, **kwargs: self.death_dialog.text(*args, household=self._client.household, **kwargs), resolver=SingleSimResolver(self.sim))
            dialog.show_dialog()

    def _show_off_lot_death_notification(self):
        if self.off_lot_death_notification is None:
            return False
        if self._client is None:
            return False
        home_zone_id = self._client.household.home_zone_id
        if home_zone_id == services.current_zone_id():
            return False
        end_vacation = True
        dead_sim_info = self.sim.sim_info
        travel_group = dead_sim_info.travel_group
        sim_info_to_travel_to = None
        for sim_info in self._client.selectable_sims:
            if sim_info.is_baby:
                pass
            else:
                if travel_group is None:
                    end_vacation = False
                elif sim_info in travel_group:
                    if sim_info.can_live_alone:
                        end_vacation = False
                        if sim_info.is_instanced():
                            sim_info_to_travel_to = None
                            break
                        if not sim_info_to_travel_to is None:
                            if sim_info.zone_id == home_zone_id:
                                sim_info_to_travel_to = sim_info
                        sim_info_to_travel_to = sim_info
                else:
                    if sim_info.is_instanced():
                        sim_info_to_travel_to = None
                        break
                    if not sim_info_to_travel_to is None:
                        if sim_info.zone_id == home_zone_id:
                            sim_info_to_travel_to = sim_info
                    sim_info_to_travel_to = sim_info
                if sim_info.is_instanced():
                    sim_info_to_travel_to = None
                    break
                if not sim_info_to_travel_to is None:
                    if sim_info.zone_id == home_zone_id:
                        sim_info_to_travel_to = sim_info
                sim_info_to_travel_to = sim_info
        if travel_group is not None and not end_vacation:
            travel_group.remove_sim_info(dead_sim_info)
        if sim_info_to_travel_to is not None:
            persistence_service = services.get_persistence_service()
            zone_data = persistence_service.get_zone_proto_buff(services.current_zone_id())
            lot_name = zone_data.name
            dialog = self.off_lot_death_notification(self.sim, resolver=SingleSimResolver(self.sim))
            dialog.show_dialog(additional_tokens=(lot_name,))
            if travel_group is not None and end_vacation:
                if services.get_active_sim() is not None:
                    travel_group.end_vacation()
                    return
                else:
                    services.travel_group_manager().destroy_travel_group_and_release_zone(travel_group)

                    def post_save_lock_travel():
                        zone_id = sim_info.zone_id or home_zone_id
                        sim_info.send_travel_switch_to_zone_op(zone_id=zone_id)

                    persistence_service.add_save_unlock_callback(post_save_lock_travel)
                    return True

            def post_save_lock_travel():
                zone_id = sim_info.zone_id or home_zone_id
                sim_info.send_travel_switch_to_zone_op(zone_id=zone_id)

            persistence_service.add_save_unlock_callback(post_save_lock_travel)
            return True
        return False

    def get_lock_save_reason(self):
        return self.create_localized_string(self.save_lock_tooltip)
