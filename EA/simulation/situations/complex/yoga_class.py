import randomfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_variants import TunableSituationJobTestfrom interactions import ParticipantTypefrom interactions.interaction_finisher import FinishingTypefrom scheduler import SituationWeeklySchedulefrom sims4.tuning.tunable import TunableInterval, TunableVariant, TunableTuple, TunableSimMinute, TunableList, TunableSet, TunableEnumWithFilter, TunableMapping, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_job import SituationJobfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport enumimport servicesimport sims4import situationsimport taglogger = sims4.log.Logger('Yoga Class', default_owner='cjiang')
class _PreClassState(CommonSituationState):
    PRE_CLASS_TIMEOUT = 'pre_class_timeout'

    def on_activate(self, reader=None):
        logger.debug('Pre yoga class.')
        super().on_activate(reader)
        self._create_or_load_alarm(self.PRE_CLASS_TIMEOUT, self.owner.pre_class_state.time_out, lambda _: self.timer_expired(), should_persist=True)

    def timer_expired(self):
        next_state = self.owner.get_next_class_state()
        self._change_state(next_state())

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(self.PRE_CLASS_TIMEOUT)

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        object_manager = services.object_manager()
        yoga_mat_tags = self.owner.instructor_mat_tags
        yoga_mat_list = list(object_manager.get_objects_with_tags_gen(*yoga_mat_tags))
        if len(yoga_mat_list) == 0:
            return (None, None)
        for found_mat in yoga_mat_list:
            self.owner._leader_mat = found_mat
            return (None, self.owner._leader_mat)
        return (None, None)

class _PostClassState(CommonSituationState):
    POST_CLASS_TIMEOUT = 'post_class_timeout'

    def on_activate(self, reader=None):
        logger.debug('Post yoga class.')
        super().on_activate(reader)
        self._create_or_load_alarm(self.POST_CLASS_TIMEOUT, self.owner.post_class_state.time_out, lambda _: self.timer_expired(), should_persist=True)

    def timer_expired(self):
        self.owner._self_destruct()

class _ClassPoseState(CommonInteractionCompletedSituationState):
    CLASS_MEMBER_DELAY_TIMEOUT = 'class_member_delay_timeout'
    MISS_INTERACTION_TIMEOUT = 'miss_interaction_timeout'
    FACTORY_TUNABLES = {'member_delay_time': TunableInterval(description='\n            The delay between when the instructor does a pose and when a class\n            member copies that pose.\n            ', tunable_type=float, default_lower=1, default_upper=2), 'miss_interaction_time_delay': TunableSimMinute(description='\n            The delay if the interaction we are monitoring to finish this state\n            is missing, we will move on.\n            ', default=30)}

    def __init__(self, member_delay_time, miss_interaction_time_delay, **kwargs):
        super().__init__(**kwargs)
        self.member_delay_time = member_delay_time
        self.miss_interaction_time_delay = miss_interaction_time_delay

    def on_activate(self, reader=None):
        super().on_activate(reader)
        class_member_job = self.owner.get_class_member_job()
        for sim in self.owner.all_sims_in_job_gen(class_member_job):
            alarm_name = '{}_{}'.format(self.CLASS_MEMBER_DELAY_TIMEOUT, sim.id)
            class_member_delay = self.member_delay_time.random_float()
            self._create_or_load_alarm(alarm_name, class_member_delay, lambda _, sim=sim: self._member_delay_timer_expired(sim), should_persist=True)
        self._create_or_load_alarm(self.MISS_INTERACTION_TIMEOUT, self.miss_interaction_time_delay, lambda _: self._on_interaction_of_interest_complete(), should_persist=True)

    def _member_delay_timer_expired(self, sim):
        class_member_job = self.owner.get_class_member_job()
        role_state = self._job_and_role_changes.get(class_member_job)
        if role_state is None:
            logger.error("{} doesn't have role state for job {}", self, class_member_job)
            return
        if self.owner.sim_has_job(sim, class_member_job):
            self.owner._set_sim_role_state(sim, role_state)

    def _set_job_role_state(self):
        class_member_job = self.owner.get_class_member_job()
        for (job, role_state) in self._job_and_role_changes.items():
            if job is not class_member_job:
                self.owner._set_job_role_state(job, role_state)

    def _on_interaction_of_interest_complete(self, **kwargs):
        next_state = self.owner.get_next_class_state()
        self._change_state(next_state())

