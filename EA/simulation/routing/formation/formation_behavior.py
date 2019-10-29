from date_and_time import create_time_spanfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom routing.route_enums import RoutingStageEventfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableReference, TunableVariant, OptionalTunable, TunableSimMinute, TunableList, Tunableimport alarmsimport services
class _BehaviorAction(HasTunableFactory, AutoFactoryInit):

    def __init__(self, master, slave, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._master = master
        self._slave = slave

    def execute_behavior_action(self):
        pass

    def stop_behavior_action(self, *, from_release):
        pass

class _BehaviorActionRunInteractionLiability(Liability):
    LIABILITY_TOKEN = 'BehaviorActionRunInteractionLiability'

    def __init__(self, action, trigger_interaction_liability, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._action = action
        self._trigger_interaction_liability = trigger_interaction_liability

    def transfer(self, interaction):
        self._action._interaction = interaction

    def release(self):
        if self._trigger_interaction_liability is not None:
            self._trigger_interaction_liability.remove_triggered_interaction()

class _BehaviorActionCancelInteractionLiability(Liability):
    LIABILITY_TOKEN = '_BehaviorActionCancelInteractionLiability'

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._trigger_interaction = interaction
        self._triggered_interaction_count = 0

    def transfer(self, interaction):
        self._trigger_interaction = interaction

    def add_triggered_interaction(self):
        self._triggered_interaction_count += 1

    def remove_triggered_interaction(self):
        self._triggered_interaction_count -= 1
        if not self._triggered_interaction_count:
            self._trigger_interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Triggered interactions finished.')

class _BehaviorActionRunInteraction(_BehaviorAction):
    FACTORY_TUNABLES = {'affordance': TunableReference(description='\n            The interaction to push.\n            ', manager=services.affordance_manager()), 'cancel_trigger_interaction': Tunable(description="\n            If this is checked, once this interaction has completed, we'll\n            attempt to cancel the triggering interaction. If multiple\n            interactions are triggered (e.g. by multiple behaviors or multiple\n            slaves), the last interaction to complete cancels the interaction.\n            ", tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = None

    def execute_behavior_action(self, resolver=None, **event_data):
        for si in self._slave.si_state:
            if si.get_liability(_BehaviorActionRunInteractionLiability.LIABILITY_TOKEN) is not None:
                return
        context = InteractionContext(self._slave, InteractionContext.SOURCE_SCRIPT, Priority.Low)
        result = self._slave.push_super_affordance(self.affordance, None, context)
        if not result:
            return
        self._interaction = result.interaction
        cancel_trigger_liability = None
        if self.cancel_trigger_interaction:
            trigger_interaction = resolver.interaction if resolver is not None else None
            if trigger_interaction is not None:
                cancel_trigger_liability = trigger_interaction.get_liability(_BehaviorActionCancelInteractionLiability.LIABILITY_TOKEN)
                if cancel_trigger_liability is None:
                    cancel_trigger_liability = _BehaviorActionCancelInteractionLiability(trigger_interaction)
                    trigger_interaction.add_liability(_BehaviorActionCancelInteractionLiability.LIABILITY_TOKEN, cancel_trigger_liability)
                cancel_trigger_liability.add_triggered_interaction()
        liability = _BehaviorActionRunInteractionLiability(self, cancel_trigger_liability)
        self._interaction.add_liability(_BehaviorActionRunInteractionLiability.LIABILITY_TOKEN, liability)

    def stop_behavior_action(self, *, from_release):
        if from_release:
            return
        if self._interaction is not None and not self._interaction.is_finishing:
            self._interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Slaved Sim required to route.')

class TunableBehaviorActionVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, run_interaction=_BehaviorActionRunInteraction.TunableFactory(), default='run_interaction', **kwargs)

class _BehaviorTrigger(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'action': TunableBehaviorActionVariant(description='\n            The action we want to execute.\n            '), 'delay': OptionalTunable(description='\n            If enabled, force a delay before executing the action.\n            ', tunable=TunableSimMinute(default=4, minimum=0))}

    def __init__(self, formation_behavior, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._formation_behavior = formation_behavior

    @property
    def master(self):
        return self._formation_behavior.master

    @property
    def slave(self):
        return self._formation_behavior.slave

    def _callback(self, *_, **event_data):
        self._formation_behavior.execute_action(self.action, delay=self.delay, **event_data)

class _BehaviorTriggerRouteEnd(_BehaviorTrigger):

    def get_events(self):
        return (RoutingStageEvent.ROUTE_END,)

class _BehaviorTriggerInteractionStart(_BehaviorTrigger):
    FACTORY_TUNABLES = {'affordance': TunableReference(description='\n            The trigger is fired if the master runs this specific interaction.\n            ', manager=services.affordance_manager())}

    def get_events(self):
        return (TestEvent.InteractionStart,)

    def _callback(self, resolver):
        if resolver.interaction is None:
            return
        if resolver.interaction.get_interaction_type() is not self.affordance:
            return
        return super()._callback(resolver=resolver)

class TunableBehaviorTriggerVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, route_stop=_BehaviorTriggerRouteEnd.TunableFactory(), interaction_start=_BehaviorTriggerInteractionStart.TunableFactory(), default='route_stop', **kwargs)

class RoutingFormationBehavior(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'behavior_triggers': TunableList(description='\n            A series of behavior definitions that describe how Sims behave while\n            slaved in this routing formation.\n            ', tunable=TunableBehaviorTriggerVariant())}

    def __init__(self, master, slave, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._master = master
        self._slave = slave
        self._triggers = [t(self) for t in self.behavior_triggers]
        self._actions = []
        self._alarms = []
        self._registered_events = set()

    @property
    def master(self):
        return self._master

    @property
    def slave(self):
        return self._slave

    def handle_event(self, actor, event_type, *args, **kwargs):
        if self.master is not actor:
            return
        for trigger in self._triggers:
            if event_type in trigger.get_events():
                trigger._callback(*args, **kwargs)

    def on_add(self):
        event_manager = services.get_event_manager()
        self._master.register_routing_stage_event(RoutingStageEvent.ROUTE_START, self.stop_actions)
        for trigger in self._triggers:
            for event_type in trigger.get_events():
                if event_type in self._registered_events:
                    pass
                elif isinstance(event_type, TestEvent):
                    event_manager.register_single_event(self, event_type)
                else:
                    self.master.register_routing_stage_event(event_type, self.handle_event)
                self._registered_events.add(event_type)

    def on_release(self):
        event_manager = services.get_event_manager()
        for event_type in self._registered_events:
            if isinstance(event_type, TestEvent):
                event_manager.unregister_single_event(self, event_type)
            else:
                self.master.unregister_routing_stage_event(event_type, self.handle_event)
        self._master.unregister_routing_stage_event(RoutingStageEvent.ROUTE_START, self.stop_actions)
        self.stop_actions(from_release=True)

    def execute_action(self, behavior_action, delay=None, **event_data):
        if delay is not None:
            alarm_handle = alarms.add_alarm(self, create_time_span(minutes=delay), self._get_delay_callback(behavior_action, **event_data))
            self._alarms.append(alarm_handle)
        else:
            behavior_action = behavior_action(self._master, self._slave)
            behavior_action.execute_behavior_action(**event_data)
            self._actions.append(behavior_action)

    def _get_delay_callback(self, behavior_action, **event_data):

        def _delay_callback(alarm_handle):
            self._alarms.remove(alarm_handle)
            self.execute_action(behavior_action, **event_data)

        return _delay_callback

    def stop_actions(self, *_, from_release=False, path=None, **__):
        if path is not None:
            slave_data = self.master.get_formation_data_for_slave(self.slave)
            if slave_data is not None and path.length() < slave_data.route_length_minimum:
                return
        for action in self._actions:
            action.stop_behavior_action(from_release=from_release)
        for alarm_handle in self._alarms:
            alarms.cancel_alarm(alarm_handle)
        self._alarms.clear()
        self._actions.clear()
