from date_and_time import create_time_span, TimeSpanfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom drama_scheduler.drama_node import BaseDramaNodefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.results import TestResultfrom gsi_handlers.drama_handlers import GSIRejectedDramaNodeScoringDatafrom interactions.utils.display_mixin import get_display_mixinfrom sims4.tuning.tunable import TunableSimMinute, OptionalTunable, TunableReference, TunableListfrom sims4.utils import classpropertyfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom ui.ui_dialog_notification import UiDialogNotificationimport alarmsimport build_buyimport elementsimport servicesimport sims4.loglogger = sims4.log.Logger('DramaNode', default_owner='jjacobson')ZONE_ID_TOKEN = 'zone_id'SHOWN_NOTIFICATION_TOKEN = 'shown_notification'DURATION_TOKEN = 'duration'VenueEventDramaNodeDisplayMixin = get_display_mixin(has_icon=True)
class VenueEventDramaNode(VenueEventDramaNodeDisplayMixin, BaseDramaNode):
    INSTANCE_TUNABLES = {'duration': TunableSimMinute(description='\n            The duration that this drama node will run for.\n            ', minimum=1, default=1), 'zone_director': OptionalTunable(description='\n            If enabled then this drama node will override the zone director\n            of the lot.\n            ', tunable=TunableReference(description='\n                The zone director that we will override onto the lot.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR))), 'notification': OptionalTunable(description='\n            If enabled then we will display a notification when this venue\n            event occurs.\n            ', tunable=UiDialogNotification.TunableFactory()), 'away_notification': OptionalTunable(description='\n            If enabled then we will display a notification when this venue\n            event occurs if player is not on the lot.\n            Additional Tokens:\n            Zone Name\n            Venue Name\n            ', tunable=UiDialogNotification.TunableFactory()), 'ending_notification': OptionalTunable(description='\n            If enabled then we will display a notification when this venue\n            event ends if the player is on the current lot that the event is\n            taking place on.\n            ', tunable=UiDialogNotification.TunableFactory()), 'zone_modifier_requirements': TunableWhiteBlackList(description='\n            A requirement on zone modifiers which must be true on both\n            scheduling and running.\n            ', tunable=TunableReference(description='\n                Allowed and disallowed zone modifiers\n                ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), pack_safe=True)), 'additional_drama_nodes': TunableList(description='\n            A list of additional drama nodes that we will score and schedule\n            when this drama node is run.  Only 1 drama node is run.\n            ', tunable=TunableReference(description='\n                A drama node that we will score and schedule when this drama\n                node is run.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._duration_alarm_handle = None
        self._zone_id = None
        self._shown_notification = False
        self._additional_nodes_processor = None
        self._duration_override = None

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.VENUE_EVENT

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def simless(cls):
        return True

    @property
    def is_calendar_deletable(self):
        return False

    def get_calendar_end_time(self):
        return self.get_calendar_start_time() + create_time_span(minutes=self.duration)

    @property
    def zone_director_override(self):
        if services.current_zone_id() == self._zone_id:
            return self.zone_director

    def _setup(self, *args, zone_id=None, gsi_data=None, **kwargs):
        result = super()._setup(*args, gsi_data=gsi_data, **kwargs)
        if not result:
            return result
        else:
            self._zone_id = zone_id
            if self._zone_id is None:
                if gsi_data is not None:
                    gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), "Failed to setup drama node because it wasn't given a zone id to run in."))
                return False
        return True

    def cleanup(self, from_service_stop=False):
        super().cleanup(from_service_stop=from_service_stop)
        if self._duration_alarm_handle is not None:
            self._duration_alarm_handle.cancel()
            self._duration_alarm_handle = None

    def _test(self, *args, **kwargs):
        if self._zone_id is None:
            return TestResult(False, 'Cannot run Venue Event Drama Node with no zone id set.')
        zone_modifiers = services.get_zone_modifier_service().get_zone_modifiers(self._zone_id)
        if not self.zone_modifier_requirements.test_collection(zone_modifiers):
            return TestResult(False, 'Incompatible zone modifiers tuned on venue.')
        return super()._test(*args, **kwargs)

    def _end_venue_behavior(self):
        if self.zone_director is not None:
            venue_service = services.venue_service()
            if type(venue_service.get_zone_director()) is self.zone_director:
                if self.ending_notification is not None:
                    dialog = self.ending_notification(services.active_sim_info())
                    dialog.show_dialog()
                venue_service.change_zone_director(venue_service.venue.zone_director(), True)
        elif self.ending_notification is not None:
            dialog = self.ending_notification(services.active_sim_info())
            dialog.show_dialog()

    def _show_notification(self):
        if self.notification is None:
            return
        if self._shown_notification:
            return
        dialog = self.notification(services.active_sim_info())
        dialog.show_dialog()
        self._shown_notification = True

    def _run_venue_behavior(self):
        services.venue_service().change_zone_director(self.zone_director(), True)
        self._show_notification()

    def _resume_venue_behavior(self):
        self._show_notification()

    def _on_venue_event_complete(self, _):
        if services.current_zone_id() == self._zone_id:
            self._end_venue_behavior()
        services.drama_scheduler_service().complete_node(self._uid)

    def _show_away_notification(self):
        if self.away_notification is None:
            return
        zone_data = services.get_persistence_service().get_zone_proto_buff(self._zone_id)
        if zone_data is None:
            return
        venue_type_id = build_buy.get_current_venue(self._zone_id)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_instance = venue_manager.get(venue_type_id)
        if venue_instance is None:
            return
        dialog = self.away_notification(services.active_sim_info())
        dialog.show_dialog(additional_tokens=(zone_data.name, venue_instance.display_name))

    def _process_scoring_gen(self, timeline):
        try:
            yield from services.drama_scheduler_service().score_and_schedule_nodes_gen(self.additional_drama_nodes, 1, zone_id=self._zone_id, timeline=timeline)
        except GeneratorExit:
            raise
        except Exception as exception:
            logger.exception('Exception while scoring DramaNodes: ', exc=exception, level=sims4.log.LEVEL_ERROR)
        finally:
            self._additional_nodes_processor = None

    def _run(self):
        self._duration_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.duration), self._on_venue_event_complete)
        if services.current_zone_id() == self._zone_id:
            self._run_venue_behavior()
            return
        self._show_away_notification()
        if self.additional_drama_nodes:
            sim_timeline = services.time_service().sim_timeline
            self._additional_nodes_processor = sim_timeline.schedule(elements.GeneratorElement(self._process_scoring_gen))

    def resume(self):
        if services.current_zone_id() == self._zone_id:
            self._resume_venue_behavior()
        if self._duration_override is not None:
            time_span = TimeSpan(self._duration_override)
        else:
            time_span = create_time_span(minutes=self.duration)
        self._duration_alarm_handle = alarms.add_alarm(self, time_span, self._on_venue_event_complete)

    def _save_custom_data(self, writer):
        writer.write_uint64(ZONE_ID_TOKEN, self._zone_id)
        writer.write_bool(SHOWN_NOTIFICATION_TOKEN, self._shown_notification)
        if self._duration_alarm_handle is not None:
            writer.write_uint64(DURATION_TOKEN, int(self._duration_alarm_handle.get_remaining_time().in_ticks()))

    def _load_custom_data(self, reader):
        self._zone_id = reader.read_uint64(ZONE_ID_TOKEN, None)
        if self._zone_id is None:
            return False
        self._shown_notification = reader.read_bool(SHOWN_NOTIFICATION_TOKEN, False)
        self._duration_override = reader.read_uint64(DURATION_TOKEN, None)
        return True

    def load(self, drama_node_proto, schedule_alarm=True):
        super_success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if not super_success:
            return False
        services.calendar_service().mark_on_calendar(self)
        return True

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO):
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier)
        if success:
            services.calendar_service().mark_on_calendar(self)
        return success

    def create_calendar_entry(self):
        calendar_entry = super().create_calendar_entry()
        calendar_entry.zone_id = self._zone_id
        build_icon_info_msg(IconInfoData(icon_resource=self._display_data.instance_display_icon), self._display_data.instance_display_name, calendar_entry.icon_info)
        calendar_entry.scoring_enabled = False
        return calendar_entry
