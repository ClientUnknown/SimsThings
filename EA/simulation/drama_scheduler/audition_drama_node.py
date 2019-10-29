import randomfrom protocolbuffers import DistributorOps_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom careers.career_gig import Gigfrom careers.career_tuning import Careerfrom date_and_time import DateAndTime, TimeSpanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom drama_scheduler.drama_node import BaseDramaNodefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable_icon import TunableIconfrom rabbit_hole.rabbit_hole import RabbitHolefrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableTuple, TunableList, Tunable, OptionalTunablefrom sims4.utils import classpropertyfrom tunable_multiplier import TunableMultiplierfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom ui.ui_dialog_picker import ObjectPickerRowimport servicesimport sims4.logAUDITION_TIME_TOKEN = 'audition_time'GIG_TIME_TOKEN = 'gig_time'logger = sims4.log.Logger('AuditionDramaNode', default_owner='bosee')
class AuditionDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'gig': Gig.TunableReference(description='\n            Gig this audition is for.\n            '), 'audition_prep_time': TunableTimeSpan(description='\n            Amount of time between the seed of the potential audition node\n            to the start of the audition time. \n            ', default_hours=5), 'audition_prep_recommendation': TunableLocalizedStringFactory(description='\n            String that gives the player more information on how to succeed\n            in this audition.\n            '), 'audition_prep_icon': OptionalTunable(description='\n            If enabled, this icon will be displayed with the audition preparation.\n            ', tunable=TunableIcon(description='\n                Icon for audition preparation.\n                ')), 'audition_outcomes': TunableList(description='\n            List of loot and multipliers which are for audition outcomes.\n            ', tunable=TunableTuple(description='\n                The information needed to determine whether or not the sim passes\n                or fails this audition. We cannot rely on the outcome of the \n                interaction because we need to run this test on uninstantiated \n                sims as well. This is similar to the fallback outcomes in \n                interactions.\n                ', loot_list=TunableList(description='\n                    Loot applied if this outcome is chosen\n                    ', tunable=LootActions.TunableReference(pack_safe=True)), weight=TunableMultiplier.TunableFactory(description='\n                    A tunable list of tests and multipliers to apply to the \n                    weight of the outcome.\n                    '), is_success=Tunable(description='\n                    Whether or not this is considered a success outcome.\n                    ', tunable_type=bool, default=False))), 'audition_rabbit_hole': RabbitHole.TunableReference(description='\n            Data required to put sim in rabbit hole.\n            '), 'skip_audition': OptionalTunable(description='\n            If enabled, we can skip auditions if sim passes tuned tests.\n            ', tunable=TunableTuple(description='\n                Data related to whether or not this audition can be skipped.\n                ', skip_audition_tests=TunableTestSet(description='\n                    Test to see if sim can skip this audition.\n                    '), skipped_audition_loot=TunableList(description='\n                    Loot applied if sim manages to skip audition\n                    ', tunable=LootActions.TunableReference(pack_safe=True)))), 'advance_notice_time': TunableTimeSpan(description='\n            The amount of time between the alert and the start of the event.\n            ', default_hours=1, locked_args={'days': 0, 'minutes': 0}), 'loot_on_schedule': TunableList(description='\n            Loot applied if the audition drama node is scheduled successfully.\n            ', tunable=LootActions.TunableReference(pack_safe=True)), 'advance_notice_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that is displayed at the advance notice time.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._calculated_audition_time = None
        self._calculated_gig_time = None

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.AUDITION

    @property
    def _require_instanced_sim(self):
        return False

    @classproperty
    def persist_when_active(cls):
        return True

    def get_picker_schedule_time(self):
        return self._calculated_audition_time

    def create_picker_row(self, owner=None, **kwargs):
        now_time = services.game_clock_service().now()
        min_audition_time = now_time + self.audition_prep_time()
        possible_audition_times = self.get_final_times_based_on_schedule(anchor_time=min_audition_time, scheduled_time_only=True)
        audition_time = min_audition_time
        if possible_audition_times is not None:
            now = services.time_service().sim_now
            for possible_audition_time in possible_audition_times:
                if possible_audition_time[0] >= now:
                    audition_time = possible_audition_time[0]
                    break
        gig = self.gig
        time_till_gig = gig.get_time_until_next_possible_gig(audition_time)
        if time_till_gig is None:
            return
        gig_time = audition_time + time_till_gig
        if self.skip_audition and self.skip_audition.skip_audition_tests.run_tests(SingleSimResolver(owner)):
            formatted_string = Career.GIG_PICKER_SKIPPED_AUDITION_LOCALIZATION_FORMAT(gig.gig_pay.lower_bound, gig.gig_pay.upper_bound, gig_time, self.audition_prep_recommendation())
        else:
            formatted_string = Career.GIG_PICKER_LOCALIZATION_FORMAT(gig.gig_pay.lower_bound, gig.gig_pay.upper_bound, audition_time, gig_time, self.audition_prep_recommendation())
        self._calculated_audition_time = audition_time
        self._calculated_gig_time = gig_time
        return gig.create_picker_row(formatted_string, owner)

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO):
        if self.skip_audition and self.skip_audition.skip_audition_tests.run_tests(resolver):
            for loot in self.skip_audition.skipped_audition_loot:
                loot.apply_to_resolver(resolver)
            resolver.sim_info_to_test.career_tracker.set_gig(self.gig, self._calculated_gig_time)
            return False
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier)
        if success:
            services.calendar_service().mark_on_calendar(self, advance_notice_time=self.advance_notice_time())
            self._send_career_ui_update(is_add=True)
            for loot in self.loot_on_schedule:
                loot.apply_to_resolver(resolver)
        return success

    def cleanup(self, from_service_stop=False):
        services.calendar_service().remove_on_calendar(self.uid)
        self._send_career_ui_update(is_add=False)
        rabbit_hole_service = services.get_rabbit_hole_service()
        if rabbit_hole_service.is_in_rabbit_hole(self._receiver_sim_info.id):
            rabbit_hole_service.remove_rabbit_hole_expiration_callback(self._receiver_sim_info, self._on_sim_return)
        super().cleanup(from_service_stop=from_service_stop)

    def resume(self):
        if not services.get_rabbit_hole_service().is_in_rabbit_hole(self._receiver_sim_info.id):
            services.drama_scheduler_service().complete_node(self.uid)

    def _run(self):
        rabbit_hole_service = services.get_rabbit_hole_service()
        rabbit_hole_service.put_sim_in_managed_rabbithole(self._receiver_sim_info, self.audition_rabbit_hole)
        rabbit_hole_service.set_rabbit_hole_expiration_callback(self._receiver_sim_info, self._on_sim_return)
        return False

    def _on_sim_return(self, canceled=False):
        receiver_sim_info = self._receiver_sim_info
        resolver = SingleSimResolver(receiver_sim_info)
        weights = []
        failure_outcomes = []
        for outcome in self.audition_outcomes:
            if canceled:
                if not outcome.is_success:
                    failure_outcomes.append(outcome)
                    weight = outcome.weight.get_multiplier(resolver)
                    if weight > 0:
                        weights.append((weight, outcome))
            else:
                weight = outcome.weight.get_multiplier(resolver)
                if weight > 0:
                    weights.append((weight, outcome))
        if failure_outcomes:
            selected_outcome = random.choice(failure_outcomes)
        else:
            selected_outcome = sims4.random.weighted_random_item(weights)
        if not selected_outcome:
            logger.error('No valid outcome is tuned on this audition. Verify weights in audition_outcome for {}.', self.guid64)
            services.drama_scheduler_service().complete_node(self.uid)
            return
        if selected_outcome.is_success:
            receiver_sim_info.career_tracker.set_gig(self.gig, self._calculated_gig_time)
        for loot in selected_outcome.loot_list:
            loot.apply_to_resolver(resolver)
        services.drama_scheduler_service().complete_node(self.uid)

    def _save_custom_data(self, writer):
        if self._calculated_audition_time is not None:
            writer.write_uint64(AUDITION_TIME_TOKEN, self._calculated_audition_time)
        if self._calculated_gig_time is not None:
            writer.write_uint64(GIG_TIME_TOKEN, self._calculated_gig_time)

    def _load_custom_data(self, reader):
        self._calculated_audition_time = DateAndTime(reader.read_uint64(AUDITION_TIME_TOKEN, None))
        self._calculated_gig_time = DateAndTime(reader.read_uint64(GIG_TIME_TOKEN, None))
        rabbit_hole_service = services.get_rabbit_hole_service()
        if rabbit_hole_service.is_in_rabbit_hole(self._receiver_sim_info.id):
            rabbit_hole_service.set_rabbit_hole_expiration_callback(self._receiver_sim_info, self._on_sim_return)
        self._send_career_ui_update()
        return True

    def _send_career_ui_update(self, is_add=True):
        audition_update_msg = DistributorOps_pb2.AuditionUpdate()
        if is_add:
            self.gig.build_gig_msg(audition_update_msg.audition_info, self._receiver_sim_info, gig_time=self._calculated_gig_time, audition_time=self._calculated_audition_time)
        op = GenericProtocolBufferOp(Operation.AUDITION_UPDATE, audition_update_msg)
        build_icon_info_msg(IconInfoData(icon_resource=self.audition_prep_icon), self.audition_prep_recommendation(), audition_update_msg.recommended_task)
        Distributor.instance().add_op(self._receiver_sim_info, op)

    def load(self, drama_node_proto, schedule_alarm=True):
        super_success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if not super_success:
            return False
        services.calendar_service().mark_on_calendar(self, advance_notice_time=self.advance_notice_time())
        return True

    def on_calendar_alert_alarm(self):
        receiver_sim_info = self._receiver_sim_info
        resolver = SingleSimResolver(receiver_sim_info)
        dialog = self.advance_notice_notification(receiver_sim_info, resolver=resolver)
        dialog.show_dialog()
