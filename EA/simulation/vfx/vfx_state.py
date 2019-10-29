from distributor.ops import ElementDistributionOpMixin, SetVFXStatefrom objects.components.needs_state_value import NeedsStateValuefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableRange, OptionalTunable, TunableReference, TunableListimport servicesimport sims4.resources
class SetEffectState(ElementDistributionOpMixin, SetVFXState):

    def __init__(self, *args, write_callback=None):
        super().__init__(*args)
        self._write_callback = write_callback

    def write(self, msg):
        super().write(msg)
        if self._write_callback:
            self._write_callback(self)

class PlayEffectState(HasTunableFactory, AutoFactoryInit, NeedsStateValue):
    FACTORY_TUNABLES = {'state_index': TunableRange(description='\n            The index of the state to apply to the VFX activated by the state\n            that is also activating this state change. This is defined in the\n            Swarm file.\n            ', tunable_type=int, minimum=0, default=0), 'state_owning_vfx': OptionalTunable(description='\n            Specify which client states the VFX that we care about are owned by.\n            ', tunable=TunableList(description='\n                Specify specific state(s) that own VFX.\n                ', tunable=TunableReference(description='\n                    The client state(s) owning the VFX we want to modify.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState', pack_safe=True)), enabled_name='Use_Specific_State', disabled_name='Use_Current_State')}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target
        self._pending_primitives = None

    def start(self):
        states_owning_vfx = (self.state_value.state,) if self.state_owning_vfx is None else self.state_owning_vfx
        client_connected = bool(services.client_manager())
        for state_owning_vfx in states_owning_vfx:
            vfx_distributable = self.distributable_manager.get_distributable('vfx_state', state_owning_vfx)
            if vfx_distributable is not None:
                target = vfx_distributable.target
                vfx_state_op = SetEffectState(target.id, vfx_distributable.actor_id, self.state_index, write_callback=self.write_callback)
                vfx_state_op.attach(target)
                if not client_connected:
                    if self._pending_primitives is None:
                        self._pending_primitives = []
                    self._pending_primitives.append(vfx_state_op)

    def stop(self, **kwargs):
        pass

    def write_callback(self, primitive):
        if self._pending_primitives:
            self._pending_primitives.remove(primitive)
