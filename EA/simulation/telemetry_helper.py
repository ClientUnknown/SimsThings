import collectionsfrom date_and_time import create_time_spanfrom objects import ALL_HIDDEN_REASONSfrom sims4.telemetry import RuleActionfrom sims4.tuning.tunable import Tunable, TunableRange, TunableList, TunableTuple, TunableEnumEntryimport alarmsimport enumimport objects.componentsimport servicesimport sims4.telemetryTELEMETRY_GROUP_REPORT = 'REPO'TELEMETRY_HOOK_EMOTION_REPORT = 'EMOT'TELEMETRY_HOOK_FUNDS_REPORT = 'FUND'TELEMETRY_HOOK_RELATIONSHIP_REPORT = 'RELA'TELEMETRY_TARGET_SIM_ID = 'tsim'TELEMETRY_REL_BIT_ID = 'biid'TELEMETRY_REL_BIT_COUNT = 'cico'TELEMETRY_EMOTION_ID = 'emot'TELEMETRY_EMOTION_INTENSITY = 'inte'TELEMETRY_HOUSEHOLD_FUNDS = 'fund'report_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_REPORT)
class TelemetrySimClassification(enum.Int, export=False):
    IS_ACTIVE_SIM = 1
    IS_IN_ACTIVE_FAMILY = 2
    IS_PLAYED_SIM = 3
    IS_NPC_SIM = 4
    IS_ACTIVE_GHOST = 5
    IS_GHOST_IN_ACTIVE_FAMILY = 6

def _classify_sim(sim_info, household):
    if not household.is_player_household:
        return TelemetrySimClassification.IS_NPC_SIM
    if household.is_played_household:
        return TelemetrySimClassification.IS_PLAYED_SIM
    if sim_info is services.active_sim_info():
        if sim_info.is_ghost:
            return TelemetrySimClassification.IS_ACTIVE_GHOST
        return TelemetrySimClassification.IS_ACTIVE_SIM
    if sim_info is not None and sim_info.is_ghost:
        return TelemetrySimClassification.IS_GHOST_IN_ACTIVE_FAMILY
    return TelemetrySimClassification.IS_IN_ACTIVE_FAMILY

def _write_common_data(hook, sim_info=None, household=None, session_id=None, record_position=False):
    sim_id = 0
    sim_mood = 0
    occult_types = 0
    current_occult_types = 0
    sim_position = None
    sim_classification = 0
    household_id = 0
    if sim_info is not None:
        if sim_info.is_npc:
            hook.disabled_hook = True
        sim_id = sim_info.id
        if hook.valid_for_npc or household is None:
            household = sim_info.household
        if sim_info.has_component(objects.components.types.BUFF_COMPONENT):
            mood = sim_info.get_mood()
            if mood is not None:
                sim_mood = mood.guid64
        occult_types = sim_info.occult_types
        current_occult_types = sim_info.current_occult_types
        if record_position:
            sim = sim_info.get_sim_instance()
            if sim is not None:
                sim_position = sim.position
    if household is not None:
        household_id = household.id
        account = household.account
        if sim_info is not None:
            sim_classification = int(_classify_sim(sim_info, household))
        if session_id is None:
            zone_id = services.current_zone_id()
            if zone_id is not None:
                client = account.get_client(zone_id)
                if client is not None:
                    session_id = client.id
    if session_id is None:
        session_id = 0
    game_clock_service = services.game_clock_service()
    game_time = int(game_clock_service.now().absolute_seconds())
    sims4.telemetry._write_common_data(hook, sim_id, household_id, session_id, game_time, sim_mood, sim_classification, occult_types, current_occult_types, sim_position)

def begin_hook(writer, hook_tag, valid_for_npc=False, sim=None, sim_info=None, **kwargs):
    hook = writer.begin_hook(hook_tag, valid_for_npc=valid_for_npc)
    if sim is not None:
        sim_info = sim.sim_info
    _write_common_data(hook, sim_info=sim_info, **kwargs)
    return hook

