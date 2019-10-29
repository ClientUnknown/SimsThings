from event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom role.role_state import RoleStatefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableSimMinutefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableInteractionOfInterest, SituationState, SituationStateDatafrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionimport alarmsimport clockimport interactionsimport servicesimport sims4.tuning.tunableimport situations.bouncer.bouncer_typeslogger = sims4.log.Logger('Situations')
class FamilyMealSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'chef': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                    The SituationJob for the sim making the meal.'), chef_cooking_role_state=RoleState.TunableReference(description="\n                    Chef's role state while making food."), chef_eating_role_state=RoleState.TunableReference(description="\n                    Chef's role state when eating."), tuning_group=GroupNames.ROLES), 'household_eater': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                    The SituationJob for an eater (a non-chef) sim.'), household_eater_cooking_role_state=RoleState.TunableReference(description="\n                    Eater's role state while food is being prepared."), household_eater_eating_role_state=RoleState.TunableReference(description="\n                    Eater's role state when eating."), tuning_group=GroupNames.ROLES), 'guest_eater': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description="\n                    The SituationJob for an eater (a non-chef) sim who doesn't live here."), guest_eater_cooking_role_state=RoleState.TunableReference(description="\n                    Guest eater's role state while food is being prepared."), guest_eater_eating_role_state=RoleState.TunableReference(description="\n                    Guest eater's role state when eating."), tuning_group=GroupNames.ROLES), 'cook_group_meal_interaction': TunableInteractionOfInterest(description='\n                                            When this interaction is started, the chef has successfully\n                                            begun preparing the meal.', tuning_group=GroupNames.TRIGGERS), 'meal_is_done_interaction': TunableInteractionOfInterest(description='\n                                            When this interaction has been completed by the chef, it will\n                                            signal the end of the eating phase.', tuning_group=GroupNames.TRIGGERS), 'call_to_meal_interaction': sims4.tuning.tunable.TunableReference(description='\n                                            Interaction that is pushed on the chef sim with the crafted \n                                            object as the target. \n                                            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'trying_to_cook_timeout': TunableSimMinute(description='\n                        The amount of time the sim will attempt to try to start cooking.', default=30, tuning_group=GroupNames.TRIGGERS), 'cooking_timeout': TunableSimMinute(description='\n                        The amount of time the sim will attempt to actually cook.', default=60, tuning_group=GroupNames.TRIGGERS), 'meal_timeout': TunableSimMinute(description='\n                        The amount of time the meal will last, assuming not all sims made it to the meal.', default=30, tuning_group=GroupNames.TRIGGERS)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, TryingToCookState), SituationStateData(2, CookState), SituationStateData(3, EatState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.chef.situation_job, cls.chef.chef_cooking_role_state), (cls.household_eater.situation_job, cls.household_eater.household_eater_cooking_role_state), (cls.guest_eater.situation_job, cls.guest_eater.guest_eater_cooking_role_state)]

    @classmethod
    def default_job(cls):
        return cls.guest_eater.situation_job

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chef_id = None

    @property
    def chef_id(self):
        return self._chef_id

    def start_situation(self):
        super().start_situation()
        self._change_state(TryingToCookState())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.chef.situation_job:
            self._chef_id = sim.sim_id

    def _has_chef_started_cooking(self, event, resolver):
        if resolver(self.cook_group_meal_interaction):
            participants = resolver.get_participants(ParticipantType.Actor)
            for sim_info in participants:
                if sim_info.id == self.chef_id:
                    return True
        return False

    def _is_chef_finished_eating(self, event, resolver):
        if resolver(self.meal_is_done_interaction):
            participants = resolver.get_participants(ParticipantType.Actor)
            for sim_info in participants:
                if sim_info.id == self.chef_id:
                    return True
        return False

    def _was_cooking_interaction_canceled(self, event, resolver):
        if resolver.interaction.has_been_user_canceled:
            participants = resolver.get_participants(ParticipantType.Actor)
            for sim_info in participants:
                if sim_info.id == self.chef_id:
                    return True
        return False
lock_instance_tunables(FamilyMealSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)
class TryingToCookState(SituationState):

    def __init__(self):
        super().__init__()
        self._try_to_cook_timeout_alarm_handle = None

    def on_activate(self, reader=None):
        super().on_activate(reader)
        trying_to_cook_timeout = self.owner.trying_to_cook_timeout
        if reader is not None:
            trying_to_cook_timeout = reader.read_float('trying_to_cook_timeout', trying_to_cook_timeout)
        self._try_to_cook_timeout_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(trying_to_cook_timeout), self._try_and_cook_timeout_callback)
        for custom_key in self.owner.cook_group_meal_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)

    def save_state(self, writer):
        super().save_state(writer)
        if self._try_to_cook_timeout_alarm_handle is not None:
            writer.write_float('try_and_cook_timeout', self._try_to_cook_timeout_alarm_handle.get_remaining_time().in_minutes())

    def on_deactivate(self):
        if self._try_to_cook_timeout_alarm_handle is not None:
            alarms.cancel_alarm(self._try_to_cook_timeout_alarm_handle)
            self._try_to_cook_timeout_alarm_handle = None
        super().on_deactivate()

    def _try_and_cook_timeout_callback(self, _):
        self.owner._self_destruct()

    def handle_event(self, sim_info, event, resolver):
        if self.owner._has_chef_started_cooking(event, resolver):
            self._change_state(CookState())

class CookState(SituationState):

    def __init__(self):
        super().__init__()
        self._cooking_timeout_alarm_handle = None

    def on_activate(self, reader=None):
        super().on_activate(reader)
        cooking_timeout = self.owner.cooking_timeout
        if reader is not None:
            cooking_timeout = reader.read_float('cooking_timeout', cooking_timeout)
        self._cooking_timeout_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(cooking_timeout), self._cooking_timeout_callback)
        self._test_event_register(TestEvent.ItemCrafted)
        for custom_key in self.owner.cook_group_meal_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def save_state(self, writer):
        super().save_state(writer)
        if self._cooking_timeout_alarm_handle is not None:
            writer.write_float('cooking_timeout', self._cooking_timeout_alarm_handle.get_remaining_time().in_minutes())

    def on_deactivate(self):
        if self._cooking_timeout_alarm_handle is not None:
            alarms.cancel_alarm(self._cooking_timeout_alarm_handle)
            self._cooking_timeout_alarm_handle = None
        super().on_deactivate()

    def _cooking_timeout_callback(self, _):
        self.owner._self_destruct()

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.ItemCrafted:
            if sim_info.sim_id == self.owner.chef_id:
                self._push_call_to_meal_interaction(sim_info, resolver)
                self.owner._self_destruct()
        elif event == TestEvent.InteractionComplete and self.owner._was_cooking_interaction_canceled(event, resolver):
            self.owner._self_destruct()

    def _push_call_to_meal_interaction(self, sim_info, resolver):
        crafted_object = resolver.event_kwargs['crafted_object']
        if crafted_object is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.Low, client=None, pick=None)
        for aop in crafted_object.potential_interactions(context):
            if aop.affordance is self.owner.call_to_meal_interaction:
                result = aop.test_and_execute(context)
                if not result:
                    logger.info('Unable to push {} because of {}'.format(aop, result))
                return

class EatState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_duration_alarm(duration_override=1)
