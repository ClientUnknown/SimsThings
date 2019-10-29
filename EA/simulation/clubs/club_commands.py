import functoolsimport operatorfrom protocolbuffers import GameplaySaveData_pb2, Clubs_pb2from clubs.club_enums import ClubGatheringStartSource, ClubHangoutSettingfrom clubs.club_sim_picker_dialog import ClubSimPickerRowfrom clubs.club_tuning import ClubTunablesfrom distributor.ops import AskAboutClubsDialogfrom distributor.system import Distributorfrom google.protobuf import text_formatfrom server_commands.argument_helpers import TunableInstanceParam, RequiredTargetParam, OptionalTargetParam, get_optional_targetfrom sims4.commands import CommandTypefrom tag import Tagfrom world.region import get_region_instance_from_zone_idimport build_buyimport servicesimport sims4
def _get_club_service(_connection):
    club_service = services.get_club_service()
    if club_service is None:
        sims4.commands.output('Club Service not loaded.', _connection)
    return club_service

@sims4.commands.Command('clubs.create_club_from_seed', command_type=sims4.commands.CommandType.Automation)
def create_club_from_seed(club_seed:TunableInstanceParam(sims4.resources.Types.CLUB_SEED), _connection=None):
    club = None
    if club_seed is not None:
        club = club_seed.create_club()
    if club is not None:
        sims4.commands.automation_output('ClubCreate; Status:Success, Id:{}'.format(club.club_id), _connection)
    else:
        sims4.commands.automation_output('ClubCreate; Status:Failed', _connection)

@sims4.commands.Command('clubs.add_sim_to_club')
def add_sim_to_club(sim:RequiredTargetParam, club_name, _connection=None):
    target_sim_info = sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Not a valid SimID.', _connection)
        return
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    club_name_lc = club_name.lower()
    for club in club_service.clubs:
        if club_name_lc in str(club).lower():
            club.add_member(target_sim_info)
            return
    sims4.commands.output('No existing club with a name including the string {}'.format(club_name_lc), _connection)

@sims4.commands.Command('clubs.add_sim_to_club_by_id', command_type=sims4.commands.CommandType.Live)
def add_sim_to_club_by_id(sim:RequiredTargetParam, club_id:int, _connection=None):
    target_sim_info = sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Not a valid SimID.', _connection)
        sims4.commands.automation_output('ClubAddSim; Status:Failed', _connection)
        return
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubAddSim; Status:Failed', _connection)
        return
    club = club_service.get_club_by_id(club_id)
    if club is not None:
        club.add_member(target_sim_info)
        sims4.commands.automation_output('ClubAddSim; Status:Success', _connection)
        return
    sims4.commands.output('No existing club with id {}'.format(club_id), _connection)
    sims4.commands.automation_output('ClubAddSim; Status:Failed', _connection)

@sims4.commands.Command('clubs.set_leader_by_id', command_type=sims4.commands.CommandType.Live)
def set_leader_by_id(sim:RequiredTargetParam, club_id:int, _connection=None):
    target_sim_info = sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Not a valid SimID.', _connection)
        sims4.commands.automation_output('ClubSetLeader; Status:Failed', _connection)
        return
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubSetLeader; Status:Failed', _connection)
        return
    club = club_service.get_club_by_id(club_id)
    if club is not None:
        club.reassign_leader(target_sim_info)
        sims4.commands.automation_output('ClubSetLeader; Status:Success', _connection)
        return
    sims4.commands.output('No existing club with id {}'.format(club_id), _connection)
    sims4.commands.automation_output('ClubSetLeader; Status:Failed', _connection)

@sims4.commands.Command('clubs.remove_sim_from_club')
def remove_sim_from_club(sim:RequiredTargetParam, club_name, _connection=None):
    target_sim_info = sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Not a valid SimID.', _connection)
        return
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    club_name_lc = club_name.lower()
    for club in club_service.clubs:
        if club_name_lc in str(club).lower():
            club.remove_member(target_sim_info)
            return
    sims4.commands.output('No existing club with a name including the string {}'.format(club_name_lc), _connection)

@sims4.commands.Command('clubs.remove_sim_from_club_by_id', command_type=sims4.commands.CommandType.Live)
def remove_sim_from_club_by_id(sim:RequiredTargetParam, club_id:int, _connection=None):
    target_sim_info = sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Not a valid SimID.', _connection)
        sims4.commands.automation_output('ClubRemoveSim; Status:Failed', _connection)
        return
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubRemoveSim; Status:Failed', _connection)
        return
    club = club_service.get_club_by_id(club_id)
    if club is not None:
        club.remove_member(target_sim_info)
        sims4.commands.automation_output('ClubRemoveSim; Status:Success', _connection)
        return
    sims4.commands.output('No existing club with id {}'.format(club_id), _connection)
    sims4.commands.automation_output('ClubRemoveSim; Status:Failed', _connection)

