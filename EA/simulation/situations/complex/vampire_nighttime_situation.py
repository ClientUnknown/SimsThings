from bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom buffs.tunable import TunableBuffReferencefrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions.base.interaction import Interactionfrom interactions.context import QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_liabilities import UncancelableLiability, UNCANCELABLE_LIABILITYfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, TunableEnumWithFilter, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom situations.ambient.walkby_limiting_tags_mixin import WalkbyLimitingTagsMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonInteractionCompletedSituationState, SituationStatefrom situations.situation_job import SituationJobfrom tag import Tagimport event_testingimport interactionsimport servicesimport sims4.logimport sims4.tuning.instancesimport sims4.tuning.tunableimport situations.bouncerimport taglogger = sims4.log.Logger('VampireNighttime', default_owner='camilogarcia')
class VampireInterruptableStateMixin(CommonInteractionCompletedSituationState):

    def on_activate(self, reader):
        super().on_activate(reader)
        for buff in self.owner.vampire_discovered_buffs:
            self._test_event_register(event_testing.test_events.TestEvent.BuffBeganEvent, buff.buff_type)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.BuffBeganEvent:
            added_buff = resolver.event_kwargs['buff']
            if any(buff.buff_type is added_buff for buff in self.owner.vampire_discovered_buffs):
                self._change_state(self.owner.vampire_job.leave_startled_state())

class _VampireArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        sim_found = False
        for sim in services.active_household().instanced_sims_gen():
            resolver = SingleSimResolver(sim.sim_info)
            if self.owner.household_sim_tests.run_tests(resolver):
                sim_found = True
            if not sim.sleeping:
                self._change_state(_LeaveState())
                return
        if not sim_found:
            self._change_state(_LeaveState())
            return
        self._change_state(self.owner.vampire_job.break_in_state())

class _BreakInState(VampireInterruptableStateMixin):

    def on_activate(self, reader=None):
        self.owner.lock_save()
        super().on_activate(reader)
        for sim in services.active_household().instanced_sims_gen():
            for si in sim.si_state:
                if self.owner.sleep_category_tag in si.affordance.interaction_category_tags:
                    si.add_liability(UNCANCELABLE_LIABILITY, UncancelableLiability())
        vampire_sim = self.owner.vampire_sim()
        bucks_tracker = BucksUtils.get_tracker_for_bucks_type(self.owner.power_buck_type, owner_id=vampire_sim.id)
        if bucks_tracker is not None:
            for active_power in self.owner.active_powers:
                if bucks_tracker.is_perk_unlocked(active_power.power):
                    vampire_sim.add_buff_from_op(buff_type=active_power.buff_to_add.buff_type, buff_reason=active_power.buff_to_add.buff_reason)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.vampire_job.bite_state())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete and resolver(self._interaction_of_interest):
            self.owner.register_selected_sim(resolver._interaction.target)
            self._on_interaction_of_interest_complete()
        super().handle_event(sim_info, event, resolver)

class _BiteState(VampireInterruptableStateMixin):
    FACTORY_TUNABLES = {'bite_interaction': Interaction.TunableReference(description='\n            Bite interaction to push on the selected Sim to be run by the\n            visiting vampire.\n            ')}

    def __init__(self, bite_interaction, **kwargs):
        super().__init__(**kwargs)
        self._bite_interaction = bite_interaction

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for si in self.owner.selected_sim.si_state:
            si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Vampire bite required cancelation.')
        vampire_sim = self.owner.vampire_sim()
        context = interactions.context.InteractionContext(vampire_sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
        enqueue_result = vampire_sim.push_super_affordance(self._bite_interaction, self.owner.selected_sim, context)
        if not enqueue_result:
            logger.error('Bite state interaction failed to push with result {}', enqueue_result)
            self._change_state(_LeaveState())

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(_LeaveState())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete:
            vampire_sim = self.owner.vampire_sim()
            if vampire_sim is None or vampire_sim.sim_info is not sim_info:
                return
            if resolver(self._interaction_of_interest):
                self._on_interaction_of_interest_complete()

class _LeaveStartledState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(_LeaveState())

class _LeaveState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        sim = self.owner.vampire_sim()
        if sim is not None:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

class VampireNighttimeSituation(WalkbyLimitingTagsMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'vampire_job': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                A reference to the SituationJob used for the Sim performing the\n                vampire nighttime situation.\n                '), arrival_state=_VampireArrivalState.TunableFactory(description='\n                The state for telling a Sim to go and to the active lot from\n                the walkby spawn point.\n                '), break_in_state=_BreakInState.TunableFactory(description='\n                The state for pushing the Sim into the house depending on the\n                active powers that it has.\n                '), bite_state=_BiteState.TunableFactory(description='\n                The state for forcing the bite interaction on the chosen\n                target Sim.\n                '), leave_startled_state=_LeaveStartledState.TunableFactory(description='\n                The state for forcing the the vampire to leave.\n                '), tuning_group=GroupNames.SITUATION), 'vampire_discovered_buffs': TunableList(description="\n            Buff's that will push the vampire to leave the situation since \n            it's been discovered by the household owners or by an anti vampire\n            object.\n            ", tunable=TunableBuffReference(description='\n                Buff to make the vampire enter its discovered state.\n                ', pack_safe=True)), 'sleep_category_tag': TunableEnumWithFilter(description='\n            These tag values are used for testing interactions.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(tag.Tag.INVALID,), filter_prefixes=('Interaction',)), 'power_buck_type': TunableEnumEntry(description='\n            Type of buck type for the vampire powers to be enabled for the \n            vampire trying to enter into the visiting household.\n            ', tunable_type=BucksType, default=BucksType.INVALID), 'active_powers': TunableList(description='\n            A list of Perks and buff to add if the perk is unlocked whenever\n            the vampire decides to enter the household.\n            ', tunable=TunableTuple(description='\n                Tuple of perk and buff powers.\n                ', power=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)), buff_to_add=TunableBuffReference(description='\n                    Temporary buff to add for the specified power to the Sim \n                    while doing the break in.\n                    '))), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI), 'household_sim_tests': TunableTestSet(description='\n            Tests to verify the Sims on the household can be valid targets\n            for the nightime visit.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_sim = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _VampireArrivalState, factory=cls.vampire_job.arrival_state), SituationStateData(2, _BreakInState, factory=cls.vampire_job.break_in_state), SituationStateData(3, _BiteState, factory=cls.vampire_job.bite_state), SituationStateData(4, _LeaveState), SituationStateData(5, _LeaveStartledState, factory=cls.vampire_job.leave_startled_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.vampire_job.situation_job, cls.vampire_job.arrival_state)]

    @classmethod
    def default_job(cls):
        return cls.vampire_job.situation_job

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    def vampire_sim(self):
        sim = next(self.all_sims_in_job_gen(self.default_job()), None)
        return sim

    def _destroy(self):
        for sim in services.active_household().instanced_sims_gen():
            for si in sim.si_state:
                if self.sleep_category_tag in si.affordance.interaction_category_tags:
                    si.remove_liability(UNCANCELABLE_LIABILITY)
        super()._destroy()
        services.get_persistence_service().unlock_save(self)

    def register_selected_sim(self, selected_sim):
        self.selected_sim = selected_sim

    def start_situation(self):
        super().start_situation()
        self._change_state(self.vampire_job.arrival_state())

    def lock_save(self):
        services.get_persistence_service().lock_save(self)

    def get_lock_save_reason(self):
        return self.save_lock_tooltip
sims4.tuning.instances.lock_instance_tunables(VampireNighttimeSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.WALKBY_SNATCHER, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)