class _ClassPoseBridge(_ClassPoseState):
    pass

class _ClassPoseDance(_ClassPoseState):
    pass

class _ClassPoseDownwardDog(_ClassPoseState):
    pass

class _ClassPoseGreeting(_ClassPoseState):
    pass

class _ClassPoseHalfMoon(_ClassPoseState):
    pass

class _ClassPoseHalfMoon_Mirror(_ClassPoseState):
    pass

class _ClassPoseTree(_ClassPoseState):
    pass

class _ClassPoseTree_Mirror(_ClassPoseState):
    pass

class _ClassPoseTriangle(_ClassPoseState):
    pass

class _ClassPoseTriangle_Mirror(_ClassPoseState):
    pass

class _ClassPoseCorpse(_ClassPoseState):
    pass

class _ClassPoseBoat(_ClassPoseState):
    pass

class _ClassPoseWarrior(_ClassPoseState):
    pass

class _ClassPoseHandstand(_ClassPoseState):
    pass

class _ClassPoseSidePlank(_ClassPoseState):
    pass

class _ClassPoseSidePlank_Mirror(_ClassPoseState):
    pass

class ClassPoseVariant(TunableVariant):

    def __init__(self, description='The variant of different class poses.', **kwargs):
        super().__init__(description=description, pose_greeting=_ClassPoseGreeting.TunableFactory(), pose_bridge=_ClassPoseBridge.TunableFactory(), pose_dance=_ClassPoseBridge.TunableFactory(), pose_downwarddog=_ClassPoseDownwardDog.TunableFactory(), pose_halfmoon=_ClassPoseHalfMoon.TunableFactory(), pose_halfmoon_mirror=_ClassPoseHalfMoon_Mirror.TunableFactory(), pose_tree=_ClassPoseTree.TunableFactory(), pose_tree_mirror=_ClassPoseTree_Mirror.TunableFactory(), pose_triangle=_ClassPoseTriangle.TunableFactory(), pose_triangle_mirror=_ClassPoseTriangle_Mirror.TunableFactory(), pose_Corpse=_ClassPoseCorpse.TunableFactory(), pose_boat=_ClassPoseBoat.TunableFactory(), pose_warrior=_ClassPoseWarrior.TunableFactory(), pose_handstand=_ClassPoseHandstand.TunableFactory(), pose_sideplank=_ClassPoseSidePlank.TunableFactory(), pose_sideplank_mirror=_ClassPoseSidePlank_Mirror.TunableFactory(), default='pose_greeting', **kwargs)

class ClassPoseEnum(enum.Int):
    GREETING = 0
    BRIDGE = 1
    DANCE = 2
    DOWNWARD_DOG = 3
    HALFMOON = 4
    TREE = 5
    TRIANGLE = 6
    CORPSE = 7
    BOAT = 8
    WARRIOR = 9
    HANDSTAND = 10
    SIDEPLANK = 11
    HALFMOON_MIRRORED = 12
    SIDEPLANK_MIRRORED = 13
    TREE_MIRRORED = 14
    TRIANGLE_MIRRORED = 15
