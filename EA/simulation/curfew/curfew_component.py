from curfew.curfew_service import CurfewServicefrom objects.components import Componentfrom objects.components.state import TunableStateValueReference, TunableStateTypeReferencefrom objects.components.types import CURFEW_COMPONENTfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableList, TunableMapping, TunableReferenceimport services
class CurfewComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=CURFEW_COMPONENT):
    FACTORY_TUNABLES = {'curfew_state_reference': TunableStateTypeReference(description='\n            This is a reference to the State type we will be manipulating when\n            we change states on this object.\n            '), 'times_state_reference': TunableStateTypeReference(description='\n            This is a reference to the State type we will be manipulating when\n            we change states on this object.\n            '), 'curfew_not_set': TunableStateValueReference(description='\n            This is the reference to the state to apply on the owning object\n            when there is no active curfew setting. Or the setting is UNSET.\n            '), 'curfew_warning_state': TunableStateValueReference(description='\n            This is the reference to the state to apply to the owning object\n            when the curfew is about to start.\n            '), 'curfew_past_state': TunableStateValueReference(description='\n            This is the reference to the state to apply to the owning object\n            when curfew is active.\n            '), 'curfew_on_state': TunableStateValueReference(description='\n            This is the reference to the state to apply to the owning object\n            when the curfew is set but not currently active.\n            '), 'not_set_state': TunableStateValueReference(description="\n            This is the reference to the state to apply to the owning object\n            when there isn't a curfew set at all.\n            "), 'times_set': TunableMapping(description='\n            This is a Mapping of time (in military time) to state to apply to\n            the owning object in order to display the correct time that the\n            curfew is set for.\n            ', key_type=int, value_type=TunableStateValueReference()), 'set_curfew_affordances': TunableList(description='\n            A List of the interactions that will be used to set the curfew\n            via this object.\n            ', tunable=TunableReference(description='\n              This is the interaction that will be used to "set" the curfew.\n                ', manager=services.affordance_manager(), class_restrictions=('SuperInteraction',)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_curfew_setting = None

    def on_add(self):
        curfew_service = services.get_curfew_service()
        current_curfew = curfew_service.get_zone_curfew(services.current_zone_id())
        if current_curfew not in self.times_set:
            pass
        self.apply_state_for_setting(current_curfew)
        self.apply_warning_state(current_curfew)
        self._register_for_alarms(curfew_service)

    def on_remove(self):
        curfew_service = services.get_curfew_service()
        self._unregister_for_alarms(curfew_service)

    def component_super_affordances_gen(self, **kwargs):
        yield from self.set_curfew_affordances

    def update_states(self, curfew_setting):
        if curfew_setting == self._current_curfew_setting:
            return
        self.apply_state_for_setting(curfew_setting)
        self.apply_warning_state(curfew_setting)

    def apply_state_for_setting(self, setting):
        if setting is CurfewService.UNSET:
            self.owner.set_state(self.times_state_reference, self.not_set_state)
        state_to_apply = self.times_set.get(setting)
        if state_to_apply is not None:
            self.owner.set_state(self.times_state_reference, state_to_apply)

    def apply_warning_state(self, curfew_setting):
        if curfew_setting is CurfewService.UNSET:
            self.owner.set_state(self.curfew_state_reference, self.curfew_not_set)
            return
        now = services.time_service().sim_now.hour()
        if now >= CurfewService.CURFEW_END_TIME and now < curfew_setting:
            self._on_curfew_over_alarm()
        elif now == curfew_setting - 1:
            self._on_warning_time_alarm()
        else:
            self._on_curfew_started_alarm()

    def _register_for_alarms(self, curfew_service):
        curfew_service.register_for_alarm_callbacks(self._on_warning_time_alarm, self._on_curfew_started_alarm, self._on_curfew_over_alarm, self.update_states)

    def _unregister_for_alarms(self, curfew_service):
        curfew_service.unregister_for_alarm_callbacks(self._on_warning_time_alarm, self._on_curfew_started_alarm, self._on_curfew_over_alarm, self.update_states)

    def _on_warning_time_alarm(self):
        self.owner.set_state(self.curfew_state_reference, self.curfew_warning_state, force_update=True)

    def _on_curfew_started_alarm(self):
        self.owner.set_state(self.curfew_state_reference, self.curfew_past_state, force_update=True)

    def _on_curfew_over_alarm(self):
        self.owner.set_state(self.curfew_state_reference, self.curfew_on_state, force_update=True)
