from _math import Vector3Immutableimport randomfrom role.role_state import RoleStatefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom singletons import UNSETfrom situations.ambient.walkby_limiting_tags_mixin import WalkbyLimitingTagsMixinfrom situations.bouncer.bouncer_types import BouncerRequestPriority, RequestSpawningOptionfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobimport filtersimport servicesimport sims4.logimport sims4.tuning.tunableimport situations.bouncerimport taglogger = sims4.log.Logger('Walkby')
class GroupAnchoredAutonomySituationCommon(SituationComplexCommon):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'object_anchor_tag': sims4.tuning.tunable.TunableEnumEntry(description="\n                                    The tag that defines the objects that are valid for the anchor point.\n                                    The situation will search the object manager for any object with this \n                                    tag and will choose one at random.  This object's position will be the \n                                    anchor point.  It is assumed that the roles in this situation will \n                                    have an autonomy modifier with off_lot_autonomy_rule set to ANCHORED.\n                                    ", tunable_type=tag.Tag, default=tag.Tag.INVALID, tuning_group=GroupNames.ROLES), 'group_filter': sims4.tuning.tunable.TunableReference(description='\n                                The group filter for this visit.  \n                            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter, tuning_group=GroupNames.ROLES)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._guests = []
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._anchor_position = UNSET
        else:
            x = reader.read_float('x_position', 0)
            y = reader.read_float('y_position', 0)
            z = reader.read_float('z_position', 0)
            level = reader.read_int32('level', UNSET)
            self._anchor_position = (Vector3Immutable(x, y, z), level)

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        guest_list = SituationGuestList(invite_only=True, host_sim_id=active_sim_info.id)
        worker_filter = cls.group_filter if cls.group_filter is not None else cls.default_job().filter
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            logger.error('Failed to find/create any sims for {}; using defaults in ambient service', cls, owner='rez')
            return guest_list
        for result in filter_results:
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, cls.default_job(), RequestSpawningOption.MUST_SPAWN, BouncerRequestPriority.BACKGROUND_LOW))
        return guest_list

    def get_new_anchor_position(self, tags, test_func=None):
        tagged_objects = [obj for obj in services.object_manager().get_objects_with_tag_gen(tags) if test_func is None or test_func(obj)]
        if not tagged_objects:
            logger.error('No objects found with the tag {} in GroupAnchoredAutonomySituation {}.  Did you forget to tune those objects?', self.object_anchor_tag, self, owner='rez')
            self._self_destruct()
            return sims4.math.Vector3.ZERO()
        chosen_index = random.randint(0, len(tagged_objects) - 1)
        chosen_obj = tagged_objects[chosen_index]
        return (chosen_obj.position, chosen_obj.level)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._guests.append(sim)
        if self._cur_state.should_anchor_new_arrival():
            logger.assert_log(self._anchor_position is not UNSET, 'Trying to set autonomy anchor without first setting the anchored object in {}', self, owner='rez')
            sim.set_anchor(self._anchor_position)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        sim.clear_anchor()
        self._guests.remove(sim)

    def set_all_autonomy_anchors(self):
        for sim in self._guests:
            sim.set_anchor(self._anchor_position)

    def clear_all_autonomny_anchors(self):
        for sim in self._guests:
            sim.clear_anchor()

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        (point, level) = self._anchor_position
        writer.write_float('x_position', point.x)
        writer.write_float('y_position', point.y)
        writer.write_float('z_position', point.z)
        if level is not UNSET:
            writer.write_int32('level', level)

