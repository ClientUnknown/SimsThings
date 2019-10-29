from objects.components.needs_state_value import NeedsStateValuefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntryimport sims4.logimport enumlogger = sims4.log.Logger('LiveDrag', default_owner='rmccord')
class LiveDragStateOp(enum.Int):
    LIVE_DRAG_OP_ALLOW = ...
    LIVE_DRAG_OP_DISABLE = ...

class LiveDragStateOperation(HasTunableFactory, AutoFactoryInit, NeedsStateValue):
    FACTORY_TUNABLES = {'operation': TunableEnumEntry(description='\n            The Live Drag change we want this state to provide.\n            LIVE_DRAG_OP_ALLOW: A setting that does not restrict live drag.\n            This will only have an effect if the previous state disabled live\n            drag. \n            LIVE_DRAG_OP_DISABLE: A setting to disable live drag for this\n            state. Only another state that forces Live Drag to enable will\n            override this state.\n            ', tunable_type=LiveDragStateOp, default=LiveDragStateOp.LIVE_DRAG_OP_ALLOW)}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def start(self, *_, **__):
        if self.target is None or self.target.live_drag_component is None:
            if not self.target.is_prop:
                logger.error('Applying a Live Drag State Op on {} from state {}. Does this object support live drag?', self.target, self.state_value)
            return
        if self.operation == LiveDragStateOp.LIVE_DRAG_OP_ALLOW:
            return
        self.target.live_drag_component.add_live_drag_state_op(self.state_value, self.operation)

    def stop(self, *_, **__):
        if self.target is None or self.target.live_drag_component is None:
            if not self.target.is_prop:
                logger.error('Removing a Live Drag State Op on {} from state {}. Does this object support live drag?', self.target, self.state_value)
            return
        if self.operation == LiveDragStateOp.LIVE_DRAG_OP_ALLOW:
            return
        self.target.live_drag_component.remove_live_drag_state_op(self.state_value)
