from protocolbuffers import UI_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom date_and_time import create_time_spanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeScoringBucket, CooldownOptionfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.test_events import TestEventfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.utils.tunable_icon import TunableIconfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom open_street_director.open_street_director_request import OpenStreetDirectorRequestfrom server.pick_info import PickInfo, PickTypefrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunableTuple, TunableRange, TunableEnumEntry, TunableSimMinute, TunableList, TunableLotDescription, TunableResourceKey, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom ui.ui_dialog import CommandArgTypefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom world.lot import get_lot_id_from_instance_idimport alarmsimport elementsimport interactions.contextimport servicesimport sims4.resourceslogger = sims4.log.Logger('DramaNode', default_owner='jjacobson')
class FestivalDramaNode(BaseDramaNode):
    GO_TO_FESTIVAL_INTERACTION = TunablePackSafeReference(description='\n        Reference to the interaction used to travel the Sims to the festival.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    INSTANCE_TUNABLES = {'festival_open_street_director': TunableReference(description='\n            Reference to the open street director in question.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OPEN_STREET_DIRECTOR)), 'street': TunableReference(description='\n            The street that this festival is allowed to run on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STREET)), 'scoring': OptionalTunable(description='\n            If enabled this DramaNode will be scored and chosen by the drama\n            service.\n            ', tunable=TunableTuple(description='\n                Data related to scoring this DramaNode.\n                ', base_score=TunableRange(description='\n                    The base score of this drama node.  This score will be\n                    multiplied by the score of the different filter results\n                    used to find the Sims for this DramaNode to find the final\n                    result.\n                    ', tunable_type=int, default=1, minimum=1), bucket=TunableEnumEntry(description="\n                    Which scoring bucket should these drama nodes be scored as\n                    part of.  Only Nodes in the same bucket are scored against\n                    each other.\n                    \n                    Change different bucket settings within the Drama Node's\n                    module tuning.\n                    ", tunable_type=DramaNodeScoringBucket, default=DramaNodeScoringBucket.DEFAULT), locked_args={'receiving_sim_scoring_filter': None})), 'pre_festival_duration': TunableSimMinute(description='\n            The amount of time in Sim minutes that this festival will be in a\n            pre-running state.  Testing against this Drama Node will consider\n            the node to be running, but the festival will not actually be.\n            ', default=120, minimum=1), 'fake_duration': TunableSimMinute(description="\n            The amount of time in Sim minutes that we will have this drama node\n            run when the festival isn't actually up and running.  When the\n            festival actually runs we will trust in the open street director to\n            tell us when we should actually end.\n            ", default=60, minimum=1), 'festival_dynamic_sign_info': OptionalTunable(description='\n            If enabled then this festival drama node can be used to populate\n            a dynamic sign.\n            ', tunable=TunableTuple(description='\n                Data for populating the dynamic sign view for the festival.\n                ', festival_name=TunableLocalizedString(description='\n                    The name of this festival.\n                    '), festival_time=TunableLocalizedString(description='\n                    The time that this festival should run.\n                    '), travel_to_festival_text=TunableLocalizedString(description='\n                    The text that will display to get you to travel to the festival.\n                    '), festival_not_started_tooltip=TunableLocalizedString(description='\n                    The tooltip that will display on the travel to festival\n                    button when the festival has not started.\n                    '), on_street_tooltip=TunableLocalizedString(description='\n                    The tooltip that will display on the travel to festival\n                    button when the player is already at the festival.\n                    '), on_vacation_tooltip=TunableLocalizedString(description='\n                    The tooltip that will display on the travel to festival\n                    button when the player is on vacation.\n                    '), display_image=TunableResourceKey(description='\n                     The image for this festival display.\n                     ', resource_types=sims4.resources.CompoundTypes.IMAGE), background_image=TunableResourceKey(description='\n                     The background image for this festival display.\n                     ', default=None, resource_types=sims4.resources.CompoundTypes.IMAGE), activity_info=TunableList(description='\n                    The different activities that are advertised to be running at this\n                    festival.\n                    ', tunable=TunableTuple(description='\n                        A single activity that will be taking place at this festival.\n                        ', activity_name=TunableLocalizedString(description='\n                            The name of this activity.\n                            '), activity_description=TunableLocalizedString(description='\n                            The description of this activity.\n                            '), icon=TunableIcon(description='\n                            The Icon that represents this festival activity.\n                            ')))), tuning_group=GroupNames.UI), 'starting_notification': OptionalTunable(description='\n            If enabled then when this festival runs we will surface a\n            notification to the players.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that will appear when this drama node runs.\n                '), tuning_group=GroupNames.UI), 'additional_drama_nodes': TunableList(description='\n            A list of additional drama nodes that we will score and schedule\n            when this drama node is run.  Only 1 drama node is run.\n            ', tunable=TunableReference(description='\n                A drama node that we will score and schedule when this drama\n                node is run.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))), 'delay_timeout': TunableSimMinute(description='\n            The amount of time in Sim minutes that the open street director has\n            been delayed that we will no longer start the festival.\n            ', default=120, minimum=0)}
    REMOVE_INSTANCE_TUNABLES = ('receiver_sim', 'sender_sim_info', 'picked_sim_info')

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.FESTIVAL

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def simless(cls):
        return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._duration_alarm = None
        self._additional_nodes_processor = None

    def cleanup(self, from_service_stop=False):
        super().cleanup(from_service_stop=from_service_stop)
        if self._duration_alarm is not None:
            alarms.cancel_alarm(self._duration_alarm)
            self._duration_alarm = None
        if self._additional_nodes_processor is not None:
            self._additional_nodes_processor.trigger_hard_stop()
            self._additional_nodes_processor = None

    def _alarm_finished_callback(self, _):
        services.drama_scheduler_service().complete_node(self.uid)

    def _request_timed_out_callback(self):
        services.drama_scheduler_service().complete_node(self.uid)

    def _open_street_director_destroyed_early_callback(self):
        services.drama_scheduler_service().complete_node(self.uid)

    def _get_time_till_end(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        duration = create_time_span(minutes=self.fake_duration + self.pre_festival_duration)
        time_left_to_go = duration - time_since_started
        return time_left_to_go

    def _setup_end_alarm(self):
        time_left_to_go = self._get_time_till_end()
        self._duration_alarm = alarms.add_alarm(self, time_left_to_go, self._alarm_finished_callback)

    def _create_open_street_director_request(self):
        festival_open_street_director = self.festival_open_street_director(drama_node_uid=self._uid)
        preroll_time = self._selected_time + create_time_span(minutes=self.pre_festival_duration)
        request = OpenStreetDirectorRequest(festival_open_street_director, priority=festival_open_street_director.priority, preroll_start_time=preroll_time, timeout=create_time_span(minutes=self.delay_timeout), timeout_callback=self._request_timed_out_callback, premature_destruction_callback=self._open_street_director_destroyed_early_callback)
        services.venue_service().request_open_street_director(request)

    def _try_and_start_festival(self):
        street = services.current_street()
        if street is not self.street:
            self._setup_end_alarm()
            return
        self._create_open_street_director_request()

    def _process_scoring_gen(self, timeline):
        try:
            yield from services.drama_scheduler_service().score_and_schedule_nodes_gen(self.additional_drama_nodes, 1, street_override=self.street, timeline=timeline)
        except GeneratorExit:
            raise
        except Exception as exception:
            logger.exception('Exception while scoring DramaNodes: ', exc=exception, level=sims4.log.LEVEL_ERROR)
        finally:
            self._additional_nodes_processor = None

    def _pre_festival_alarm_callback(self, _):
        self._try_and_start_festival()
        services.get_event_manager().process_events_for_household(TestEvent.FestivalStarted, services.active_household())
        if self.starting_notification is not None:
            starting_notification = self.starting_notification(services.active_sim_info())
            starting_notification.show_dialog(response_command_tuple=tuple([CommandArgType.ARG_TYPE_INT, self.guid64]))
        if self.additional_drama_nodes:
            sim_timeline = services.time_service().sim_timeline
            self._additional_nodes_processor = sim_timeline.schedule(elements.GeneratorElement(self._process_scoring_gen))

    def _setup_pre_festival_alarm(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        duration = create_time_span(minutes=self.pre_festival_duration)
        time_left_to_go = duration - time_since_started
        self._duration_alarm = alarms.add_alarm(self, time_left_to_go, self._pre_festival_alarm_callback)

    def _run(self):
        self._setup_pre_festival_alarm()
        services.get_event_manager().process_events_for_household(TestEvent.FestivalStarted, services.active_household())
        return False

    def resume(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        if time_since_started < create_time_span(minutes=self.pre_festival_duration):
            self._setup_pre_festival_alarm()
        else:
            self._try_and_start_festival()

    def is_on_festival_street(self):
        street = services.current_street()
        return street is self.street

    def is_during_pre_festival(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        if time_since_started < create_time_span(minutes=self.pre_festival_duration):
            return True
        return False

    @classmethod
    def show_festival_info(cls):
        if cls.festival_dynamic_sign_info is None:
            return
        ui_info = cls.festival_dynamic_sign_info
        festival_info = UI_pb2.DynamicSignView()
        festival_info.drama_node_guid = cls.guid64
        festival_info.name = ui_info.festival_name
        lot_id = get_lot_id_from_instance_id(cls.street.travel_lot)
        persistence_service = services.get_persistence_service()
        zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        zone_protobuff = persistence_service.get_zone_proto_buff(zone_id)
        if zone_protobuff is not None:
            festival_info.venue = LocalizationHelperTuning.get_raw_text(zone_protobuff.name)
        festival_info.time = ui_info.festival_time
        festival_info.image = sims4.resources.get_protobuff_for_key(ui_info.display_image)
        festival_info.background_image = sims4.resources.get_protobuff_for_key(ui_info.background_image)
        festival_info.action_label = ui_info.travel_to_festival_text
        running_nodes = services.drama_scheduler_service().get_running_nodes_by_class(cls)
        active_sim_info = services.active_sim_info()
        if all(active_node.is_during_pre_festival() for active_node in running_nodes):
            festival_info.disabled_tooltip = ui_info.festival_not_started_tooltip
        elif any(active_node.is_on_festival_street() for active_node in running_nodes):
            festival_info.disabled_tooltip = ui_info.on_street_tooltip
        elif active_sim_info.is_in_travel_group():
            festival_info.disabled_tooltip = ui_info.on_vacation_tooltip
        for activity in ui_info.activity_info:
            with ProtocolBufferRollback(festival_info.activities) as activity_msg:
                activity_msg.name = activity.activity_name
                activity_msg.description = activity.activity_description
                activity_msg.icon = create_icon_info_msg(IconInfoData(activity.icon))
        distributor = Distributor.instance()
        distributor.add_op(active_sim_info, GenericProtocolBufferOp(Operation.DYNAMIC_SIGN_VIEW, festival_info))

    @classmethod
    def travel_to_festival(cls):
        active_sim_info = services.active_sim_info()
        active_sim = active_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if active_sim is None:
            return
        lot_id = cls.street.get_lot_to_travel_to()
        if lot_id is None:
            return
        pick = PickInfo(pick_type=PickType.PICK_TERRAIN, lot_id=lot_id, ignore_neighborhood_id=True)
        context = interactions.context.InteractionContext(active_sim, interactions.context.InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, interactions.priority.Priority.High, insert_strategy=interactions.context.QueueInsertStrategy.NEXT, pick=pick)
        active_sim.push_super_affordance(FestivalDramaNode.GO_TO_FESTIVAL_INTERACTION, None, context)
lock_instance_tunables(FestivalDramaNode, allow_during_work_hours=False, cooldown_option=CooldownOption.ON_RUN)
class ShowFestivalInfoSuperInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'festival_drama_node': FestivalDramaNode.TunableReference(description='\n            The festival drama node whose info we will show.\n            ', tuning_group=GroupNames.CORE)}

    def _run_interaction_gen(self, timeline):
        self.festival_drama_node.show_festival_info()
