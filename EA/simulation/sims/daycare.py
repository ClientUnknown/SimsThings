from _weakrefset import WeakSetfrom weakref import WeakKeyDictionaryfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypeSimfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom objects import ALL_HIDDEN_REASONSfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import HasTunableFactory, TunableReference, TunablePackSafeReference, AutoFactoryInit, TunableEnumFlags, TunableMappingfrom singletons import DEFAULTfrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom world.travel_tuning import TravelTuningimport servicesimport sims4.loglogger = sims4.log.Logger('Daycare', default_owner='epanero')
class DaycareTuning:
    NANNY_SERVICE_NPC = TunableReference(description='\n        The nanny service NPC. We check if this is hired to take \n        away babies on sims leaving.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SERVICE_NPC))
    BUTLER_SERVICE_NPC = TunablePackSafeReference(description='\n        The butler service NPC. If selected to look after children, the butler\n        should have similar effects as the nanny with regards to Daycare.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SERVICE_NPC))
    NANNY_SERVICE_NPC_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        A dialog that shows up when toddlers (not babies) are left home alone\n        requiring daycare. If the player selects Ok, a Nanny NPC is hired for\n        the duration of daycare, and the player can keep playing with their\n        toddlers. If Cancel is selected, regular daycare behavior kicks in and\n        the toddlers become uncontrollable.\n        ')
    DAYCARE_TRAIT_ON_KIDS = TunableReference(description='\n        The trait that indicates a baby is at daycare.\n        ', manager=services.trait_manager())
    NANNY_TRAIT_ON_KIDS = TunableReference(description='\n        The trait that children and babies that are with the nanny have.\n        ', manager=services.trait_manager())
    SEND_BABY_TO_DAYCARE_NOTIFICATION_SINGLE_BABY = TunableUiDialogNotificationSnippet(description='\n        The message appearing when a single baby is sent to daycare. You can\n        reference this single baby by name.\n        ')
    SEND_BABY_TO_DAYCARE_NOTIFICATION_MULTIPLE_BABIES = TunableUiDialogNotificationSnippet(description='\n        The message appearing when multiple babies are sent to daycare. You can\n        not reference any of these babies by name.\n        ')
    BRING_BABY_BACK_FROM_DAYCARE_NOTIFICATION_SINGLE_BABY = TunableUiDialogNotificationSnippet(description='\n        The message appearing when a single baby is brought back from daycare.\n        You can reference this single baby by name.\n        ')
    BRING_BABY_BACK_FROM_DAYCARE_NOTIFICATION_MULTIPLE_BABIES = TunableUiDialogNotificationSnippet(description='\n        The message appearing when multiple babies are brought back from\n        daycare. You can not reference any of these babies by name.\n        ')
    SEND_CHILD_TO_NANNY_NOTIFICATION_SINGLE = TunableUiDialogNotificationSnippet(description='\n        The message appears when a single child is sent to the nanny. You can\n        reference this single nanny by name.\n        ')
    SEND_CHILD_TO_NANNY_NOTIFICATION_MULTIPLE = TunableUiDialogNotificationSnippet(description='\n        The message appearing when multiple children are sent to the nanny. You\n        can not reference any of these children by name.\n        ')
    BRING_CHILD_BACK_FROM_NANNY_NOTIFICATION_SINGLE = TunableUiDialogNotificationSnippet(description='\n        The message appearing when a single child is brought back from the\n        nanny. You can reference this single child by name.\n        ')
    BRING_CHILD_BACK_FROM_NANNY_NOTIFICATION_MULTIPLE = TunableUiDialogNotificationSnippet(description='\n        The message appearing when multiple children are brought back from\n        the nanny. You can not reference any of these by name.\n        ')
    GO_TO_DAYCARE_INTERACTION = TunableReference(description='\n        An interaction to push on instantiated Sims that need to go to Daycare.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    DAYCARE_AWAY_ACTIONS = TunableMapping(description='\n        Map of commodities to away action.  When the default away action is\n        asked for we look at the ad data of each commodity and select the away\n        action linked to the commodity that is advertising the highest.\n        \n        This set of away actions is used exclusively for Sims in daycare.\n        ', key_type=TunableReference(description='\n            The commodity that we will look at the advertising value for.\n            ', manager=services.get_instance_manager(Types.STATISTIC), class_restrictions=('Commodity',)), value_type=TunableReference(description='\n            The away action that will applied if the key is the highest\n            advertising commodity of the ones listed.\n            ', manager=services.get_instance_manager(Types.AWAY_ACTION)))

class DaycareLiability(Liability, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participants': TunableEnumFlags(description='\n            The participants this liability is applied to.\n            ', enum_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor)}

    def __init__(self, interaction, *args, participants=DEFAULT, **kwargs):
        if participants is DEFAULT:
            participants = ParticipantTypeSim.Actor
        super().__init__(*args, participants=participants, **kwargs)
        self._sim_infos = []

    def on_add(self, interaction):
        super().on_add(interaction)
        participants = interaction.get_participants(self.participants)
        for participant in participants:
            self._sim_infos.append(participant.sim_info)

    def on_run(self):
        super().on_run()
        daycare_service = services.daycare_service()
        for sim_info in self._sim_infos:
            if daycare_service is not None:
                daycare_service.set_sim_globally_unavailable(sim_info)
                daycare_service.set_sim_unavailable(sim_info)

    def release(self):
        super().release()
        daycare_service = services.daycare_service()
        for sim_info in self._sim_infos:
            if daycare_service is not None:
                daycare_service.set_sim_globally_available(sim_info)
                daycare_service.set_sim_available(sim_info)

class DaycareService(Service):

    def __init__(self):
        self._unavailable_sims = WeakSet()
        self._global_unavailable_sims = WeakSet()
        self._daycare_interactions = WeakKeyDictionary()
        self._excluded_sims = WeakSet()
        self._nanny_dialog_shown = False

    def on_sim_reset(self, sim):
        sim_info = sim.sim_info
        daycare_interaction = self._daycare_interactions.get(sim_info)
        if daycare_interaction is not None:
            del self._daycare_interactions[sim_info]
            self._apply_daycare_effects_to_sim(sim_info)

    def get_available_sims_gen(self):
        for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
            if sim.sim_info in self._global_unavailable_sims:
                pass
            else:
                yield sim.sim_info

    def _apply_daycare_effects_to_sim(self, sim_info):
        self._excluded_sims.discard(sim_info)
        sim = services.object_manager().get(sim_info.id)
        if sim_info.is_baby:
            sim.empty_baby_state()
        elif sim_info.is_toddler:
            daycare_interaction = self._daycare_interactions.get(sim_info)
            if daycare_interaction is None:
                aop = AffordanceObjectPair(DaycareTuning.GO_TO_DAYCARE_INTERACTION, None, DaycareTuning.GO_TO_DAYCARE_INTERACTION, None)
                context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True)
                execute_result = aop.test_and_execute(context)
                if execute_result:
                    self._daycare_interactions[sim_info] = execute_result.interaction
        return True

    def _remove_daycare_effects_from_sim(self, sim_info):
        sim = services.object_manager().get(sim_info.id)
        if sim_info.is_baby and sim is not None:
            sim.enable_baby_state()
        elif sim_info.is_toddler:
            daycare_interaction = self._daycare_interactions.pop(sim_info, None)
            if daycare_interaction is not None:
                daycare_interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Daycare no longer necessary.', ignore_must_run=True)
        if sim_info in self._excluded_sims:
            self._excluded_sims.discard(sim_info)
            return False
        return True

    def _is_sim_available(self, sim_info, household, current_zone_id):
        if sim_info.zone_id == household.home_zone_id:
            if sim_info.zone_id != current_zone_id:
                if sim_info.career_tracker is None or sim_info.career_tracker.currently_at_work or services.hidden_sim_service().is_hidden(sim_info.id):
                    return False
                return True
            elif sim_info not in self._unavailable_sims:
                return True
        return False

    def _start_nanny_service(self, household, sim_infos, callback_fn):

        def _can_trigger_nanny_service(sim_info):
            if not sim_info.is_toddler:
                return False
            else:
                daycare_interaction = self._daycare_interactions.get(sim_info)
                if daycare_interaction is not None:
                    return False
            return True

        if not any(_can_trigger_nanny_service(sim_info) for sim_info in sim_infos):
            callback_fn()
            return

        def _on_response(dialog):
            self._nanny_dialog_shown = False
            if dialog.accepted:
                service_npc_service = services.current_zone().service_npc_service
                service_npc_service.request_service(household, DaycareTuning.NANNY_SERVICE_NPC, from_load=True)
            else:
                callback_fn()

        if self._nanny_dialog_shown or services.current_zone().service_npc_service.is_service_already_in_request_list(household, DaycareTuning.NANNY_SERVICE_NPC):
            return
        self._nanny_dialog_shown = True
        hire_nanny_dialog = DaycareTuning.NANNY_SERVICE_NPC_DIALOG(None)
        hire_nanny_dialog.show_dialog(additional_tokens=(DaycareTuning.NANNY_SERVICE_NPC.cost_up_front, DaycareTuning.NANNY_SERVICE_NPC.cost_hourly), on_response=_on_response)

    def _get_running_situation_for_service(self, service_npc):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            for service_npc_situation in situation_manager.get_situations_by_type(service_npc.situation):
                return service_npc_situation

    def is_daycare_service_npc_available(self, sim_info=None, household=None):
        household = services.active_household() if household is None else household
        if household.home_zone_id == services.current_zone_id():
            nanny_situation = self._get_running_situation_for_service(DaycareTuning.NANNY_SERVICE_NPC)
            if nanny_situation is not None:
                if sim_info is None:
                    return True
                service_sim = nanny_situation.service_sim()
                if service_sim is not None and service_sim.sim_info is sim_info:
                    return True
            if DaycareTuning.BUTLER_SERVICE_NPC is not None:
                butler_situation = self._get_running_situation_for_service(DaycareTuning.BUTLER_SERVICE_NPC)
                if butler_situation.is_in_childcare_state:
                    if sim_info is None:
                        return True
                    service_sim = butler_situation.service_sim()
                    if service_sim.sim_info is sim_info:
                        return True
        elif sim_info is None:
            all_hired_service_npcs = household.get_all_hired_service_npcs()
            for service_npc in (DaycareTuning.NANNY_SERVICE_NPC, DaycareTuning.BUTLER_SERVICE_NPC):
                if service_npc is None:
                    pass
                elif service_npc.guid64 in all_hired_service_npcs:
                    return True
        return False

    def _is_any_sim_available(self, household):
        if self.is_daycare_service_npc_available(household=household):
            return True
        current_zone_id = services.current_zone_id()
        return any(self._is_sim_available(sim_info, household, current_zone_id) for sim_info in household.can_live_alone_info_gen())

    def _is_everyone_on_vacation(self, household):
        return all(sim_info.is_in_travel_group() for sim_info in household.can_live_alone_info_gen())

    def _enable_daycare_or_nanny_if_necessary(self, household):
        is_active_household = services.active_household() == household
        nanny_sim_infos = self.get_sim_infos_for_nanny(household)
        sent_sim_infos = []
        for sim_info in nanny_sim_infos:
            if not sim_info.trait_tracker.has_trait(DaycareTuning.NANNY_TRAIT_ON_KIDS):
                sent_sim_infos.append(sim_info)
                sim_info.add_trait(DaycareTuning.NANNY_TRAIT_ON_KIDS)
                if sim_info.has_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS):
                    sim_info.remove_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS)
                if sim_info.zone_id != household.home_zone_id:
                    sim_info.inject_into_inactive_zone(household.home_zone_id)
        if is_active_household:
            services.client_manager().get_first_client().send_selectable_sims_update()
            self._show_nanny_notification(household, sent_sim_infos, is_enable=True)
        if nanny_sim_infos:
            return
        if not self._is_any_sim_available(household):
            current_zone_id = services.current_zone_id()
            daycare_sim_infos = self.get_sim_infos_for_daycare(household)
            if not daycare_sim_infos:
                return

            def _on_send_to_daycare():
                sent_sim_infos = []
                for sim_info in daycare_sim_infos:
                    if household.home_zone_id == current_zone_id:
                        self._apply_daycare_effects_to_sim(sim_info)
                    if not sim_info.trait_tracker.has_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS):
                        sent_sim_infos.append(sim_info)
                        sim_info.add_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS)
                        if sim_info.zone_id != household.home_zone_id:
                            sim_info.inject_into_inactive_zone(household.home_zone_id)
                    if sim_info.zone_id != current_zone_id:
                        sim_info.away_action_tracker.reset_to_default_away_action()
                if is_active_household:
                    services.client_manager().get_first_client().send_selectable_sims_update()
                    self._show_daycare_notification(household, sent_sim_infos, is_enable=True)

            if is_active_household and household.home_zone_id == current_zone_id:
                self._start_nanny_service(household, daycare_sim_infos, _on_send_to_daycare)
            else:
                _on_send_to_daycare()

    def default_away_action(self, sim_info):
        highest_advertising_value = None
        highest_advertising_away_action = None
        for (commodity, away_action) in DaycareTuning.DAYCARE_AWAY_ACTIONS.items():
            commodity_instance = sim_info.get_statistic(commodity, add=False)
            if commodity_instance is None:
                pass
            elif not away_action.test(sim_info=sim_info, target=None):
                pass
            else:
                advertising_value = commodity_instance.autonomous_desire
                if not highest_advertising_value is None:
                    if highest_advertising_value < advertising_value:
                        highest_advertising_value = advertising_value
                        highest_advertising_away_action = away_action
                highest_advertising_value = advertising_value
                highest_advertising_away_action = away_action
        return highest_advertising_away_action

    def _disable_daycare_or_nanny_if_necessary(self, household, returning_sim_infos=()):
        returned_children = []
        eligible_nanny_count = self.get_number_of_eligible_nanny_sims(household)
        if eligible_nanny_count and not self._is_everyone_on_vacation(household):
            sim_infos_for_nanny = self.get_sim_infos_for_nanny(household, check_for_vacation=False)
            for sim_info in sim_infos_for_nanny:
                if sim_info.has_trait(DaycareTuning.NANNY_TRAIT_ON_KIDS):
                    sim_info.remove_trait(DaycareTuning.NANNY_TRAIT_ON_KIDS)
                    if sim_info not in returning_sim_infos:
                        returned_children.append(sim_info)
            self._show_nanny_notification(household, returned_children, is_enable=False)
        eligible_daycare_count = self.get_number_of_eligible_daycare_sims(household)
        if eligible_daycare_count and self._is_any_sim_available(household):
            daycare_sim_infos = list(self.get_sim_infos_for_daycare(household))
            for sim_info in tuple(daycare_sim_infos):
                if self._remove_daycare_effects_from_sim(sim_info) and sim_info in returning_sim_infos:
                    daycare_sim_infos.remove(sim_info)
                if sim_info.has_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS):
                    sim_info.remove_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS)
            if not returned_children:
                self._show_daycare_notification(household, daycare_sim_infos, is_enable=False)
        if services.active_household() == household:
            services.client_manager().get_first_client().send_selectable_sims_update()

    def is_daycare_enabled(self, household):
        return not self._is_any_sim_available(household)

    def get_abandoned_toddlers(self, household, sims_infos_to_ignore=()):
        caretaker_zone_ids = set()
        offlot_toddlers = set()
        abandoned_toddlers = []
        current_zone_id = services.current_zone_id()
        for sim_info in household:
            if sim_info in sims_infos_to_ignore:
                pass
            elif not sim_info.is_toddler:
                if sim_info.can_live_alone:
                    caretaker_zone_ids.add(sim_info.zone_id)
                    if sim_info.zone_id == current_zone_id:
                        pass
                    elif sim_info.zone_id == sim_info.household.home_zone_id:
                        pass
                    else:
                        offlot_toddlers.add(sim_info)
            elif sim_info.zone_id == current_zone_id:
                pass
            elif sim_info.zone_id == sim_info.household.home_zone_id:
                pass
            else:
                offlot_toddlers.add(sim_info)
        for toddler in offlot_toddlers:
            if toddler.zone_id not in caretaker_zone_ids:
                abandoned_toddlers.append(toddler)
        return abandoned_toddlers

    def get_sim_infos_for_daycare(self, household):
        sim_infos_for_daycare = []
        for sim_info in household:
            if not sim_info.is_toddler_or_younger:
                pass
            elif sim_info.is_pet:
                pass
            elif sim_info.zone_id != sim_info.household.home_zone_id:
                pass
            else:
                sim_infos_for_daycare.append(sim_info)
        sim_infos_for_daycare.extend(self.get_abandoned_toddlers(household))
        return sim_infos_for_daycare

    def get_sim_infos_for_nanny(self, household, check_for_vacation=True):
        if check_for_vacation and not self._is_everyone_on_vacation(household):
            return []
        sim_infos_for_nanny = []
        for sim_info in household:
            if not sim_info.is_child_or_younger:
                pass
            elif sim_info.is_pet:
                pass
            elif sim_info.is_in_travel_group():
                pass
            else:
                sim_infos_for_nanny.append(sim_info)
        sim_infos_for_nanny.extend(self.get_abandoned_toddlers(household))
        return sim_infos_for_nanny

    def get_number_of_eligible_daycare_sims(self, household):
        return sum(1 for sim_info in household if sim_info.is_toddler_or_younger and not sim_info.is_pet)

    def get_number_of_eligible_nanny_sims(self, household):
        return sum(1 for sim_info in household if sim_info.is_child_or_younger and not sim_info.is_pet)

    def on_sim_spawn(self, sim_info):
        current_zone = services.current_zone()
        if not current_zone.is_zone_running:
            return
        if sim_info.is_child_or_younger:
            return
        household = sim_info.household
        if household is not None:
            if household.home_zone_id == current_zone.id:
                self._unavailable_sims.add(sim_info)
                self.set_sim_available(sim_info)
            else:
                self.set_sim_unavailable(sim_info)

    def on_loading_screen_animation_finished(self):
        household = services.active_household()
        if household is None:
            return
        if household.home_zone_id == services.current_zone_id():
            returning_sim_infos = [sim_info for sim_info in services.sim_info_manager().get_traveled_to_zone_sim_infos() if sim_info not in self._unavailable_sims]
            if returning_sim_infos:
                for sim_info in returning_sim_infos:
                    if sim_info.is_child_or_younger:
                        pass
                    else:
                        self._unavailable_sims.add(sim_info)
                for sim_info in returning_sim_infos:
                    if sim_info.is_child_or_younger:
                        pass
                    else:
                        self.set_sim_available(sim_info, returning_sim_infos=returning_sim_infos)
            else:
                self._enable_daycare_or_nanny_if_necessary(household)
        else:
            self._enable_daycare_or_nanny_if_necessary(household)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=services.active_sim_info())

    def refresh_household_daycare_nanny_status(self, sim_info, try_enable_if_selectable_toddler=False):
        household = services.active_household()
        if household is not None:
            try_enable = try_enable_if_selectable_toddler and (sim_info.is_toddler and sim_info.is_selectable)
            if try_enable or self.is_anyone_with_nanny(household) or self.is_anyone_at_daycare(household):
                self._disable_daycare_or_nanny_if_necessary(household)
            else:
                self._enable_daycare_or_nanny_if_necessary(household)
            services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=sim_info)

    def refresh_daycare_status(self, baby):
        household = baby.household
        if household is None:
            return
        if self.is_daycare_enabled(household):
            self._apply_daycare_effects_to_sim(baby)
        else:
            self._remove_daycare_effects_from_sim(baby)

    def exclude_sim_from_daycare(self, sim_info):
        self._excluded_sims.add(sim_info)

    def is_sim_info_at_daycare(self, sim_info):
        return sim_info.has_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS)

    def is_anyone_at_daycare(self, household):
        return any(sim_info.has_trait(DaycareTuning.DAYCARE_TRAIT_ON_KIDS) for sim_info in household if sim_info.is_toddler_or_younger)

    def is_anyone_with_nanny(self, household):
        return any(sim_info.has_trait(DaycareTuning.NANNY_TRAIT_ON_KIDS) for sim_info in household if sim_info.is_child_or_younger)

    def set_sim_available(self, sim_info, returning_sim_infos=()):
        household = sim_info.household
        daycare_previously_enabled = self.is_anyone_at_daycare(household)
        nanny_previously_enabled = False if daycare_previously_enabled else self.is_anyone_with_nanny(household)
        self._unavailable_sims.discard(sim_info)
        if daycare_previously_enabled or nanny_previously_enabled:
            self._disable_daycare_or_nanny_if_necessary(household, returning_sim_infos=returning_sim_infos)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=sim_info)

    def set_sim_globally_available(self, sim_info):
        self._global_unavailable_sims.discard(sim_info)

    def set_sim_unavailable(self, sim_info):
        household = sim_info.household
        nanny_previously_disabled = not self.is_anyone_with_nanny(household)
        daycare_previously_disabled = True if not nanny_previously_disabled else not self.is_anyone_at_daycare(household)
        self._unavailable_sims.add(sim_info)
        if nanny_previously_disabled or daycare_previously_disabled:
            self._enable_daycare_or_nanny_if_necessary(household)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=sim_info)

    def set_sim_globally_unavailable(self, sim_info):
        self._global_unavailable_sims.add(sim_info)

    def _show_nanny_notification(self, household, sim_infos, is_enable=False):
        if sim_infos:
            if is_enable:
                if len(sim_infos) == 1:
                    self._show_notification(DaycareTuning.SEND_CHILD_TO_NANNY_NOTIFICATION_SINGLE, sim_infos, household)
                else:
                    self._show_notification(DaycareTuning.SEND_CHILD_TO_NANNY_NOTIFICATION_MULTIPLE, sim_infos, household)
            elif len(sim_infos) == 1:
                self._show_notification(DaycareTuning.BRING_CHILD_BACK_FROM_NANNY_NOTIFICATION_SINGLE, sim_infos, household)
            else:
                self._show_notification(DaycareTuning.BRING_CHILD_BACK_FROM_NANNY_NOTIFICATION_MULTIPLE, sim_infos, household)

    def _show_daycare_notification(self, household, sim_infos, is_enable=False):
        if sim_infos:
            if is_enable:
                if len(sim_infos) == 1:
                    self._show_notification(DaycareTuning.SEND_BABY_TO_DAYCARE_NOTIFICATION_SINGLE_BABY, sim_infos, household)
                else:
                    self._show_notification(DaycareTuning.SEND_BABY_TO_DAYCARE_NOTIFICATION_MULTIPLE_BABIES, sim_infos, household)
            elif len(sim_infos) == 1:
                self._show_notification(DaycareTuning.BRING_BABY_BACK_FROM_DAYCARE_NOTIFICATION_SINGLE_BABY, sim_infos, household)
            else:
                self._show_notification(DaycareTuning.BRING_BABY_BACK_FROM_DAYCARE_NOTIFICATION_MULTIPLE_BABIES, sim_infos, household)

    def _show_notification(self, notification, sim_infos, household, resolver=None):
        if not services.current_zone().is_zone_running:
            return
        if not household.is_active_household:
            return
        additional_token = sim_infos if len(sim_infos) > 1 else sim_infos[0]
        dialog = notification(None, resolver)
        dialog.show_dialog(additional_tokens=(additional_token,))

    def send_active_household_toddlers_home(self):
        active_household = services.active_household()
        if active_household is None:
            return
        instanced_toddlers = [sim for sim in active_household.instanced_sims_gen() if sim.sim_info.is_toddler]
        for toddler in instanced_toddlers:
            interaction_context = InteractionContext(toddler, InteractionContext.SOURCE_SCRIPT, Priority.Critical)
            toddler.push_super_affordance(TravelTuning.GO_HOME_INTERACTION, None, interaction_context)