class AnchoredOpenStreetsAutonomySituation(WalkbyLimitingTagsMixin, GroupAnchoredAutonomySituationCommon):
    INSTANCE_TUNABLES = {'role': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                          The situation job for all sims in this situation.\n                          '), arriving_role_state=RoleState.TunableReference(description='\n                          The role state for the sim arriving on the spawn point and waiting \n                          for the rest of the group.  This is the initial state.\n                          '), do_stuff_role_state=RoleState.TunableReference(description='\n                          The role state for the sim doing stuff.\n                          '), leave_role_state=RoleState.TunableReference(description='\n                          The role state for the sim leaving.\n                          '), tuning_group=GroupNames.ROLES), 'group_filter': sims4.tuning.tunable.TunableReference(description="\n                                The group filter for this walkby.  If set, this filter will be used \n                                instead of the filter tuned in the walker_job.  If it's None, the \n                                filter in the walker_job will be used.  Note that all sims spawned \n                                with this filter will be put into the walker_job job.\n                            ", manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter, tuning_group=GroupNames.ROLES), 'wait_for_arrival_timeout': sims4.tuning.tunable.TunableSimMinute(description='\n                                        The amount of time the sim waits at the spawn point before doing\n                                        stuff.\n                                        ', default=30, tuning_group=GroupNames.TRIGGERS), 'do_stuff_timeout': sims4.tuning.tunable.TunableSimMinute(description='\n                                    The amount of time the sim does stuff before leaving.\n                                    ', default=180, tuning_group=GroupNames.TRIGGERS)}
    REMOVE_INSTANCE_TUNABLES = situations.situation.Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _ArrivingState), SituationStateData(2, _DoStuffState), SituationStateData(3, _LeaveState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.role.situation_job, cls.role.arriving_role_state)]

    @classmethod
    def default_job(cls):
        return cls.role.situation_job

    @property
    def guests(self):
        return self._guests

    def start_situation(self):
        super().start_situation()

        def not_on_active_lot(obj):
            return not obj.is_on_active_lot()

        self._anchor_position = self.get_new_anchor_position(self.object_anchor_tag, test_func=not_on_active_lot)
        self._change_state(_ArrivingState())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if self._cur_state.transition_to_doing_stuff_when_full() and (self.group_filter is None or len(self._guests) >= self.group_filter.get_filter_count()):
            self._change_state(_DoStuffState())

    def _on_sim_removed_from_situation_prematurely(self, sim, sim_job):
        super()._on_sim_removed_from_situation_prematurely(sim, sim_job)
        self.manager.add_sim_to_auto_fill_blacklist(sim.id, sim_job)

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return cls.group_filter.get_filter_count()

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.OPEN_STREETS

    def _get_remaining_time_for_gsi(self):
        if self._cur_state is not None:
            return self._cur_state._get_remaining_time_for_gsi()
        return super()._get_remaining_time_for_gsi()
sims4.tuning.instances.lock_instance_tunables(AnchoredOpenStreetsAutonomySituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.WALKBY, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)
class AnchoredAutonomySituationStateMixin:

    def should_anchor_new_arrival(self):
        return False

class _AnchoredOpenStreetsAutonomySituationState(SituationState, AnchoredAutonomySituationStateMixin):

    def transition_to_doing_stuff_when_full(self):
        return False

class _ArrivingState(_AnchoredOpenStreetsAutonomySituationState):
    _WAIT_FOR_ARRIVAL_TIMEOUT = 'wait_for_arrival_timeout'

    def __init__(self):
        super().__init__()
        self._wait_for_arrival_alarm_handle = None

    def transition_to_doing_stuff_when_full(self):
        return True

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._create_or_load_alarm(self._WAIT_FOR_ARRIVAL_TIMEOUT, self.owner.wait_for_arrival_timeout, self._on_waited_too_long, should_persist=True, reader=reader)

    def _on_waited_too_long(self, _):
        if not self.owner.guests:
            self.owner._self_destruct()
        else:
            self._change_state(_DoStuffState())

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(self._WAIT_FOR_ARRIVAL_TIMEOUT)

class _DoStuffState(_AnchoredOpenStreetsAutonomySituationState):
    _DO_STUFF_TIMEOUT = 'do_stuff_timeout'

    def should_anchor_new_arrival(self):
        return True

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.role.situation_job, self.owner.role.do_stuff_role_state)
        self._create_or_load_alarm(self._DO_STUFF_TIMEOUT, self.owner.do_stuff_timeout, self._on_done_doing_stuff, should_persist=True, reader=reader)
        self.owner.set_all_autonomy_anchors()

    def on_deactivate(self):
        self.owner.clear_all_autonomny_anchors()
        super().on_deactivate()

    def _on_done_doing_stuff(self, _):
        self._change_state(_LeaveState())

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(self._DO_STUFF_TIMEOUT)

class _LeaveState(_AnchoredOpenStreetsAutonomySituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.role.situation_job, self.owner.role.leave_role_state)

    def _get_remaining_time_for_gsi(self):
        return self.owner._get_remaining_time()
