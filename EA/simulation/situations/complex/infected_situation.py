from buffs.tunable import TunableBuffReferencefrom date_and_time import create_time_spanfrom event_testing.resolver import SingleSimResolverfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestListfrom situations.situation_types import SituationSerializationOptionfrom situations.sub_situation_mixin import SubSituationOwnerMixinfrom tag import TunableTagfrom tunable_multiplier import TestedSumfrom tunable_time import TunableTimeOfDayimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('InfectedSituation', default_owner='tingyul')
class _InfectedState(CommonSituationState):
    pass

class InfectedSituation(SubSituationOwnerMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'infected_state': _InfectedState.TunableFactory(display_name='Infected State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'possessed_start_time': TunableTimeOfDay(description='\n            Time of day Sims become possessed.\n            ', tuning_group=GroupNames.SITUATION), 'possessed_duration_hours': TestedSum.TunableFactory(description='\n            How long the possession lasts.\n            ', tuning_group=GroupNames.SITUATION), 'possessed_situation': Situation.TunableReference(description='\n            Possessed situation to place Sim in.\n            ', class_restrictions=('PossessedSituation',), tuning_group=GroupNames.SITUATION), 'default_job_and_role': TunableSituationJobAndRoleState(description='\n            The job/role the infected Sim will be in.\n            ', tuning_group=GroupNames.SITUATION), 'possessed_buff_tag': TunableTag(description='\n            Tag for buffs that can add the Possessed Mood through the Infection\n            System. Possessed status is refreshed when these buffs are added\n            or removed.\n            ', filter_prefixes=('Buff',)), 'possessed_buff_no_animate_tag': TunableTag(description='\n            Possession buffs with this tag will not play the start possession\n            animation.\n            ', filter_prefixes=('Buff',)), 'possession_time_buff': TunableBuffReference(description='\n            The buff to add to the Sim when it is the possessed start time.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_possession_alarm = None
        self._end_possession_alarm = None
        self._possession_sources = []

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(0, cls.infected_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return ((cls.default_job_and_role.job, cls.default_job_and_role.role_state),)

    @classmethod
    def default_job(cls):
        pass

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    def start_situation(self):
        super().start_situation()
        self._change_state(self.infected_state())
        sim_info = self._get_sim_info()
        for buff in sim_info.Buffs.get_all_buffs_with_tag(self.possessed_buff_tag):
            self._request_possession(buff.buff_type, animate_possession_override=False)
        now = services.time_service().sim_now
        time_span_day = create_time_span(days=1)
        start_day_time = self._get_possessed_start_day_time()
        time_span = now.time_till_next_day_time(start_day_time)
        self._start_possession_alarm = alarms.add_alarm(self, time_span, self._on_possession_start, repeating_time_span=time_span_day, repeating=True)
        end_day_time = self._get_possessed_end_day_time()
        sim_info.Buffs.on_buff_added.register(self._on_buff_added)
        sim_info.Buffs.on_buff_removed.register(self._on_buff_removed)
        in_possession_window = now.time_between_day_times(start_day_time, end_day_time)
        if in_possession_window:
            elapsed_time = create_time_span(days=1) - now.time_till_next_day_time(start_day_time)
            self._trigger_possession_time(elapsed_time=elapsed_time)

    def on_remove(self):
        sim_info = self._get_sim_info()
        sim_info.Buffs.on_buff_added.unregister(self._on_buff_added)
        sim_info.Buffs.on_buff_removed.unregister(self._on_buff_removed)
        super().on_remove()

    @property
    def sim_id(self):
        return self._guest_list.host_sim_id

    def _get_sim_info(self):
        sim_info = services.sim_info_manager().get(self.sim_id)
        return sim_info

    def _get_possessed_start_day_time(self):
        return self.possessed_start_time

    def _get_possessed_end_day_time(self):
        sim_info = self._get_sim_info()
        if sim_info is None:
            logger.error('Missing SimInfo for infected sim')
            return
        start_day_time = self._get_possessed_start_day_time()
        resolver = SingleSimResolver(sim_info)
        hours = self.possessed_duration_hours.get_modified_value(resolver)
        end_day_time = start_day_time + create_time_span(hours=hours)
        return end_day_time

    def _on_possession_start(self, _):
        self._trigger_possession_time()

    def _trigger_possession_time(self, elapsed_time=None):
        sim_info = self._get_sim_info()
        if sim_info is None:
            logger.error('Missing SimInfo for infected sim')
            return
        possession_buff = self.possession_time_buff
        sim_info.add_buff_from_op(possession_buff.buff_type, possession_buff.buff_reason)
        buff_commodity = sim_info.get_statistic(possession_buff.buff_type.commodity, add=False)
        if buff_commodity:
            resolver = SingleSimResolver(sim_info)
            hours = self.possessed_duration_hours.get_modified_value(resolver)
            buff_time = hours*60
            if elapsed_time is not None:
                buff_time -= elapsed_time.in_minutes()
            buff_commodity.set_value(buff_time)

    def _on_sub_situation_end(self, sub_situation_id):
        if services.current_zone().is_zone_shutting_down:
            return
        if self._possession_sources:
            sim_info = self._get_sim_info()
            for source in tuple(self._possession_sources):
                sim_info.remove_buff_by_type(source)

    def _start_possession_situation(self, animate_possession_override=None):
        guest_list = SituationGuestList(invite_only=True, host_sim_id=self.sim_id)
        animate_possession = services.current_zone().is_zone_running
        if animate_possession_override is not None:
            animate_possession = animate_possession_override
        self._create_sub_situation(self.possessed_situation, guest_list=guest_list, user_facing=False, animate_possession=animate_possession)

    def _on_possession_sources_changed(self):
        sub_situations = self._get_sub_situations()
        if sub_situations:
            sub_situations[0].on_possession_sources_changed()

    def _request_possession(self, source, animate_possession_override=None):
        if source in self._possession_sources:
            logger.error('Redundant source: {}', source)
            return
        self._possession_sources.append(source)
        if not self._sub_situation_ids:
            self._start_possession_situation(animate_possession_override=animate_possession_override)
        self._on_possession_sources_changed()

    def _remove_possession_request(self, source):
        if source not in self._possession_sources:
            logger.error('Missing source: {}', source)
            return
        self._possession_sources.remove(source)
        self._on_possession_sources_changed()

    def _on_buff_added(self, buff_type, owner_sim_id):
        if self.possessed_buff_tag not in buff_type.tags:
            return
        animate = None
        if self.possessed_buff_no_animate_tag in buff_type.tags:
            animate = False
        self._request_possession(buff_type, animate_possession_override=animate)

    def _on_buff_removed(self, buff_type, owner_sim_id):
        if self.possessed_buff_tag not in buff_type.tags:
            return
        self._remove_possession_request(buff_type)

    def get_possession_source(self):
        sim_info = self._get_sim_info()
        if sim_info is None:
            return (None, None)
        buff_component = sim_info.Buffs
        longest_source = None
        buff_duration = None
        for source in self._possession_sources:
            buff = buff_component.get_buff_by_type(source)
            if buff is None:
                pass
            else:
                buff_commodity = buff.get_commodity_instance()
                if buff_commodity is None:
                    longest_source = buff
                    buff_duration = None
                    break
                buff_value = buff_commodity.get_value()
                if not buff_duration is None:
                    if buff_value > buff_duration:
                        buff_duration = buff_value
                        longest_source = buff
                buff_duration = buff_value
                longest_source = buff
        return (longest_source, buff_duration)
