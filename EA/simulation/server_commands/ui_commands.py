from protocolbuffers import Dialog_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom protocolbuffers.UI_pb2 import HovertipCreatedfrom distributor.ops import GenericProtocolBufferOpfrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom google.protobuf import text_formatfrom server_commands.argument_helpers import OptionalTargetParam, OptionalSimInfoParam, get_optional_target, TunableInstanceParamfrom sims4.localization import LocalizationHelperTuningfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.commands
@sims4.commands.Command('ui.dialog.respond', command_type=sims4.commands.CommandType.Live)
def ui_dialog_respond(dialog_id:int, response:int, _connection=None):
    zone = services.current_zone()
    if not zone.ui_dialog_service.dialog_respond(dialog_id, response):
        sims4.commands.output('That is not a valid response.', _connection)
        return False
    return True

@sims4.commands.Command('ui.dialog.pick_result', command_type=sims4.commands.CommandType.Live)
def ui_dialog_pick_result(dialog_id:int, ingredient_check:bool, *choices, _connection=None):
    zone = services.current_zone()
    if not zone.ui_dialog_service.dialog_pick_result(dialog_id, choices, ingredient_check=ingredient_check):
        sims4.commands.output('That is not a valid pick result.', _connection)
        return False
    return True

@sims4.commands.Command('ui.dialog.text_input', command_type=sims4.commands.CommandType.Live)
def ui_dialog_text_input(dialog_id:int, text_input_name:str, text_input_value:str, _connection=None):
    zone = services.current_zone()
    if not zone.ui_dialog_service.dialog_text_input(dialog_id, text_input_name, text_input_value):
        sims4.commands.output('Unable to set dialog text input for {0} to {1}'.format(text_input_name, text_input_value), _connection)
        return False
    return True

@sims4.commands.Command('ui.dialog.auto_respond', command_type=sims4.commands.CommandType.Automation)
def ui_dialog_auto_respond(enable:bool=None, _connection=None):
    zone = services.current_zone()
    auto_respond = enable if enable is not None else not zone.ui_dialog_service.auto_respond
    zone.ui_dialog_service.set_auto_respond(auto_respond)
    sims4.commands.output('UI Dialog auto_respond set to {}'.format(auto_respond), _connection)

@sims4.commands.Command('ui.toggle_silence_phone', command_type=sims4.commands.CommandType.Live)
def toggle_silence_phone(sim_id:OptionalTargetParam=None, _connection=None):
    zone = services.current_zone()
    zone.ui_dialog_service.toggle_is_phone_silenced()
    return True

@sims4.commands.Command('ui.dialog.notification_test')
def ui_dialog_notification_test(*all_text, _connection=None):
    client = services.client_manager().get(_connection)
    all_text_str = ' '.join(all_text)
    if '/' in all_text:
        (title, text) = all_text_str.split('/')
        notification = UiDialogNotification.TunableFactory().default(client.active_sim, text=lambda **_: LocalizationHelperTuning.get_raw_text(text), title=lambda **_: LocalizationHelperTuning.get_raw_text(title))
    else:
        notification = UiDialogNotification.TunableFactory().default(client.active_sim, text=lambda **_: LocalizationHelperTuning.get_raw_text(all_text_str))
    notification.show_dialog(icon_override=IconInfoData(obj_instance=client.active_sim))

@sims4.commands.Command('ui.create_hovertip', command_type=sims4.commands.CommandType.Live)
def ui_create_hovertip(target_id:int=None, is_from_ui:bool=None, _connection=None):
    if target_id is None:
        return
    zone = services.current_zone()
    client = services.client_manager().get(_connection)
    if client is None or zone is None:
        return
    target = zone.find_object(target_id)
    if target is not None and target.valid_for_distribution:
        is_hovertip_created = target.on_hovertip_requested()
        hovertip_created_msg = HovertipCreated()
        hovertip_created_msg.is_from_ui = is_from_ui
        hovertip_created_msg.is_success = is_hovertip_created
        Distributor.instance().add_op(target, GenericProtocolBufferOp(Operation.HOVERTIP_CREATED, hovertip_created_msg))

@sims4.commands.Command('ui.trigger_screen_slam')
def ui_trigger_screenslam(screenslam_reference:TunableInstanceParam(sims4.resources.Types.SNIPPET), opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    screenslam_reference.send_screen_slam_message(sim_info)
    return True

@sims4.commands.Command('ui.dialog.multi_picker_result', command_type=sims4.commands.CommandType.Live)
def ui_dialog_multi_picker_result(dialog_id:int, multi_picker_proto:str, _connection=None):
    response_proto = Dialog_pb2.MultiPickerResponse()
    text_format.Merge(multi_picker_proto, response_proto)
    ui_dialog_service = services.ui_dialog_service()
    if ui_dialog_service is not None:
        dialog = ui_dialog_service.get_dialog(dialog_id)
        if dialog is not None:
            dialog.multi_picker_result(response_proto)
