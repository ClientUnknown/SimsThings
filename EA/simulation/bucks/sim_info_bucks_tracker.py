from bucks.bucks_enums import BucksTypefrom bucks.bucks_tracker import BucksTrackerBasefrom distributor.ops import SetBuckFundsfrom distributor.system import Distributorfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableEnumEntry, TunableMapping, Tunable, TunableTuple, TunableReferencefrom sims4.tuning.tunable_base import ExportModesimport servicesimport sims4
class SimInfoBucksTracker(BucksTrackerBase):
    BUCK_TYPE_TO_CATEGORIES_MAPPING = TunableMapping(description='\n        A mapping of buck type to the categorized buck perks. \n        ', key_type=TunableEnumEntry(description='\n            A type of bucks that this kind of tracker holds.\n            ', tunable_type=BucksType, default=BucksType.INVALID, pack_safe=True), value_type=TunableMapping(description='\n            Ordered list of buck perks categories that will appear in the \n            rewards UI along with the perks that belong in the category.\n            ', key_type=Tunable(description='\n                An integer value used to set the specific order of the categories\n                in the UI. the lower numbers are displayed first in the UI.\n                ', tunable_type=int, default=0), value_type=TunableTuple(description='\n                Tuning structure holding all of the localized string data for the \n                tuned Perk Category.        \n                ', category_name=TunableLocalizedString(description='\n                    This is the localized name of the category that will show up \n                    in the bucks UI.\n                    '), category_tooltip=TunableLocalizedString(description='\n                    This is the description that will show up when the user hovers\n                    over the catgory name for a while.\n                    '), rewards=TunableMapping(description='\n                    An ordered list of the rewards that will appear in this\n                    category.\n                    ', key_type=Tunable(description='\n                        An integer value used to order the appearance of the rewards\n                        inside of the category. The smaller numbers are sorted to\n                        the front of the list.\n                        ', tunable_type=int, default=0), value_type=TunableReference(description='\n                        The Buck Perk (reward) to display in the category panel of\n                        the UI.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True, allow_none=True), allow_none=True, tuple_name='SimRewardCategoryMapping'), export_class_name='SimRewardCategoryInfoTuple'), tuple_name='SimCategoryMapping'), tuple_name='SimBuckToCategoryMapping', export_modes=ExportModes.ClientBinary)

    def distribute_bucks(self, bucks_type):
        op = SetBuckFunds(bucks_type, self._bucks[bucks_type], sim_id=self._owner.id)
        Distributor.instance().add_op_with_no_owner(op)

    def unlock_perk(self, perk, unlocked_by=None):
        super().unlock_perk(perk, unlocked_by=unlocked_by)
        self._owner.trait_tracker.update_day_night_tracking_state(force_update=True)

    def lock_perk(self, perk, refund_cost=False, distribute=True):
        super().lock_perk(perk, refund_cost=refund_cost, distribute=distribute)
        self._owner.trait_tracker.update_day_night_tracking_state(force_update=True, full_reset=True)

    def validate_perks(self, bucks_type, current_rank):
        bucks_perks_by_rank = SimInfoBucksTracker.BUCK_TYPE_TO_CATEGORIES_MAPPING.get(bucks_type, None)
        if bucks_perks_by_rank is None:
            return
        for (required_rank, tuning) in bucks_perks_by_rank.items():
            if required_rank > current_rank:
                for perk in tuning.rewards.values():
                    if perk is None:
                        pass
                    elif self.is_perk_unlocked(perk):
                        self.lock_perk(perk, refund_cost=True)
