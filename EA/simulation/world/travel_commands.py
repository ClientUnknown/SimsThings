import operatorfrom protocolbuffers import UI_pb2, Consts_pb2, FileSerialization_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor import shared_messagesfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom server_commands.argument_helpers import get_optional_target, OptionalTargetParamfrom singletons import EMPTY_SETfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom world.travel_tuning import TravelTuningimport servicesimport sims4.commands
@sims4.commands.Command('travel.get_sims_available', command_type=sims4.commands.CommandType.Live)
def get_sims_available_for_travel(opt_sim_id:OptionalTargetParam=None, opt_target_id:OptionalTargetParam=None, _connection=None):
    actor_sim = get_optional_target(opt_sim_id, _connection)
    target_sim = get_optional_target(opt_target_id, _connection)
    if actor_sim is not None:
        actor_sim_info = actor_sim.sim_info
    else:
        if not opt_sim_id:
            sims4.commands.output('No sim_info id specified for travel.get_sims_available', _connection)
            return False
        actor_sim_info = services.sim_info_manager().get(opt_sim_id)
    if actor_sim_info is None:
        sims4.commands.output('Invalid sim_info id: {}'.format(opt_sim_id), _connection)
        return False

    def get_sim_filter_gsi_name():
        return 'Travel Command: Gather Available Sims'

    sim_filter = TravelTuning.TRAVEL_AVAILABILITY_SIM_FILTER
    filtered_sims = services.sim_filter_service().submit_filter(sim_filter, None, sim_constraints=None, requesting_sim_info=actor_sim_info, blacklist_sim_ids=EMPTY_SET, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
    if target_sim is not None and target_sim in filtered_sims:
        filtered_sims.remove(target_sim)
    filtered_sim_with_default_selection = get_default_selection_data(actor_sim, filtered_sims)
    if target_sim is not None and target_sim is not actor_sim:
        filtered_sim_with_default_selection.insert(0, (target_sim, True))
    msg = UI_pb2.AvailableSimsForTravel()
    msg.actor_sim_id = actor_sim_info.id
    msg.sim_ids_for_travel.extend([filter_result.sim_info.id for filter_result in filtered_sims])
    active_household_id = services.active_household_id()
    for (sim_info, selected_by_default) in filtered_sim_with_default_selection:
        with ProtocolBufferRollback(msg.available_sims) as sim_data:
            sim_data.sim_id = sim_info.id
            sim_data.is_active_household = sim_info.household_id == active_household_id
            sim_data.household_id = sim_info.household_id
            sim_data.is_at_work = sim_info.career_tracker.currently_at_work
            sim_data.zone_id = sim_info.zone_id
            sim_data.age = sim_info.age
            sim_data.selected_by_default = selected_by_default
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_AVAILABLE_SIMS_FOR_TRAVEL)
    Distributor.instance().add_op_with_no_owner(op)
    return True

def get_default_selection_data(actor_sim, filter_list):
    default_selection_data = []
    club_service = services.get_club_service()
    ensemble_service = services.ensemble_service()
    gathering = None
    ensemble = None
    if club_service is not None:
        gathering = club_service.sims_to_gatherings_map.get(actor_sim)
    if ensemble_service is not None:
        ensembles = ensemble_service.get_all_ensembles_for_sim(actor_sim)
    familiar_tracker = actor_sim.sim_info.familiar_tracker
    active_familiar_sim_id = None
    if familiar_tracker is not None:
        active_familiar_sim_id = familiar_tracker.active_familiar_id_pet_id
    for item in filter_list:
        sim_info = item.sim_info
        if sim_info.sim_id == active_familiar_sim_id:
            default_selection_data.append((sim_info, True))
        else:
            sim = sim_info.get_sim_instance()
            if sim is not None and (gathering and club_service.sims_to_gatherings_map.get(sim) is gathering or ensembles and any(sim in ensemble for ensemble in ensembles)):
                default_selection_data.append((sim_info, True))
            else:
                default_selection_data.append((sim_info, False))
    default_selection_data.sort(key=operator.itemgetter(1), reverse=True)
    return default_selection_data

@sims4.commands.Command('travel.send_travel_view_household_info', command_type=sims4.commands.CommandType.Live)
def send_travel_view_household_info(_connection=None):
    msg = UI_pb2.TravelViewHouseholdsInfo()
    for household in tuple(services.household_manager().values()):
        with ProtocolBufferRollback(msg.household_locations) as household_location_data:
            household_location_data.household_id = household.id
            household_location_data.household_name = household.name
            household_location_data.home_zone_id = household.home_zone_id
            household_location_data.is_played = household.is_player_household
            for sim_info in household:
                with ProtocolBufferRollback(household_location_data.sim_info_status) as sim_info_location_status:
                    sim_info_location_status.sim_id = sim_info.id
                    sim_info_location_status.age = sim_info.age
                    sim_info_location_status.is_at_home = sim_info.is_at_home
                    sim_info_location_status.zone_id = sim_info.zone_id
    distributor = Distributor.instance()
    distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.TRAVEL_VIEW_HOUSEHOLDS_INFO, msg))
    travel_group_list_msg = FileSerialization_pb2.TravelGroupList()
    for travel_group in tuple(services.travel_group_manager().values()):
        with ProtocolBufferRollback(travel_group_list_msg.travel_groups) as travel_group_data:
            travel_group.save_data(travel_group_data)
    distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.TRAVEL_GROUP_LIST, travel_group_list_msg))

@sims4.commands.Command('travel.travel_sims_to_zone', command_type=sims4.commands.CommandType.Live)
def travel_sims_to_zone(opt_sim_id:OptionalTargetParam, zone_id:int, *traveling_sim_ids, _connection=None):
    sim_or_sim_info = get_optional_target(opt_sim_id, _connection)
    if sim_or_sim_info is None:
        if opt_sim_id:
            sim_or_sim_info = services.sim_info_manager().get(opt_sim_id)
            if sim_or_sim_info is None:
                sims4.commands.output('Invalid Sim id: {} specified for travel.travel_sims_to_zone'.format(opt_sim_id), _connection)
                return False
        else:
            sims4.commands.output('No Sim id specified for travel.travel_sims_to_zone', _connection)
            return False
    zone_proto_buff = services.get_persistence_service().get_zone_proto_buff(zone_id)
    if zone_proto_buff is None:
        sims4.commands.output('Invalid Zone Id: {}. Zone does not exist.'.format(zone_id), _connection)
        return False
    situation_manager = services.get_zone_situation_manager()
    situation = situation_manager.DEFAULT_TRAVEL_SITUATION
    guest_list = situation.get_predefined_guest_list()
    if guest_list is None:
        guest_list = SituationGuestList(invite_only=True, host_sim_id=sim_or_sim_info.id)
        default_job = situation.default_job()
        sim_info_manager = services.sim_info_manager()
        for sim_id in traveling_sim_ids:
            sim_id = int(sim_id)
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            else:
                guest_info = SituationGuestInfo.construct_from_purpose(sim_id, default_job, SituationInvitationPurpose.INVITED)
                guest_list.add_guest_info(guest_info)
        guest_info = SituationGuestInfo.construct_from_purpose(sim_or_sim_info.id, default_job, SituationInvitationPurpose.INVITED)
        guest_list.add_guest_info(guest_info)
    situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False, zone_id=zone_id)
