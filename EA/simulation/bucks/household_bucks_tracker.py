from bucks.bucks_tracker import BucksTrackerBasefrom distributor.ops import SetBuckFundsfrom distributor.system import Distributorfrom households.household_tracker import HouseholdTrackerimport services
class HouseholdBucksTracker(BucksTrackerBase, HouseholdTracker):

    def on_all_households_and_sim_infos_loaded(self):
        if not self._owner.id == services.active_household_id():
            return
        super().on_all_households_and_sim_infos_loaded()

    def on_zone_load(self):
        if not self._owner.id == services.active_household_id():
            return
        super().on_zone_load()

    def _owner_sim_info_gen(self):
        yield from self._owner

    def household_lod_cleanup(self):
        self.clear_bucks_tracker()

    def distribute_bucks(self, bucks_type):
        op = SetBuckFunds(bucks_type, self._bucks[bucks_type])
        Distributor.instance().add_op_with_no_owner(op)
