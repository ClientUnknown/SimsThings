from protocolbuffers import Dialog_pb2, DistributorOps_pb2from distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class FundsTransferDialog:
    PLAYER_HOUSEHOLD_TITLE = TunableLocalizedString(description='\n        This is the text that will show for the players home lot. Typically,\n        the lot name would show but the home lot should say something along the\n        lines of "Player Household" to avoid confusion.\n        ')

    @classmethod
    def show_dialog(cls, first_time_buyer=False):
        business_managers = services.business_service().get_business_managers_for_household()
        if not business_managers:
            logger.error('Trying to show the balance transfer dialog but failed to find any owned businesses for the active household.')
            return False
        active_household = services.active_household()
        current_zone_id = services.current_zone_id()
        current_business_manager = business_managers.get(current_zone_id, None)
        balance_transfer_msg = Dialog_pb2.BalanceTransferDialog()
        balance_transfer_msg.transfer_amount = min(active_household.funds.money, current_business_manager.tuning_data.initial_funds_transfer_amount) if first_time_buyer else 0
        if first_time_buyer or current_business_manager is None:
            cls._add_household(balance_transfer_msg, active_household)
            cls._try_add_current_business_lot(balance_transfer_msg, business_managers, current_zone_id)
        else:
            cls._try_add_current_business_lot(balance_transfer_msg, business_managers, current_zone_id)
            cls._add_household(balance_transfer_msg, active_household)
        for (zone_id, business_manager) in business_managers.items():
            if zone_id == current_zone_id:
                pass
            else:
                zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
                if zone_data is None:
                    logger.error("Business tracker thinks a zone exists that doesn't. Zone id:{}", zone_id)
                else:
                    with ProtocolBufferRollback(balance_transfer_msg.lot_data) as lot_data:
                        lot_data.lot_name = LocalizationHelperTuning.get_raw_text(zone_data.name)
                        lot_data.zone_id = zone_id
                        lot_data.balance = business_manager.funds.money
        transfer_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.RETAIL_BALANCE_TRANSFER_DIALOG, balance_transfer_msg)
        Distributor.instance().add_op_with_no_owner(transfer_op)

    @classmethod
    def _add_household(cls, balance_transfer_msg, active_household):
        home_lot_data = balance_transfer_msg.lot_data.add()
        home_lot_data.lot_name = cls.PLAYER_HOUSEHOLD_TITLE
        home_lot_data.zone_id = active_household.home_zone_id
        home_lot_data.balance = active_household.funds.money

    @classmethod
    def _try_add_current_business_lot(cls, balance_transfer_msg, business_managers, current_zone_id):
        business_manager = business_managers.get(current_zone_id, None)
        if business_manager is not None:
            business_data = balance_transfer_msg.lot_data.add()
            business_data.lot_name = business_manager.tuning_data.current_business_lot_transfer_dialog_entry
            business_data.zone_id = current_zone_id
            business_data.balance = business_manager.funds.money
