from date_and_time import TimeSpanfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom drama_scheduler.drama_node import BaseDramaNodefrom drama_scheduler.drama_node_types import DramaNodeTypefrom sims4.utils import classpropertyfrom situations.situation_serialization import SituationSeedfrom situations.situation_types import SituationCallbackOptionfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog import UiDialogOkCancel, ButtonTypeimport servicesimport sims4.loglogger = sims4.log.Logger('PlayerPlannedDramaNode', default_owner='bosee')
class PlayerPlannedDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'advance_notice_time': TunableTimeSpan(description='\n            The number of time between the alert and the start of the event.\n            ', default_hours=1, locked_args={'days': 0, 'minutes': 0}), 'dialog': UiDialogOkCancel.TunableFactory(description='\n            The ok cancel dialog that will display to the user.\n            ')}

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.PLAYER_PLANNED

    def __init__(self, *args, uid=None, situation_seed=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._situation_seed = situation_seed

    def _run(self):
        situation_seed = self._situation_seed
        if situation_seed is None:
            return True
        situation_manager = services.get_zone_situation_manager()
        dialog = self.dialog(self._receiver_sim_info, resolver=self._get_resolver())

        def response(dialog):
            cleanup_node = True
            if dialog.response is not None and dialog.response == ButtonType.DIALOG_RESPONSE_OK:
                cleanup_node = False
                if situation_seed.zone_id == services.current_zone_id():
                    situation_manager.create_situation_from_seed(situation_seed)
                    situation_manager.register_for_callback(situation_seed.situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_planned_drama_node_ended)
                else:
                    situation_manager.travel_seed(situation_seed)
            if cleanup_node:
                services.drama_scheduler_service().complete_node(self.uid)

        dialog.show_dialog(on_response=response, additional_tokens=(situation_seed.situation_type.display_name,))
        return False

    def _on_planned_drama_node_ended(self, situation_id, callback_option, _):
        services.drama_scheduler_service().complete_node(self.uid)

    def on_situation_creation_during_zone_spin_up(self):
        services.get_zone_situation_manager().register_for_callback(self._situation_seed.situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_planned_drama_node_ended)

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO):
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier)
        if success:
            services.calendar_service().mark_on_calendar(self, advance_notice_time=self.advance_notice_time())
        return success

    def cleanup(self, from_service_stop=False):
        services.calendar_service().remove_on_calendar(self.uid)
        super().cleanup(from_service_stop=from_service_stop)

    def get_calendar_sims(self):
        return tuple(self._situation_seed.invited_sim_infos_gen())

    def create_calendar_entry(self):
        calendar_entry = super().create_calendar_entry()
        situation_type = self._situation_seed.situation_type
        calendar_entry.zone_id = self._situation_seed.zone_id
        build_icon_info_msg(IconInfoData(icon_resource=situation_type.calendar_icon), situation_type.display_name, calendar_entry.icon_info)
        calendar_entry.scoring_enabled = self._situation_seed.scoring_enabled
        return calendar_entry

    def create_calendar_alert(self):
        calendar_alert = super().create_calendar_alert()
        situation_type = self._situation_seed.situation_type
        calendar_alert.zone_id = self._situation_seed.zone_id
        if self._situation_seed.situation_type.calendar_alert_description is not None:
            calendar_alert.description = situation_type.calendar_alert_description
        build_icon_info_msg(IconInfoData(icon_resource=situation_type.calendar_icon), situation_type.display_name, calendar_alert.calendar_icon)
        return calendar_alert

    def save(self, drama_node_proto):
        super().save(drama_node_proto)
        self._situation_seed.serialize_to_proto(drama_node_proto.stored_situation)

    def load(self, drama_node_proto, schedule_alarm=True):
        super_success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if not super_success:
            return False
        self._situation_seed = SituationSeed.deserialize_from_proto(drama_node_proto.stored_situation)
        if not self.get_sender_sim_info().is_npc:
            services.calendar_service().mark_on_calendar(self, advance_notice_time=self.advance_notice_time())
        return True
