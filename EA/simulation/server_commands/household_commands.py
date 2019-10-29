from protocolbuffers import Consts_pb2, UI_pb2from distributor import shared_messagesfrom distributor.system import Distributorfrom objects import ALL_HIDDEN_REASONSfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_targetfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Commands')
class HouseholdCommandTuning:
    HOUSEHOLD_NEIGHBOR_MOVED_IN_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        The notification that is displayed when a household is moved in next\n        door.\n        Passed in token is the household name of the household that ends up\n        living in the house.\n        ')

@sims4.commands.Command('households.list')
def list_households(household_id:int=None, _connection=None):
    household_manager = services.household_manager()
    output = sims4.commands.Output(_connection)
    output('Household report:')
    if household_id is not None:
        households = (household_manager.get(household_id),)
    else:
        households = household_manager.get_all()
    for household in households:
        output('{}, {} Sims'.format(str(household), len(household)))
        for sim_info in household.sim_info_gen():
            if sim_info.is_instanced(allow_hidden_flags=0):
                output(' Instanced: {}'.format(sim_info))
            elif sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                output(' Hidden: {}'.format(sim_info))
            else:
                output(' Off lot: {}'.format(sim_info))

@sims4.commands.Command('households.modify_funds', command_type=sims4.commands.CommandType.Automation)
def modify_household_funds(amount:int, household_id:int=0, reason=None, _connection=None):
    if reason is None:
        reason = Consts_pb2.TELEMETRY_MONEY_CHEAT
    if household_id == 0:
        tgt_client = services.client_manager().get(_connection)
        if tgt_client is not None:
            household = tgt_client.household
    else:
        household = services.household_manager().get(household_id)
    if household is not None:
        if amount > 0:
            household.funds.add(amount, reason)
        else:
            household.funds.try_remove(-amount, reason)
    else:
        sims4.commands.output('Invalid Household id: {}'.format(household_id), _connection)

@sims4.commands.Command('households.get_value', command_type=sims4.commands.CommandType.DebugOnly)
def get_value(household_id:int, billable:bool=False, _connection=None):
    household = services.household_manager().get(household_id)
    if household is not None:
        value = household.household_net_worth(billable=billable)
        sims4.commands.output('Simoleon value of household {} is {}.'.format(household, value), _connection)
    else:
        sims4.commands.output('Invalid Household id: {}'.format(household_id), _connection)

@sims4.commands.Command('households.get_household_display_info', command_type=sims4.commands.CommandType.Automation)
def get_household_display_info(lot_id:int, _connection=None):
    persistence_service = services.get_persistence_service()
    household_display_info = UI_pb2.HouseholdDisplayInfo()
    household_id = persistence_service.get_household_id_from_lot_id(lot_id)
    if household_id is None:
        household_id = 0
    household = services.household_manager().get(household_id)
    if household is None:
        household_id = 0
    else:
        household_display_info.at_home_sim_ids.extend(household.get_sims_at_home_not_instanced_not_busy())
    household_display_info.household_id = household_id
    household_display_info.lot_id = lot_id
    op = shared_messages.create_message_op(household_display_info, Consts_pb2.MSG_UI_HOUSEHOLD_DISPLAY_INFO)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('households.merge_with_active', command_type=sims4.commands.CommandType.Live)
def merge_with_active(household_id:int, _connection=None):
    client = services.client_manager().get(_connection)
    household = client.household
    household.merge(household_id)

@sims4.commands.Command('households.merge_with_neighbor', command_type=sims4.commands.CommandType.Live)
def merge_with_neighbor(zone_id:int, merge:bool, household_id:int, _connection=None):
    venue_type = services.venue_service().get_venue_tuning(zone_id)
    if venue_type is None:
        return
    if not venue_type.is_residential:
        return
    old_household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
    household_manager = services.household_manager()
    if old_household_id is not None:
        old_household = household_manager.get(old_household_id)
    else:
        old_household = None
    if merge:
        if old_household is None:
            logger.error('Trying to merge None old household with a new one of household id {}.', household_id, owner='jjacobson')
            return
        old_household.merge(household_id, should_spawn=zone_id == services.current_zone_id(), selectable=False)
        notification_household = old_household
    else:
        if old_household is not None:
            old_household.clear_household_lot_ownership()
        new_household = household_manager.load_household(household_id)
        new_household.move_into_zone(zone_id)
        notification_household = new_household
    zone_name = ''
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is not None:
            zone_name = zone_data.name
    dialog = HouseholdCommandTuning.HOUSEHOLD_NEIGHBOR_MOVED_IN_NOTIFICATION(None)
    dialog.show_dialog(additional_tokens=(notification_household.name, zone_name))

@sims4.commands.Command('households.fill_visible_commodities_world', command_type=sims4.commands.CommandType.Cheat)
def set_visible_commodities_to_best_value_for_world(opt_object:OptionalTargetParam=None, _connection=True):
    for sim_info in services.sim_info_manager().objects:
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=True)

@sims4.commands.Command('households.fill_visible_commodities_household', command_type=sims4.commands.CommandType.Cheat)
def set_visible_commodities_to_best_value_for_household(opt_object:OptionalTargetParam=None, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim
    household = active_sim_info.household
    for sim_info in household.sim_info_gen():
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=True)

def _set_motive_decay(sim_infos, enable=True):
    for sim_info in sim_infos:
        for commodity in sim_info.commodity_tracker.get_all_commodities():
            if commodity.is_visible:
                current_decay_modifier = commodity.get_decay_rate_modifier()
                if enable:
                    if current_decay_modifier == 0:
                        commodity.remove_decay_rate_modifier(0)
                        commodity.send_commodity_progress_msg()
                        if not current_decay_modifier == 0:
                            commodity.add_decay_rate_modifier(0)
                            commodity.send_commodity_progress_msg()
                elif not current_decay_modifier == 0:
                    commodity.add_decay_rate_modifier(0)
                    commodity.send_commodity_progress_msg()

@sims4.commands.Command('households.enable_household_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def enable_household_motive_decay(opt_object:OptionalTargetParam=None, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim
    household = active_sim_info.household
    _set_motive_decay(household.sim_info_gen(), True)

@sims4.commands.Command('households.disable_household_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def disable_household_motive_decay(opt_object:OptionalTargetParam=None, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim
    household = active_sim_info.household
    _set_motive_decay(household.sim_info_gen(), False)

@sims4.commands.Command('households.enable_world_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def enable_world_motive_decay(opt_object:OptionalTargetParam=None, _connection=True):
    _set_motive_decay(services.sim_info_manager().objects, True)

@sims4.commands.Command('households.disable_world_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def disable_world_motive_decay(opt_object:OptionalTargetParam=None, _connection=True):
    _set_motive_decay(services.sim_info_manager().objects, False)

@sims4.commands.Command('households.collection_view_update', command_type=sims4.commands.CommandType.Live)
def collection_view_update(collection_id:int=0, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim_info
    active_sim_info.household.collection_tracker.mark_as_viewed(collection_id)
