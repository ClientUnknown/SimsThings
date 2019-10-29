from animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom carry.carry_elements import enter_carry_while_holdingfrom element_utils import build_element, build_critical_section_with_finallyfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.constraints import GLOBAL_STUB_CREATE_TARGETfrom interactions.context import QueueInsertStrategyfrom interactions.priority import Priorityfrom interactions.utils.routing import FollowPathfrom objects.system import create_objectfrom postures import PostureTrackfrom routing.route_events.route_event_type_animation import RouteEventTypeAnimationfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableReference, TunableMapping, OptionalTunable, TunableEnumEntryimport servicesimport sims4.loglogger = sims4.log.Logger('RouteEvents', default_owner='bosee')
class _RouteEventTypeCarry(RouteEventTypeAnimation):

    def _execute_internal(self, actor):
        raise NotImplementedError

    def execute(self, actor, **kwargs):
        if actor.routing_component.route_interaction is None:
            return
        return self._execute_internal(actor)

    def process(self, actor):
        pass

class RouteEventTypeCreateCarry(_RouteEventTypeCarry):
    FACTORY_TUNABLES = {'traits_to_object_to_create': TunableMapping(description='\n            ', key_type=TunableReference(description='\n                If sim has this trait, then create the object in the accompanying\n                value. Otherwise, fall back to default_object_to_create.\n                ', manager=services.get_instance_manager(Types.TRAIT), pack_safe=True), value_type=TunableReference(description='\n                The definition of the object to be created if sim has this trait.\n                ', manager=services.definition_manager())), 'default_object_to_create': TunableReference(description='\n            The definition of the object to be created.\n            ', manager=services.definition_manager()), 'carry_interaction': TunableReference(description='\n            Interaction to hold onto the object created.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'priority_override': OptionalTunable(description='\n            If enabled then we will override the priority of the the carry\n            interaction.  If disabled then we will continue to use the\n            priority of the route event that pushed this.\n            ', tunable=TunableEnumEntry(description='\n                The overwritten priority to use.\n                ', tunable_type=Priority, default=Priority.Low))}

    @classmethod
    def test(cls, actor, event_data_tuning):
        if actor is None:
            return TestResult(False, 'None actor for RouteEventTypeCreateCarry')
        return super().test(actor, event_data_tuning, ignore_carry=True)

    def prepare(self, actor):

        def set_target(asm):
            asm.set_current_state('entry')
            asm.set_actor(self.animation_element.actor_name, actor)
            asm.set_actor(self.animation_element.target_name, GLOBAL_STUB_CREATE_TARGET)
            return True

        super().prepare(actor, setup_asm_override=set_target)

    def should_remove_on_execute(self):
        return False

    def _execute_internal(self, actor):
        left_carry_target = actor.posture_state.left.target
        right_carry_target = actor.posture_state.right.target
        if left_carry_target is not None or right_carry_target is not None:
            actor.routing_component.remove_route_event_by_data(self)
            return
        object_to_create = None
        for (trait, trait_based_object) in self.traits_to_object_to_create.items():
            if actor.has_trait(trait):
                object_to_create = trait_based_object
                break
        if object_to_create is None:
            object_to_create = self.default_object_to_create
        created_object = create_object(object_to_create)

        def set_target(asm):
            asm.set_current_state('entry')
            asm.set_actor(self.animation_element.actor_name, actor)
            asm.set_actor(self.animation_element.target_name, created_object)
            return True

        route_interaction = actor.routing_component.route_interaction
        route_event_animation = self.animation_element(route_interaction, setup_asm_additional=set_target, enable_auto_exit=False)
        asm = route_event_animation.get_asm(use_cache=False)
        if asm is None:
            logger.warn('Unable to get a valid Route Event ASM ({}) for {}.', route_event_animation, actor)
            actor.routing_component.remove_route_event_by_data(self)
            return

        def _send_arb(timeline):
            self.arb = Arb()
            route_event_animation.append_to_arb(asm, self.arb)
            route_event_animation.append_exit_to_arb(asm, self.arb)
            if self.arb is None:
                logger.error('Unable to create arb for Route Event: {}', self)
                return False
            distribute_arb_element(self.arb, master=actor, immediate=True)
            return True

        enter_carry_element = enter_carry_while_holding(route_interaction, obj=created_object, owning_affordance=self.carry_interaction, carry_track_override=PostureTrack.RIGHT, target_participant_type=ParticipantType.CarriedObject, sequence=build_element(_send_arb), carry_sim=actor, asm_context=asm.context, priority_override=self.priority_override, target_override=created_object)

        def event_finished(_):
            if actor.routing_component is None:
                return
            actor.routing_component.remove_route_event_by_data(self)

        enter_carry_element = build_critical_section_with_finally(enter_carry_element, event_finished)
        umbrella_timeline = services.time_service().sim_timeline
        umbrella_timeline.schedule(enter_carry_element)
