import servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessEmployeeData:

    def __init__(self, employee_manager, employee_sim_info, employee_type):
        self._employee_manager = employee_manager
        self._employee_sim_info_id = employee_sim_info.id
        self._employee_type = employee_type
        self._payroll_data = {}
        self._career_level_buff_handle = None
        self._has_leveled_up = {}
        self._employee_type_data = employee_manager._business_manager.tuning_data.employee_data_map[self._employee_type]

    @property
    def employee_sim_id(self):
        return self._employee_sim_info_id

    @property
    def employee_type(self):
        return self._employee_type

    def get_employee_sim_info(self):
        return services.sim_info_manager().get(self._employee_sim_info_id)

    def has_leveled_up_skill(self, skill):
        if skill not in self._has_leveled_up:
            return False
        return self._has_leveled_up[skill]

    def leveled_skill_up(self, skill):
        self._has_leveled_up[skill] = True

    def add_career_buff(self):
        self.remove_career_buff()
        employee_sim_info = self.get_employee_sim_info()
        if employee_sim_info is None:
            logger.error('Trying to add career buff to employee Sim Info does not exist for business employee data with sim_id:{}', self.employee_sim_id)
            return
        current_career = employee_sim_info.career_tracker.get_career_by_uid(self._employee_type_data.career.guid64)
        desired_career_level = self._employee_manager.get_desired_career_level(employee_sim_info, self.employee_type)
        career_level_delta = current_career.level - desired_career_level
        career_level_buff = self._employee_type_data.career_level_delta_buffs.get(career_level_delta)
        if career_level_buff is not None:
            self._career_level_buff_handle = employee_sim_info.add_buff(career_level_buff)

    def remove_career_buff(self):
        employee_sim_info = self.get_employee_sim_info()
        if employee_sim_info is None:
            logger.error('Trying to remove career buff to employee Sim Info does not exist for business employee data with sim_id:{}', self.employee_sim_id)
            return
        if self._career_level_buff_handle is not None:
            employee_sim_info.remove_buff(self._career_level_buff_handle)