YOGA_CLASS_GROUP = 'Yoga Class'
class YogaClassSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'class_pose_map': TunableMapping(description='\n            The static map to mapping yoga pose state to the certain pose enum.\n            Put it here instead of in the module tuning is for pack safe reason.\n            This should only be tuned on prototype, and not suggesting to change/override\n            in tuning instance unless you have very strong reason.\n            ', key_type=TunableEnumEntry(tunable_type=ClassPoseEnum, default=ClassPoseEnum.GREETING), key_name='pose_enum', value_type=ClassPoseVariant(), value_name='pose_content', tuning_group=YOGA_CLASS_GROUP), 'pre_class_state': TunableTuple(description='\n                Information related to the pre class situation state.\n                ', situation_state=_PreClassState.TunableFactory(description='\n                    Pre Class Situation State.  The yoga instructor will idle\n                    in the yoga leader mat, and class members will join the\n                    situation and idle on their mats.\n                    '), time_out=TunableSimMinute(description='\n                    How long the pre class session will last.\n                    ', default=15, minimum=1), tuning_group=GroupNames.STATE), 'post_class_state': TunableTuple(description='\n                The third situation state.  Sims in the class will randomly\n                chatting after the class.\n                ', situation_state=_PostClassState.TunableFactory(), time_out=TunableSimMinute(description='\n                    How long the post class session will last.\n                    ', default=15, minimum=1), tuning_group=GroupNames.STATE), 'class_pose_states': TunableList(description='\n                The sequence of the yoga poses we want the class to run.\n                ', tunable=TunableEnumEntry(tunable_type=ClassPoseEnum, default=ClassPoseEnum.GREETING), tuning_group=GroupNames.STATE), '_class_member_job': SituationJob.TunableReference(description='\n                The situation job for class members.\n                ', tuning_group=YOGA_CLASS_GROUP), 'instructor_mat_tags': TunableSet(description="\n                The instructor's yoga mat tags.\n                ", tunable=TunableEnumWithFilter(tunable_type=tag.Tag, filter_prefixes=('Func_YogaClass',), default=tag.Tag.INVALID), tuning_group=YOGA_CLASS_GROUP), 'member_mat_tags': TunableSet(description="\n                The class memeber's yoga mat tags.\n                ", tunable=TunableEnumWithFilter(tunable_type=tag.Tag, filter_prefixes=('Func_YogaClass',), default=tag.Tag.INVALID), tuning_group=YOGA_CLASS_GROUP), 'number_of_npc_class_members': TunableInterval(description='\n                The range of how many NPCs will join the class.\n                ', tunable_type=int, default_lower=1, default_upper=3, tuning_group=YOGA_CLASS_GROUP), 'member_situation_job_test': TunableSituationJobTest(description='\n            The situation job test to determine whether npc sim should be\n            picked as class member.\n            ', tuning_group=YOGA_CLASS_GROUP, locked_args={'participant': ParticipantType.Actor, 'tooltip': None})}

    @classmethod
    def _states(cls):
        class_pose_map = cls.class_pose_map
        situation_states = [SituationStateData(1, _PreClassState, factory=cls.pre_class_state.situation_state), SituationStateData(2, _PostClassState, factory=cls.post_class_state.situation_state), SituationStateData(3, _ClassPoseBridge, factory=class_pose_map[ClassPoseEnum.BRIDGE]), SituationStateData(4, _ClassPoseDance, factory=class_pose_map[ClassPoseEnum.DANCE]), SituationStateData(5, _ClassPoseDownwardDog, factory=class_pose_map[ClassPoseEnum.DOWNWARD_DOG]), SituationStateData(6, _ClassPoseGreeting, factory=class_pose_map[ClassPoseEnum.GREETING]), SituationStateData(7, _ClassPoseHalfMoon, factory=class_pose_map[ClassPoseEnum.HALFMOON]), SituationStateData(8, _ClassPoseTree, factory=class_pose_map[ClassPoseEnum.TREE]), SituationStateData(9, _ClassPoseTriangle, factory=class_pose_map[ClassPoseEnum.TRIANGLE]), SituationStateData(10, _ClassPoseCorpse, factory=class_pose_map[ClassPoseEnum.CORPSE]), SituationStateData(11, _ClassPoseBoat, factory=class_pose_map[ClassPoseEnum.BOAT]), SituationStateData(12, _ClassPoseWarrior, factory=class_pose_map[ClassPoseEnum.WARRIOR]), SituationStateData(13, _ClassPoseHandstand, factory=class_pose_map[ClassPoseEnum.HANDSTAND]), SituationStateData(14, _ClassPoseSidePlank, factory=class_pose_map[ClassPoseEnum.SIDEPLANK])]
        factory_method = class_pose_map.get(ClassPoseEnum.TREE_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(15, _ClassPoseTree_Mirror, factory=factory_method))
        factory_method = class_pose_map.get(ClassPoseEnum.TRIANGLE_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(16, _ClassPoseTriangle_Mirror, factory=class_pose_map[ClassPoseEnum.TRIANGLE_MIRRORED]))
        factory_method = class_pose_map.get(ClassPoseEnum.HALFMOON_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(17, _ClassPoseHalfMoon_Mirror, factory=class_pose_map[ClassPoseEnum.HALFMOON_MIRRORED]))
        factory_method = class_pose_map.get(ClassPoseEnum.SIDEPLANK_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(18, _ClassPoseSidePlank_Mirror, factory=class_pose_map[ClassPoseEnum.SIDEPLANK_MIRRORED]))
        return tuple(situation_states)

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def get_class_member_job(cls):
        return cls._class_member_job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.pre_class_state.situation_state._tuned_values.job_and_role_changes.items())

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._leader_mat = None
        self._class_pose_index = 0

    def start_situation(self):
        super().start_situation()
        self._add_npc_class_members()
        self._change_state(self.pre_class_state.situation_state())
        self._set_class_id_to_zone(self.id)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def _add_npc_class_members(self):
        sim_info_manager = services.sim_info_manager()
        member_num = self.number_of_npc_class_members.random_int()
        candidate_ids = [sim.id for sim in sim_info_manager.instanced_sims_on_active_lot_gen() if not sim.is_selectable]
        sim_filter_service = services.sim_filter_service()
        filter_result_list = sim_filter_service.submit_filter(self.get_class_member_job().filter, None, allow_yielding=False, sim_constraints=candidate_ids, requesting_sim_info=services.active_sim_info(), gsi_source_fn=self.get_sim_filter_gsi_name)
        tested_filter_result_list = []
        for filter_result in filter_result_list:
            single_sim_resolver = SingleSimResolver(filter_result.sim_info)
            if single_sim_resolver(self.member_situation_job_test):
                tested_filter_result_list.append(filter_result)
        random_results = []
        if len(tested_filter_result_list) < member_num:
            random_results = tested_filter_result_list
        else:
            random_results = random.sample(tested_filter_result_list, member_num)
        class_job = self.get_class_member_job()
        for filter_result in random_results:
            self.invite_sim_to_job(filter_result.sim_info, class_job)

    def _set_class_id_to_zone(self, class_id):
        zone_director = services.venue_service().get_zone_director()
        if zone_director is None:
            logger.error('Set yoga class id with None zone director')
            return
        if not hasattr(zone_director, 'set_class_id'):
            logger.error('Set yoga class id in invalid zone director {}', zone_director)
            return
        zone_director.set_class_id(class_id)

    def get_next_class_state(self):
        next_state = None
        if self._class_pose_index < len(self.class_pose_states):
            next_state_enum = self.class_pose_states[self._class_pose_index]
            next_state = self.class_pose_map[next_state_enum]
            self._class_pose_index = self._class_pose_index + 1
        else:
            next_state = self.post_class_state.situation_state
        return next_state

    def on_remove(self):
        super().on_remove()
        self._set_class_id_to_zone(None)

    def cancel_sim_si(self, job_type, affordance_to_cancel, cancel_reason_msg):
        for (sim, situation_sim) in self._situation_sims.items():
            if situation_sim.current_job_type == job_type:
                sim_interactions = sim.get_all_running_and_queued_interactions()
                for si in sim_interactions:
                    if si.affordance is affordance_to_cancel:
                        si.cancel(finishing_type=FinishingType.SITUATIONS, cancel_reason_msg=cancel_reason_msg)

    def _on_sim_removed_from_situation_prematurely(self, sim, sim_job):
        super()._on_sim_removed_from_situation_prematurely(sim, sim_job)
        if self.num_of_sims > 0:
            return
        self._self_destruct()

