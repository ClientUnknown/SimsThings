from protocolbuffers import Routing_pb2from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, Tunable, TunableRange, TunableRealSecond
class PortalEvent(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'time': Tunable(description='\n            The time from when the portal happens.\n            \n            A positive number is after the portal happens and a negative \n            number is before a portal happens. So if you want a sim to fade\n            out before using a portal the value here should be -1.\n            ', tunable_type=float, default=1.0)}

    def get_portal_op(self, actor, obj):
        raise NotImplementedError

    def get_portal_event_type(self):
        raise NotImplementedError

class PortalEventEnter(PortalEvent):

    def get_portal_op(self, actor, obj):
        op = Routing_pb2.PortalEnterEvent()
        op.portal_object_id = obj.id
        return op

    def get_portal_event_type(self):
        return Routing_pb2.RouteEvent.PORTAL_ENTER

class PortalEventExit(PortalEvent):

    def get_portal_op(self, actor, obj):
        op = Routing_pb2.PortalExitEvent()
        op.portal_object_id = obj.id
        return op

    def get_portal_event_type(self):
        return Routing_pb2.RouteEvent.PORTAL_EXIT

class PortalEventChangeOpacity(PortalEvent):
    FACTORY_TUNABLES = {'opacity': TunableRange(description='\n            The target opacity to set the actor to. 0 is invisible and 1 is\n            fully visible.\n            ', tunable_type=float, default=0, minimum=0, maximum=1), 'duration': TunableRealSecond(description='\n            How long the change in opacity should take in seconds.\n            ', default=0.0)}

    def get_portal_op(self, actor, obj):
        op = Routing_pb2.PortalChangeOpacityEvent()
        op.object_id = actor.id
        op.opacity = self.opacity
        op.duration = self.duration
        return op

    def get_portal_event_type(self):
        return Routing_pb2.RouteEvent.PORTAL_CHANGE_OPACITY

class TunablePortalEventVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, enter=PortalEventEnter.TunableFactory(), exit=PortalEventExit.TunableFactory(), change_opacity=PortalEventChangeOpacity.TunableFactory(), default='change_opacity', **kwargs)
