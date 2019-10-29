from _collections import defaultdictfrom collections import namedtupleimport weakreffrom interactions import ParticipantTypefrom interactions.utils.tunable_provided_affordances import TunableProvidedAffordancesfrom sims4.tuning.tunable import TunableReference, TunableSet, TunableMappingfrom sims4.utils import flexmethodfrom singletons import EMPTY_SETimport clockimport servicesimport sims4.loglogger = sims4.log.Logger('InUse')
class _CraftingLockoutData:

    def __init__(self):
        self._crafting_lockout_ref_counts = {}

    def add_lockout(self, crafting_type):
        if self._crafting_lockout_ref_counts.get(crafting_type):
            self._crafting_lockout_ref_counts[crafting_type] += 1
        else:
            self._crafting_lockout_ref_counts[crafting_type] = 1

    def get_ref_count(self, crafting_type, from_autonomy=False):
        ref_count = self._crafting_lockout_ref_counts.get(crafting_type)
        if ref_count:
            return ref_count
        return 0

class LockoutMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lockouts = weakref.WeakKeyDictionary()
        self._crafting_lockouts = weakref.WeakKeyDictionary()

    def add_lockout(self, obj, duration_in_sim_minutes):
        if self is obj:
            return
        interval = clock.interval_in_sim_minutes(duration_in_sim_minutes)
        end_time = services.time_service().sim_now + interval
        lockout = self._lockouts.get(obj, None)
        if lockout is None or lockout < end_time:
            self._lockouts[obj] = end_time
        crafting_lockout = self._crafting_lockouts.get(obj, None)
        if crafting_lockout is None:
            crafting_lockout_data = None
            for super_affordance in obj.super_affordances():
                if hasattr(super_affordance, 'crafting_type_requirement') and super_affordance.crafting_type_requirement is not None:
                    if crafting_lockout_data is None:
                        crafting_lockout_data = _CraftingLockoutData()
                    crafting_lockout_data.add_lockout(super_affordance.crafting_type_requirement)
            if crafting_lockout_data is not None:
                self._crafting_lockouts[obj] = crafting_lockout_data

    def clear_all_lockouts(self):
        self._lockouts = weakref.WeakKeyDictionary()
        self._crafting_lockouts = weakref.WeakKeyDictionary()

    def has_lockout(self, obj):
        lockout = self._lockouts.get(obj, None)
        if lockout:
            if lockout < services.time_service().sim_now:
                del self._lockouts[obj]
                if obj in self._crafting_lockouts:
                    del self._crafting_lockouts[obj]
                return False
            else:
                return True
        return False

    def get_lockouts_gen(self):
        current_time = services.time_service().sim_now
        for obj in self._lockouts:
            lockout = self._lockouts.get(obj, None)
            if lockout >= current_time:
                yield (obj, lockout - current_time)

    def get_autonomous_crafting_lockout_ref_count(self, crafting_type):
        ref_count = 0
        for crafting_lockout_data in self._crafting_lockouts.values():
            ref_count += crafting_lockout_data.get_ref_count(crafting_type)
        return ref_count

class InUseError(Exception):

    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return 'Attempt to reserve an unavailable object - ' + str(self.obj)

class NotInUseError(Exception):

    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return 'Attempt to release an object that is already free - ' + str(self.obj)
