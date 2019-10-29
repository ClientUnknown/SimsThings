from protocolbuffers import Sims_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom aspirations.aspiration_tuning import AspirationBasicfrom aspirations.aspiration_types import AspriationTypefrom buffs.tunable import TunableBuffReferencefrom date_and_time import create_time_span, DateAndTime, TimeSpanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetWithTooltipfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.loot import LootActionsfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableListfrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import constpropertyfrom tunable_time import TunableTimeSpanimport alarmsimport servicesTimedAspirationDefinitionDisplayMixin = get_display_mixin(has_description=True, has_icon=True, use_string_tokens=True, export_modes=ExportModes.All)
class TimedAspiration(TimedAspirationDefinitionDisplayMixin, AspirationBasic):
    INSTANCE_TUNABLES = {'duration': TunableTimeSpan(description='\n            The time that this aspiration is active within the tracker.\n            '), 'on_complete_loot_actions': TunableList(description='\n           List of loots operations that will be awarded when \n           this aspiration complete.\n           ', tunable=LootActions.TunableReference()), 'on_failure_loot_actions': TunableList(description='\n           List of loots operations that will be awarded when \n           this aspiration fails.\n           ', tunable=LootActions.TunableReference()), 'on_cancel_loot_actions': TunableList(description='\n           List of loots operations that will be awarded when \n           this aspiration is cancelled.\n           ', tunable=LootActions.TunableReference()), 'warning_buff': TunableBuffReference(description='\n            The buff that is given to the Sim when the aspiration is getting\n            close to timing out.\n            '), 'tests': TunableTestSetWithTooltip(description='\n            Test set that must pass for this aspiration to be available.\n            ')}

    @constproperty
    def aspiration_type():
        return AspriationType.TIMED_ASPIRATION

    @classmethod
    def apply_on_complete_loot_actions(cls, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot_action in cls.on_complete_loot_actions:
            loot_action.apply_to_resolver(resolver)

    @classmethod
    def apply_on_failure_loot_actions(cls, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot_action in cls.on_failure_loot_actions:
            loot_action.apply_to_resolver(resolver)

    @classmethod
    def apply_on_cancel_loot_actions(cls, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot_action in cls.on_cancel_loot_actions:
            loot_action.apply_to_resolver(resolver)
lock_instance_tunables(TimedAspiration, do_not_register_events_on_load=True)
class TimedAspirationData:

    def __init__(self, tracker, aspiration):
        self._tracker = tracker
        self._aspiration = aspiration
        self._end_time = None
        self._end_alarm_handle = None
        self._warning_alarm_handle = None

    def clear(self):
        self.send_timed_aspiration_to_client(Sims_pb2.TimedAspirationUpdate.REMOVE)
        self._tracker.deactivate_aspiration(self._aspiration)
        if self._end_alarm_handle is not None:
            self._end_alarm_handle.cancel()
            self._end_alarm_handle = None
        if self._warning_alarm_handle is not None:
            self._warning_alarm_handle.cancel()
            self._warning_alarm_handle = None
        self._end_time = None

    def save(self, msg):
        msg.aspiration = self._aspiration.guid64
        msg.end_time = self._end_time.absolute_ticks()

    def load(self, msg):
        now = services.time_service().sim_now
        self._end_time = DateAndTime(msg.end_time)
        time_till_end = self._end_time - now
        if time_till_end <= TimeSpan.ZERO:
            return False
        self._tracker.activate_aspiration(self._aspiration, from_load=True)
        self.send_timed_aspiration_to_client(Sims_pb2.TimedAspirationUpdate.ADD)
        self._end_alarm_handle = alarms.add_alarm(self, time_till_end, self._aspiration_timed_out, cross_zone=True)
        time_till_warning = time_till_end - create_time_span(days=1)
        if time_till_warning > TimeSpan.ZERO:
            self._warning_alarm_handle = alarms.add_alarm(self, time_till_warning, self._give_aspiration_warning, cross_zone=True)
        return True

    def schedule(self):
        now = services.time_service().sim_now
        duration = self._aspiration.duration()
        warning_duration = duration - create_time_span(days=1)
        self._end_time = now + duration
        self._end_alarm_handle = alarms.add_alarm(self, duration, self._aspiration_timed_out, cross_zone=True)
        self._warning_alarm_handle = alarms.add_alarm(self, warning_duration, self._give_aspiration_warning, cross_zone=True)
        self._tracker.activate_aspiration(self._aspiration)
        self.send_timed_aspiration_to_client(Sims_pb2.TimedAspirationUpdate.ADD)

    def complete(self):
        self._aspiration.apply_on_complete_loot_actions(self._tracker.owner_sim_info)
        self._tracker.deactivate_timed_aspiration(self._aspiration)

    def _aspiration_timed_out(self, _):
        self._aspiration.apply_on_failure_loot_actions(self._tracker.owner_sim_info)
        self._tracker.deactivate_timed_aspiration(self._aspiration)

    def _give_aspiration_warning(self, _):
        self._tracker.owner_sim_info.add_buff(self._aspiration.warning_buff.buff_type, buff_reason=self._aspiration.warning_buff.buff_reason)
        self._warning_alarm_handle.cancel()
        self._warning_alarm_handle = None

    def send_timed_aspiration_to_client(self, update_type):
        if services.current_zone().is_zone_shutting_down:
            return
        owner = self._tracker.owner_sim_info
        msg = Sims_pb2.TimedAspirationUpdate()
        msg.update_type = update_type
        msg.sim_id = owner.id
        msg.timed_aspiration_id = self._aspiration.guid64
        if update_type == Sims_pb2.TimedAspirationUpdate.ADD:
            msg.timed_aspiration_end_time = self._end_time.absolute_ticks()
        distributor = Distributor.instance()
        distributor.add_op(owner, GenericProtocolBufferOp(Operation.TIMED_ASPIRATIONS_UPDATE, msg))
