import randomfrom interactions.interaction_finisher import FinishingTypefrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableSimMinute, TunableSet, TunableEnumWithFilterfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.ambient.walkby_limiting_tags_mixin import WalkbyLimitingTagsMixinfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateDatafrom situations.situation_job import SituationJobfrom tag import Tagimport alarmsimport clockimport interactionsimport servicesimport sims4.logimport sims4.tuning.tunableimport situations.bouncerimport terrainlogger = sims4.log.Logger('Walkby')
class WalkbyAmbientSituation(WalkbyLimitingTagsMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'walker_job': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                        A reference to the SituationJob used for the Sim performing the walkby\n                        '), walkby_state=RoleState.TunableReference(description='The state while the sim is walking by.'), flavor_interaction_state=RoleState.TunableReference(description='\n                            The role state when the sim does a flavor interaction.\n                            '), tuning_group=GroupNames.SITUATION), 'flavor_affordances': sims4.tuning.tunable.TunableList(description='\n            When selected for walkby flavor the sim runs one of the affordances in\n            this list.\n            ', tunable=sims4.tuning.tunable.TunableReference(services.affordance_manager())), 'flavor_cooldown': TunableSimMinute(description='\n                The minimum amount of time from the end of one flavor action\n                until the walkby sim can perform another.\n                ', default=5, minimum=1, maximum=480), 'flavor_chance_to_start': sims4.tuning.tunable.TunablePercent(description='\n                This is the percentage chance that each walkby sim will start a flavor\n                interaction, such as using the phone, on an\n                ambient service ping. At most one will start per ping.\n                ', default=1)}
    REMOVE_INSTANCE_TUNABLES = situations.situation.Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _LeaveState), SituationStateData(2, _FlavorInteractionState), SituationStateData(3, _SocialState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.walker_job.situation_job, cls.walker_job.walkby_state)]

    @classmethod
    def default_job(cls):
        return cls.walker_job.situation_job

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._walker = None
        self._flavor_cooldown_until = services.time_service().sim_now + clock.interval_in_sim_minutes(10)
        self._social_cooldown_until = services.time_service().sim_now + clock.interval_in_sim_minutes(10)
        self._other_social_situation = None
        self._social_interaction = None

    def start_situation(self):
        super().start_situation()
        initial_state = self._states()[0].state_type
        self._change_state(initial_state())

    def _save_custom_state(self, writer):
        uid = self._state_type_to_uid(_LeaveState)
        writer.write_uint32(situations.situation_complex.SituationComplexCommon.STATE_ID_KEY, uid)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.default_job():
            self._walker = sim

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if self._walker is sim:
            self._walker = None

    def _on_sim_removed_from_situation_prematurely(self, sim, sim_job):
        super()._on_sim_removed_from_situation_prematurely(sim, sim_job)
        self.manager.add_sim_to_auto_fill_blacklist(sim.id, sim_job)

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    def get_sim_available_for_walkby_flavor(self):
        if self._cur_state is None or not self._cur_state._is_available_for_interruption():
            return
        if services.time_service().sim_now < self._flavor_cooldown_until:
            return
        if self._walker is not None and self._walker.opacity < 1.0:
            return
        if self._walker is not None and terrain.is_position_in_street(self._walker.position):
            return
        return self._walker

    def get_sim_available_for_social(self):
        if self._cur_state is None or not self._cur_state._is_available_for_interruption():
            return
        if services.time_service().sim_now < self._social_cooldown_until:
            return
        if self._walker is not None and self._walker.opacity < 1.0:
            return
        return self._walker

    def random_chance_to_start_flavor_interaction(self):
        return sims4.random.random_chance(self.flavor_chance_to_start*100)

    def start_flavor_interaction(self):
        self._change_state(_FlavorInteractionState())

    def start_social(self, other_situation, social_interaction=None):
        self._other_social_situation = other_situation
        self._social_interaction = social_interaction
        self._change_state(_SocialState())

    def _on_flavor_finished(self):
        self._flavor_cooldown_until = services.time_service().sim_now + clock.interval_in_sim_minutes(self.flavor_cooldown)
        self._change_state(_LeaveState())

    def _on_social_finished(self):
        self._other_social_situation = None
        self._social_interaction = None
        self._social_cooldown_until = services.time_service().sim_now + clock.interval_in_sim_minutes(services.current_zone().ambient_service.SOCIAL_COOLDOWN)
        self._change_state(_LeaveState())

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.OPEN_STREETS
sims4.tuning.instances.lock_instance_tunables(WalkbyAmbientSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.WALKBY, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)
class _LeaveState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.walker_job.situation_job, self.owner.walker_job.walkby_state)

    def _is_available_for_interruption(self):
        return True

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (self.owner.walker_job.walkby_state, role_affordance_target)