class TelemetryTuning:
    BUFF_ALARM_TIME = TunableRange(description="\n        Integer value in sim minutes in which the buff alarm will trigger to \n        send a telemetry report of current active buff's on the household sims.\n        ", tunable_type=int, minimum=1, default=60)
    EMOTION_REL_ALARM_TIME = TunableRange(description='\n        Integer value in sim minutes in which the emotion and relationship \n        alarm will trigger to send a telemetry report of the emotion and \n        relationship status of the household sims.\n        ', tunable_type=int, minimum=1, default=60)
    HOOK_ACTIONS = TunableList(description='\n        List of hook actions that we want to drop or collect to create rules \n        to disable them from triggering.\n        ', tunable=TunableTuple(description='\n            Hook actions.\n            ', module_tag=Tunable(description="\n                Module identifier of the hook where the action should be \n                applied.\n                Can be empty if we want to apply an action by only group or \n                hook tag. \n                e.g. 'GAME'.  \n                ", tunable_type=str, default=''), group_tag=Tunable(description="\n                Group identifier of the hook where the action should be \n                applied.\n                Can be empty if we want to apply an action by only module or \n                hook tag.\n                e.g. 'WHIM'\n                ", tunable_type=str, default=''), hook_tag=Tunable(description="\n                Tag identifier of the hook where the action should be \n                applied.\n                Can be empty if we want to apply an action by only module or \n                group tag.\n                e.g. 'WADD'\n                ", tunable_type=str, default=''), priority=Tunable(description="\n                Priority for this rule to apply.  The rules are sorted in \n                priority order (lowest priority first).  The the first rule \n                that matches a hook causes the hook to be blocked or collected, \n                depending on the value of action. \n                e.g. We can have an action to COLLECT hook {GAME, WHIM, WADD} \n                with priority 0, and an action to DROP hooks with module 'GAME'\n                {GAME, '', ''} with priority 1, this means the collected hook\n                action will have more importance than the rule to drop all \n                GAME hooks.                \n                ", tunable_type=int, default=0), action=TunableEnumEntry(description='\n                Action to take for the specified tags. \n                COLLECT to enable the hook.\n                DROP to disable the hook.\n                ', tunable_type=RuleAction, default=RuleAction.DROP)))

    @classmethod
    def filter_tunable_hooks(cls):
        for hook in TelemetryTuning.HOOK_ACTIONS:
            module_tag = hook.module_tag
            group_tag = hook.group_tag
            hook_tag = hook.hook_tag
            if module_tag == '':
                module_tag = None
            if group_tag == '':
                group_tag = None
            if hook_tag == '':
                hook_tag = None
            sims4.telemetry.add_filter_rule(hook.priority, module_tag, group_tag, hook_tag, None, hook.action)

class HouseholdTelemetryTracker:

    def __init__(self, household):
        self._buff_alarm = None
        self._emotion_relationship_alarm = None
        self._household = household

    def initialize_alarms(self):
        if self._buff_alarm is not None:
            alarms.cancel_alarm(self._buff_alarm)
        self._buff_alarm = alarms.add_alarm(self, create_time_span(minutes=TelemetryTuning.BUFF_ALARM_TIME), self.buff_telemetry_report, True)
        if self._emotion_relationship_alarm is not None:
            alarms.cancel_alarm(self._emotion_relationship_alarm)
        self._emotion_relationship_alarm = alarms.add_alarm(self, create_time_span(minutes=TelemetryTuning.EMOTION_REL_ALARM_TIME), self.emotion_relation_telemetry_report, True)

    def buff_telemetry_report(self, handle):
        for sim in self._household.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
            with begin_hook(report_telemetry_writer, TELEMETRY_HOOK_EMOTION_REPORT, sim=sim) as hook:
                hook.write_guid(TELEMETRY_EMOTION_ID, sim.get_mood().guid64)
                hook.write_int(TELEMETRY_EMOTION_INTENSITY, sim.get_mood_intensity())

    def emotion_relation_telemetry_report(self, handle):
        household_bit_dict = collections.defaultdict(lambda : 0)
        for sim in self._household.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
            for bit in sim.sim_info.relationship_tracker.get_all_bits():
                household_bit_dict[bit.guid64] += 1
        for (bit_id, bit_count) in household_bit_dict.items():
            with begin_hook(report_telemetry_writer, TELEMETRY_HOOK_RELATIONSHIP_REPORT, household=self._household) as hook:
                hook.write_guid(TELEMETRY_REL_BIT_ID, bit_id)
                hook.write_int(TELEMETRY_REL_BIT_COUNT, bit_count)
        with begin_hook(report_telemetry_writer, TELEMETRY_HOOK_FUNDS_REPORT, household=self._household) as hook:
            hook.write_int(TELEMETRY_HOUSEHOLD_FUNDS, self._household.funds.money)

    def on_client_disconnect(self):
        if self._buff_alarm is not None:
            alarms.cancel_alarm(self._buff_alarm)
            self._buff_alarm = None
        if self._emotion_relationship_alarm is not None:
            alarms.cancel_alarm(self._emotion_relationship_alarm)
            self._emotion_relationship_alarm = None
