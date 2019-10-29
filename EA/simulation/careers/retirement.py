from protocolbuffers.DistributorOps_pb2 import Operationimport protocolbuffersfrom careers.career_mixins import CareerKnowledgeMixinfrom date_and_time import TimeSpanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableReference, TunableRangefrom singletons import DEFAULTfrom tunable_multiplier import TunableMultiplierfrom tunable_time import TunableTimeOfDayfrom ui.ui_dialog_notification import UiDialogNotificationimport alarmsimport date_and_timeimport servicesimport sims4.resources
def _get_notification_tunable_factory(**kwargs):
    return UiDialogNotification.TunableFactory(locked_args={'text_tokens': DEFAULT, 'icon': None, 'secondary_icon': None}, **kwargs)

class Retirement(CareerKnowledgeMixin):
    CAREER_TRACK_RETIRED = TunableReference(description='\n        A carer track for retired Sims. This is used for "Ask about Career"\n        notifications.\n        ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_TRACK))
    DAILY_HOURS_WORKED_FALLBACK = TunableRange(description='\n        If a Sim retires from a career that has no fixed schedule, use this\n        number to compute average hours worked per day.\n        ', tunable_type=float, minimum=1, maximum=24, default=5)
    DAILY_PAY_TIME = TunableTimeOfDay(description='\n        The time of day the retirement payout will be given.\n        ', default_hour=7)
    DAILY_PAY_MULTIPLIER = TunableMultiplier.TunableFactory(description='\n        Multiplier on the average daily pay of the retired career the Sim will\n        get every day.\n        ')
    DAILY_PAY_NOTIFICATION = _get_notification_tunable_factory(description='\n        Message when a Sim receives a retirement payout.\n        ')
    RETIREMENT_NOTIFICATION = _get_notification_tunable_factory(description='\n        Message when a Sim retires.\n        ')
    __slots__ = ('_sim_info', '_career_uid', '_alarm_handle')

    def __init__(self, sim_info, retired_career_uid):
        self._sim_info = sim_info
        self._career_uid = retired_career_uid
        self._alarm_handle = None

    @property
    def current_track_tuning(self):
        return self.CAREER_TRACK_RETIRED

    @property
    def career_uid(self):
        return self._career_uid

    def start(self, send_retirement_notification=False):
        self._add_alarm()
        self._distribute()
        if send_retirement_notification:
            self.send_dialog(Retirement.RETIREMENT_NOTIFICATION)

    def stop(self):
        self._clear_alarm()

    def _add_alarm(self):
        now = services.time_service().sim_now
        time_span = now.time_till_next_day_time(Retirement.DAILY_PAY_TIME)
        if time_span == TimeSpan.ZERO:
            time_span = time_span + TimeSpan(date_and_time.sim_ticks_per_day())
        self._alarm_handle = alarms.add_alarm(self._sim_info, time_span, self._alarm_callback, repeating=False, use_sleep_time=False)

    def _clear_alarm(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _alarm_callback(self, alarm_handle):
        self._add_alarm()
        self.pay_retirement()

    def pay_retirement(self):
        pay = self._get_daily_pay()
        self._sim_info.household.funds.add(pay, protocolbuffers.Consts_pb2.TELEMETRY_MONEY_CAREER, self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS))
        self.send_dialog(Retirement.DAILY_PAY_NOTIFICATION, pay)

    def get_career_text_tokens(self):
        career_level = self._get_career_level_tuning()
        career_track = self._get_career_track_tuning()
        return (career_level.title(self._sim_info), career_track.career_name(self._sim_info), None)

    def _get_career_history(self):
        return self._sim_info.career_tracker.career_history[self._career_uid]

    def _get_career_track_tuning(self):
        history = self._get_career_history()
        return history.career_track

    def _get_career_level_tuning(self):
        history = self._get_career_history()
        track = self._get_career_track_tuning()
        return track.career_levels[history.level]

    def _get_daily_pay(self):
        career_history = self._get_career_history()
        resolver = SingleSimResolver(self._sim_info)
        multiplier = Retirement.DAILY_PAY_MULTIPLIER.get_multiplier(resolver)
        adjusted_pay = int(career_history.daily_pay*multiplier)
        return adjusted_pay

    def send_dialog(self, notification, *additional_tokens, icon_override=None, on_response=None):
        if self._sim_info.is_npc:
            return
        resolver = SingleSimResolver(self._sim_info)
        dialog = notification(self._sim_info, resolver=resolver)
        if dialog is not None:
            track = self._get_career_track_tuning()
            level = self._get_career_level_tuning()
            job = level.title(self._sim_info)
            career = track.career_name(self._sim_info)
            tokens = (job, career) + additional_tokens
            icon_override = IconInfoData(icon_resource=track.icon) if icon_override is None else icon_override
            dialog.show_dialog(additional_tokens=tokens, icon_override=icon_override, secondary_icon_override=IconInfoData(obj_instance=self._sim_info), on_response=on_response)

    def _distribute(self):
        op = protocolbuffers.DistributorOps_pb2.SetCareers()
        with ProtocolBufferRollback(op.careers) as career_op:
            career_history = self._get_career_history()
            career_op.career_uid = self._career_uid
            career_op.career_level = career_history.level
            career_op.career_track = career_history.career_track.guid64
            career_op.user_career_level = career_history.user_level
            career_op.is_retired = True
        distributor = Distributor.instance()
        if distributor is not None:
            distributor.add_op(self._sim_info, GenericProtocolBufferOp(Operation.SET_CAREER, career_op))
