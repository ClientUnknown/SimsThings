from animation.animation_utils import flush_all_animationsfrom animation.object_animation import ObjectAnimationElementfrom element_utils import build_elementfrom elements import FunctionElement, SoftSleepElementfrom event_testing.resolver import DoubleObjectResolverfrom interactions.utils.loot import LootActionsfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableRange, TunableSimMinute, TunableListfrom tag import TunableTagsimport date_and_timeimport element_utilsimport services
class _ObjectRoutingActionAnimation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'reference': ObjectAnimationElement.TunableReference(description='\n            The animation to play.\n            '), 'event_id': OptionalTunable(description='\n            If enabled, loot and actions for this route destination is\n            blocked on this event.\n            ', tunable=TunableRange(tunable_type=int, default=100, minimum=1)), 'loop_time': TunableSimMinute(description='\n            For looping content, how long to idle for. For one-shot content,\n            leave this as zero.\n            ', default=0)}

    def __call__(self, timeline, obj, target, callback=None):
        executed_actions = False
        if self.event_id is not None:

            def _execute_actions(_):
                nonlocal executed_actions
                executed_actions = True
                if callback is not None:
                    callback()
                action_event_handle.release()

            animation_context = obj.get_idle_animation_context()
            action_event_handle = animation_context.register_event_handler(_execute_actions, handler_id=self.event_id)
        if self.loop_time > 0:
            sleep_element = SoftSleepElement(date_and_time.create_time_span(minutes=self.loop_time))
            sequence = build_element(sleep_element)
        else:
            sequence = ()
        animation_element = self.reference(obj, target=target, sequence=sequence)
        animation_element = build_element((animation_element, flush_all_animations))
        result = yield from element_utils.run_child(timeline, animation_element)
        if not result:
            return result
        if executed_actions or callback is not None:
            fn_element = FunctionElement(callback)
            yield from element_utils.run_child(timeline, fn_element)
        return True

class ObjectRoutingBehaviorAction(HasTunableSingletonFactory, AutoFactoryInit):

    def run_action_gen(self, timeline, obj, target):
        raise NotImplementedError

class ObjectRoutingBehaviorActionAnimation(ObjectRoutingBehaviorAction):
    FACTORY_TUNABLES = {'animation': _ObjectRoutingActionAnimation.TunableFactory()}

    def run_action_gen(self, timeline, obj, target):
        result = yield from self.animation(timeline, obj, target)
        if not result:
            return result
        return True

class ObjectRoutingBehaviorActionDestroyObjects(ObjectRoutingBehaviorAction):
    FACTORY_TUNABLES = {'radius': TunableDistanceSquared(description='\n            Only objects within this distance are considered.\n            ', default=1), 'tags': TunableTags(description='\n            Only objects with these tags are considered.\n            ', filter_prefixes=('Func',)), 'animation_success': _ObjectRoutingActionAnimation.TunableFactory(description='\n            The animation to play if there are objects to destroy.\n            '), 'animation_failure': _ObjectRoutingActionAnimation.TunableFactory(description='\n            The animation to play if there are no objects to destroy.\n            '), 'loot_success': TunableList(description='\n            For each destroyed object, apply this loot between the routing\n            object (Actor) and the destroyed object (Object).\n            ', tunable=LootActions.TunableReference())}

    def run_action_gen(self, timeline, obj, target):
        objects = tuple(o for o in services.object_manager().get_objects_matching_tags(self.tags, match_any=True) if (o.position - obj.position).magnitude_squared() <= self.radius)
        if not objects:
            result = yield from self.animation_failure(timeline, obj, target)
            return result
        else:

            def _callback():
                for o in objects:
                    resolver = DoubleObjectResolver(obj, o)
                    for loot_action in self.loot_success:
                        loot_action.apply_to_resolver(resolver)
                    o.remove_from_client(fade_duration=obj.FADE_DURATION)
                    o.destroy(source=self, cause='Object being destroyed by ObjectRoutingBehaviorActionDestroyObjects')

            result = yield from self.animation_success(timeline, obj, target, callback=_callback)
            if not result:
                return result
        return True
