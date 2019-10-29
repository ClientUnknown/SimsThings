from autonomy.autonomy_modifier import UNLIMITED_AUTONOMY_RULEfrom autonomy.settings import AutonomyRandomizationfrom date_and_time import DateAndTimefrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom interactions.aop import AffordanceObjectPairfrom interactions.interaction_finisher import FinishingTypefrom objects.components.state import ObjectStateValuefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableRange, TunableList, TunableReference, TunableTuple, TunableThresholdfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonInteractionCompletedSituationState, SituationStateData, SituationStatefrom situations.situation_types import SituationCreationUIOptionfrom statistics.commodity import Commodityfrom tag import TunableTagsfrom ui.ui_dialog_notification import UiDialogNotificationimport autonomyimport elementsimport enumimport interactionsimport servicesimport sims4.logimport situationsimport taglogger = sims4.log.Logger('Situations', default_owner='rmccord')OBSTACLE_COURSE_START_TIME_TOKEN = 'course_start_time'OBSTACLE_COURSE_END_TIME_TOKEN = 'course_end_time'
class ObstacleCourseProgress(enum.Int, export=False):
    NOT_STARTED = 0
    RUNNING = ...
    FINISHED = ...

class WaitForSimJobsState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self.owner.setup_obstacle_course()

class RunCourseState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'obstacle_affordance_list': TunableList(description='\n            List of interactions we want to run autonomy with to find our next\n            obstacle.\n            ', tunable=TunableReference(description='\n                An interaction to traverse an obstacle.\n                ', manager=services.affordance_manager()))}

    def __init__(self, *args, obstacle_affordance_list=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.obstacle_affordance_list = obstacle_affordance_list
        self._autonomy_request_handle = None
        self._autonomy_request = None
        self._interaction_context = None

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if self.owner.course_progress < ObstacleCourseProgress.RUNNING:
            self.owner.start_course()
            self.owner.validate_obstacle_course()

    def on_deactivate(self):
        super().on_deactivate()

    def _additional_tests(self, sim_info, event, resolver):
        athlete = self.owner.get_athlete()
        if athlete is None or not sim_info.id == athlete.id:
            return False
        return True

    def _on_interaction_of_interest_complete(self, **kwargs):
        if self.owner.course_progress == ObstacleCourseProgress.RUNNING:
            self._schedule_obstacle_autonomy_request()
        elif self.owner.course_progress == ObstacleCourseProgress.FINISHED:
            self.owner.finish_situation()

    def _schedule_obstacle_autonomy_request(self):
        if self._autonomy_request_handle is not None:
            logger.error('Obstacle Course Situation attempted to run autonomy request while a previous request is still being processed')
            return
        sim = self.owner.get_athlete()
        self._create_autonomy_request(sim)
        timeline = services.time_service().sim_timeline
        self._autonomy_request_handle = timeline.schedule(elements.GeneratorElement(self._run_obstacle_course_autonomy_request))

    def _run_obstacle_course_autonomy_request(self, timeline):
        try:
            selected_interaction = yield from services.autonomy_service().find_best_action_gen(timeline, self._autonomy_request, randomization_override=AutonomyRandomization.DISABLED)
        finally:
            self._autonomy_request_handle = None
        if self.owner is None:
            return False
        if selected_interaction is not None:
            selected_interaction.invalidate()
            affordance = selected_interaction.affordance
            aop = AffordanceObjectPair(affordance, selected_interaction.target, affordance, None)
            result = aop.test_and_execute(self._interaction_context)
            if not result:
                return result
            self.owner.continue_course()
            return True
        self.owner.finish_course()
        return True

    def _create_autonomy_request(self, sim, **kwargs):
        autonomy_service = services.autonomy_service()
        if autonomy_service is None:
            return (None, None)
        obstacles = []
        object_manager = services.object_manager()
        for obj_id in self.owner.obstacle_ids:
            obstacle = object_manager.get(obj_id)
            if obstacle is not None:
                obstacles.append(obstacle)
        if not obstacles:
            return (None, None)
        self._interaction_context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, client=None, pick=None)
        commodity_list = []
        for affordance in self.obstacle_affordance_list:
            commodity_list.extend(affordance.commodity_flags)
        self._autonomy_request = autonomy.autonomy_request.AutonomyRequest(sim, commodity_list=commodity_list, skipped_static_commodities=None, object_list=obstacles, affordance_list=self.obstacle_affordance_list, channel=None, context=self._interaction_context, autonomy_mode=autonomy.autonomy_modes.FullAutonomy, ignore_user_directed_and_autonomous=True, is_script_request=True, consider_scores_of_zero=True, ignore_lockouts=True, apply_opportunity_cost=False, record_test_result=None, distance_estimation_behavior=autonomy.autonomy_request.AutonomyDistanceEstimationBehavior.FINAL_PATH, off_lot_autonomy_rule_override=UNLIMITED_AUTONOMY_RULE, autonomy_mode_label_override='ObstacleCourse', **kwargs)

class ObstacleCourseSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'coach_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the coach Sim. Pre-populated as\n            the actor of the Situation.\n            ', tuning_group=GroupNames.ROLES), 'athlete_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the athlete. Pre-populated as the\n            target of the Situation.\n            ', tuning_group=GroupNames.ROLES), 'run_course_state': RunCourseState.TunableFactory(tuning_group=GroupNames.STATE), 'obstacle_tags': TunableTags(description='\n            Tags to use when searching for obstacle course objects.\n            ', filter_prefixes=('Func_PetObstacleCourse',), minlength=1), 'setup_obstacle_state_value': ObjectStateValue.TunableReference(description='\n            The state to setup obstacles before we run the course.\n            '), 'teardown_obstacle_state_value': ObjectStateValue.TunableReference(description='\n            The state to teardown obstacles after we run the course or when the\n            situation ends.\n            '), 'failure_commodity': Commodity.TunableReference(description='\n            The commodity we use to track how many times the athlete has failed\n            to overcome an obstacle.\n            '), 'obstacles_required': TunableRange(description='\n            The number of obstacles required for the situation to be available. \n            If the obstacles that the pet can route to drops below this number,\n            the situation is destroyed.\n            ', tunable_type=int, default=4, minimum=1), 'unfinished_notification': UiDialogNotification.TunableFactory(description='\n            The dialog for when the situation ends prematurely or the dog never\n            finishes the course.\n            Token 0: Athlete\n            Token 1: Coach\n            Token 2: Time\n            ', tuning_group=GroupNames.UI), 'finish_notifications': TunableList(description='\n            A list of thresholds and notifications to play given the outcome of\n            the course. We run through the thresholds until one passes, and\n            play the corresponding notification.\n            ', tuning_group=GroupNames.UI, tunable=TunableTuple(description='\n                A threshold and notification to play if the threshold passes.\n                ', threshold=TunableThreshold(description='\n                    A threshold to compare the number of failures from the\n                    failure commodity when the course is finished.\n                    '), notification=UiDialogNotification.TunableFactory(description='\n                    Notification to play when the situation ends.\n                    Token 0: Athlete\n                    Token 1: Coach\n                    Token 2: Failure Count\n                    Token 3: Time\n                    ')))}

    @classmethod
    def _states(cls):
        return (SituationStateData(0, WaitForSimJobsState), SituationStateData(1, RunCourseState, factory=cls.run_course_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.coach_job_and_role_state.job, cls.coach_job_and_role_state.role_state), (cls.athlete_job_and_role_state.job, cls.athlete_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def get_prepopulated_job_for_sims(cls, sim, target_sim_id=None):
        prepopulate = [(sim.id, cls.coach_job_and_role_state.job.guid64)]
        if target_sim_id is not None:
            prepopulate.append((target_sim_id, cls.athlete_job_and_role_state.job.guid64))
        return prepopulate

    @classmethod
    def get_obstacles(cls):
        object_manager = services.object_manager()
        found_objects = set()
        for tag in cls.obstacle_tags:
            found_objects.update(object_manager.get_objects_matching_tags({tag}))
        return found_objects

    @classmethod
    def is_situation_available(cls, *args, **kwargs):
        obstacles = cls.get_obstacles()
        if len(obstacles) < cls.obstacles_required:
            return TestResult(False, 'Not enough obstacles.')
        return super().is_situation_available(*args, **kwargs)

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.LOT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            obstacles = self.get_obstacles()
            if not obstacles:
                self._self_destruct()
            self._obstacle_ids = {obstacle.id for obstacle in obstacles}
            self._course_start_time = DateAndTime(reader.read_uint64(OBSTACLE_COURSE_START_TIME_TOKEN, services.time_service().sim_now))
            self._course_end_time = DateAndTime(reader.read_uint64(OBSTACLE_COURSE_END_TIME_TOKEN, services.time_service().sim_now))
        else:
            self._obstacle_ids = set()
            self._course_start_time = None
            self._course_end_time = None
        self._course_progress = ObstacleCourseProgress.NOT_STARTED

    @property
    def course_progress(self):
        return self._course_progress

    @property
    def obstacle_ids(self):
        return self._obstacle_ids

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._course_start_time is not None:
            writer.write_uint64(OBSTACLE_COURSE_START_TIME_TOKEN, int(self._course_start_time))
        if self._course_end_time is not None:
            writer.write_uint64(OBSTACLE_COURSE_END_TIME_TOKEN, int(self._course_end_time))

    def start_situation(self):
        super().start_situation()
        self._register_obstacle_course_events()
        self._change_state(WaitForSimJobsState())

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self._self_destruct()

    def _on_add_sim_to_situation(self, sim, job_type, *args, **kwargs):
        super()._on_add_sim_to_situation(sim, job_type, *args, **kwargs)
        if self.get_coach() is not None and self.get_athlete() is not None:
            object_manager = services.object_manager()
            obstacles = {object_manager.get(obstacle_id) for obstacle_id in self._obstacle_ids}
            sim_info_manager = services.sim_info_manager()
            users = sim_info_manager.instanced_sims_gen()
            for user in users:
                if user in self._situation_sims:
                    pass
                else:
                    for interaction in user.get_all_running_and_queued_interactions():
                        target = interaction.target
                        target = target.part_owner if target is not None and target.is_part else target
                        if target is not None and target in obstacles:
                            interaction.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Obstacle Course Starting')
            self._change_state(self.run_course_state())

    def _register_obstacle_course_events(self):
        services.get_event_manager().register_single_event(self, TestEvent.ObjectDestroyed)
        services.get_event_manager().register_single_event(self, TestEvent.OnExitBuildBuy)

    def _unregister_obstacle_course_events(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.ObjectDestroyed)
        services.get_event_manager().unregister_single_event(self, TestEvent.OnExitBuildBuy)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.ObjectDestroyed:
            destroyed_object = resolver.get_resolved_arg('obj')
            if destroyed_object.id in self._obstacle_ids:
                self._obstacle_ids.remove(destroyed_object.id)
                if len(self._obstacle_ids) < self.obstacles_required:
                    self._self_destruct()
        elif event == TestEvent.OnExitBuildBuy:
            self.validate_obstacle_course()

    def on_remove(self):
        coach = self.get_coach()
        athlete = self.get_athlete()
        if coach is not None and athlete is not None:
            if self.course_progress > ObstacleCourseProgress.NOT_STARTED and self.course_progress < ObstacleCourseProgress.FINISHED:
                course_end_time = services.time_service().sim_now
                course_time_span = course_end_time - self._course_start_time
                unfinished_dialog = self.unfinished_notification(coach)
                unfinished_dialog.show_dialog(additional_tokens=(athlete, coach, course_time_span))
            athlete.commodity_tracker.remove_statistic(self.failure_commodity)
        self.teardown_obstacle_course()
        self._unregister_obstacle_course_events()
        super().on_remove()

    def start_course(self):
        self._course_progress = ObstacleCourseProgress.RUNNING
        self._course_start_time = services.time_service().sim_now if self._course_start_time is None else self._course_start_time

    def continue_course(self):
        self._change_state(self.run_course_state())

    def finish_course(self):
        self._course_end_time = services.time_service().sim_now
        self._course_progress = ObstacleCourseProgress.FINISHED
        self._change_state(self.run_course_state())

    def finish_situation(self):
        course_time_span = self._course_end_time - self._course_start_time
        athlete = self.get_athlete()
        coach = self.get_coach()
        failures = athlete.commodity_tracker.get_value(self.failure_commodity)
        for threshold_notification in self.finish_notifications:
            if threshold_notification.threshold.compare(failures):
                dialog = threshold_notification.notification(coach)
                dialog.show_dialog(additional_tokens=(athlete, coach, failures, course_time_span))
                break
        logger.error("Obstacle Course Situation doesn't have a threshold, notification for failure count of {}", failures)
        self._self_destruct()

    def setup_obstacle_course(self):
        obstacles = self.get_obstacles()
        if len(obstacles) < self.obstacles_required:
            self._self_destruct()
        self._obstacle_ids = {obstacle.id for obstacle in obstacles}

    def validate_obstacle_course(self):
        athlete = self.get_athlete()
        if athlete is None:
            self._self_destruct()
            return
        all_obstacles = self.get_obstacles()
        if len(all_obstacles) < self.obstacles_required:
            self._self_destruct()
            return
        valid_obstacles = set()
        for obstacle in all_obstacles:
            currentState = obstacle.get_state(self.setup_obstacle_state_value.state)
            if obstacle.is_connected(athlete):
                valid_obstacles.add(obstacle)
                if currentState == self.teardown_obstacle_state_value:
                    obstacle.set_state(self.setup_obstacle_state_value.state, self.setup_obstacle_state_value, immediate=True)
                    if currentState == self.setup_obstacle_state_value:
                        obstacle.set_state(self.setup_obstacle_state_value.state, self.teardown_obstacle_state_value, immediate=True)
            elif currentState == self.setup_obstacle_state_value:
                obstacle.set_state(self.setup_obstacle_state_value.state, self.teardown_obstacle_state_value, immediate=True)
        if len(valid_obstacles) < self.obstacles_required:
            self._self_destruct()
        else:
            self._obstacle_ids = {obstacle.id for obstacle in valid_obstacles}

    def teardown_obstacle_course(self):
        obstacles = self.get_obstacles()
        for obstacle in obstacles:
            obstacle.set_state(self.teardown_obstacle_state_value.state, self.teardown_obstacle_state_value, immediate=True)

    def get_coach(self):
        return next(iter(self.all_sims_in_job_gen(self.coach_job_and_role_state.job)), None)

    def get_athlete(self):
        return next(iter(self.all_sims_in_job_gen(self.athlete_job_and_role_state.job)), None)
lock_instance_tunables(ObstacleCourseSituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)