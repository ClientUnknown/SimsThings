import autonomyimport role.role_state
class RoleStateTracker:
    ACTIVE_ROLE_INDEX = 0

    def __init__(self, sim):
        self._sim = sim
        self._role_states = []
        self._always_active_roles = []
        for _ in role.role_state.RolePriority:
            self._role_states.append([])
        self._active_role_states = set()

    def __iter__(self):
        return iter(self._role_states)

    def __len__(self):
        return len(self._role_states)

    def reset(self):
        role_states_to_remove = [role_state for role_priority in self for role_state in role_priority]
        for role_state in role_states_to_remove:
            self.remove_role(role_state, activate_next_lower_priority_role=False)

    def shutdown(self):
        self.reset()
        self._sim = None

    def _find_active_role_priority(self):
        index = len(self._role_states) - 1
        if index >= 0:
            if self._role_states[index]:
                return index
            index -= 1
        return index

    def add_role(self, new_role_state, role_affordance_target=None, situation=None, **affordance_override_kwargs):
        old_active_priority = self._find_active_role_priority()
        self._role_states[new_role_state.role_priority].append(new_role_state)
        new_active_priority = self._find_active_role_priority()
        if new_role_state.role_priority >= old_active_priority or new_role_state.always_active:
            new_role_state.on_role_activate(role_affordance_target=role_affordance_target, situation=situation, **affordance_override_kwargs)
            if new_role_state.always_active:
                self._always_active_roles.append(new_role_state)
            if old_active_priority != -1:
                for role_state in self._role_states[old_active_priority]:
                    if not role_state.always_active:
                        role_state.on_role_deactivated()
        self._active_role_states.clear()
        self._active_role_states.update(self._role_states[new_active_priority])
        self._active_role_states.update(self._always_active_roles)
        self._sim.cancel_actively_running_full_autonomy_request()

    def remove_role(self, role_state_to_remove, activate_next_lower_priority_role=True):
        if role_state_to_remove not in self._role_states[role_state_to_remove.role_priority]:
            return
        if activate_next_lower_priority_role:
            old_active_priority = self._find_active_role_priority()
        self._role_states[role_state_to_remove.role_priority].remove(role_state_to_remove)
        if role_state_to_remove in self._always_active_roles:
            self._always_active_roles.remove(role_state_to_remove)
        new_active_priority = self._find_active_role_priority()
        self._active_role_states.clear()
        self._active_role_states.update(self._role_states[new_active_priority])
        self._active_role_states.update(self._always_active_roles)
        if old_active_priority != new_active_priority:
            for role_state in self._role_states[new_active_priority]:
                if role_state not in self._always_active_roles:
                    role_state.on_role_activate()
        role_state_to_remove.on_role_deactivated()
        self._sim.cancel_actively_running_full_autonomy_request()

    @property
    def active_role_states(self):
        return tuple(self._active_role_states)

    def get_autonomy_state(self):
        for role_state in self.active_role_states:
            if role_state.autonomy_state_override:
                return role_state.autonomy_state_override
        return autonomy.settings.AutonomyState.UNDEFINED
