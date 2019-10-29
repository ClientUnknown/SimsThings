from protocolbuffers import Situations_pb2from distributor.ops import SituationMeterUpdateOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.tuning.tunable import AutoFactoryInit, TunableReference, HasTunableSingletonFactory, Tunable, TunableList, TunableTuple, OptionalTunablefrom snippets import TunableColorSnippetimport services
class SituationMeterData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'_meter_id': Tunable(description='\n            Meter ID used by UI to differentiate meters from each other\n            (when multiple meters exist in a situation).\n            \n            This will typically be assigned by a GPE in code as opposed to tuned.\n            ', tunable_type=bool, default=True), '_threshold_data': TunableList(description='\n            List of thresholds for this meter.\n            ', tunable=TunableTuple(color=TunableColorSnippet(description='\n                    Color of meter at this specified threshold.\n                    \n                    Note: alpha value is not used.\n                    '), threshold_value=Tunable(description='\n                    Value at or above which this threshold exists. \n                    ', tunable_type=int, default=0))), '_display_text': OptionalTunable(description='\n            Optional meter display text.\n            ', tunable=TunableLocalizedString()), '_tooltip': OptionalTunable(description='\n            Optional tooltip text.\n            ', tunable=TunableLocalizedString())}

    def build_data_message(self, msg):
        msg.meter_id = self._meter_id
        display_text = self._display_text
        if display_text is not None:
            msg.meter_text = display_text
        tooltip = self._tooltip
        if tooltip is not None:
            msg.meter_tooltip = tooltip
        self._build_meter_threshold_data(msg.thresholds)

    def _build_meter_threshold_data(self, msg):
        for threshold in self._threshold_data:
            with ProtocolBufferRollback(msg) as threshold_msg:
                threshold_msg.color = threshold.color
                threshold_msg.threshold = threshold.threshold_value

    def create_meter(self, situation):
        return SituationMeter(situation, self._meter_id)

class ValueBasedSituationMeterData(SituationMeterData):
    FACTORY_TUNABLES = {'_min_value': Tunable(description='\n            Minimum value of the meter.\n            ', tunable_type=int, default=0), '_max_value': Tunable(description='\n            Maximum value of the meter.\n            ', tunable_type=int, default=100)}

    def build_data_message(self, msg):
        super().build_data_message(msg)
        msg.minimum_value = self._min_value
        msg.maximum_value = self._max_value

class StatBasedSituationMeterData(SituationMeterData):
    FACTORY_TUNABLES = {'stat': TunableReference(description='\n            Statistic this meter is based off of.\n            ', manager=services.get_instance_manager(Types.STATISTIC)), 'auto_update_on_stat_change': Tunable(description='\n            If set, the meter will automatically update when the associated\n            stat changes.  Unset this for cases when you want the situation\n            to control when the meter changes.\n            ', tunable_type=bool, default=True)}

    def build_data_message(self, msg):
        super().build_data_message(msg)
        msg.minimum_value = self.stat.min_value
        msg.maximum_value = self.stat.max_value

    def create_meter_with_sim_info(self, situation, sim_info):
        return StatBasedSituationMeter(situation, self._meter_id, sim_info.get_stat_instance(self.stat, add=True), auto_update=self.auto_update_on_stat_change)

class SituationMeter:

    def __init__(self, situation, meter_id):
        self._situation = situation
        self._meter_id = meter_id
        self._dirty = True

    def destroy(self):
        self._situation = None

    def _create_update_message(self):
        msg = Situations_pb2.SituationMeterUpdate()
        msg.situation_id = self._situation.id
        msg.meter_id = self._meter_id
        msg.update_value = self._situation._get_effective_score_for_levels(self._situation._score)
        return msg

    def send_update_if_dirty(self):
        if not self._dirty:
            return
        self.send_update()
        self._dirty = False

    def send_update(self):
        if self._situation is None:
            return
        if self._situation.is_user_facing and services.get_zone_situation_manager().is_distributed(self._situation):
            distributor = Distributor.instance()
            op = SituationMeterUpdateOp(self._create_update_message())
            distributor.add_op(self._situation, op)

class StatBasedSituationMeter(SituationMeter):

    def __init__(self, situation, meter_id, stat_inst, *args, auto_update=True, **kwargs):
        super().__init__(situation, meter_id, *args, **kwargs)
        self._stat_inst = stat_inst
        self._auto_update = auto_update
        self._watcher_handle = self._stat_inst.tracker.add_watcher(self._on_stat_change)

    def destroy(self):
        super().destroy()
        self._stat_inst.tracker.remove_watcher(self._watcher_handle)
        self._watcher_handle = None
        self._stat_inst = None

    def _on_stat_change(self, stat_type, old_value, new_value):
        self._dirty = True
        if self._auto_update:
            self.send_update_if_dirty()

    def _create_update_message(self):
        msg = Situations_pb2.SituationMeterUpdate()
        msg.situation_id = self._situation.id
        msg.meter_id = self._meter_id
        msg.update_value = int(self._stat_inst.get_value())
        return msg
