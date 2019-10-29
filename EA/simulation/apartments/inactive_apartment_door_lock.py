from objects.components.portal_lock_data import LockData, LockResultfrom objects.components.portal_locking_enums import LockPriority, LockSide, LockType
class InactiveApartmentDoorLockData(LockData):

    def __init__(self, door):
        super().__init__(lock_type=LockType.INACTIVE_APARTMENT_DOOR, lock_priority=LockPriority.SYSTEM_LOCK, lock_sides=LockSide.LOCK_FRONT, should_persist=True)
        self._door = door

    def test_lock(self, sim):
        if self._door.get_household_owner_id() == sim.household_id:
            return LockResult(False, self.lock_type, self.lock_priority, self.lock_sides)
        return LockResult(True, self.lock_type, self.lock_priority, self.lock_sides)
