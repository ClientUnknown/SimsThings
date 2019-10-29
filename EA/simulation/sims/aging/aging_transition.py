from event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom interactions.utils.loot import LootActionsfrom relationships.relationship_bit import RelationshipBitfrom sims.sim_dialogs import SimPersonalityAssignmentDialogfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableTuple, TunableReference, TunableList, TunableSet, OptionalTunable, TunableVariant, TunableLiteralOrRandomValuefrom sims4.tuning.tunable_base import GroupNamesfrom snippets import define_snippetfrom ui.ui_dialog import PhoneRingTypefrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.resources
class AgingTransition(HasTunableSingletonFactory, AutoFactoryInit):

    class _AgeTransitionShowDialog(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'dialog': SimPersonalityAssignmentDialog.TunableFactory(locked_args={'phone_ring_type': PhoneRingType.NO_RING})}

        def __call__(self, sim_info, **kwargs):
            dialog = self.dialog(sim_info, assignment_sim_info=sim_info, resolver=SingleSimResolver(sim_info))
            dialog.show_dialog(**kwargs)

    class _AgeTransitionShowNotification(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'dialog': UiDialogNotification.TunableFactory()}

        def __call__(self, sim_info, **__):
            dialog = self.dialog(sim_info, resolver=SingleSimResolver(sim_info))
            dialog.show_dialog()

    FACTORY_TUNABLES = {'age_up_warning_notification': OptionalTunable(tunable=UiDialogNotification.TunableFactory(description='\n                Notification to show up when Age Up is impending.\n                ', tuning_group=GroupNames.UI)), 'age_up_available_notification': OptionalTunable(tunable=UiDialogNotification.TunableFactory(description='\n                Notification to show when Age Up is ready.\n                ', tuning_group=GroupNames.UI)), '_age_duration': TunableLiteralOrRandomValue(description="\n            The time, in Sim days, required for a Sim to be eligible to\n            transition from this age to the next one.\n            \n            If a random range is specified, the random value will be seeded on\n            the Sim's ID.\n            ", tunable_type=float, default=1), '_use_initial_age_randomization': Tunable(description="\n            If checked, instead of randomizing the duration of each individual age,\n            the sims's initial age progress will be randomly offset on first load. \n            ", tunable_type=bool, default=False), 'age_transition_warning': Tunable(description='\n            Number of Sim days prior to the transition a Sim will get a warning\n            of impending new age.\n            ', tunable_type=float, default=1), 'age_transition_delay': Tunable(description='\n            Number of Sim days after transition time elapsed before auto- aging\n            occurs.\n            ', tunable_type=float, default=1), 'age_transition_dialog': TunableVariant(description='\n            The dialog or notification that is displayed when the Sim ages up.\n            ', show_dialog=_AgeTransitionShowDialog.TunableFactory(), show_notification=_AgeTransitionShowNotification.TunableFactory(), locked_args={'no_dialog': None}, default='no_dialog', tuning_group=GroupNames.UI), 'age_trait': TunableReference(description="\n            The age trait that corresponds to this Sim's age\n            ", manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), 'relbit_based_loot': TunableList(description='\n            List of loots given based on bits set in existing relationships.\n            Applied after per household member loot.\n            ', tunable=TunableTuple(description='\n                Loot given to sim aging up (actor) and each sim (target) with a\n                "chained" relationship via recursing through the list of relbit\n                sets.\n                ', relationship=TunableList(description='\n                    List specifying a series of relationship(s) to recursively \n                    traverse to find the desired target sim.  i.e. to find \n                    "cousins", we get all the "parents".  And then we \n                    get "aunts/uncles" by getting the "siblings" of those \n                    "parents".  And then we finally get the "cousins" by \n                    getting the "children" of those "aunts/uncles".\n                    \n                    So:\n                     Set of "parent" bitflag(s)\n                     Set of "sibling" bitflag(s)\n                     Set of "children" bitflag(s)\n                    \n                    Can also find direct existing relationships by only having a\n                    single entry in the list.\n                    ', tunable=TunableSet(description='\n                        Set of relbits to use for this relationship.\n                        ', tunable=RelationshipBit.TunableReference(description='\n                            The relationship bit between greeted Sims.\n                            ', pack_safe=True))), loot=TunableList(description='\n                    Loot given between sim aging up and sims with the previously\n                    specified chain of relbits. (may create a relationship).\n                    ', tunable=LootActions.TunableReference(description='\n                        A loot action given to sim aging up.\n                        ', pack_safe=True))), tuning_group=GroupNames.TRIGGERS), 'per_household_member_loot': TunableList(description="\n            Loots given between sim aging up (actor) and each sim in that sims\n            household (target).  Applied before relbit based loot'\n            ", tunable=LootActions.TunableReference(description='\n                A loot action given between sim aging up (actor) and each sim in\n                that sims household (target).\n                ', pack_safe=True), tuning_group=GroupNames.TRIGGERS), 'single_sim_loot': TunableList(description='\n            Loots given to sim aging up (actor). Last loot applied.\n            ', tunable=LootActions.TunableReference(description='\n                A loot action given to sim aging up.\n                ', pack_safe=True), tuning_group=GroupNames.TRIGGERS)}

    def get_age_duration(self, sim_info):
        if self._use_initial_age_randomization:
            return (self._age_duration.upper_bound + self._age_duration.lower_bound)/2
        return self._get_random_age_duration(sim_info)

    def _get_random_age_duration(self, sim_info):
        return self._age_duration.random_float(seed=(self.age_trait.guid64, sim_info.sim_id))

    def get_randomized_progress(self, sim_info, age_progress):
        if self._use_initial_age_randomization:
            previous_age_duration = self._get_random_age_duration(sim_info)
            current_age_duration = self.get_age_duration(sim_info)
            if sims4.math.almost_equal(previous_age_duration, current_age_duration):
                return age_progress
            age_progress = current_age_duration + age_progress - previous_age_duration
            if age_progress < 0:
                age_progress = self._age_duration.upper_bound - self._age_duration.lower_bound + age_progress
        return age_progress

    def _apply_aging_transition_relbit_loot(self, source_info, cur_info, relbit_based_loot, level):
        if level == len(relbit_based_loot.relationship):
            resolver = DoubleSimResolver(source_info, cur_info)
            for loot in relbit_based_loot.loot:
                loot.apply_to_resolver(resolver)
            return
        relationship_tracker = cur_info.relationship_tracker
        for target_sim_id in relationship_tracker.target_sim_gen():
            if set(relationship_tracker.get_all_bits(target_sim_id)) & relbit_based_loot.relationship[level]:
                new_sim_info = services.sim_info_manager().get(target_sim_id)
                self._apply_aging_transition_relbit_loot(source_info, new_sim_info, relbit_based_loot, level + 1)

    def apply_aging_transition_loot(self, sim_info):
        if self.per_household_member_loot:
            for member_info in sim_info.household.sim_info_gen():
                if member_info is sim_info:
                    pass
                else:
                    resolver = DoubleSimResolver(sim_info, member_info)
                    for household_loot in self.per_household_member_loot:
                        household_loot.apply_to_resolver(resolver)
        for relbit_based_loot in self.relbit_based_loot:
            self._apply_aging_transition_relbit_loot(sim_info, sim_info, relbit_based_loot, 0)
        resolver = SingleSimResolver(sim_info)
        for loot in self.single_sim_loot:
            loot.apply_to_resolver(resolver)

    def show_age_transition_dialog(self, sim_info, **kwargs):
        if self.age_transition_dialog is not None:
            self.age_transition_dialog(sim_info, **kwargs)
(TunableAgingTransitionReference, _) = define_snippet('Aging_Transition', AgingTransition.TunableFactory())