@sims4.commands.Command('clubs.start_gathering_by_club_id', command_type=sims4.commands.CommandType.Live)
def start_gathering_by_club_id(club_id:int, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubGatheringStart; Status:Failed', _connection)
        return
    club = club_service.get_club_by_id(club_id)
    if club is None:
        sims4.commands.output('No Club exists with this ID.', _connection)
        sims4.commands.automation_output('ClubGatheringStart; Status:Failed', _connection)
        return
    persistence_service = services.get_persistence_service()
    venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
    current_zone_id = services.current_zone_id()

    def _start_gathering(zone_id=None):
        start_gathering = functools.partial(club_service.start_gathering, club, invited_sims=(services.active_sim_info(),))
        if zone_id is None:
            venue_type = venue_manager.get(build_buy.get_current_venue(current_zone_id))
            if venue_type.is_residential:
                if not club.is_zone_valid_for_gathering(current_zone_id):
                    club.show_club_notification(services.active_sim_info(), ClubTunables.CLUB_GATHERING_START_RESIDENTIAL_INVALID_DIALOG)
                    return
            elif not club.is_zone_valid_for_gathering(current_zone_id):
                club.show_club_notification(services.active_sim_info(), ClubTunables.CLUB_GATHERING_START_INVALID_DIALOG)
                return
            start_gathering()
        else:
            start_gathering(zone_id=zone_id)

    zone_id = club.get_hangout_zone_id(prefer_current=True)
    if zone_id:
        current_region = services.current_region()
        hangout_region = get_region_instance_from_zone_id(zone_id)
        if not current_region.is_region_compatible(hangout_region):
            zone_id = 0
    if zone_id and (zone_id == current_zone_id or persistence_service.is_save_locked()):
        _start_gathering()
    else:

        def on_response(dialog):
            if dialog.closed:
                return
            if dialog.accepted:
                _start_gathering(zone_id=zone_id)
            else:
                _start_gathering()

        if club.hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
            venue_name = club.hangout_venue.display_name
        elif club.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            venue_name = zone_data.name if zone_data is not None else ''
        club.show_club_notification(services.active_sim_info(), ClubTunables.CLUB_GATHERING_START_SELECT_LOCATION_DIALOG, additional_tokens=(venue_name,), on_response=on_response)
    sims4.commands.automation_output('ClubGatheringStart; Status:Success', _connection)
    return True

@sims4.commands.Command('clubs.join_gathering_by_club_id', command_type=sims4.commands.CommandType.Live)
def join_gathering_by_club_id(club_id:int, sim_id:OptionalTargetParam=None, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return False
    club = club_service.get_club_by_id(club_id)
    if club is None:
        return False
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        return False
    club_gathering = club_service.clubs_to_gatherings_map.get(club)
    if club_gathering is None:
        return False
    current_gathering = club_service.sims_to_gatherings_map.get(sim)
    if current_gathering is not None and current_gathering.associated_club is not club:
        current_gathering.remove_sim_from_situation(sim)
    club_gathering.invite_sim_to_job(sim, job=club_gathering.default_job())
    return True

@sims4.commands.Command('clubs.end_gathering_by_club_id', command_type=sims4.commands.CommandType.Live)
def end_gathering_by_club_id(club_id:int, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubGatheringEnd; Status:Failed', _connection)
        return
    club = club_service.get_club_by_id(club_id)
    if club is None:
        sims4.commands.output('No Club exists with this ID.', _connection)
        sims4.commands.automation_output('ClubGatheringEnd; Status:Failed', _connection)
        return
    gathering = club_service.clubs_to_gatherings_map.get(club)
    if gathering is None:
        sims4.commands.output('No Gathering exists for a Club with this ID.', _connection)
        sims4.commands.automation_output('ClubGatheringEnd; Status:Failed', _connection)
        return
    gathering._self_destruct()
    sims4.commands.automation_output('ClubGatheringEnd; Status:Success', _connection)

@sims4.commands.Command('clubs.request_invite', command_type=sims4.commands.CommandType.Live)
def request_club_invite(club_id:int, _connection=None):
    sim_info = services.active_sim_info()
    if sim_info is None:
        return
    club_service = services.get_club_service()
    if club_service is None:
        return
    club = club_service.get_club_by_id(club_id)
    if club is None:
        return
    if any(club_member.is_selectable for club_member in club.members):
        club.show_club_notification(sim_info, ClubTunables.CLUB_GATHERING_DIALOG_REQUEST_INVITE_ACTIVE_SIM)
    elif club in club_service.clubs_to_gatherings_map:
        club.show_club_notification(sim_info, ClubTunables.CLUB_GATHERING_DIALOG_REQUEST_INVITE_CURRENT_LOT)
    else:
        club_hangout_zone_id = club.get_hangout_zone_id()
        if club.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
            current_region = services.current_region()
            hangout_region = get_region_instance_from_zone_id(club_hangout_zone_id)
            if not current_region.is_region_compatible(hangout_region):
                club.show_club_notification(sim_info, ClubTunables.CLUB_GATHERING_DIALOG_REQUEST_INVITE_UNAVAILABLE, target_sim_id=club.leader.sim_id)
                return
        elif not club_hangout_zone_id:
            if services.active_lot_id() == services.active_household_lot_id():

                def on_response(dialog):
                    if dialog.accepted:
                        club_service.start_gathering(club, host_sim_id=sim_info.sim_id, invited_sims=(sim_info,), ignore_zone_validity=True)

                club.show_club_notification(sim_info, ClubTunables.CLUB_GATHERING_DIALOG_REQUEST_INVITE_NO_LOT, target_sim_id=club.leader.sim_id, on_response=on_response)
            else:
                club.show_club_notification(sim_info, ClubTunables.CLUB_GATHERING_DIALOG_REQUEST_INVITE_NO_LOT_NOT_HOME, target_sim_id=club.leader.sim_id)
            return
        club.show_club_gathering_dialog(sim_info, flavor_text=ClubTunables.CLUB_GATHERING_DIALOG_TEXT_REQUEST_INVITE, start_source=ClubGatheringStartSource.APPLY_FOR_INVITE)

@sims4.commands.Command('clubs.refresh_safe_seed_data_for_club')
def refresh_safe_seed_data_for_club(club_id:int, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    club = club_service.get_club_by_id(club_id)
    if club is None:
        sims4.commands.output('No Club exists with this ID.', _connection)
        return
    if club.club_seed is None:
        sims4.commands.output('Club has no associated ClubSeed.', _connection)
        return
    club_service.refresh_safe_seed_data_for_club(club)
    sims4.commands.output('Club successfully refreshed.', _connection)

@sims4.commands.Command('clubs.request_club_building_info', command_type=CommandType.Live)
def request_club_building_info(_connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    club_service.send_club_building_info()

@sims4.commands.Command('clubs.validate_sims_against_criteria', command_type=CommandType.Live)
def validate_sims_against_criteria(criteria_data:str, *sim_ids, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    proto = Clubs_pb2.ClubBuildingInfo()
    text_format.Merge(criteria_data, proto)
    club_service.send_club_criteria_validation(sim_ids, proto)

@sims4.commands.Command('clubs.show_add_member_picker', command_type=CommandType.Live)
def show_add_club_member_picker(criteria_data:str, max_selectable:int=8, *excluded_sim_ids, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return False
    criteria_msg = Clubs_pb2.ClubBuildingInfo()
    text_format.Merge(criteria_data, criteria_msg)
    criterias = [club_service._load_specific_criteria(data) for data in criteria_msg.criterias]
    active_sim_info = services.active_sim_info()
    sim_filter_service = services.sim_filter_service()
    dialog = ClubTunables.CLUB_ADD_MEMBER_PICKER_DIALOG(services.active_sim_info(), club_building_info=criteria_msg, max_selectable=max_selectable)

    def get_sim_filter_gsi_name():
        return 'Club Command: Add Club Member'

    valid_sim_infos = []
    for sim_info in services.sim_info_manager().get_all():
        if sim_info.sim_id in excluded_sim_ids:
            pass
        elif sim_info.is_baby:
            pass
        elif sim_info.is_ghost and not sim_info.is_selectable:
            pass
        elif not club_service.can_sim_info_join_more_clubs(sim_info):
            pass
        elif not all(criteria.test_sim_info(sim_info) for criteria in criterias):
            pass
        else:
            results = sim_filter_service.submit_filter(ClubTunables.CLUB_ADD_MEMBER_FILTER, callback=None, requesting_sim_info=active_sim_info, sim_constraints=(sim_info.sim_id,), allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
            if results:
                valid_sim_infos.append((sim_info, results[0].score))
    for (sim_info, _) in sorted(valid_sim_infos, key=operator.itemgetter(1), reverse=True)[:ClubTunables.CLUB_ADD_MEMBER_CAP]:
        dialog_row = ClubSimPickerRow(sim_info.sim_id)
        dialog.add_row(dialog_row)
    dialog.show_dialog(additional_tokens=(max_selectable,))
    return True

@sims4.commands.Command('clubs.validate_sim_against_clubs', command_type=CommandType.Live)
def validate_sim_against_clubs(sim_id:int, *club_ids, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    club_service.send_club_validation(sim_id, club_ids)

@sims4.commands.Command('clubs.create_club', command_type=CommandType.Live)
def create_club(club_data:str, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubCreate; Status:Failed', _connection)
        return
    proto = GameplaySaveData_pb2.Club()
    text_format.Merge(club_data, proto)
    club = club_service.create_club_from_new_data(proto)
    sims4.commands.automation_output('ClubCreate; Status:Success, Id:{}'.format(club.club_id), _connection)

@sims4.commands.Command('clubs.update_club', command_type=CommandType.Live)
def update_club(club_data:str, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    proto = GameplaySaveData_pb2.Club()
    text_format.Merge(club_data, proto)
    club_service.update_club_from_data(proto)

@sims4.commands.Command('clubs.remove_club_by_id', command_type=CommandType.Live)
def remove_club_by_id(club_id:int, _connection=None):
    club_service = _get_club_service(_connection)
    if club_service is None:
        sims4.commands.automation_output('ClubDestroy; Status:Failed', _connection)
        return
    club = club_service.get_club_by_id(club_id)
    if club is None:
        sims4.commands.output('No Club exists with this ID.', _connection)
        sims4.commands.automation_output('ClubDestroy; Status:Failed', _connection)
        return
    club_service.remove_club(club)
    sims4.commands.automation_output('ClubDestroy; Status:Success', _connection)

@sims4.commands.Command('clubs.set_club_outfit_style', command_type=CommandType.Live)
def set_club_outfit_style(club_id:int, style_tag:Tag, _connection=None):
    club = get_club_from_service_by_id(club_id, _connection)
    if club is None:
        return False
    club.set_associated_style(style_tag)
    sims4.commands.output('The {} group now has an associated style of {}'.format(club, style_tag), _connection)

@sims4.commands.Command('clubs.set_club_outfit_color', command_type=CommandType.Live)
def set_club_outfit_color(club_id:int, color_tag:Tag, _connection=None):
    club = get_club_from_service_by_id(club_id, _connection)
    if club is None:
        return False
    club.set_associated_color(color_tag)
    sims4.commands.output('The {} group now has an associated color of {}'.format(club, color_tag), _connection)

def get_club_from_service_by_id(club_id, _connection):
    club_service = services.get_club_service()
    if club_service is None:
        sims4.commands.output('A Pack with Clubs/Groups is not installed.', _connection)
        return
    else:
        club = club_service.get_club_by_id(club_id)
        if club is None:
            sims4.commands.output('Club not found with id {}. Please Specify an existing club id.'.format(club_id), _connection)
            return
    return club

@sims4.commands.Command('clubs.show_ask_about_clubs_dialog_for_sim', command_type=CommandType.Live)
def show_ask_about_clubs_dialog_for_sim(sim:RequiredTargetParam, _connection):
    club_service = _get_club_service(_connection)
    if club_service is None:
        return
    target_sim_info = sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Not a valid SimID.', _connection)
        return
    participant_clubs = club_service.get_clubs_for_sim_info(target_sim_info)
    if not participant_clubs:
        return
    op = AskAboutClubsDialog(target_sim_info.id, [club.id for club in participant_clubs])
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('clubs.set_outfit_setting', command_type=CommandType.Live)
def set_outfit_setting(club_id:int, setting:int, _connection):
    club = get_club_from_service_by_id(club_id, _connection)
    if club is None:
        return False
    club.set_outfit_setting(setting)

@sims4.commands.Command('qa.clubs.get_members', command_type=CommandType.Automation)
def qa_get_members(club_id:int, _connection):
    club = get_club_from_service_by_id(club_id, _connection)
    if club is None:
        sims4.commands.automation_output('ClubMembers; Status:Failed', _connection)
        return False
    sims4.commands.automation_output('ClubMembers; Status:Begin', _connection)
    members = club.members
    for member in members:
        sims4.commands.automation_output('ClubMembers; Status:Data, SimId:{}'.format(member.sim_id), _connection)
    sims4.commands.automation_output('ClubMembers; Status:End', _connection)

@sims4.commands.Command('qa.clubs.get_leader', command_type=CommandType.Automation)
def qa_get_leader(club_id:int, _connection):
    club = get_club_from_service_by_id(club_id, _connection)
    if club is None:
        sims4.commands.automation_output('ClubLeader; Status:Failed', _connection)
        return False
    leader = club.leader
    if leader is None:
        sims4.commands.automation_output('ClubLeader; Status:Failed', _connection)
        return False
    sims4.commands.automation_output('ClubLeader; Status:Success, SimId:{}'.format(leader.sim_id), _connection)

@sims4.commands.Command('qa.clubs.create_club', command_type=CommandType.Automation)
def qa_create_club(club_name:str, sim_id:int, _connection=None):
    club_data = '\n        name: "{0}"\n        description: "{0}"\n        leader: {1}\n        members: {1}\n        '.format(club_name, sim_id)
    create_club(club_data, _connection)
