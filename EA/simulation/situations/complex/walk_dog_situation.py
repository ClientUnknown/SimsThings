import operatorimport randomfrom carry.carry_utils import get_carried_objects_genfrom event_testing.results import TestResultfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom sims4.math import Thresholdfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunablePackSafeReference, TunableInterval, TunableSimMinute, TunableRange, TunableTuple, TunableReference, Tunable, TunableList, TunableEnumWithFilterfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, CommonInteractionCompletedSituationState, SituationStateData, SituationStatefrom situations.situation_types import SituationCreationUIOptionfrom statistics.commodity import Commodityfrom tag import TunableTags, Tagimport enumimport interactionsimport servicesimport sims4.logimport sims4.mathimport situationsimport taglogger = sims4.log.Logger('Situations', default_owner='rmccord')
class WalkDogProgress(enum.Int, export=False):
    WALK_DOG_NOT_STARTED = 0
    WALK_DOG_WALKING = ...
    WALK_DOG_FINISHING = ...
    WALK_DOG_DONE = ...

class WaitForSimJobs(SituationState):
    pass

class WalkState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'attractor_node_affordance': TunablePackSafeReference(description='\n            The affordance that the dog walker runs on the next attractor point\n            object.\n            ', manager=services.affordance_manager()), 'max_attempts': TunableRange(description='\n            The maximum number of attempts we will try to walk to a node before\n            walking to the next node.\n            ', tunable_type=int, default=3, minimum=1), 'time_between_attempts': TunableSimMinute(description='\n            The time in sim minutes between attempts to walk to the current\n            attractor point.\n            ', default=5)}
    RETRY_ALARM_NAME = 'retry_walk'

    def __init__(self, attractor_id, *args, attractor_node_affordance=None, max_attempts=1, time_between_attempts=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.attractor_node_affordance = attractor_node_affordance
        self.max_attempts = max_attempts
        self.time_between_attempts = time_between_attempts
        self._attractor_point = services.object_manager().get(attractor_id)
        self._attempts = 0
        self._walk_interaction = None

    def push_walk_affordance(self, alarm_handle):
        sim = self.owner.get_walker()
        if sim.has_any_interaction_running_or_queued_of_types((self.attractor_node_affordance,)):
            return
        for (_, carry_posture, carry_target) in get_carried_objects_gen(sim):
            if carry_target.transient and carry_posture.source_interaction.running:
                break
        return
        self._cancel_alarm(WalkState.RETRY_ALARM_NAME)
        self._attempts += 1
        if self._attempts > self.max_attempts:
            self.owner.walk_onward()
            return
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, run_priority=Priority.Low, insert_strategy=QueueInsertStrategy.NEXT)
        walk_aop = interactions.aop.AffordanceObjectPair(self.attractor_node_affordance, self._attractor_point, self.attractor_node_affordance, None)
        test_result = walk_aop.test(context)
        if test_result:
            execute_result = walk_aop.execute(context)
            if execute_result:
                self._walk_interaction = execute_result[1]
        self._create_or_load_alarm(WalkState.RETRY_ALARM_NAME, self.time_between_attempts, self.push_walk_affordance, repeating=True)

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if self._attractor_point is None:
            self.owner.walk_onward()
            return
        self.push_walk_affordance(None)
        self._create_or_load_alarm(WalkState.RETRY_ALARM_NAME, 1, self.push_walk_affordance, repeating=True)

    def on_deactivate(self):
        self._cancel_alarm(WalkState.RETRY_ALARM_NAME)
        if self._walk_interaction is not None:
            self._walk_interaction.cancel(FinishingType.SITUATIONS, "Walk Dog Situation Ended. Don't continue to walk.")
            self._walk_interaction = None
        super().on_deactivate()

    def _additional_tests(self, sim_info, event, resolver):
        return sim_info.id == self.owner.get_walker().id

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._walk_interaction = None
        self.owner.wait_around(self._attractor_point)

