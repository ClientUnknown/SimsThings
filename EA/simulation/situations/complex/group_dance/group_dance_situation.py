from event_testing.test_events import TestEventfrom interactions.aop import AffordanceObjectPairfrom interactions.constraints import JigConstraint, ObjectJigConstraintfrom interactions.context import InteractionContext, InteractionSourcefrom interactions.jig_part_constraint_interaction import JigPartConstraintInteractionfrom interactions.priority import Priorityfrom objects.system import create_objectfrom sims4.tuning.tunable import TunableTuple, TunableSimMinutefrom sims4.utils import classpropertyfrom situations.situation_complex import CommonSituationState, SituationStateData, SituationComplexCommonimport placementimport servicesimport sims4.logimport situations.situation_typeslogger = sims4.log.Logger('Group Dance', default_owner='trevor')
class _PreSituationState(CommonSituationState):
    PRE_GROUP_DANCE_TIMEOUT = 'pre_group_dance_timeout'

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._test_event_register(TestEvent.InteractionStart, self.owner.constraint_affordance)
        self._create_or_load_alarm(self.PRE_GROUP_DANCE_TIMEOUT, self.owner.pre_situation_state.time_out, lambda _: self.timer_expired(), should_persist=True)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionStart and resolver._interaction.affordance is self.owner.constraint_affordance:
            self.owner.sim_finish_routing(sim_info)

    def timer_expired(self):
        next_state = self.owner.get_next_dance_state()
        self._change_state(next_state())

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(self.PRE_GROUP_DANCE_TIMEOUT)
DANCE_TUNING_GROUP = 'Dance'
class GroupDanceSituation(SituationComplexCommon):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'pre_situation_state': TunableTuple(description='\n            Information related to the pre dance situation state.\n            ', situation_state=_PreSituationState.TunableFactory(description='\n                The pre-dance situation state. Get everyone to their positions\n                and idle.\n                '), time_out=TunableSimMinute(description='\n                How long this will last.\n                ', default=15, minimum=1), tuning_group=DANCE_TUNING_GROUP), 'constraint_affordance': JigPartConstraintInteraction.TunableReference()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jig_object = None
        self._routing_sims = []
        self._jig_index = 0
        self._jig_liability = None
        self._reservation_handler = None

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.DONT

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreSituationState, factory=cls.pre_situation_state.situation_state),)

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.pre_situation_state.situation_state._tuned_values.job_and_role_changes.items())

    @property
    def should_route_sims_on_add(self):
        return False

    def start_situation(self):
        super().start_situation()
        dance_floor = self._get_dance_floor()
        if dance_floor is not None:
            self._reservation_handler = dance_floor.get_reservation_handler(self.initiating_sim_info.get_sim_instance())
            self._reservation_handler.begin_reservation()

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._check_route_sim(sim)

    def _check_route_sim(self, sim):
        raise NotImplementedError

    def get_and_increment_sim_jig_index(self, sim):
        index = self._jig_index
        self._jig_index += 1
        return index

    def _self_destruct(self):
        if self._reservation_handler is not None:
            self._reservation_handler.end_reservation()
            self._reservation_handler = None
        super()._self_destruct()

    def _get_ignored_object_ids(self):
        ignored_sim_ids = [sim.id for sim in self.all_sims_in_situation_gen()]
        return ignored_sim_ids

    def get_jig_definition(self):
        raise NotImplementedError

    def get_next_dance_state(self):
        raise NotImplementedError

    def _create_situation_geometry(self):
        leader_sim = self.initiating_sim_info.get_sim_instance()
        if leader_sim is None:
            logger.error('No leader sim for {}', self)
            self._self_destruct()
            return
        jig_definition = self.get_jig_definition()
        if jig_definition is None:
            logger.error('Failed to retrieve a jig definition for {}', self)
            self._self_destruct()
            return
        self._jig_object = create_object(jig_definition)
        if self._jig_object is None:
            logger.error('Cannot create jig {} for {}', jig_definition, self)
            self._self_destruct()
            return
        search_flags = placement.FGLSearchFlagsDefault | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS
        routing_surface = leader_sim.routing_surface
        dance_floor = self._get_dance_floor()
        start_position = dance_floor.position if dance_floor is not None else leader_sim.position
        starting_location = placement.create_starting_location(position=start_position, routing_surface=routing_surface)
        fgl_context = placement.create_fgl_context_for_object(starting_location, self._jig_object, search_flags=search_flags, ignored_object_ids=self._get_ignored_object_ids())
        (translation, orientation) = placement.find_good_location(fgl_context)
        if translation is not None:
            self._jig_object.move_to(routing_surface=routing_surface, translation=translation, orientation=orientation)

    def _get_dance_floor(self):
        seed = self._seed
        default_target_id = seed.extra_kwargs.get('default_target_id', None)
        if default_target_id is not None:
            dance_floor = services.object_manager().get(default_target_id)
            return dance_floor

    def _route_sim(self, sim, jig_index):
        interaction_context = InteractionContext(sim, InteractionSource.SCRIPT_WITH_USER_INTENT, Priority.High)
        aop = AffordanceObjectPair(self.constraint_affordance, self._jig_object, self.constraint_affordance, None, jig_object=self._jig_object, jig_part_index=jig_index)
        result = aop.test_and_execute(interaction_context)
        if result:
            if self._jig_liability is None:
                liability = JigConstraint.JigConstraintLiability(self._jig_object)
                self._jig_liability = liability
            else:
                liability = JigConstraint.JigConstraintLiability(self._jig_object, source_liability=self._jig_liability)
            result.interaction.add_liability(ObjectJigConstraint.JIG_CONSTRAINT_LIABILITY, liability)
        self._routing_sims.append(sim.id)

    def sim_finish_routing(self, sim_info):
        if sim_info.id in self._routing_sims:
            self._routing_sims.remove(sim_info.id)
            if not self._routing_sims:
                next_state = self.get_next_dance_state()
                self._change_state(next_state())
        else:
            logger.error('Sim {} finishes routing but not in routing sim list of situation {}', sim_info, self)
