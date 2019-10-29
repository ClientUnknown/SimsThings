import operatorfrom buffs.tunable import TunableBuffReferencefrom business.business_situation_mixin import BusinessSituationMixinfrom date_and_time import create_time_spanfrom sims4.tuning.tunable import TunableSimMinute, TunableMapping, TunablePercent, TunableIntervalimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('BusinessEmployeeSituationMixin')
class BusinessEmployeeSituationMixin(BusinessSituationMixin):
    INSTANCE_TUNABLES = {'total_work_time': TunableInterval(description='\n            The amount of time in sim minutes an employee will work before\n            leaving for the day.\n            ', tunable_type=TunableSimMinute, default_lower=1, default_upper=2), 'total_work_time_buffs': TunableMapping(description="\n            A mapping from percentage duration worked to buffs applied to\n            employees working more than this amount. Buffs don't stack; the\n            higher percentage buff is the applied one.\n            ", key_type=TunablePercent(description='\n                The percentage duration worked.\n                ', default=50), value_type=TunableBuffReference(description='\n                The buff applied to employees working over the specified amount.\n                '))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._work_buff_handle = None
        self._work_alarm_handle = None
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._original_duration = self.total_work_time.random_int()
        else:
            self._original_duration = reader.read_uint64('original_duration', self.duration)

    def _on_career_removed(self, _):
        self._on_business_closed()
        return True

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            career = business_manager.get_employee_career(sim.sim_info)
            if career is not None and self._on_career_removed not in career.on_career_removed:
                career.on_career_removed.append(self._on_career_removed)
            if business_manager.is_owned_by_npc:
                self._add_to_employee_manager_for_npc_businesses(sim.sim_info, business_manager)

    def _add_to_employee_manager_for_npc_businesses(self, sim_info, business_manager):
        if not business_manager.is_employee(sim_info):
            zone_director = services.venue_service().get_zone_director()
            employee_type = zone_director.get_employee_type_for_situation(self.id)
            if employee_type is None:
                logger.error('Failed to find employee type for sim {} in situation {}', sim_info, self)
                return
            business_manager.add_employee(sim_info, employee_type, is_npc_employee=True)

    def _destroy(self):
        self._clock_out()
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            employee_sim_info = self.get_employee_sim_info()
            if employee_sim_info is not None:
                career = business_manager.get_employee_career(employee_sim_info)
                if career is not None and self._on_career_removed in career.on_career_removed:
                    career.on_career_removed.remove(self._on_career_removed)
        super()._destroy()

    def _clock_in(self):
        employee_sim_info = self.get_employee_sim_info()
        if employee_sim_info is None:
            return
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and not business_manager.is_employee_clocked_in(employee_sim_info):
            business_manager.on_employee_clock_in(employee_sim_info)

    def _clock_out(self):
        employee_sim_info = self.get_employee_sim_info()
        if employee_sim_info is None:
            return
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.is_employee_clocked_in(employee_sim_info):
            business_manager.on_employee_clock_out(employee_sim_info)
        self._remove_work_buffs()

    def _start_work_duration(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.is_owner_household_active:
            self._clock_in()
            self.change_duration(self._original_duration)
            self._update_work_buffs()

    def _update_work_buffs(self, *_, from_load=False, **__):
        self._remove_work_buffs()
        employee_sim_info = self.get_employee_sim_info()
        if employee_sim_info is None:
            return
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and not business_manager.is_employee_clocked_in(employee_sim_info):
            return
        if not self.total_work_time_buffs:
            return
        previous_duration = None
        elapsed_duration = self._original_duration - self._get_remaining_time_in_minutes()
        for (duration_percent, buff) in sorted(self.total_work_time_buffs.items(), key=operator.itemgetter(0), reverse=True):
            required_duration = duration_percent*self._original_duration
            if elapsed_duration >= required_duration:
                self._work_buff_handle = employee_sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason, from_load=from_load)
                break
            previous_duration = required_duration - elapsed_duration
        if previous_duration is not None:
            alarm_duration = create_time_span(minutes=previous_duration)
            self._work_alarm_handle = alarms.add_alarm(self, alarm_duration, self._update_work_buffs)

    def _remove_work_buffs(self):
        if self._work_alarm_handle is not None:
            alarms.cancel_alarm(self._work_alarm_handle)
        if self._work_buff_handle is not None:
            employee_sim_info = self.get_employee_sim_info()
            if employee_sim_info is not None:
                employee_sim_info.remove_buff(self._work_buff_handle)
