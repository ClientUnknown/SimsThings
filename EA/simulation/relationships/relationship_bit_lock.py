from date_and_time import DATE_AND_TIME_ZERO, DateAndTimefrom relationships.relationship_bit import RelationshipBitTypefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableEnumEntry, TunableSimMinute, TunablePercentimport clockimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Relationship', default_owner='jjacobson')
class RelationshipBitLock(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_LOCK)):
    INSTANCE_TUNABLES = {'group_id': TunableEnumEntry(description='\n            The group that this lock applies to.  No two locks can belong to\n            the same group.\n            ', tunable_type=RelationshipBitType, default=RelationshipBitType.Invalid, invalid_enums=(RelationshipBitType.Invalid, RelationshipBitType.NoGroup)), 'timeout': TunableSimMinute(description='\n            The amount of time in Sim minutes that this Relationship Bit Lock\n            will be locked before potentially allowing a Relationship Bit\n            Change.\n            ', default=360, minimum=1), 'relock_percentage': TunablePercent(description='\n            The percent chance that we will just relock this Relationship Bit\n            Lock and prevent a change when one attempts to occur.  If we are\n            relocked then we will not change the bit.\n            ', default=0)}
    relationship_bit_cache = None

    @classmethod
    def get_lock_type_for_group_id(cls, group_id):
        return cls.relationship_bit_cache.get(group_id, None)

    def __init__(self):
        self._locked_time = DATE_AND_TIME_ZERO

    @property
    def end_time(self):
        return self._locked_time + clock.interval_in_sim_minutes(self.timeout)

    def lock(self):
        self._locked_time = services.time_service().sim_now

    def unlock(self):
        self._locked_time = DATE_AND_TIME_ZERO

    def try_and_aquire_lock_permission(self):
        if self._locked_time == DATE_AND_TIME_ZERO:
            return True
        now = services.time_service().sim_now
        if now < self.end_time:
            return False
        elif sims4.random.random_chance(self.relock_percentage*100):
            self.lock()
            return False
        return True

    def save(self, msg):
        msg.relationship_bit_lock_type = self.guid64
        msg.locked_time = self._locked_time.absolute_ticks()

    def load(self, msg):
        self._locked_time = DateAndTime(msg.locked_time)

def build_relationship_bit_lock_cache(manager):
    RelationshipBitLock.relationship_bit_cache = {}
    for relationship_bit_lock in services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_LOCK).types.values():
        if relationship_bit_lock.group_id in RelationshipBitLock.relationship_bit_cache:
            logger.error('Two Relationship Bit Locks with the Same Group Id Found: {} and {}', relationship_bit_lock, RelationshipBitLock.relationship_bit_cache[relationship_bit_lock.group_id])
        RelationshipBitLock.relationship_bit_cache[relationship_bit_lock.group_id] = relationship_bit_lock
services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_LOCK).add_on_load_complete(build_relationship_bit_lock_cache)