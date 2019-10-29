from protocolbuffers.ResourceKey_pb2 import ResourceKeyfrom audio.primitive import TunablePlayAudiofrom careers.career_base import EvaluationResult, Evaluationfrom careers.career_enums import GigResultfrom careers.career_tuning import _get_career_notification_tunable_factoryfrom careers.prep_tasks.prep_task import PrepTaskfrom careers.prep_tasks.prep_task_tracker_mixin import PrepTaskTrackerMixinfrom date_and_time import DateAndTimefrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.tests import TunableTestSetfrom filters.tunable import TunableSimFilterfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable_icon import TunableIconfrom relationships.relationship_bit import RelationshipBit, RelationshipBitCollectionUidfrom scheduler import WeeklySchedulefrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableInterval, TunableList, TunableReference, TunableTuple, OptionalTunable, TunableEnumEntry, Tunable, TunableMapping, TunableVariant, TunableIntervalLiteral, TunableRangefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import flexmethodfrom situations.situation_types import SituationMedalfrom tunable_multiplier import TunableMultiplierfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog_labeled_icons import UiDialogLabeledIconsfrom ui.ui_dialog_picker import ObjectPickerRow, OddJobPickerRowimport randomimport servicesimport sims4logger = sims4.log.Logger('Gig', default_owner='bosee')_GigDisplayMixin = get_display_mixin(has_description=True, has_icon=True, use_string_tokens=True)
class Gig(HasTunableReference, _GigDisplayMixin, PrepTaskTrackerMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.CAREER_GIG)):
    INSTANCE_TUNABLES = {'career': TunableReference(description='\n            The career this gig is associated with.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'gig_time': WeeklySchedule.TunableFactory(description='\n            A tunable schedule that will determine when you have to be at work.\n            ', export_modes=ExportModes.All), 'gig_prep_time': TunableTimeSpan(description='\n            The amount of time between when a gig is selected and when it\n            occurs.\n            ', default_hours=5), 'gig_prep_tasks': TunableList(description='\n            A list of prep tasks the Sim can do to improve their performance\n            during the gig. \n            ', tunable=PrepTask.TunableFactory()), 'loots_on_schedule': TunableList(description='\n            Loot actions to apply when a sim gets a gig.\n            ', tunable=LootActions.TunableReference()), 'audio_on_prep_task_completion': OptionalTunable(description='\n            A sting to play at the time a prep task completes.\n            ', tunable=TunablePlayAudio(locked_args={'immediate': True, 'joint_name_hash': None, 'play_on_active_sim_only': True})), 'gig_pay': TunableVariant(description='\n            Base amount of pay for this gig. Can be either a flat amount or a\n            range.\n            ', range=TunableInterval(tunable_type=int, default_lower=0, default_upper=100, minimum=0), flat_amount=TunableIntervalLiteral(tunable_type=int, default=0, minimum=0), default='range'), 'additional_pay_per_overmax_level': OptionalTunable(description='\n            If checked, overmax levels will be considered when calculating pay\n            for this gig. The actual implementation of this may vary by gig\n            type.\n            ', tunable=TunableRange(tunable_type=int, default=0, minimum=0)), 'result_based_gig_pay_multipliers': OptionalTunable(description='\n            A set of multipliers for gig pay. The multiplier used depends on the\n            GigResult of the gig. The meanings of each GigResult may vary by\n            gig type.\n            ', tunable=TunableMapping(description='\n                A map between the result type of the gig and the additional pay\n                the sim will receive.\n                ', key_type=TunableEnumEntry(tunable_type=GigResult, default=GigResult.SUCCESS), value_type=TunableMultiplier.TunableFactory())), 'initial_result_based_career_performance': OptionalTunable(description="\n            A mapping between the GigResult for this gig and the initial\n            career performance for the Sim's first gig.\n            ", tunable=TunableMapping(description='\n                A map between the result type of the gig and the initial career\n                performance the Sim will receive.\n                ', key_type=TunableEnumEntry(description='\n                    The GigResult enum that represents the outcome of the Gig.\n                    ', tunable_type=GigResult, default=GigResult.SUCCESS), value_type=Tunable(description='\n                    The initial performance value that will be applied.\n                    ', tunable_type=float, default=0))), 'result_based_career_performance': OptionalTunable(description='\n            A mapping between the GigResult for this gig and the change in\n            career performance for the sim.\n            ', tunable=TunableMapping(description='\n                A map between the result type of the gig and the career\n                performance the sim will receive.\n                ', key_type=TunableEnumEntry(description='\n                    The GigResult enum that represents the outcome of the Gig.\n                    ', tunable_type=GigResult, default=GigResult.SUCCESS), value_type=Tunable(description='\n                    The performance modification.\n                    ', tunable_type=float, default=0))), 'result_based_career_performance_multiplier': OptionalTunable(description='\n            A mapping between the GigResult and the multiplier for the career \n            performance awarded.\n            ', tunable=TunableMapping(description='\n                A map between the result type of the gig and the career\n                performance multiplier.\n                ', key_type=TunableEnumEntry(description='\n                    The GigResult enum that represents the outcome of the Gig.\n                    ', tunable_type=GigResult, default=GigResult.SUCCESS), value_type=TunableMultiplier.TunableFactory(description='\n                    The performance modification multiplier.\n                    '))), 'result_based_loots': OptionalTunable(description='\n            A mapping between the GigResult for this gig and a loot list to\n            optionally apply. The resolver for this loot list is either a\n            SingleSimResolver of the working sim or a DoubleSimResolver with the\n            target being the customer if there is a customer sim.\n            ', tunable=TunableMapping(description='\n                A map between the result type of the gig and the loot list.\n                ', key_type=TunableEnumEntry(tunable_type=GigResult, default=GigResult.SUCCESS), value_type=TunableList(description='\n                    Loot actions to apply.\n                    ', tunable=LootActions.TunableReference(description='\n                        The loot action applied.\n                        ', pack_safe=True)))), 'payout_stat_data': TunableMapping(description='\n            Stats, and its associated information, that are gained (or lost) \n            when sim finishes this gig.\n            ', key_type=TunableReference(description='\n                Stat for this payout.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), value_type=TunableTuple(description='\n                Data about this payout stat. \n                ', base_amount=Tunable(description='\n                    Base amount (pre-modifiers) applied to the sim at the end\n                    of the gig.\n                    ', tunable_type=float, default=0.0), medal_to_payout=TunableMapping(description='\n                    Mapping of medal -> stat multiplier.\n                    ', key_type=TunableEnumEntry(description='\n                        Medal achieved in this gig.\n                        ', tunable_type=SituationMedal, default=SituationMedal.TIN), value_type=TunableMultiplier.TunableFactory(description='\n                        Mulitiplier on statistic payout if scorable situation\n                        ends with the associate medal.\n                        ')), ui_threshold=TunableList(description='\n                    Thresholds and icons we use for this stat to display in \n                    the end of day dialog. Tune in reverse of highest threshold \n                    to lowest threshold.\n                    ', tunable=TunableTuple(description='\n                        Threshold and icon for this stat and this gig.\n                        ', threshold_icon=TunableIcon(description='\n                            Icon if the stat is of this threshold.\n                            '), threshold_description=TunableLocalizedStringFactory(description='\n                            Description to use with icon\n                            '), threshold=Tunable(description='\n                            Threshold that the stat must >= to.\n                            ', tunable_type=float, default=0.0))))), 'career_events': TunableList(description='\n             A list of available career events for this gig.\n             ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CAREER_EVENT))), 'gig_cast_rel_bit_collection_id': TunableEnumEntry(description='\n            If a rel bit is applied to the cast member, it must be of this collection id.\n            We use this to clear the rel bit when the gig is over.\n            ', tunable_type=RelationshipBitCollectionUid, default=RelationshipBitCollectionUid.Invalid, invalid_enums=(RelationshipBitCollectionUid.All,)), 'gig_cast': TunableList(description='\n            This is the list of sims that need to spawn for this gig. \n            ', tunable=TunableTuple(description='\n                Data for cast members. It contains a test which tests against \n                the owner of this gig and spawn the necessary sims. A bit\n                may be applied through the loot action to determine the type \n                of cast members (costars, directors, etc...) \n                ', filter_test=TunableTestSet(description='\n                    Test used on owner sim.\n                    '), sim_filter=TunableSimFilter.TunableReference(description='\n                    If filter test is passed, this sim is created and stored.\n                    '), cast_member_rel_bit=OptionalTunable(description='\n                    If tuned, this rel bit will be applied on the spawned cast \n                    member.\n                    ', tunable=RelationshipBit.TunableReference(description='\n                        Rel bit to apply.\n                        ')))), 'end_of_gig_dialog': OptionalTunable(description='\n            A results dialog to show. This dialog allows a list\n            of icons with labels. Stats are added at the end of this icons.\n            ', tunable=UiDialogLabeledIcons.TunableFactory()), 'disabled_tooltip': OptionalTunable(description='\n            If tuned, the tooltip when this row is disabled.\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.UI), 'end_of_gig_notifications': OptionalTunable(description='\n            If enabled, a notification to show at the end of the gig instead of\n            a normal career message. Tokens are:\n            * 0: The Sim owner of the career\n            * 1: The level name (e.g. Chef)\n            * 2: The career name (e.g. Culinary)\n            * 3: The company name (e.g. Maids United)\n            * 4: The pay for the gig\n            * 5: The gratuity for the gig\n            * 6: The customer (sim) of the gig, if there is a customer.\n            * 7: A bullet list of loots and payments as a result of this gig.\n                 This list uses the text tuned on the loots themselves to create\n                 bullets for each loot. Those texts will generally have tokens 0\n                 and 1 be the subject and target sims (of the loot) but may\n                 have additional tokens depending on the type of loot.\n            ', tunable=TunableMapping(description='\n                A map between the result type of the gig and the post-gig\n                notification.\n                ', key_type=TunableEnumEntry(tunable_type=GigResult, default=GigResult.SUCCESS), value_type=_get_career_notification_tunable_factory()), tuning_group=GroupNames.UI), 'end_of_gig_overmax_notification': OptionalTunable(description='\n            If tuned, the notification that will be used if the sim gains an\n            overmax level during this gig. Will override the overmax\n            notification in career messages. The following tokens are provided:\n            * 0: The Sim owner of the career\n            * 1: The level name (e.g. Chef)\n            * 2: The career name (e.g. Culinary)\n            * 3: The company name (e.g. Maids United)\n            * 4: The overmax level\n            * 5: The pay for the gig\n            * 6: Additional pay tuned at additional_pay_per_overmax_level \n            * 7: The overmax rewards in a bullet-point list, in the form of a\n                 string. These are tuned on the career_track\n            ', tunable=_get_career_notification_tunable_factory(), tuning_group=GroupNames.UI), 'end_of_gig_overmax_rewardless_notification': OptionalTunable(description='\n            If tuned, the notification that will be used if the sim gains an\n            overmax level with no reward during this gig. Will override the\n            overmax rewardless notification in career messages.The following\n            tokens are provided:\n            * 0: The Sim owner of the career\n            * 1: The level name (e.g. Chef)\n            * 2: The career name (e.g. Culinary)\n            * 3: The company name (e.g. Maids United)\n            * 4: The overmax level\n            * 5: The pay for the gig\n            * 6: Additional pay tuned at additional_pay_per_overmax_level \n            ', tunable=_get_career_notification_tunable_factory(), tuning_group=GroupNames.UI), 'end_of_gig_promotion_text': OptionalTunable(description='\n            A string that, if enabled, will be pre-pended to the bullet\n            list of results in the promotion notification. Tokens are:\n            * 0 : The Sim owner of the career\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.UI), 'end_of_gig_demotion_text': OptionalTunable(description='\n            A string that, if enabled, will be pre-pended to the bullet\n            list of results in the promotion notification. Tokens are:\n            * 0 : The Sim owner of the career\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.UI), 'odd_job_tuning': OptionalTunable(description='\n            Tuning specific to odd jobs. Leave untuned if this gig is not an\n            odd job.\n            ', tunable=TunableTuple(customer_description=TunableLocalizedStringFactory(description='\n                    The description of the odd job written by the customer.\n                    Token 0 is the customer sim.\n                    '), use_customer_description_as_gig_description=Tunable(description='\n                    If checked, the customer description will be used as the\n                    gig description. This description is used as the tooltip\n                    for the gig icon in the career panel.\n                    ', tunable_type=bool, default=False), result_based_gig_gratuity_multipliers=TunableMapping(description='\n                    A set of multipliers for the gig gratuity.  This maps the\n                    result type of the gig and the gratuity multiplier (a \n                    percentage).  The base pay will be multiplied by this \n                    multiplier in order to determine the actual gratuity \n                    amount.\n                    ', key_type=TunableEnumEntry(description='\n                        The GigResult enum that represents the outcome of the \n                        Gig.\n                        ', tunable_type=GigResult, default=GigResult.SUCCESS), value_type=TunableMultiplier.TunableFactory(description='\n                        The gratuity multiplier to be calculated for this \n                        GigResult.\n                        ')), result_based_gig_gratuity_chance_multipliers=TunableMapping(description='\n                    A set of multipliers for determining the gig gratuity \n                    chance (i.e., the probability the Sim will receive gratuity \n                    in addition to the base pay).  The gratuity chance depends \n                    on the GigResult of the gig.  This maps the result type of \n                    the gig and the gratuity chance/percentage.  If this map\n                    (or a GigResult) is left untuned, then no gratuity is \n                    added.\n                    ', key_type=TunableEnumEntry(description='\n                        The GigResult enum that represents the outcome of the \n                        Gig.\n                        ', tunable_type=GigResult, default=GigResult.SUCCESS), value_type=TunableMultiplier.TunableFactory(description='\n                        The multiplier to be calculated for this GigResult.  \n                        This represents the percentage chance the Sim will \n                        receive gratuity.  If the Sim is to not receive \n                        gratuity, the base value should be 0 (without further\n                        tests).  If this Sim is guaranteed to receive gratuity,\n                        the base value should be 1 (without further tests).\n                        ')), gig_gratuity_bullet_point_text=OptionalTunable(description='\n                    If enabled, the gig gratuity will be a bullet point in the\n                    bullet pointed list of loots and money supplied to the end\n                    of gig notification (this is token 7 of that notification).\n                    If disabled, gratuity will be omitted from that list.\n                    Tokens:\n                    * 0: The sim owner of the career\n                    * 1: The customer\n                    * 2: the gratuity amount \n                    ', tunable=TunableLocalizedStringFactory()))), 'tip': OptionalTunable(description='\n            A tip that is displayed with the gig in pickers and in the career\n            panel. Can produce something like "Required Skill: Fitness 2".\n            ', tunable=TunableTuple(tip_title=TunableLocalizedStringFactory(description='\n                    The title string of the tip. Could be something like "Required\n                    Skill.\n                    '), tip_text=TunableLocalizedStringFactory(description='\n                    The text string of the tip. Could be something like "Fitness 2".\n                    '), tip_icon=OptionalTunable(tunable=TunableIcon(description='\n                        An icon to show along with the tip.\n                        ')))), 'critical_failure_test': OptionalTunable(description='\n            The tests for checking whether or not the Sim should receive the \n            CRITICAL_FAILURE outcome.  This will override other GigResult \n            behavior.\n            ', tunable=TunableTestSet(description='\n                The tests to be performed on the Sim (and any customer).  If \n                the tests pass, the outcome will be CRITICAL_FAILURE.  \n                '))}

    def __init__(self, owner, customer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._customer_id = customer.id if customer is not None else None
        self._upcoming_gig_time = None
        self._gig_result = None
        self._gig_pay = None
        self._gig_gratuity = None
        self._loot_strings = None
        self._gig_attended = False

    @classmethod
    def get_aspiration(cls):
        pass

    @classmethod
    def get_time_until_next_possible_gig(cls, starting_time):
        required_prep_time = cls.gig_prep_time()
        start_considering_prep = starting_time + required_prep_time
        (time_until, _) = cls.gig_time().time_until_next_scheduled_event(start_considering_prep)
        if not time_until:
            return
        return time_until + required_prep_time

    def notify_gig_attended(self):
        self._gig_attended = True

    def has_attended_gig(self):
        return self._gig_attended

    def notify_canceled(self):
        self._gig_result = GigResult.CANCELED

    def get_career_performance(self, first_gig=False):
        if not self.result_based_career_performance:
            return 0
        if self.initial_result_based_career_performance is not None and first_gig and self._gig_result in self.initial_result_based_career_performance:
            return self.initial_result_based_career_performance[self._gig_result]
        performance_modifier = 1
        if self._gig_result in self.result_based_career_performance_multiplier:
            resolver = self.get_resolver_for_gig()
            performance_modifier = self.result_based_career_performance_multiplier[self._gig_result].get_multiplier(resolver)
        return self.result_based_career_performance.get(self._gig_result, 0)*performance_modifier

    def treat_work_time_as_due_date(self):
        return False

    @classmethod
    def create_picker_row(cls, description=None, scheduled_time=None, owner=None, gig_customer=None, enabled=True, **kwargs):
        tip = cls.tip
        description = cls.gig_picker_localization_format(cls.gig_pay.lower_bound, cls.gig_pay.upper_bound, scheduled_time, tip.tip_title(), tip.tip_text(), gig_customer)
        if enabled or cls.disabled_tooltip is not None:
            row_tooltip = lambda *_: cls.disabled_tooltip(owner)
        elif cls.display_description is None:
            row_tooltip = None
        else:
            row_tooltip = lambda *_: cls.display_description(owner)
        if cls.odd_job_tuning is not None:
            customer_description = cls.odd_job_tuning.customer_description(gig_customer)
            row = OddJobPickerRow(customer_id=gig_customer.id, customer_description=customer_description, tip_title=tip.tip_title(), tip_text=tip.tip_text(), tip_icon=tip.tip_icon, name=cls.display_name(owner), icon=cls.display_icon, row_description=description, row_tooltip=row_tooltip, is_enable=enabled)
        else:
            row = ObjectPickerRow(name=cls.display_name(owner), icon=cls.display_icon, row_description=description, row_tooltip=row_tooltip, is_enable=enabled)
        return row

    def get_gig_time(self):
        return self._upcoming_gig_time

    def get_gig_customer(self):
        return self._customer_id

    def clean_up_gig(self):
        if self.gig_prep_tasks:
            self.prep_task_cleanup()

    def save_gig(self, gig_proto_buff):
        gig_proto_buff.gig_type = self.guid64
        gig_proto_buff.gig_time = self._upcoming_gig_time
        if hasattr(gig_proto_buff, 'gig_attended'):
            gig_proto_buff.gig_attended = self._gig_attended
        if self._customer_id:
            gig_proto_buff.customer_sim_id = self._customer_id

    def load_gig(self, gig_proto_buff):
        self._upcoming_gig_time = DateAndTime(gig_proto_buff.gig_time)
        if self.gig_prep_tasks:
            self.prep_time_start(self._owner, self.gig_prep_tasks, self.guid64, self.audio_on_prep_task_completion)
        if gig_proto_buff.HasField('customer_sim_id'):
            self._customer_id = gig_proto_buff.customer_sim_id
        if gig_proto_buff.HasField('gig_attended'):
            self._gig_attended = gig_proto_buff.gig_attended

    def set_gig_time(self, upcoming_gig_time):
        self._upcoming_gig_time = upcoming_gig_time

    def get_resolver_for_gig(self):
        if self._customer_id is not None:
            customer_sim_info = services.sim_info_manager().get(self._customer_id)
            if customer_sim_info is not None:
                return DoubleSimResolver(self._owner, customer_sim_info)
        return SingleSimResolver(self._owner)

    def set_up_gig(self):
        if self.gig_prep_tasks:
            self.prep_time_start(self._owner, self.gig_prep_tasks, self.guid64, self.audio_on_prep_task_completion)
        if self.loots_on_schedule:
            resolver = self.get_resolver_for_gig()
            for loot_actions in self.loots_on_schedule:
                loot_actions.apply_to_resolver(resolver)

    def collect_rabbit_hole_rewards(self):
        pass

    def _get_additional_loots(self):
        if self.result_based_loots is not None and self._gig_result is not None:
            loots = self.result_based_loots.get(self._gig_result)
            if loots is not None:
                return loots
        return ()

    def collect_additional_rewards(self):
        loots = self._get_additional_loots()
        if loots:
            self._loot_strings = []
            resolver = self.get_resolver_for_gig()
            for loot_actions in loots:
                self._loot_strings.extend(loot_actions.apply_to_resolver_and_get_display_texts(resolver))

    def _determine_gig_outcome(self):
        raise NotImplementedError

    def get_pay(self, overmax_level=None, **kwargs):
        self._determine_gig_outcome()
        pay = self.gig_pay.lower_bound
        if self.additional_pay_per_overmax_level:
            pay = pay + overmax_level*self.additional_pay_per_overmax_level
        resolver = self.get_resolver_for_gig()
        if self._gig_result in self.result_based_gig_pay_multipliers:
            multiplier = self.result_based_gig_pay_multipliers[self._gig_result].get_multiplier(resolver)
            pay = int(pay*multiplier)
        gratuity = 0
        if self.odd_job_tuning.result_based_gig_gratuity_chance_multipliers:
            gratuity_multiplier = 0
            gratuity_chance = 0
            if self._gig_result in self.odd_job_tuning.result_based_gig_gratuity_chance_multipliers:
                gratuity_chance = self.odd_job_tuning.result_based_gig_gratuity_chance_multipliers[self._gig_result].get_multiplier(resolver)
            if self._gig_result in self.odd_job_tuning.result_based_gig_gratuity_multipliers:
                gratuity_multiplier = self.odd_job_tuning.result_based_gig_gratuity_multipliers[self._gig_result].get_multiplier(resolver)
                gratuity = int(pay*gratuity_multiplier)
        self._gig_pay = pay
        self._gig_gratuity = gratuity
        return pay + gratuity

    def get_promotion_evaluation_result(self, reward_text, *args, first_gig=False, **kwargs):
        if self._gig_result is not None and self.end_of_gig_notifications is not None:
            notification = self.end_of_gig_notifications.get(self._gig_result, None)
            if notification:
                customer_sim_info = services.sim_info_manager().get(self._customer_id)
                if self.end_of_gig_promotion_text and not first_gig:
                    results_list = self.get_results_list(self.end_of_gig_promotion_text(self._owner))
                else:
                    results_list = self.get_results_list()
                return EvaluationResult(Evaluation.PROMOTED, notification, self._gig_pay, self._gig_gratuity, customer_sim_info, results_list)

    def get_demotion_evaluation_result(self, *args, first_gig=False, **kwargs):
        if self._gig_result is not None and self.end_of_gig_notifications is not None:
            notification = self.end_of_gig_notifications.get(self._gig_result, None)
            if notification:
                customer_sim_info = services.sim_info_manager().get(self._customer_id)
                if self.end_of_gig_demotion_text and not first_gig:
                    results_list = self.get_results_list(self.end_of_gig_demotion_text(self._owner))
                else:
                    results_list = self.get_results_list()
                return EvaluationResult(Evaluation.DEMOTED, notification, self._gig_pay, self._gig_gratuity, customer_sim_info, results_list)

    def get_overmax_evaluation_result(self, overmax_level, reward_text, *args, **kwargs):
        if reward_text and self.end_of_gig_overmax_notification:
            return EvaluationResult(Evaluation.PROMOTED, self.end_of_gig_overmax_notification, overmax_level, self._gig_pay, self.additional_pay_per_overmax_level, reward_text)
        elif self.end_of_gig_overmax_rewardless_notification:
            return EvaluationResult(Evaluation.PROMOTED, self.end_of_gig_overmax_rewardless_notification, overmax_level, self._gig_pay, self.additional_pay_per_overmax_level)

    def _get_strings_for_results_list(self):
        strings = []
        if self._gig_pay is not None:
            strings.append(LocalizationHelperTuning.MONEY(self._gig_pay))
        if self.odd_job_tuning is not None and self._gig_gratuity:
            gratuity_text_factory = self.odd_job_tuning.gig_gratuity_bullet_point_text
            if gratuity_text_factory is not None:
                customer_sim_info = services.sim_info_manager().get(self._customer_id)
                gratuity_text = gratuity_text_factory(self._owner, customer_sim_info, self._gig_gratuity)
                strings.append(gratuity_text)
        if self._loot_strings:
            strings.extend(self._loot_strings)
        return strings

    def get_results_list(self, *additional_tokens):
        return LocalizationHelperTuning.get_bulleted_list((None,), additional_tokens, self._get_strings_for_results_list())

    def get_end_of_gig_evaluation_result(self, **kwargs):
        if self._gig_result is not None and self.end_of_gig_notifications is not None:
            notification = self.end_of_gig_notifications.get(self._gig_result, None)
            if notification:
                customer_sim_info = services.sim_info_manager().get(self._customer_id)
                return EvaluationResult(Evaluation.ON_TARGET, notification, self._gig_pay, self._gig_gratuity, customer_sim_info, self.get_results_list())

    @classmethod
    def _get_base_pay_for_gig_owner(cls, owner):
        overmax_pay = cls.additional_pay_per_overmax_level
        if overmax_pay is not None:
            career = owner.career_tracker.get_career_by_uid(cls.career.guid64)
            if career is not None:
                overmax_pay *= career.overmax_level
                return (cls.gig_pay.lower_bound + overmax_pay, cls.gig_pay.upper_bound + overmax_pay)
        return (cls.gig_pay.lower_bound, cls.gig_pay.upper_bound)

    @classmethod
    def build_gig_msg(cls, msg, sim, gig_time=None, gig_customer=None):
        msg.gig_type = cls.guid64
        msg.gig_name = cls.display_name(sim)
        (pay_lower, pay_upper) = cls._get_base_pay_for_gig_owner(sim)
        msg.min_pay = pay_lower
        msg.max_pay = pay_upper
        msg.gig_icon = ResourceKey()
        msg.gig_icon.instance = cls.display_icon.instance
        msg.gig_icon.group = cls.display_icon.group
        msg.gig_icon.type = cls.display_icon.type
        if cls.odd_job_tuning is not None and cls.odd_job_tuning.use_customer_description_as_gig_description and gig_customer is not None:
            customer_sim_info = services.sim_info_manager().get(gig_customer)
            if customer_sim_info is not None:
                msg.gig_description = cls.odd_job_tuning.customer_description(customer_sim_info)
        else:
            msg.gig_description = cls.display_description(sim)
        if gig_time is not None:
            msg.gig_time = gig_time
        if gig_customer is not None:
            msg.customer_id = gig_customer
        if cls.tip is not None:
            msg.tip_title = cls.tip.tip_title()
            if cls.tip.tip_icon is not None or cls.tip.tip_text is not None:
                build_icon_info_msg(IconInfoData(icon_resource=cls.tip.tip_icon), None, msg.tip_icon, desc=cls.tip.tip_text())

    def send_prep_task_update(self):
        if self.gig_prep_tasks:
            self._prep_task_tracker.send_prep_task_update()

    def _apply_payout_stat(self, medal, payout_display_data=None):
        owner_sim = self._owner
        resolver = SingleSimResolver(owner_sim)
        payout_stats = self.payout_stat_data
        for stat in payout_stats.keys():
            stat_tracker = owner_sim.get_tracker(stat)
            if not owner_sim.get_tracker(stat).has_statistic(stat):
                pass
            else:
                stat_data = payout_stats[stat]
                stat_multiplier = 1.0
                if medal in stat_data.medal_to_payout:
                    multiplier = stat_data.medal_to_payout[medal]
                    stat_multiplier = multiplier.get_multiplier(resolver)
                stat_total = stat_data.base_amount*stat_multiplier
                stat_tracker.add_value(stat, stat_total)
                if payout_display_data is not None:
                    for threshold_data in stat_data.ui_threshold:
                        if stat_total >= threshold_data.threshold:
                            payout_display_data.append(threshold_data)
                            break
