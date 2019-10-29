from bucks.bucks_tracker import BucksTrackerBasefrom clubs.club_telemetry import club_telemetry_writer, TELEMETRY_HOOK_CLUB_PERKPURCHASED, TELEMETRY_FIELD_CLUB_ID, TELEMETRY_FIELD_CLUB_PERKID, TELEMETRY_FIELD_CLUB_PERKCOST, TELEMETRY_FIELD_CLUB_BUCKSAMOUNTfrom clubs.club_tuning import ClubTunablesfrom distributor.ops import SetBuckFundsfrom distributor.system import Distributorfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableMapping, Tunable, TunableTuple, TunableReferencefrom sims4.tuning.tunable_base import ExportModesimport servicesimport sims4.resourcesimport telemetry_helper
class ClubBucksTracker(BucksTrackerBase):
    EP02_CLUB_BUCKS = 24577
    BUCKS_TRACKER_REWARDS_CATEGORIES = TunableMapping(description='\n        Ordered list of Club Bucks Reward categories that will appear in the \n        Club Bucks rewards UI along with the perks that belong in the category.\n        ', key_type=Tunable(description='\n            An integer value used to set the specific order of the categories\n            in the UI. the lower numbers are displayed first in the UI.\n            ', tunable_type=int, default=0), value_type=TunableTuple(description='\n            Tuning structure holding all of the localized string data for the \n            tuned Perk Category.        \n            ', category_name=TunableLocalizedString(description='\n                This is the localized name of the category that will show up \n                in the club bucks UI.\n                '), category_tooltip=TunableLocalizedString(description='\n                This is the description that will show up when the user hovers\n                over the catgory name for a while.\n                '), rewards=TunableMapping(description='\n                An ordered list of the rewards that will appear in this\n                category.\n                ', key_type=Tunable(description='\n                    An integer value used to order the appearance of the rewards\n                    inside of the category. The smaller numbers are sorted to\n                    the front of the list.\n                    ', tunable_type=int, default=0), value_type=TunableReference(description='\n                    The Buck Perk (reward) to display in the category panel of\n                    the UI.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True), tuple_name='RewardCategoryMapping'), export_class_name='RewardCategoryInfoTuple'), tuple_name='CategoryMapping', export_modes=ExportModes.ClientBinary)

    def try_modify_bucks(self, bucks_type, amount, distribute=True, reason=None):
        result = super().try_modify_bucks(bucks_type, amount, distribute=distribute)
        if amount > 0:
            self._owner.handle_club_bucks_earned(bucks_type, amount, reason=reason)
        return result

    def distribute_bucks(self, bucks_type):
        op = SetBuckFunds(bucks_type, self._bucks[bucks_type], club_id=self._owner.id)
        Distributor.instance().add_op_with_no_owner(op)

    def _award_rewards(self, perk, sim_info=None):
        if not perk.rewards:
            return
        sim_infos = (sim_info,) if sim_info is not None else self._owner.members
        for sim_info in sim_infos:
            for reward in perk.rewards:
                reward().open_reward(sim_info)

    def _owner_sim_info_gen(self):
        yield from self._owner.members

    def pay_for_and_unlock_perk(self, perk):
        result = super().pay_for_and_unlock_perk(perk)
        if result:
            with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_PERKPURCHASED) as hook:
                hook.write_int(TELEMETRY_FIELD_CLUB_ID, self._owner.id)
                hook.write_guid(TELEMETRY_FIELD_CLUB_PERKID, perk.guid64)
                hook.write_int(TELEMETRY_FIELD_CLUB_PERKCOST, perk.unlock_cost)
                hook.write_int(TELEMETRY_FIELD_CLUB_BUCKSAMOUNT, self._bucks[ClubTunables.CLUB_BUCKS_TYPE])
        club_service = services.get_club_service()
        if club_service is not None:
            club_service.distribute_club_update((self._owner,))
        return result

    def load_data(self, owner_proto):
        super().load_data(owner_proto)
        if ClubBucksTracker.EP02_CLUB_BUCKS in self._bucks:
            old_bucks_amount = self._bucks.pop(ClubBucksTracker.EP02_CLUB_BUCKS)
            self.try_modify_bucks(ClubTunables.CLUB_BUCKS_TYPE, old_bucks_amount, distribute=False)
