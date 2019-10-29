from objects import ALL_HIDDEN_REASONSfrom objects.system import create_objectfrom sims.sim_info_types import Agefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableMapping, TunableEnumEntryimport servicesimport sims4.resources
class SchoolTuning(HasTunableSingletonFactory, AutoFactoryInit):

    class _SchoolData(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'school_career': TunableReference(description='\n                The career for this age.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'school_homework': TunableReference(description='\n                The homework object for this school career.\n                ', manager=services.definition_manager())}

    FACTORY_TUNABLES = {'school_data': TunableMapping(description='\n            Ensure Sims of these ages are auto-enrolled in school.\n            ', key_type=TunableEnumEntry(description='\n                The age for which we ensure a school career is added.\n                ', tunable_type=Age, default=Age.CHILD), value_type=_SchoolData.TunableFactory(), minlength=1)}

    def update_school_data(self, sim_info, create_homework=False):
        self._apply_school_career(sim_info)
        if create_homework:
            self._create_homework(sim_info)

    def _apply_school_career(self, sim_info):
        for (school_age, school_data) in self.school_data.items():
            school_career_type = school_data.school_career
            if school_age == sim_info.age:
                if school_career_type.guid64 not in sim_info.careers:
                    sim_info.career_tracker.add_career(school_career_type(sim_info, init_track=True))
                    sim_info.career_tracker.remove_career(school_career_type.guid64, post_quit_msg=False)
            else:
                sim_info.career_tracker.remove_career(school_career_type.guid64, post_quit_msg=False)

    def _create_homework(self, sim_info):
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        school_data = self.school_data.get(sim_info.age, None)
        if school_data is None:
            return
        inventory = sim.inventory_component
        if inventory.has_item_with_definition(school_data.school_homework):
            return
        obj = create_object(school_data.school_homework)
        if obj is not None:
            obj.update_ownership(sim)
            if inventory.can_add(obj):
                inventory.player_try_add_object(obj)
                return
            obj.destroy(source=self, cause='Failed to add homework to sim inventory')