class YogaClassScheduleMixin:
    INSTANCE_TUNABLES = {'yoga_class_schedule': SituationWeeklySchedule.TunableFactory(description='\n            The schedule to trigger yoga class automatically. Player triggered\n            yoga classes will trump scheduled yoga classes.\n            ', schedule_entry_data={'pack_safe': True}), 'yoga_instructor_idle_situation': Situation.TunablePackSafeReference(description='\n            The idle situation to find yoga instructor.\n            '), 'yoga_class_starting_notification': TunableUiDialogNotificationSnippet(description='\n                The notification that is displayed whenever a yoga class starts.\n                ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_class_id = None
        self._yoga_class_schedule = None
        if self.yoga_instructor_idle_situation is not None:
            self._yoga_class_schedule = self.yoga_class_schedule(start_callback=self._start_yoga_class)

    def on_shutdown(self):
        super().on_shutdown()
        if self._yoga_class_schedule is not None:
            self._yoga_class_schedule.destroy()

    def set_class_id(self, class_id):
        if self._current_class_id is not None and class_id is not None and self._current_class_id != class_id:
            logger.error('Try to create new yoga class {} while the current one {} is still running', class_id, self._current_class_id, owner='cjiang')
            return
        self._current_class_id = class_id

    def _start_yoga_class(self, scheduler, alarm_data, extra_data):
        if self._current_class_id is not None:
            return
        entry = alarm_data.entry
        yoga_class_situation_type = entry.situation
        situation_manager = services.get_zone_situation_manager()
        possible_existing_class_situations = situation_manager.get_situations_by_tags(yoga_class_situation_type.tags)
        if possible_existing_class_situations:
            return
        yoga_idle_situation = situation_manager.get_situation_by_type(self.yoga_instructor_idle_situation)
        if yoga_idle_situation is None:
            logger.warn('No idle situation for yoga instructor in the venue, cannot start class', owner='cjiang')
            return
        yoga_instructor = next(yoga_idle_situation.all_sims_in_situation_gen(), None)
        if yoga_instructor is None:
            logger.warn('No yoga instructor found in the venue, cannot start class', owner='cjiang')
            return
        instructor_sis = yoga_instructor.get_all_running_and_queued_interactions()
        for si in instructor_sis:
            si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='YogaClassStart')
        guest_list = SituationGuestList()
        guest_info = SituationGuestInfo.construct_from_purpose(yoga_instructor.id, yoga_class_situation_type.venue_situation_player_job, SituationInvitationPurpose.INVITED)
        guest_list.add_guest_info(guest_info)
        try:
            creation_source = self.instance_name
        except:
            creation_source = 'yoga class start'
        self._current_class_id = situation_manager.create_situation(yoga_class_situation_type, guest_list=guest_list, user_facing=False, creation_source=creation_source)
        class_situation = situation_manager.get(self._current_class_id)
        invited_sim = services.get_active_sim()
        if invited_sim is None:
            return
        class_member_job = class_situation.get_class_member_job()
        if class_member_job.can_sim_be_given_job(invited_sim.id, invited_sim.sim_info):
            resolver = SingleSimResolver(yoga_instructor)
            dialog = self.yoga_class_starting_notification(yoga_instructor.sim_info, resolver=resolver)
            dialog.show_dialog(additional_tokens=(class_situation.display_name,))
