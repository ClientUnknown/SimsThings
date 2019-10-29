from _sims4_collections import frozendictfrom element_utils import build_element, CleanupTypefrom elements import SoftSleepElementfrom event_testing.resolver import GlobalResolver, SingleSimResolver, SingleActorAndObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.interaction_finisher import FinishingTypefrom objects.object_creation import ObjectCreationOpfrom objects.placement.placement_helper import _PlacementStrategyLocationfrom sims4 import randomfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableSimMinute, TunableSet, OptionalTunable, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateDatafrom tag import TunableTagsfrom tunable_multiplier import TunableMultiplierfrom vfx import PlayEffectimport clockimport services
class _PreparationState(CommonSituationState):
    FACTORY_TUNABLES = {'creation_ops': TunableList(tunable=ObjectCreationOp.TunableFactory(description='\n                The operation that will create the objects.\n                ', locked_args={'destroy_on_placement_failure': True})), 'locked_args': {'job_and_role_changes': frozendict(), 'allow_join_situation': False, 'time_out': None}}

    def __init__(self, *args, creation_ops=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_ops = creation_ops

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        resolver = self.owner._get_placement_resolver()
        for operation in self.creation_ops:
            operation.apply_to_resolver(resolver)
        self.owner.on_objects_ready()

class _WaitingToMoveState(CommonSituationState):
    FACTORY_TUNABLES = {'locked_args': {'job_and_role_changes': frozendict(), 'allow_join_situation': False}}

    def timer_expired(self):
        self.owner.on_ready_to_move()
OBJECT_TOKEN = 'object_id'
class MovingObjectsSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_preparation_state': _PreparationState.TunableFactory(tuning_group=GroupNames.STATE), '_waiting_to_move_state': _WaitingToMoveState.TunableFactory(tuning_group=GroupNames.STATE), '_tests_to_continue': TunableTestSet(description='\n            A list of tests that must pass in order to continue the situation\n            after the tuned duration for the waiting state has elapsed.\n            ', tuning_group=GroupNames.STATE), 'starting_requirements': TunableTestSet(description='\n            A list of tests that must pass in order for the situation\n            to start.\n            ', tuning_group=GroupNames.SITUATION), 'object_tags': TunableTags(description='\n            Tags used to find objects which will move about.\n            ', tuning_group=GroupNames.SITUATION), 'placement_strategy_locations': TunableList(description='\n            A list of weighted location strategies.\n            ', tunable=TunableTuple(weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this strategy relative to other locations.\n                    '), placement_strategy=_PlacementStrategyLocation.TunableFactory(description='\n                    The placement strategy for the object.\n                    ')), minlength=1, tuning_group=GroupNames.SITUATION), 'fade': OptionalTunable(description='\n            If enabled, the objects will fade-in/fade-out as opposed to\n            immediately moving to their location.\n            ', tunable=TunableTuple(out_time=TunableSimMinute(description='\n                    Time over which the time will fade out.\n                    ', default=1), in_time=TunableSimMinute(description='\n                    Time over which the time will fade in.\n                    ', default=1)), enabled_by_default=True, tuning_group=GroupNames.SITUATION), 'vfx_on_move': OptionalTunable(description='\n            If tuned, apply this one-shot vfx on the moving object when it\n            is about to move.\n            ', tunable=PlayEffect.TunableFactory(), tuning_group=GroupNames.SITUATION), 'situation_end_loots_to_apply_on_objects': TunableSet(description='\n            The loots to apply on the tagged objects when the situation ends \n            or is destroyed.\n            \n            E.g. use this to reset objects to a specific state after \n            the situation is over.\n            \n            The loot will be processed with the active sim as the actor,\n            and the object as the target.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.ACTION), pack_safe=True), tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._target_id = self._seed.extra_kwargs.get('default_target_id', None)
        else:
            self._target_id = reader.read_uint64(OBJECT_TOKEN, None)

    @classmethod
    def _states(cls):
        return (SituationStateData(0, _PreparationState, factory=cls._preparation_state), SituationStateData(1, _WaitingToMoveState, factory=cls._waiting_to_move_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return []

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        if not cls.starting_requirements:
            return True
        else:
            resolver = SingleSimResolver(services.active_sim_info())
            if not cls.starting_requirements.run_tests(resolver):
                return False
        return True

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._target_id is not None:
            writer.write_uint64(OBJECT_TOKEN, self._target_id)

    def start_situation(self):
        super().start_situation()
        self._change_state(self._preparation_state())

    def load_situation(self):
        if not self.situation_meets_starting_requirements():
            return False
        return super().load_situation()

    def on_objects_ready(self):
        self._change_state(self._waiting_to_move_state())

    def on_ready_to_move(self):
        if self._tests_to_continue.run_tests(GlobalResolver()):
            self._move_objects()
            self._change_state(self._waiting_to_move_state())
        else:
            self._self_destruct()

    def _get_placement_resolver(self):
        additional_participants = {}
        if self._target_id is not None:
            target = services.object_manager().get(self._target_id)
            additional_participants[ParticipantType.Object] = (target,)
            if target.is_sim:
                additional_participants[ParticipantType.TargetSim] = (target.sim_info,)
        return SingleSimResolver(services.active_sim_info(), additional_participants=additional_participants)

    def _destroy(self):
        objects_of_interest = services.object_manager().get_objects_matching_tags(self.object_tags, match_any=True)
        if not objects_of_interest:
            return
        active_sim_info = services.active_sim_info()
        for obj in objects_of_interest:
            resolver = SingleActorAndObjectResolver(active_sim_info, obj, self)
            for loot in self.situation_end_loots_to_apply_on_objects:
                loot.apply_to_resolver(resolver)
        super()._destroy()

    def _move_objects(self):
        objects_to_move = services.object_manager().get_objects_matching_tags(self.object_tags, match_any=True)
        if not objects_to_move:
            return
        resolver = self._get_placement_resolver()
        choices = [(location.weight.get_multiplier(resolver), location.placement_strategy) for location in self.placement_strategy_locations]
        chosen_strategy = random.weighted_random_item(choices)
        do_fade = self.fade is not None
        out_sequence = []
        moves = []
        in_sequence = []
        for object_to_move in objects_to_move:
            object_to_move.cancel_interactions_running_on_object(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Object changing location.')
            if self.vfx_on_move is not None:
                out_sequence.append(lambda _, object_to_move=object_to_move: self.vfx_on_move(object_to_move).start_one_shot())
            if do_fade:
                out_sequence.append(lambda _, object_to_move=object_to_move: object_to_move.fade_out(self.fade.out_time))
            moves.append(lambda _, object_to_move=object_to_move: chosen_strategy.try_place_object(object_to_move, resolver))
            if do_fade:
                in_sequence.append(lambda _, object_to_move=object_to_move: object_to_move.fade_in(self.fade.in_time))
        sequence = []
        if out_sequence:
            sequence.append(out_sequence)
            sequence.append(SoftSleepElement(clock.interval_in_sim_minutes(self.fade.out_time)))
        sequence.append(moves)
        if in_sequence:
            sequence.append(in_sequence)
        element = build_element(sequence, critical=CleanupType.RunAll)
        services.time_service().sim_timeline.schedule(element)