class WaitAroundState(CommonSituationState):
    FACTORY_TUNABLES = {'wait_stat_and_value': TunableTuple(description='\n            The stat and initial value on the dog that decides when we should\n            walk to the next node in the situation. The timer for this state is\n            a fallback if the Sim and dog end up taking too long.\n            ', stat=Commodity.TunableReference(description='\n                The stat we track on the Dog, to notify us when the Sim should attempt to walk\n                to the next attractor point.\n                \n                When the stat reaches its convergence value, we enter the walk state.\n                '), initial_value=Tunable(description='\n                The initial value we should set on the Dog to decide when they should walk again. \n                ', tunable_type=float, default=5))}

    def __init__(self, *args, wait_stat_and_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.wait_stat_and_value = wait_stat_and_value
        self.wait_listener = None

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        pet = self.owner.get_pet()
        wait_stat = pet.commodity_tracker.get_statistic(self.wait_stat_and_value.stat, add=True)
        wait_stat.set_value(self.wait_stat_and_value.initial_value)
        op = operator.le if wait_stat.get_decay_rate() <= 0 else operator.ge
        threshold = Threshold(wait_stat.convergence_value, op)
        if threshold.compare(wait_stat.get_value()):
            self.on_wait_stat_zero(wait_stat)
        else:
            self.wait_listener = wait_stat.create_and_add_callback_listener(threshold, self.on_wait_stat_zero)

    def remove_wait_listener(self):
        pet = self.owner.get_pet()
        if pet is not None:
            if self.wait_listener is not None:
                pet.commodity_tracker.remove_listener(self.wait_listener)
            pet.commodity_tracker.remove_statistic(self.wait_stat_and_value.stat)
        self.wait_listener = None

    def on_deactivate(self):
        self.remove_wait_listener()
        super().on_deactivate()

    def on_wait_stat_zero(self, stat):
        self.remove_wait_listener()
        self.owner.walk_onward()

    def timer_expired(self):
        self.owner.walk_onward()

class FinishWalkState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'go_home_affordance': TunableReference(description='\n            The affordance that the dog walker runs to go home.\n            ', manager=services.affordance_manager())}

    def __init__(self, *args, go_home_affordance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.go_home_affordance = go_home_affordance

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        walker = self.owner.get_walker()
        if walker is None or not walker.sim_info.lives_here:
            self.owner.walk_onward()
        context = InteractionContext(walker, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
        aop = interactions.aop.AffordanceObjectPair(self.go_home_affordance, walker, self.go_home_affordance, None)
        aop.test_and_execute(context)

    def _additional_tests(self, sim_info, event, resolver):
        walker = self.owner.get_walker()
        if walker is None or not sim_info.id == walker.id:
            return False
        return True

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.walk_onward()

    def timer_expired(self):
        self.owner.walk_onward()

class WalkDogSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'walker_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the Sim walking the dog. Pre-populated as\n            the actor of the Situation.\n            '), 'dog_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the dog being walked. Pre-populated as the\n            target of the Situation.\n            '), 'walk_nodes': TunableInterval(description='\n            How many nodes in the world we want to traverse for our walk.\n            Currently this will only affect fallback attractor points. We will\n            try to use ALL of the attractor points returned by search tags.\n            ', tunable_type=int, default_lower=5, default_upper=6, minimum=1), 'finish_walk_state': FinishWalkState.TunableFactory(tuning_group=GroupNames.STATE), 'walk_state': WalkState.TunableFactory(tuning_group=GroupNames.STATE), 'wait_around_state': WaitAroundState.TunableFactory(tuning_group=GroupNames.STATE), 'attractor_point_tags': TunableTuple(description='\n            Tags that are used to select objects and attractor points for our\n            path.\n            ', fallback_tags=TunableTags(description="\n                Tags to use if we don't find any objects with the search tags.\n                This is primarily so we can have a separate list for pre-\n                patched worlds where there are no hand-placed attractor points.\n                ", filter_prefixes=('AtPo',), minlength=1), search_tags=TunableList(description="\n                A list of path tags to look for in order. This will search for\n                objects with each tag, find the closest object, and use it's\n                matching tag to find others for a full path. \n                \n                Example: Short_1, Short_2 are in the list. We would search for \n                all objects with either of those tags, and grab the closest \n                one. If the object has Short_1 tag on it, we find all objects \n                with Short_1 to create our path.\n                ", tunable=TunableEnumWithFilter(description='\n                    A set of attractor point tags we use to pull objects from when\n                    searching for attractor points to create a walking path from.\n                    ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=('AtPo',)), unique_entries=True))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if cls.attractor_point_tags.fallback_tags.issubset(cls.attractor_point_tags.search_tags):
            logger.error('Walk Dog Situation {} fallback tags are a subset of search tags. You need at least one tag to be different in fallback tags.', cls)

    @classmethod
    def _states(cls):
        return (SituationStateData(0, WalkState), SituationStateData(1, WaitAroundState), SituationStateData(2, FinishWalkState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.walker_job_and_role_state.job, cls.walker_job_and_role_state.role_state), (cls.dog_job_and_role_state.job, cls.dog_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def get_prepopulated_job_for_sims(cls, sim, target_sim_id=None):
        prepopulate = [(sim.id, cls.walker_job_and_role_state.job.guid64)]
        if target_sim_id is not None:
            prepopulate.append((target_sim_id, cls.dog_job_and_role_state.job.guid64))
        return prepopulate

    @classmethod
    def has_walk_nodes(cls):
        object_manager = services.object_manager()
        found_objects = object_manager.get_objects_matching_tags(set(cls.attractor_point_tags.search_tags) | cls.attractor_point_tags.fallback_tags, match_any=True)
        if found_objects:
            return True
        return False

    @classmethod
    def get_walk_nodes(cls):
        object_manager = services.object_manager()

        def get_objects(tag_set):
            found_objects = set()
            for tag in tag_set:
                found_objects.update(object_manager.get_objects_matching_tags({tag}))
            return found_objects

        attractor_objects = get_objects(cls.attractor_point_tags.search_tags)
        if not attractor_objects:
            return (get_objects(cls.attractor_point_tags.fallback_tags), True)
        return (attractor_objects, False)

    @classmethod
    def is_situation_available(cls, *args, **kwargs):
        result = cls.has_walk_nodes()
        if not result:
            return TestResult(False, 'Not enough attractor points to walk the dog.')
        return super().is_situation_available(*args, **kwargs)

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.DONT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._walker = None
        self._dog = None
        self._path_index = 0
        self._path_obj_ids = []
        self.walk_dog_progress = WalkDogProgress.WALK_DOG_NOT_STARTED

    def _on_remove_sim_from_situation(self, sim):
        if sim is self.get_walker() or sim is self.get_pet():
            self._self_destruct()
        super()._on_remove_sim_from_situation

    def _on_add_sim_to_situation(self, *args, **kwargs):
        super()._on_add_sim_to_situation(*args, **kwargs)
        if self.get_walker() is not None and self.get_pet() is not None:
            self._build_walking_path()
            if not self._path_obj_ids:
                self._self_destruct()
                return
            self.walk_onward()

    def get_walker(self):
        if self._walker is None:
            self._walker = next(iter(self.all_sims_in_job_gen(self.walker_job_and_role_state.job)), None)
        return self._walker

    def get_pet(self):
        if self._dog is None:
            self._dog = next(iter(self.all_sims_in_job_gen(self.dog_job_and_role_state.job)), None)
        return self._dog

    def _build_walking_path(self):
        (attractor_objects, is_fallback) = self.get_walk_nodes()
        if not attractor_objects:
            logger.warn('Could not build a path for {}', self)
            return
        sim = self.get_walker() or self.get_pet()
        sim_position = sim.position
        all_obj_and_pos_list = [(obj, obj.position) for obj in attractor_objects]
        min_dist_obj = min(all_obj_and_pos_list, key=lambda k: (k[1] - sim_position).magnitude_2d_squared())[0]
        obj_and_pos_list = []
        if not is_fallback:
            tags = min_dist_obj.get_tags()
            matching_tags = {tag for tag in self.attractor_point_tags.search_tags if tag in tags}
            for obj_pos in all_obj_and_pos_list:
                if obj_pos[0].has_any_tag(matching_tags):
                    obj_and_pos_list.append(obj_pos)
        else:
            obj_and_pos_list = all_obj_and_pos_list
        positions = [item[1] for item in obj_and_pos_list]
        center = sum(positions, sims4.math.Vector3.ZERO())/len(positions)
        obj_and_pos_list.sort(key=lambda k: sims4.math.atan2(k[1].x - center.x, k[1].z - center.z), reverse=True)
        start_index = 0
        for (obj, _) in obj_and_pos_list:
            if obj is min_dist_obj:
                break
            start_index += 1
        if not is_fallback:
            num_nodes = len(obj_and_pos_list)
        elif self.walk_nodes.lower_bound == self.walk_nodes.upper_bound:
            num_nodes = self.walk_nodes.lower_bound
        else:
            num_nodes = random.randrange(self.walk_nodes.lower_bound, self.walk_nodes.upper_bound)
        clockwise = 1 if random.randint(2, 4) % 2 else -1
        index = start_index
        for _ in range(num_nodes):
            if index >= len(obj_and_pos_list):
                index = 0
            elif index < 0:
                index = len(obj_and_pos_list) - 1
            (node, _) = obj_and_pos_list[index]
            self._path_obj_ids.append(node.id)
            index += clockwise
        if self._path_obj_ids[-1] != min_dist_obj.id:
            self._path_obj_ids.append(min_dist_obj.id)

    def walk_onward(self):
        if self._path_index < len(self._path_obj_ids):
            self.walk_dog_progress = WalkDogProgress.WALK_DOG_WALKING
            self._change_state(self.walk_state(self._path_obj_ids[self._path_index]))
            self._path_index += 1
            return
        if self.walk_dog_progress == WalkDogProgress.WALK_DOG_WALKING:
            self.walk_dog_progress = WalkDogProgress.WALK_DOG_FINISHING
            self._change_state(self.finish_walk_state())
            return
        elif self.walk_dog_progress >= WalkDogProgress.WALK_DOG_FINISHING:
            self.walk_dog_progress = WalkDogProgress.WALK_DOG_DONE
            self._self_destruct()
            return

    def wait_around(self, attractor_point):
        self._change_state(self.wait_around_state())
lock_instance_tunables(WalkDogSituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)