ProvidedAffordanceData = namedtuple('ProvidedAffordanceData', ('affordance', 'object_filter', 'allow_self'))
class AffordanceCacheMixin:
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._super_affordances_cache = None
        self._target_provided_affordances_cache = None
        self._actor_mixers_cache = None
        self._provided_mixers_cache = None

    def add_to_affordance_caches(self, super_affordances, target_provided_affordances):
        if super_affordances:
            if self._super_affordances_cache is None:
                self._super_affordances_cache = set()
            self._super_affordances_cache.update(super_affordances)
        if target_provided_affordances:
            if self._target_provided_affordances_cache is None:
                self._target_provided_affordances_cache = []
            for provided_affordance_data in target_provided_affordances:
                self._target_provided_affordances_cache.append(provided_affordance_data)

    def add_to_actor_mixer_cache(self, actor_mixers):
        if actor_mixers:
            if self._actor_mixers_cache is None:
                self._actor_mixers_cache = defaultdict(set)
            for (super_affordance, mixer_affordances) in actor_mixers.items():
                self._actor_mixers_cache[super_affordance].update(mixer_affordances)

    def add_to_provided_mixer_cache(self, provided_mixers):
        if provided_mixers:
            if self._provided_mixers_cache is None:
                self._provided_mixers_cache = defaultdict(set)
            for (super_affordance, mixer_affordances) in provided_mixers.items():
                self._provided_mixers_cache[super_affordance].update(mixer_affordances)

    def get_provided_super_affordances(self):
        return (None, None)

    def get_actor_and_provided_mixers_list(self):
        return (None, None)

    def get_sim_info_from_provider(self):
        raise NotImplementedError

    def update_affordance_caches(self):
        self._super_affordances_cache = None
        self._target_provided_affordances_cache = None
        self._actor_mixers_cache = None
        self._provided_mixers_cache = None
        (super_affordances, target_provided_affordances) = self.get_provided_super_affordances()
        self.add_to_affordance_caches(super_affordances, target_provided_affordances)
        (list_actor_mixers, list_provided_mixers) = self.get_actor_and_provided_mixers_list()
        if list_actor_mixers is not None:
            for actor_mixers in list_actor_mixers:
                self.add_to_actor_mixer_cache(actor_mixers)
        if list_provided_mixers is not None:
            for provided_mixers in list_provided_mixers:
                self.add_to_provided_mixer_cache(provided_mixers)

    def get_cached_super_affordances_gen(self):
        if self._super_affordances_cache is not None:
            yield from self._super_affordances_cache

    def get_cached_target_super_affordances_gen(self, context, target):
        sim_info = self.get_sim_info_from_provider()
        affordances_to_skip = set()
        if self._target_provided_affordances_cache is not None:
            for provided_affordance_data in self._target_provided_affordances_cache:
                if not provided_affordance_data.object_filter is None or provided_affordance_data.allow_self is None:
                    yield provided_affordance_data.affordance
                elif not target.is_sim or not target.sim_info is sim_info or not provided_affordance_data.allow_self:
                    pass
                elif provided_affordance_data.affordance in affordances_to_skip:
                    pass
                elif not provided_affordance_data.object_filter.is_object_valid(target):
                    pass
                else:
                    affordances_to_skip.add(provided_affordance_data.affordance)
                    yield provided_affordance_data.affordance

    def get_cached_target_provided_affordances_data_gen(self):
        if self._target_provided_affordances_cache is not None:
            yield from self._target_provided_affordances_cache

    def get_cached_actor_mixers(self, super_interaction):
        if self._actor_mixers_cache is not None:
            if super_interaction in self._actor_mixers_cache:
                return self._actor_mixers_cache[super_interaction]
            else:
                return EMPTY_SET
        return EMPTY_SET

    def get_cached_provided_mixers_gen(self, super_interaction):
        if self._provided_mixers_cache is not None:
            yield from self._provided_mixers_cache.get(super_interaction, ())

class SuperAffordanceProviderMixin:
    INSTANCE_TUNABLES = {'super_affordances': TunableSet(description='\n            Super affordances this adds to the object.\n            ', tunable=TunableReference(description='\n                A super affordance added to this object.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True))}
    FACTORY_TUNABLES = INSTANCE_TUNABLES

    @classmethod
    def get_provided_super_affordances_gen(cls):
        yield from cls.super_affordances

class TargetSuperAffordanceProviderMixin:
    INSTANCE_TUNABLES = {'target_super_affordances': TunableProvidedAffordances(description='\n            Super affordances this adds to the target.\n            ', locked_args={'target': ParticipantType.Object, 'carry_target': ParticipantType.Invalid, 'is_linked': False, 'unlink_if_running': False})}
    FACTORY_TUNABLES = INSTANCE_TUNABLES

class MixerProviderMixin:
    INSTANCE_TUNABLES = {'provided_mixers': TunableMapping(description='\n            Mixers this adds to an associated target object.\n            ', key_type=TunableReference(description='\n                The super affordance these mixers are associated with.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True), value_type=TunableSet(description='\n                Set of mixer affordances associated with the super affordance.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), category='asm', description='Linked Affordance', class_restrictions=('MixerInteraction',), pack_safe=True)))}

    @flexmethod
    def get_mixers(cls, inst, super_interaction):
        inst_or_cls = inst if inst is not None else cls
        mixers = inst_or_cls.provided_mixers.get(super_interaction, [])
        return mixers

class MixerActorMixin:
    INSTANCE_TUNABLES = {'actor_mixers': TunableMapping(description='\n            Mixers this adds to an associated actor object. (When targeting\n            something else.)\n            ', key_type=TunableReference(description='\n                The super affordance these mixers are associated with.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True), value_type=TunableSet(description='\n                Set of mixer affordances associated with the super affordance.\n                ', tunable=TunableReference(description='\n                    Linked mixer affordance.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), category='asm', class_restrictions=('MixerInteraction',), pack_safe=True)))}

    @flexmethod
    def get_actor_mixers(cls, inst, super_interaction):
        inst_or_cls = inst if inst is not None else cls
        mixers = inst_or_cls.actor_mixers.get(super_interaction, [])
        return mixers
