from event_testing.resolver import DoubleSimResolverfrom interactions import ParticipantTypefrom interactions.base.super_interaction import SuperInteractionfrom objects import ALL_HIDDEN_REASONSfrom relationships.relationship_tests import TunableRelationshipTestfrom situations.visiting.visiting_tuning import VisitingTuningfrom ui.ui_dialog_notification import UiDialogNotificationimport interactionsimport servicesimport sims4logger = sims4.log.Logger('VisitingInteractions', default_owner='camilogarcia')
class RingDoorbellSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'_nobody_home_failure_notification': UiDialogNotification.TunableFactory(description='\n                Notification that displays if no one was home when they tried\n                to ring the doorbell.\n                '), '_bad_relationship_failure_notification': UiDialogNotification.TunableFactory(description="\n                Notification that displays if there wasn't high enough\n                relationship with any of the household members when they\n                tried to ring the doorbell.\n                "), '_success_notification': UiDialogNotification.TunableFactory(description='\n                Notification that displays if the user succeeded in becoming\n                greeted when they rang the doorbell.\n                '), '_relationship_test': TunableRelationshipTest(description='\n                The Relationship test ran between the sim running the\n                interaction and all of the npc family members to see if they\n                are allowed in.\n                ', locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.TargetSim})}

    def _get_owner_sim_infos(self):
        owner_household_or_travel_group = services.household_manager().get(services.current_zone().lot.owner_household_id)
        if owner_household_or_travel_group is None:
            owner_household_or_travel_group = services.travel_group_manager().get_travel_group_by_zone_id(services.current_zone_id())
        if owner_household_or_travel_group is None:
            return
        owner_sim_infos = tuple(owner_household_or_travel_group)
        return owner_sim_infos

    def _make_greeted(self):
        services.get_zone_situation_manager().make_waiting_player_greeted(self.sim)
        self._try_make_always_welcomed(self.sim)

    def _try_make_always_welcomed(self, sim):
        if any(sim.sim_info.has_trait(trait) for trait in VisitingTuning.ALWAYS_WELCOME_TRAITS):
            current_household = services.owning_household_of_active_lot()
            if current_household is None:
                logger.error('Current household is None when trying to run the ring doorbell interaction for visiting sim {}', sim)
                return
            current_household.add_always_welcome_sim(sim.sim_info.id)

    def _show_nobody_home_dialog(self):
        resolver = self.get_resolver()
        dialog = self._nobody_home_failure_notification(self.sim, resolver)
        dialog.show_dialog()

    def _try_to_be_invited_in(self):
        owner_sim_infos = self._get_owner_sim_infos()
        if owner_sim_infos is None:
            self._show_nobody_home_dialog()
            return
        occupants = tuple(sim_info for sim_info in owner_sim_infos if sim_info.is_at_home)
        num_occupants = len(occupants)
        for sim_info in occupants:
            if sim_info.is_pet:
                num_occupants -= 1
            else:
                sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if not sim is None:
                    if sim.has_running_and_queued_interactions_with_liability(interactions.rabbit_hole.RABBIT_HOLE_LIABILTIY):
                        num_occupants -= 1
                num_occupants -= 1
        if num_occupants == 0:
            self._show_nobody_home_dialog()
            return
        for occupant in occupants:
            relationship_resolver = DoubleSimResolver(self.sim.sim_info, occupant)
            if relationship_resolver(self._relationship_test):
                resolver = self.get_resolver()
                dialog = self._success_notification(self.sim, resolver)
                dialog.show_dialog()
                self._make_greeted()
                return
        dialog = self._bad_relationship_failure_notification(self.sim, resolver)
        dialog.show_dialog()

    def _post_perform(self):
        super()._post_perform()
        self.add_exit_function(self._try_to_be_invited_in)