class _FlavorInteractionState(SituationState):

    def __init__(self):
        super().__init__()
        self._interaction = None

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.walker_job.situation_job, self.owner.walker_job.flavor_interaction_state)

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        self.owner._cancel_leave_interaction(sim)
        success = self._push_interaction(sim)
        if not success:
            self.owner._on_flavor_finished()

    def on_deactivate(self):
        if self._interaction is not None:
            self._interaction.unregister_on_finishing_callback(self._on_finishing_callback)
            self._interaction = None
        super().on_deactivate()

    def _push_interaction(self, sim):
        affordances = self.owner.flavor_affordances
        if not affordances:
            return False
        affordance = affordances[random.randint(0, len(affordances) - 1)]
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High)
        enqueue_result = sim.push_super_affordance(affordance, None, context)
        if enqueue_result and enqueue_result.interaction.is_finishing:
            return False
        self._interaction = enqueue_result.interaction
        self._interaction.register_on_finishing_callback(self._on_finishing_callback)
        return True

    def _on_finishing_callback(self, interaction):
        if self._interaction is not interaction:
            return
        self.owner._on_flavor_finished()

    def _is_available_for_interruption(self):
        return False

class _SocialState(SituationState):

    def __init__(self):
        super().__init__()
        self._other_situation = None
        self._interaction = None
        self._timeout_handle = None
        self._sim_id = None

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._other_situation = self.owner._other_social_situation
        self._interaction = self.owner._social_interaction
        self._timeout_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(services.current_zone().ambient_service.SOCIAL_MAX_DURATION), self.timer_expired)
        self.owner._set_job_role_state(self.owner.walker_job.situation_job, self.owner.walker_job.flavor_interaction_state)

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        self.owner._cancel_leave_interaction(sim)
        self._sim_id = sim.sim_id
        if self._interaction is not None:
            self._interaction.register_on_finishing_callback(self._on_finishing_callback)
            return
        target_sim = self._other_situation.get_sim_available_for_walkby_flavor()
        if target_sim is None:
            self.owner._on_social_finished()
            return
        self._interaction = self._push_social(sim, target_sim)
        if self._interaction is not None:
            self._interaction.register_on_finishing_callback(self._on_finishing_callback)
            self._other_situation.start_social(self, self._interaction)
        else:
            self.owner._on_social_finished()

    def on_deactivate(self):
        if self._interaction is not None:
            self._interaction.unregister_on_finishing_callback(self._on_finishing_callback)
            self._interaction = None
        if self._timeout_handle is not None:
            alarms.cancel_alarm(self._timeout_handle)
            self._timeout_handle = None
        if self._sim_id is not None:
            sim = services.object_manager().get(self._sim_id)
            if sim is not None and self._on_social_group_changed in sim.on_social_group_changed:
                sim.on_social_group_changed.remove(self._on_social_group_changed)
        super().on_deactivate()

    def _push_social(self, sim, target_sim):
        affordances = services.current_zone().ambient_service.SOCIAL_AFFORDANCES
        if not affordances:
            return
        affordance = affordances[random.randint(0, len(affordances) - 1)]
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High)
        enqueue_result = sim.push_super_affordance(affordance, target_sim, context)
        if enqueue_result and enqueue_result.interaction.is_finishing:
            return
        return enqueue_result.interaction

    def _on_finishing_callback(self, interaction):
        if self._interaction is not interaction:
            return
        if self._sim_id is not None:
            sim = services.object_manager().get(self._sim_id)
            if sim is not None and tuple(sim.get_groups_for_sim_gen()):
                self._interaction = None
                if self._on_social_group_changed not in sim.on_social_group_changed:
                    sim.on_social_group_changed.append(self._on_social_group_changed)
                return
        self.owner._on_social_finished()

    def _on_social_group_changed(self, sim, group):
        if self._sim_id is not None:
            sim = services.object_manager().get(self._sim_id)
            if sim is not None and not tuple(sim.get_groups_for_sim_gen()):
                self.owner._on_social_finished()

    def timer_expired(self, _):
        if self._interaction is not None:
            self._interaction.cancel(FinishingType.SITUATIONS, 'Social walkby state timeout')

    def _is_available_for_interruption(self):
        return False
