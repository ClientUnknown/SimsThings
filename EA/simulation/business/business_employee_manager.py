from _collections import defaultdictfrom collections import Counterfrom math import floorimport itertoolsimport mathfrom business.business_employee import BusinessEmployeeDatafrom date_and_time import DateAndTimefrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Genderfrom sims.sim_info_utils import sim_info_auto_finderfrom sims4.math import clampfrom singletons import DEFAULTimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessEmployeeManager:
    LEGACY_EMPLOYEE_TYPE = 1

    def __init__(self, business_manager):
        self._business_manager = business_manager
        self._employee_sim_ids = defaultdict(set)
        self._employees = {}
        self._daily_employee_wages = 0
        self._employee_payroll = {}
        self._employee_uniform_data_male = defaultdict()
        self._employee_uniform_data_female = defaultdict()

    @property
    def employee_count(self):
        return len(self._employees)

    def get_employee_types(self):
        return tuple(employee_type for employee_type in self._employee_sim_ids)

    def save_data(self, data):
        data.daily_employee_wages = self._daily_employee_wages
        if self._employee_sim_ids:
            for (employee_type, employee_ids) in self._employee_sim_ids.items():
                for employee_id in employee_ids:
                    with ProtocolBufferRollback(data.employee_data) as employee_data:
                        employee_data.employee_type = employee_type
                        employee_data.employee_id = employee_id
        else:
            for (employee_id, employee_info) in self._employees.items():
                with ProtocolBufferRollback(data.employee_data) as employee_data:
                    employee_data.employee_type = employee_info.employee_type
                    employee_data.employee_id = employee_id
        for (employee_type, uniform_data_male) in self._employee_uniform_data_male.items():
            with ProtocolBufferRollback(data.employee_uniforms_male) as employee_uniforms_male:
                employee_uniforms_male.employee_type = employee_type
                employee_uniforms_male.employee_uniform_data.mannequin_id = uniform_data_male.sim_id
                uniform_data_male.save_sim_info(employee_uniforms_male.employee_uniform_data)
        for (employee_type, uniform_data_female) in self._employee_uniform_data_female.items():
            with ProtocolBufferRollback(data.employee_uniforms_female) as employee_uniforms_female:
                employee_uniforms_female.employee_type = employee_type
                employee_uniforms_female.employee_uniform_data.mannequin_id = uniform_data_female.sim_id
                uniform_data_female.save_sim_info(employee_uniforms_female.employee_uniform_data)
        for (sim_id, payroll_tuple) in self._employee_payroll.items():
            with ProtocolBufferRollback(data.employee_payroll) as employee_payroll:
                employee_payroll.sim_id = sim_id
                clock_in_time = payroll_tuple[0]
                if clock_in_time is not None:
                    employee_payroll.clock_in_time = clock_in_time
                payroll_entry = payroll_tuple[1]
                if payroll_entry is not None:
                    for (career_level, hours_worked) in payroll_entry.items():
                        with ProtocolBufferRollback(employee_payroll.payroll_data) as payroll_data:
                            payroll_data.career_level_guid = career_level.guid64
                            payroll_data.hours_worked = hours_worked

    def _load_uniform_data(self, persistence_service, uniform_data, employee_type, gender):
        if gender == Gender.MALE:
            data_dictionary = self._employee_uniform_data_male
        else:
            data_dictionary = self._employee_uniform_data_female
        employee_uniform_data = uniform_data
        data_dictionary[employee_type] = self.get_employee_uniform_data(employee_type, gender, sim_id=uniform_data.mannequin_id)
        if persistence_service is not None:
            persisted_data = persistence_service.get_mannequin_proto_buff(uniform_data.mannequin_id)
            if persisted_data is not None:
                employee_uniform_data = persisted_data
        data_dictionary[employee_type].load_sim_info(employee_uniform_data)
        self._send_employee_uniform_data(data_dictionary[employee_type])
        persistence_service.del_mannequin_proto_buff(uniform_data.mannequin_id)

    def _load_payroll_data(self, payroll_data):
        career_level_manager = services.get_instance_manager(sims4.resources.Types.CAREER_LEVEL)
        for payroll_msg in payroll_data.employee_payroll:
            payroll_data = Counter()
            for payroll_entry_msg in payroll_msg.payroll_data:
                career_level = career_level_manager.get(payroll_entry_msg.career_level_guid)
                if career_level is None:
                    pass
                else:
                    payroll_data[career_level] = payroll_entry_msg.hours_worked
            if not payroll_data:
                pass
            else:
                clock_in_time = DateAndTime(payroll_msg.clock_in_time) if payroll_msg.clock_in_time else None
                self._employee_payroll[payroll_msg.sim_id] = (clock_in_time, payroll_data)

    def load_data(self, data):
        self._daily_employee_wages = data.daily_employee_wages
        for employee_data in data.employee_data:
            self._employee_sim_ids[employee_data.employee_type].add(employee_data.employee_id)
        persistence_service = services.get_persistence_service()
        for male_uniform in data.employee_uniforms_male:
            self._load_uniform_data(persistence_service, male_uniform.employee_uniform_data, male_uniform.employee_type, Gender.MALE)
        for female_uniform in data.employee_uniforms_female:
            self._load_uniform_data(persistence_service, female_uniform.employee_uniform_data, female_uniform.employee_type, Gender.FEMALE)
        self._load_payroll_data(data)

    def load_legacy_data(self, save_data):
        self._daily_employee_wages = save_data.daily_employee_wages
        for employee_id in save_data.employee_ids:
            self._employee_sim_ids[self.LEGACY_EMPLOYEE_TYPE].add(employee_id)
        persistence_service = services.get_persistence_service()
        if save_data.HasField('employee_uniform_data_male'):
            self._load_uniform_data(persistence_service, save_data.employee_uniform_data_male, self.LEGACY_EMPLOYEE_TYPE, Gender.MALE)
        if save_data.HasField('employee_uniform_data_female'):
            self._load_uniform_data(persistence_service, save_data.employee_uniform_data_female, self.LEGACY_EMPLOYEE_TYPE, Gender.FEMALE)
        self._load_payroll_data(save_data)

    def _try_reload_outfit_data(self, employee_uniform_dict, persistence_service, gender):
        for (uniform_type, uniform_sim_info_wrapper) in employee_uniform_dict.items():
            persisted_data = persistence_service.get_mannequin_proto_buff(uniform_sim_info_wrapper.id)
            if persisted_data is None:
                pass
            else:
                self._load_uniform_data(persistence_service, persisted_data, uniform_type, gender)

    def reload_employee_uniforms(self):
        persistence_service = services.get_persistence_service()
        if persistence_service is None:
            return
        self._try_reload_outfit_data(self._employee_uniform_data_male, persistence_service, Gender.MALE)
        self._try_reload_outfit_data(self._employee_uniform_data_female, persistence_service, Gender.FEMALE)

    def on_zone_load(self):
        sim_info_manager = services.sim_info_manager()
        for (employee_type, employee_id_list) in self._employee_sim_ids.items():
            for employee_id in employee_id_list:
                sim_info = sim_info_manager.get(employee_id)
                if sim_info is not None:
                    self._employees[sim_info.sim_id] = BusinessEmployeeData(self, sim_info, employee_type)
        self._employee_sim_ids.clear()
        self.update_employees(add_career_remove_callback=True)
        for employee_uniform in itertools.chain(self._employee_uniform_data_male.values(), self._employee_uniform_data_female.values()):
            self._send_employee_uniform_data(employee_uniform)
        services.get_event_manager().register_single_event(self, TestEvent.SkillLevelChange)
        if not self._business_manager.is_active_household_and_zone():
            return
        if self._business_manager.is_open:
            for sim_info in self.get_employees_on_payroll():
                if self.get_employee_career(sim_info) is None:
                    self.on_employee_clock_out(sim_info)
                (clock_in_time, _) = self._employee_payroll[sim_info.sim_id]
                if clock_in_time is not None:
                    self._register_employee_callbacks(sim_info)
                    employee_data = self.get_employee_data(sim_info)
                    employee_data.add_career_buff()

    def on_client_disconnect(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.SkillLevelChange)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SkillLevelChange:
            employee_data = self._employees.get(sim_info.sim_id, None)
            if employee_data is not None:
                skill = resolver.event_kwargs['skill']
                if self._business_manager.is_valid_employee_skill(skill.stat_type, employee_data.employee_type):
                    employee_data.leveled_skill_up(skill.stat_type)
                    if self._business_manager.tuning_data.show_empolyee_skill_level_up_notification:
                        skill.force_show_level_notification(resolver.event_kwargs['new_level'])

    def open_business(self):
        if self._business_manager.is_owned_by_npc:
            return
        if self._business_manager.business_zone_id == services.current_zone_id():
            zone_director = services.venue_service().get_zone_director()
            zone_director.start_employee_situations(self._employees, owned_by_npc=not self._business_manager.is_owner_household_active)
        else:
            for employee_id in self._employees:
                employee_sim_info = services.sim_info_manager().get(employee_id)
                if employee_sim_info is not None:
                    self.on_employee_clock_in(employee_sim_info)

    def close_business(self):
        for sim_info in itertools.chain(self.get_employees_gen(), self.get_employees_on_payroll()):
            self.on_employee_clock_out(sim_info)
        self._daily_employee_wages = self.get_total_employee_wages()
        self._employee_payroll.clear()

    def _clear_state(self):
        self._daily_employee_wages = 0

    def get_employee_tuning_data_for_employee_type(self, employee_type):
        return self._business_manager.tuning_data.employee_data_map.get(employee_type, None)

    def get_employee_data(self, employee_sim_info):
        return self._employees.get(employee_sim_info.sim_id, None)

    def get_employee_career(self, employee_sim_info):
        employee_data = self.get_employee_data(employee_sim_info)
        if employee_data is None:
            return
        employee_type_tuning_data = self.get_employee_tuning_data_for_employee_type(employee_data.employee_type)
        if employee_type_tuning_data is None:
            return
        return employee_sim_info.career_tracker.get_career_by_uid(employee_type_tuning_data.career.guid64)

    def get_employee_career_level(self, employee_sim_info):
        career = self.get_employee_career(employee_sim_info)
        if career is None:
            return
        return career.current_level_tuning

    def is_employee(self, sim_info):
        if self._employee_sim_ids:
            for employee_ids in self._employee_sim_ids.values():
                if sim_info.sim_id in employee_ids:
                    return True
            return False
        return sim_info.sim_id in self._employees

    def is_employee_clocked_in(self, sim_info):
        (clock_in_time, _) = self._employee_payroll.get(sim_info.sim_id, (None, None))
        return clock_in_time is not None

    def on_employee_clock_in(self, employee_sim_info):
        self._register_employee_callbacks(employee_sim_info)
        clock_in_time = services.time_service().sim_now
        if employee_sim_info.sim_id not in self._employee_payroll:
            self._employee_payroll[employee_sim_info.sim_id] = (clock_in_time, Counter())
        (_, payroll_data) = self._employee_payroll[employee_sim_info.sim_id]
        career_level = self.get_employee_career_level(employee_sim_info)
        if career_level is None:
            logger.error('Employee {} trying to clock in with career level None for Business {}', employee_sim_info, self._business_manager)
        else:
            payroll_data[career_level] += 0
            self._employee_payroll[employee_sim_info.sim_id] = (clock_in_time, payroll_data)
        employee_data = self.get_employee_data(employee_sim_info)
        if employee_data is not None:
            employee_data.add_career_buff()
        else:
            logger.error('{} is being clocked in but not registered as an employee.', employee_sim_info)

    def on_employee_clock_out(self, employee_sim_info, career_level=DEFAULT):
        career = self.get_employee_career(employee_sim_info)
        if career is not None:
            if self.on_employee_career_promotion in career.on_promoted:
                career.on_promoted.unregister(self.on_employee_career_promotion)
            if self.on_employee_career_demotion in career.on_demoted:
                career.on_demoted.unregister(self.on_employee_career_demotion)
        if employee_sim_info.sim_id not in self._employee_payroll:
            return
        (clock_in_time, payroll_data) = self._employee_payroll[employee_sim_info.sim_id]
        if clock_in_time is not None:
            career_level = self.get_employee_career_level(employee_sim_info) if career_level is DEFAULT else career_level
            if career_level is not None:
                clock_out_time = services.time_service().sim_now
                payroll_data[career_level] += (clock_out_time - clock_in_time).in_hours()
        self._employee_payroll[employee_sim_info.sim_id] = (None, payroll_data)
        employee_data = self.get_employee_data(employee_sim_info)
        if employee_data is not None:
            employee_data.remove_career_buff()
        else:
            logger.error('{} is being clocked out but not registered as an employee.', employee_sim_info)

    def get_employee_wages(self, employee_sim_info):
        if not self._business_manager.is_open:
            return 0
        if employee_sim_info.sim_id not in self._employee_payroll:
            return 0
        (clock_in_time, payroll_data) = self._employee_payroll[employee_sim_info.sim_id]
        total_wages = sum(career_level.simoleons_per_hour*round(hours_worked) for (career_level, hours_worked) in payroll_data.items())
        if clock_in_time is not None:
            hours_worked = (services.time_service().sim_now - clock_in_time).in_hours()
            total_wages += self.get_employee_career_level(employee_sim_info).simoleons_per_hour*round(hours_worked)
        return math.ceil(total_wages)

    def get_total_employee_wages_per_hour(self):
        total = 0
        for sim_info in self.get_employee_sim_infos():
            career_level = self.get_employee_career_level(sim_info)
            total += career_level.simoleons_per_hour
        return total

    def get_total_employee_wages(self):
        return sum(self.get_employee_wages(sim_info) for sim_info in self.get_employees_on_payroll())

    def final_daily_wages(self):
        return self._daily_employee_wages

    def get_employee_wages_breakdown_gen(self, employee_sim_info):
        if employee_sim_info.sim_id not in self._employee_payroll:
            return
        (clock_in_time, payroll_data) = self._employee_payroll[employee_sim_info.sim_id]
        for (career_level, hours_worked) in payroll_data.items():
            hours_worked += (services.time_service().sim_now - clock_in_time).in_hours()
            yield (career_level, round(hours_worked))

    @sim_info_auto_finder
    def get_employees_gen(self):
        yield from self._employees

    def get_desired_career_level(self, sim_info, employee_type):
        employee_tuning_data = self.get_employee_tuning_data_for_employee_type(employee_type)
        skill_completion = 0
        for (skill_type, skill_data) in employee_tuning_data.employee_skills.items():
            skill_or_skill_type = sim_info.get_stat_instance(skill_type) or skill_type
            user_value = skill_or_skill_type.get_user_value()
            max_skill_level = skill_or_skill_type.max_level
            skill_completion += skill_data.weight*user_value/max_skill_level
        skill_completion = skill_completion/len(employee_tuning_data.employee_skills.keys())
        max_career_level = len(employee_tuning_data.career.start_track.career_levels) - 1
        career_level = clamp(0, floor(employee_tuning_data.weighted_skill_to_career_level_ratio*skill_completion*max_career_level), max_career_level)
        return career_level

    def add_employee(self, sim_info, employee_type, is_npc_employee=False):
        if self.is_employee(sim_info):
            logger.error('Trying to add a duplicate employee: {}. Trying to add as type: {}', sim_info, employee_type)
            return
        employee_tuning_data = self.get_employee_tuning_data_for_employee_type(employee_type)
        employee_career_type = employee_tuning_data.career
        if employee_career_type is None:
            logger.error('Trying to add an employee with an invalid type: {}.', employee_type)
            return
        employee_career = employee_career_type(sim_info)
        employee = BusinessEmployeeData(self, sim_info, employee_type)
        career_location = employee_career.get_career_location()
        career_location.set_zone_id(self._business_manager.business_zone_id)
        career_level = self.get_desired_career_level(sim_info, employee_type) + 1
        sim_info.career_tracker.add_career(employee_career, user_level_override=career_level)
        sim_info.add_statistic(employee_tuning_data.satisfaction_commodity, employee_tuning_data.satisfaction_commodity.initial_value)
        self._employees[sim_info.sim_id] = employee
        self._register_on_employee_career_removed_callback(sim_info, career=employee_career)
        if is_npc_employee:
            return
        zone_director = services.venue_service().get_zone_director()
        if zone_director is not None:
            zone_director.on_add_employee(sim_info, employee)

    def remove_employee(self, sim_info):
        employee_data = self.get_employee_data(sim_info)
        if employee_data is None:
            logger.error("Trying to remove an employee from a business but the employee doesn't belong to this business. {}", sim_info)
            return
        if self._business_manager.is_open:
            self.on_employee_clock_out(sim_info)
        if sim_info.sim_id in self._employee_payroll:
            del self._employee_payroll[sim_info.sim_id]
        employee_tuning_data = self.get_employee_tuning_data_for_employee_type(employee_data.employee_type)
        self._unregister_on_employee_career_removed_callback(sim_info)
        sim_info.career_tracker.remove_career(employee_tuning_data.career.guid64)
        if self.is_employee(sim_info):
            del self._employees[sim_info.sim_id]

    def remove_invalid_employee(self, sim_id):
        if sim_id in self._employee_payroll:
            del self._employee_payroll[sim_id]
        if sim_id in self._employees:
            del self._employees[sim_id]

    def update_employees(self, add_career_remove_callback=False):
        for employee_data in tuple(self._employees.values()):
            employee_type_data = self.get_employee_tuning_data_for_employee_type(employee_data.employee_type)
            employee_sim_info = employee_data.get_employee_sim_info()
            if employee_sim_info is None:
                self.remove_invalid_employee(employee_data.employee_sim_id)
            elif employee_sim_info.career_tracker is None:
                self.remove_employee(employee_sim_info)
            else:
                career = employee_sim_info.career_tracker.get_career_by_uid(employee_type_data.career.guid64)
                if career is None:
                    self.remove_employee(employee_sim_info)
                elif add_career_remove_callback:
                    self._register_on_employee_career_removed_callback(employee_sim_info, career=career)

    @sim_info_auto_finder
    def get_employee_sim_infos(self):
        return self._employees

    @sim_info_auto_finder
    def get_employees_on_payroll(self):
        return self._employee_payroll

    def run_employee_interaction(self, affordance, target_sim):
        active_sim = services.get_active_sim()
        if active_sim is None:
            return False
        context = InteractionContext(active_sim, InteractionContext.SOURCE_PIE_MENU, Priority.High)
        return active_sim.push_super_affordance(affordance, None, context, picked_item_ids=(target_sim.sim_id,))

    def _register_employee_callbacks(self, employee_sim_info):
        career = self.get_employee_career(employee_sim_info)
        if career is None:
            logger.error('Employee {} does not have active business career', employee_sim_info)
            return
        if self.on_employee_career_promotion not in career.on_promoted:
            career.on_promoted.register(self.on_employee_career_promotion)
        if self.on_employee_career_demotion not in career.on_demoted:
            career.on_demoted.register(self.on_employee_career_demotion)

    def on_employee_career_promotion(self, sim_info):
        if not self._business_manager.is_open:
            return
        if sim_info.sim_id not in self._employee_payroll:
            return
        career = self.get_employee_career(sim_info)
        self.on_employee_clock_out(sim_info, career_level=career.previous_level_tuning)
        self.on_employee_clock_in(sim_info)

    def on_employee_career_demotion(self, sim_info):
        if not self._business_manager.is_open:
            return
        if sim_info.sim_id not in self._employee_payroll:
            return
        career = self.get_employee_career(sim_info)
        self.on_employee_clock_out(sim_info, career_level=career.next_level_tuning)
        self.on_employee_clock_in(sim_info)

    def _register_on_employee_career_removed_callback(self, employee_sim_info, career=None):
        if career is None:
            career = self.get_employee_career(employee_sim_info)
        if self.on_employee_career_removed not in career.on_career_removed:
            career.on_career_removed.append(self.on_employee_career_removed)

    def _unregister_on_employee_career_removed_callback(self, employee_sim_info):
        career = self.get_employee_career(employee_sim_info)
        if career is not None and self.on_employee_career_removed in career.on_career_removed:
            career.on_career_removed.remove(self.on_employee_career_removed)

    def on_employee_career_removed(self, sim_info):
        if self.is_employee(sim_info):
            self.remove_employee(sim_info)
        return True

    def get_employee_uniform_data(self, employee_type, gender:Gender, sim_id=0):
        employee_type_tuning_data = self.get_employee_tuning_data_for_employee_type(employee_type)
        if employee_type_tuning_data is None:
            logger.error('Trying to get employee uniform data for an invalid employee type: {}.', employee_type)
            return
        if gender == Gender.MALE:
            if self._employee_uniform_data_male and self._employee_uniform_data_male[employee_type] is None:
                self._employee_uniform_data_male[employee_type] = SimInfoBaseWrapper(sim_id=sim_id)
                self._employee_uniform_data_male[employee_type].load_from_resource(employee_type_tuning_data.uniform_male)
                self._employee_uniform_data_male[employee_type].set_current_outfit((OutfitCategory.CAREER, 0))
                if not sim_id:
                    self._send_employee_uniform_data(self._employee_uniform_data_male[employee_type])
            return self._employee_uniform_data_male[employee_type]
        elif gender == Gender.FEMALE:
            if self._employee_uniform_data_female and self._employee_uniform_data_female[employee_type] is None:
                self._employee_uniform_data_female[employee_type] = SimInfoBaseWrapper(sim_id=sim_id)
                self._employee_uniform_data_female[employee_type].load_from_resource(employee_type_tuning_data.uniform_female)
                self._employee_uniform_data_female[employee_type].set_current_outfit((OutfitCategory.CAREER, 0))
                if not sim_id:
                    self._send_employee_uniform_data(self._employee_uniform_data_female[employee_type])
            return self._employee_uniform_data_female[employee_type]

    def _send_employee_uniform_data(self, employee_uniform_data):
        employee_uniform_data.manager = services.sim_info_manager()
        Distributor.instance().add_object(employee_uniform_data)

    def get_number_of_employees_by_type(self, employee_type):
        return sum(1 for employee_data in self._employees.values() if employee_data.employee_type == employee_type)

    def get_employees_by_type(self, employee_type):
        return [employee for (employee, employee_data) in self._employees.items() if employee_data.employee_type == employee_type]
