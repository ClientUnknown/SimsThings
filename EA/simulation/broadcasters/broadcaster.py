import weakreffrom broadcasters.broadcaster_effect import TunableBroadcasterEffectVariantfrom broadcasters.broadcaster_utils import BroadcasterClockTypefrom event_testing.resolver import DoubleObjectResolver, SingleSimResolverfrom event_testing.tests import TunableTestSetfrom fire.fire_tuning import FireTuningfrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import Anywherefrom routing.route_events.route_event import RouteEventfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableList, TunableVariant, TunableTuple, Tunable, TunableSimMinute, OptionalTunable, AutoFactoryInit, HasTunableSingletonFactory, TunableSet, TunableEnumEntryfrom socials.clustering import ObjectClusterRequestfrom tag import Tagfrom uid import unique_idimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Broadcaster', default_owner='epanero')
class _BroadcasterLosComponent:

    def __init__(self, broadcaster):
        self.broadcaster = broadcaster

    @property
    def constraint(self):
        return self.broadcaster.get_constraint()

    @property
    def default_position(self):
        broadcasting_object = self.broadcaster.broadcasting_object
        return broadcasting_object.intended_position + broadcasting_object.intended_forward*0.1

@unique_id('broadcaster_id')
class Broadcaster(HasTunableReference, RouteEventProviderMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.BROADCASTER)):

    class _BroadcasterObjectFilter(HasTunableSingletonFactory, AutoFactoryInit):

        def is_affecting_objects(self):
            raise NotImplementedError

        def can_affect_object(self, obj):
            raise NotImplementedError

    class _BroadcasterObjectFilterNone(HasTunableSingletonFactory):

        def __str__(self):
            return 'Nothing'

        def is_affecting_objects(self):
            return (False, None)

        def can_affect_object(self, obj):
            return False

    class _BroadcasterObjectFilterFlammable(HasTunableSingletonFactory):

        def __str__(self):
            return 'Flammable Objects'

        def is_affecting_objects(self):
            return (True, {FireTuning.FLAMMABLE_TAG})

        def can_affect_object(self, obj):
            target_object_tags = obj.get_tags()
            if FireTuning.FLAMMABLE_TAG in target_object_tags:
                return True
            return False

    class _BroadcasterObjectFilterTags(HasTunableSingletonFactory, AutoFactoryInit):

        def __str__(self):
            return '{}'.format(', '.join(str(tag) for tag in self.tags))

        FACTORY_TUNABLES = {'tags': TunableSet(description='\n                An object with any tag in this set can be affected by the\n                broadcaster.\n                ', tunable=TunableEnumEntry(description='\n                    A tag.\n                    ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True))}

        def is_affecting_objects(self):
            return (True, self.tags)

        def can_affect_object(self, obj):
            target_object_tags = obj.get_tags()
            if self.tags & target_object_tags:
                return True
            return False

    FREQUENCY_ENTER = 0
    FREQUENCY_PULSE = 1
    INSTANCE_TUNABLES = {'clock_type': TunableEnumEntry(description="\n            Denotes whether broadcasters of this type are managed in real time\n            or game time.\n            \n            Most broadcasters should be managed in Game Time because they will\n            update with the speed of the game, including performance dips, and\n            speed changes. However, Real Time broadcasters are more performant\n            because they will only update based on the frequency of real time.\n            You should use real time updates if the broadcaster is enabled for\n            the lifetime of the object, there are a lot of that type, or timing\n            doesn't matter as much.\n            \n            One Shot Interaction broadcasters should always be Game Time.\n            Environment Score broadcasters should be in Real Time. Consult an\n            engineer if you have questions.\n            ", tunable_type=BroadcasterClockType, default=BroadcasterClockType.GAME_TIME), 'constraints': TunableList(description='\n            A list of constraints that define the area of influence of this\n            broadcaster. It is required that at least one constraint be defined.\n            ', tunable=TunableGeometricConstraintVariant(constraint_locked_args={'multi_surface': True}, circle_locked_args={'require_los': False}, disabled_constraints={'spawn_points', 'current_position'}), minlength=1), 'effects': TunableList(description='\n            A list of effects that are applied to Sims and objects affected by\n            this broadcaster.\n            ', tunable=TunableBroadcasterEffectVariant()), 'route_events': TunableList(description="\n            Specify any route events that are triggered when the Sim follows a\n            path that has points within this broadcaster's constraints.\n            ", tunable=RouteEvent.TunableReference(description='\n                A Route Event that is to be played when a Sim plans a route\n                through this broadcaster.\n                ', pack_safe=True)), 'frequency': TunableVariant(description='\n            Define in what instances and how often this broadcaster affects Sims\n            and objects in its area of influence.\n            ', on_enter=TunableTuple(description='\n                Sims and objects are affected by this broadcaster when they\n                enter in its area of influence, or when the broadcaster is\n                created.\n                ', locked_args={'frequency_type': FREQUENCY_ENTER}, allow_multiple=Tunable(description="\n                    If checked, then Sims may react multiple times if they re-\n                    enter the broadcaster's area of influence. If unchecked,\n                    then Sims will only react to the broadcaster once.\n                    ", tunable_type=bool, default=False)), on_pulse=TunableTuple(description='\n                Sims and objects are constantly affected by this broadcaster\n                while they are in its area of influence.\n                ', locked_args={'frequency_type': FREQUENCY_PULSE}, cooldown_time=TunableSimMinute(description='\n                    The time interval between broadcaster pulses. Sims would not\n                    react to the broadcaster for at least this amount of time\n                    while in its area of influence.\n                    ', default=8)), default='on_pulse'), 'clustering': OptionalTunable(description='\n            If set, then similar broadcasters, i.e. broadcasters of the same\n            instance, will be clustered together if their broadcasting objects\n            are close by. This improves performance and avoids having Sims react\n            multiple times to similar broadcasters. When broadcasters are\n            clustered together, there is no guarantee as to what object will be\n            used for testing purposes.\n            \n            e.g. Stinky food reactions are clustered together. A test on the\n            broadcaster should not, for example, differentiate between a stinky\n            lobster and a stinky steak, because the broadcasting object is\n            arbitrary and undefined.\n            \n            e.g. Jealousy reactions are not clustered together. A test on the\n            broadcaster considers the relationship between two Sims. Therefore,\n            it would be unwise to consider an arbitrary Sim if two jealousy\n            broadcasters are close to each other.\n            ', tunable=ObjectClusterRequest.TunableFactory(description='\n                Specify how clusters for this particular broadcaster are formed.\n                ', locked_args={'minimum_size': 1}), enabled_by_default=True), 'allow_objects': TunableVariant(description='\n            If enabled, then in addition to all instantiated Sims, some objects\n            will be affected by this broadcaster. Some tuned effects might still\n            only apply to Sims (e.g. affordance pushing).\n            \n            Setting this tuning field has serious performance repercussions. Its\n            indiscriminate use could undermine our ability to meet Minspec\n            goals. Please use this sparingly.\n            ', disallow=_BroadcasterObjectFilterNone.TunableFactory(), from_tags=_BroadcasterObjectFilterTags.TunableFactory(), from_flammable=_BroadcasterObjectFilterFlammable.TunableFactory(), default='disallow'), 'allow_sims': Tunable(description='\n            If checked then this broadcaster will consider Sims. This is on by\n            default. \n            \n            If neither allow_objects or allow_sims is checked that will result\n            in a tuning error.\n            ', tunable_type=bool, default=True), 'allow_sim_test': OptionalTunable(description='\n            If enabled, allows for a top level test set to determine which\n            sims can be affected by the broadcaster at all.\n            ', tunable=TunableTestSet()), 'immediate': Tunable(description='\n            If checked, this broadcaster will trigger a broadcaster update when\n            added to the service. This adds a performance cost so please use\n            this sparingly. This can be used for one-shot interactions that\n            generate broadcasters because the update interval might be excluded\n            in the interaction duration.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls):
        (allow_objects, _) = cls.allow_objects.is_affecting_objects()
        if cls.allow_sims or not allow_objects:
            logger.error('Broadcaster {} is tuned to not allow any objects as targets.', cls)

    @classmethod
    def register_static_callbacks(cls, *args, **kwargs):
        for broadcaster_effect in cls.effects:
            broadcaster_effect.register_static_callbacks(*args, **kwargs)

    @classmethod
    def get_broadcaster_service(cls):
        current_zone = services.current_zone()
        if current_zone is not None:
            if cls.clock_type == BroadcasterClockType.GAME_TIME:
                return current_zone.broadcaster_service
            if cls.clock_type == BroadcasterClockType.REAL_TIME:
                return current_zone.broadcaster_real_time_service
            raise NotImplementedError

    def __init__(self, *args, broadcasting_object, interaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._broadcasting_object_ref = weakref.ref(broadcasting_object, self._on_broadcasting_object_deleted)
        self._interaction = interaction
        self._constraint = None
        self._affected_objects = weakref.WeakKeyDictionary()
        self._current_objects = weakref.WeakSet()
        self._linked_broadcasters = weakref.WeakSet()
        broadcasting_object.register_on_location_changed(self._on_broadcasting_object_moved)
        self._quadtree = None
        self._cluster_request = None

    @property
    def broadcasting_object(self):
        if self._broadcasting_object_ref is not None:
            return self._broadcasting_object_ref()

    @property
    def interaction(self):
        return self._interaction

    @property
    def quadtree(self):
        return self._quadtree

    @property
    def cluster_request(self):
        return self._cluster_request

    def _on_broadcasting_object_deleted(self, _):
        broadcaster_service = self.get_broadcaster_service()
        if broadcaster_service is not None:
            broadcaster_service.remove_broadcaster(self)

    def _on_broadcasting_object_moved(self, *_, **__):
        self.regenerate_constraint()
        broadcaster_service = self.get_broadcaster_service()
        if broadcaster_service is not None:
            broadcaster_service.update_cluster_request(self)

    def on_processed(self):
        for affected_object in self._affected_objects:
            if affected_object not in self._current_objects:
                self.remove_broadcaster_effect(affected_object)
        self._current_objects.clear()

    def on_removed(self):
        for affected_object in self._affected_objects:
            self.remove_broadcaster_effect(affected_object)
        broadcasting_object = self.broadcasting_object
        if broadcasting_object is not None:
            for broadcaster_effect in self.effects:
                if broadcaster_effect.apply_when_removed:
                    broadcaster_effect.apply_broadcaster_loot(self)
            broadcasting_object.unregister_on_location_changed(self._on_broadcasting_object_moved)

    def on_added_to_quadtree_and_cluster_request(self, quadtree, cluster_request):
        self._quadtree = quadtree
        self._cluster_request = cluster_request

    def can_affect(self, obj):
        if obj.is_sim:
            if not self.allow_sims:
                return False
        elif not self.allow_objects.can_affect_object(obj):
            return False
        broadcasting_object = self.broadcasting_object
        if broadcasting_object is None:
            return False
        if obj is broadcasting_object:
            return False
        elif any(obj is linked_broadcaster.broadcasting_object for linked_broadcaster in self._linked_broadcasters):
            return False
        return True

    def on_event_executed(self, route_event, sim):
        super().on_event_executed(route_event, sim)
        if self.can_affect(sim):
            self.apply_broadcaster_effect(sim)

    def is_route_event_valid(self, route_event, time, sim, path):
        if not self.can_affect(sim):
            return False
        constraint = self.get_constraint()
        if constraint.valid and constraint.geometry is None:
            return False
        else:
            (transform, routing_surface) = path.get_location_data_at_time(time)
            if not (constraint.geometry.test_transform(transform) and constraint.is_routing_surface_valid(routing_surface)):
                return False
        return True

    def apply_broadcaster_effect(self, affected_object):
        if affected_object.is_sim and self.allow_sim_test and not self.allow_sim_test.run_tests(SingleSimResolver(affected_object.sim_info)):
            return
        self._current_objects.add(affected_object)
        if self._should_apply_broadcaster_effect(affected_object):
            self._affected_objects[affected_object] = (services.time_service().sim_now, True)
            for broadcaster_effect in self.effects:
                broadcaster_effect.apply_broadcaster_effect(self, affected_object)
        for linked_broadcaster in self._linked_broadcasters:
            linked_broadcaster._apply_linked_broadcaster_effect(affected_object, self._affected_objects[affected_object])

    def _apply_linked_broadcaster_effect(self, affected_object, data):
        self._apply_linked_broadcaster_data(affected_object, data)
        for broadcaster_effect in self.effects:
            if broadcaster_effect.apply_when_linked:
                broadcaster_effect.apply_broadcaster_effect(self, affected_object)

    def _apply_linked_broadcaster_data(self, affected_object, data):
        if affected_object in self._affected_objects:
            was_in_area = self._affected_objects[affected_object][1]
            is_in_area = data[1]
            if was_in_area and not is_in_area:
                self.remove_broadcaster_effect(affected_object)
        self._affected_objects[affected_object] = data

    def remove_broadcaster_effect(self, affected_object, is_linked=False):
        affected_object_data = self._affected_objects.get(affected_object)
        if affected_object_data is None:
            return
        if not affected_object_data[1]:
            return
        self._affected_objects[affected_object] = (affected_object_data[0], False)
        self._current_objects.discard(affected_object)
        for broadcaster_effect in self.effects:
            if not broadcaster_effect.apply_when_linked:
                if not is_linked:
                    broadcaster_effect.remove_broadcaster_effect(self, affected_object)
            broadcaster_effect.remove_broadcaster_effect(self, affected_object)
        if not is_linked:
            for linked_broadcaster in self._linked_broadcasters:
                linked_broadcaster.remove_broadcaster_effect(affected_object, is_linked=True)

    def _should_apply_broadcaster_effect(self, affected_object):
        if self.frequency.frequency_type == self.FREQUENCY_ENTER:
            if affected_object not in self._affected_objects:
                return True
            elif self.frequency.allow_multiple and not self._affected_objects[affected_object][1]:
                return True
            return False
        if self.frequency.frequency_type == self.FREQUENCY_PULSE:
            last_reaction = self._affected_objects.get(affected_object, None)
            if last_reaction is None:
                return True
            else:
                time_since_last_reaction = services.time_service().sim_now - last_reaction[0]
                if time_since_last_reaction.in_minutes() > self.frequency.cooldown_time:
                    return True
                else:
                    return False
            return False

    def clear_linked_broadcasters(self):
        self._linked_broadcasters.clear()

    def set_linked_broadcasters(self, broadcasters):
        self.clear_linked_broadcasters()
        self._linked_broadcasters.update(broadcasters)
        for linked_broadcaster in self._linked_broadcasters:
            linked_broadcaster.clear_linked_broadcasters()
            for (obj, data) in linked_broadcaster._affected_objects.items():
                if obj not in self._affected_objects:
                    self._affected_objects[obj] = data
        for linked_broadcaster in self._linked_broadcasters:
            for (obj, data) in self._affected_objects.items():
                linked_broadcaster._apply_linked_broadcaster_data(obj, data)

    def get_linked_broadcasters_gen(self):
        yield from self._linked_broadcasters

    def regenerate_constraint(self, *_, **__):
        self._constraint = None

    def get_constraint(self):
        if not (self._constraint is None or self._constraint.valid):
            self._constraint = Anywhere()
            for tuned_constraint in self.constraints:
                self._constraint = self._constraint.intersect(tuned_constraint.create_constraint(None, target=self.broadcasting_object, target_position=self.broadcasting_object.position))
        return self._constraint

    def get_resolver(self, affected_object):
        return DoubleObjectResolver(affected_object, self.broadcasting_object)

    def get_clustering(self):
        broadcasting_object = self.broadcasting_object
        if broadcasting_object is None:
            return
        if broadcasting_object.is_sim:
            return
        if broadcasting_object.is_in_inventory():
            return
        if broadcasting_object.routing_surface is None:
            return
        return self.clustering

    def should_cluster(self):
        return self.get_clustering() is not None

    def get_affected_object_count(self):
        return sum(1 for data in self._affected_objects.values() if data[1])

    @property
    def id(self):
        return self.broadcaster_id

    @property
    def lineofsight_component(self):
        return _BroadcasterLosComponent(self)

    @property
    def position(self):
        return self.broadcasting_object.position

    @property
    def routing_surface(self):
        return self.broadcasting_object.routing_surface

    @property
    def parts(self):
        return self.broadcasting_object.parts
