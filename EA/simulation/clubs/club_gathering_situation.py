from _collections import defaultdictfrom buffs.appearance_modifier.appearance_modifier import AppearanceModifierfrom buffs.buff import Bufffrom buffs.tunable import TunableBuffReferencefrom clock import interval_in_sim_minutesfrom clubs import club_tuningfrom clubs.club_enums import ClubRuleEncouragementStatus, ClubGatheringKeys, ClubGatheringStartSource, ClubGatheringVibefrom clubs.club_tuning import ClubTunablesfrom date_and_time import create_time_spanfrom distributor.ops import StartClubGathering, EndClubGathering, UpdateClubGathering, SendClubInteractionRuleUpdatefrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import DoubleSimResolverfrom event_testing.test_events import TestEventfrom interactions import ParticipantType, priorityfrom interactions.context import InteractionContextfrom role.role_state import RoleStatefrom sims.self_interactions import ForceChangeToCurrentOutfitfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableSimMinute, TunableRange, Tunable, TunableMapping, TunableList, TunableEnumEntryfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import BouncerRequestFactoryfrom situations.bouncer.bouncer_types import BouncerRequestPriority, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, SituationStatefrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport alarmsimport clockimport enumimport servicesimport sims4logger = sims4.log.Logger('Clubs', default_owner='tastle')
class GatheringUpdateType(enum.Int, export=False):
    ADD_MEMBER = 0
    REMOVE_MEMBER = 1

class AssociatedClubRequestFactory(BouncerRequestFactory):

    def _can_assign_sim_to_request(self, sim):
        club_service = services.get_club_service()
        return self._situation.associated_club in club_service.get_clubs_for_sim_info(sim.sim_info)

class ClubGatheringSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_default_job': SituationJob.TunableReference(description='\n            The default job for all members of this situation.\n            '), '_default_role_state': RoleState.TunableReference(description='\n            The Role State for Sims in the default job of this situation.\n            '), '_default_gathering_vibe': TunableEnumEntry(description='\n            The default Club vibe to use for the gathering.\n            ', tunable_type=ClubGatheringVibe, default=ClubGatheringVibe.NO_VIBE), '_vibe_buffs': TunableMapping(description="        \n            A Mapping of ClubGatheringVibe to List of buffs.\n            \n            When setting the vibe for the gathering the type is found in the\n            mapping and then each buff is processed in order until one of them\n            can be added. Then evaluation stops.\n            \n            Example: The club vibe is getting set to ClubGatheringVibe.Angry.\n            That entry has 3 buffs associated with it in the mapping. Angry3,\n            Angry2, Angry1 in that order. Angry3 doesn't pass evaluation so it\n            is passed. Next Angry2 does pass evaluation and so we add Angry2\n            Vibe Buff to the gathering. Angry1 is never evaluated in this\n            situation. Angry1 is only ever evaluated if Angry3 and Angry2 both\n            fail.\n            ", key_type=ClubGatheringVibe, value_type=TunableList(description='\n                A List of buff to attempt to use on the gathering. Order is\n                important as we do not try to give any buffs after one is given\n                to the gathering.\n                ', tunable=Buff.TunableReference(), minlength=1)), '_gathering_buff_reason': TunableLocalizedString(description='\n            The reason the gathering buff was added. Displayed on the buff\n            tooltip.\n            '), '_initial_disband_timer': TunableSimMinute(description='\n            The number of Sim minutes after a Gathering is created before it\n            can disband due to lack of members.\n            ', default=30, minimum=1), '_initial_notification': TunableUiDialogNotificationSnippet(description='\n            A notification that shows up once the gathering starts.\n            '), '_minimum_number_of_sims': TunableRange(description='\n            The minimum number of Sims that must be present in a Gathering to\n            keep it from disbanding.\n            ', tunable_type=int, default=3, minimum=2), 'time_between_bucks_rewards': TunableSimMinute(description='\n            The time in Sim Minutes to wait before awarding\n            the first club bucks for being in a gathering.\n            ', default=10), 'reward_bucks_per_interval': Tunable(description='\n            The amount of Club Bucks to award to the associated club at each \n            tuned interval.\n            ', tunable_type=int, default=1), 'rule_breaking_buff': TunableBuffReference(description='\n            Award this buff whenever a Sim breaks the rules.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, seed):
        super().__init__(seed)
        self.associated_club = None
        self._current_gathering_buff = None
        self._current_gathering_vibe = None
        self._sim_gathering_time_checks = {}
        self._can_disband = False
        self._initial_disband_timer_handle = None
        self._rewards_timer = None
        self._time_tracker_timer = None
        self._validity_household_id_override = None
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            start_source = reader.read_uint64(ClubGatheringKeys.START_SOURCE, None)
            disband_ticks = reader.read_uint64(ClubGatheringKeys.DISBAND_TICKS, 0)
            self._validity_household_id_override = reader.read_uint64(ClubGatheringKeys.HOUSEHOLD_ID_OVERRIDE, None)
            associated_club_id = reader.read_uint64(ClubGatheringKeys.ASSOCIATED_CLUB_ID, None)
            if associated_club_id is not None:
                club_service = services.get_club_service()
                associated_club = club_service.get_club_by_id(associated_club_id)
                self.initialize_gathering(associated_club, disband_ticks=disband_ticks, start_source=start_source)
            current_gathering_buff_guid = reader.read_uint64(ClubGatheringKeys.GATHERING_BUFF, 0)
            self._current_gathering_buff = services.get_instance_manager(sims4.resources.Types.BUFF).get(current_gathering_buff_guid)
            vibe = reader.read_uint64(ClubGatheringKeys.GATHERING_VIBE, self._default_gathering_vibe)
            self.set_club_vibe(vibe)

    @classmethod
    def default_job(cls):
        return cls._default_job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.default_job(), cls._default_role_state)]

    @classmethod
    def _states(cls):
        return (SituationStateData(1, ClubGatheringSituationState),)

    def _destroy(self):
        if self._initial_disband_timer_handle is not None:
            self._initial_disband_timer_handle.cancel()
            self._initial_disband_timer_handle = None
        if self._rewards_timer is not None:
            self._rewards_timer.cancel()
            self._rewards_timer = None
        if self._time_tracker_timer is not None:
            self._time_tracker_timer.cancel()
            self._time_tracker_timer = None
        super()._destroy()

    def _disband_timer_callback(self, _):
        self._can_disband = True
        if self._initial_disband_timer_handle is not None:
            alarms.cancel_alarm(self._initial_disband_timer_handle)
            self._initial_disband_timer_handle = None
        self._disband_if_neccessary()

    def _disband_if_neccessary(self):
        if not self._can_disband:
            return
        if len(list(self.all_sims_in_situation_gen())) < self._minimum_number_of_sims:
            self._self_destruct()

    def on_remove(self):
        self._can_disband = False
        super().on_remove()
        self._cleanup_gathering()

    def _cleanup_gathering(self):
        club_service = services.get_club_service()
        if club_service is None:
            logger.error("Attempting to end a Gathering but the ClubService doesn't exist.")
            return
        op = EndClubGathering(self.associated_club.club_id)
        Distributor.instance().add_op_with_no_owner(op)
        club_service.on_gathering_ended(self)

    def start_situation(self):
        super().start_situation()
        self._change_state(ClubGatheringSituationState())

    def load_situation(self):
        result = super().load_situation()
        if result and not (self.associated_club is None or self.is_validity_overridden() or self.associated_club.is_zone_valid_for_gathering(services.current_zone_id())):
            self._cleanup_gathering()
            return False
        return result

    def is_validity_overridden(self):
        return self._validity_household_id_override == services.active_household_id() and services.active_household_lot_id() == services.active_lot_id()

    def initialize_gathering(self, associated_club, disband_ticks=None, start_source=None):
        club_service = services.get_club_service()
        if club_service is None:
            logger.error("Attempting to start a Gathering but the ClubService doesn't exist.")
            return
        self.associated_club = associated_club
        if start_source is not None:
            if start_source == ClubGatheringStartSource.APPLY_FOR_INVITE:
                invited_sim = services.sim_info_manager().get(self._guest_list.host_sim_id)
                self.associated_club.show_club_notification(invited_sim, ClubTunables.CLUB_GATHERING_START_DIALOG)
            elif any(sim_info.is_selectable for sim_info in self._guest_list.invited_sim_infos_gen()):
                initial_notification = self._initial_notification(services.active_sim_info())
                initial_notification.show_dialog(icon_override=IconInfoData(icon_resource=associated_club.icon), additional_tokens=(associated_club.name,))
            self._initial_disband_timer_handle = alarms.add_alarm(self.associated_club, interval_in_sim_minutes(self._initial_disband_timer), self._disband_timer_callback)
        elif disband_ticks > 0:
            self._initial_disband_timer_handle = alarms.add_alarm(self.associated_club, clock.TimeSpan(disband_ticks), self._disband_timer_callback)
        time_between_rewards = create_time_span(minutes=self.time_between_bucks_rewards)
        self._rewards_timer = alarms.add_alarm(self, time_between_rewards, self._award_club_bucks, True)
        time_between_gathering_checks = create_time_span(minutes=club_tuning.ClubTunables.MINUTES_BETWEEN_CLUB_GATHERING_PULSES)
        self._time_tracker_timer = alarms.add_alarm(self, time_between_gathering_checks, self._add_time_in_gathering, True)
        op = StartClubGathering(self.associated_club.club_id)
        Distributor.instance().add_op_with_no_owner(op)
        club_service.on_gathering_started(self)

    def _on_minimum_number_of_members_reached(self):
        self._can_disband = True
        if self._initial_disband_timer_handle is not None:
            alarms.cancel_alarm(self._initial_disband_timer_handle)
            self._initial_disband_timer_handle = None

    def _on_add_sim_to_situation(self, sim, *args, **kwargs):
        super()._on_add_sim_to_situation(sim, *args, **kwargs)
        club_service = services.get_club_service()
        if club_service is None:
            logger.error("Attempting to add a Sim to a Gathering but the ClubService doesn't exist.")
            return
        club_service.on_sim_added_to_gathering(sim, self)
        self.add_club_vibe_buff_to_sim(sim)
        relationship_tracker = sim.relationship_tracker
        relationship_tracker.add_create_relationship_listener(self._relationship_added_callback)
        sim.sim_info.register_for_outfit_changed_callback(self._on_outfit_changed)
        if self._can_disband or len(list(self.all_sims_in_situation_gen())) >= self._minimum_number_of_sims:
            self._on_minimum_number_of_members_reached()
        op = UpdateClubGathering(GatheringUpdateType.ADD_MEMBER, self.associated_club.club_id, sim.id)
        Distributor.instance().add_op_with_no_owner(op)
        if self.associated_club.member_should_spin_into_club_outfit(sim):
            self._push_spin_into_current_outfit_interaction(sim)
        self._sim_gathering_time_checks[sim] = services.time_service().sim_timeline.now

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        sim.remove_buff_by_type(self._current_gathering_buff)
        self._disband_if_neccessary()
        club_service = services.get_club_service()
        if club_service is None:
            logger.error("Attempting to add a Sim to a Gathering but the ClubService doesn't exist.")
            return
        club_service.on_sim_removed_from_gathering(sim, self)
        relationship_tracker = sim.relationship_tracker
        relationship_tracker.remove_create_relationship_listener(self._relationship_added_callback)
        sim.sim_info.unregister_for_outfit_changed_callback(self._on_outfit_changed)
        if self.associated_club.member_should_spin_into_club_outfit(sim):
            sim.sim_info.register_for_outfit_changed_callback(self._on_outfit_removed)
            self._push_spin_into_current_outfit_interaction(sim)
        else:
            self._remove_apprearance_modifiers(sim.sim_info)
        if self.associated_club in club_service.clubs_to_gatherings_map:
            op = UpdateClubGathering(GatheringUpdateType.REMOVE_MEMBER, self.associated_club.club_id, sim.id)
            Distributor.instance().add_op_with_no_owner(op)
        if sim in self._sim_gathering_time_checks:
            self._process_time_in_gathering_event(sim)
            del self._sim_gathering_time_checks[sim]

    def set_club_vibe(self, vibe):
        self._current_gathering_vibe = vibe
        vibe_buffs = self._vibe_buffs.get(vibe, ())
        member = self.associated_club.members[0]
        for buff in vibe_buffs:
            if buff.can_add(member):
                if buff is not self._current_gathering_buff:
                    for sim in self.all_sims_in_situation_gen():
                        sim.remove_buff_by_type(self._current_gathering_buff)
                        self.add_club_vibe_buff_to_sim(sim, buff)
                    self._current_gathering_buff = buff
                return

    def add_club_vibe_buff_to_sim(self, sim, buff=None):
        buff = self._current_gathering_buff if buff is None else buff
        if buff is None:
            return
        if sim.has_buff(buff):
            return
        sim.add_buff(buff, self._gathering_buff_reason)

    def _relationship_added_callback(self, relationship):
        resolver = DoubleSimResolver(relationship.find_sim_info_a(), relationship.find_sim_info_b(), additional_participants={ParticipantType.AssociatedClub: (self.associated_club,)})
        for (perk, benefit) in ClubTunables.NEW_RELATIONSHIP_MODS.items():
            if self.associated_club.bucks_tracker.is_perk_unlocked(perk):
                if not benefit.test_set.run_tests(resolver=resolver):
                    pass
                else:
                    benefit.loot.apply_to_resolver(resolver=resolver)

    def _award_club_bucks(self, handle):
        qualified_sims = [sim for sim in self._situation_sims if self._sim_satisfies_requirement_for_bucks(sim)]
        if not qualified_sims:
            return
        if any(sim for sim in self._situation_sims if club_tuning.ClubTunables.CLUB_BUCKS_REWARDS_MULTIPLIER.trait in sim.sim_info.trait_tracker.equipped_traits):
            multiplier = club_tuning.ClubTunables.CLUB_BUCKS_REWARDS_MULTIPLIER.multiplier
        else:
            multiplier = 1
        bucks_tracker = self.associated_club.bucks_tracker
        if bucks_tracker is None:
            return
        bucks_tracker.try_modify_bucks(ClubTunables.CLUB_BUCKS_TYPE, int(self.reward_bucks_per_interval*multiplier), reason='Time in club gathering')

    def _sim_satisfies_requirement_for_bucks(self, sim):
        if not sim.is_selectable:
            return False
        elif not sim.sim_info.is_instanced():
            return False
        return True

    def _on_outfit_changed(self, sim_info, outfit_category_and_index):
        club = self.associated_club
        (cas_parts_add, cas_parts_remove) = club.get_club_outfit_parts(sim_info, outfit_category_and_index)
        appearance_tracker = sim_info.appearance_tracker
        appearance_tracker.remove_appearance_modifiers(self.guid, source=self)
        modifiers = []
        for cas_part in cas_parts_add:
            modifier = AppearanceModifier.SetCASPart(cas_part=cas_part, should_toggle=False, replace_with_random=False, update_genetics=False, _is_combinable_with_same_type=True, remove_conflicting=False, outfit_type_compatibility=None)
            modifiers.append(modifier)
        for cas_part in cas_parts_remove:
            modifier = AppearanceModifier.SetCASPart(cas_part=cas_part, should_toggle=True, replace_with_random=False, update_genetics=False, _is_combinable_with_same_type=True, remove_conflicting=False, outfit_type_compatibility=None)
            modifiers.append(modifier)
        for modifier in modifiers:
            appearance_tracker.add_appearance_modifier(modifier, self.guid, 1, False, source=self)
        appearance_tracker.evaluate_appearance_modifiers()
        if sim_info.appearance_tracker.appearance_override_sim_info is not None:
            sim = sim_info.get_sim_instance()
            if sim is not None:
                sim.apply_outfit_buffs_for_sim_info(sim_info.appearance_tracker.appearance_override_sim_info, outfit_category_and_index)

    def _on_outfit_removed(self, sim_info, outfit_category_and_index):
        self._remove_apprearance_modifiers(sim_info)

    def _remove_apprearance_modifiers(self, sim_info):
        sim_info.appearance_tracker.remove_appearance_modifiers(self.guid, source=self)
        sim_info.unregister_for_outfit_changed_callback(self._on_outfit_removed)

    def _push_spin_into_current_outfit_interaction(self, sim):
        sim.sim_info.set_outfit_dirty(sim.get_current_outfit()[0])
        change_outfit_context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, priority.Priority.High)
        return sim.push_super_affordance(ForceChangeToCurrentOutfit, None, change_outfit_context)

    def remove_all_club_outfits(self):
        for sim in self.all_sims_in_situation_gen():
            self._push_spin_into_current_outfit_interaction(sim)

    def _add_time_in_gathering(self, handle):
        qualified_sims = [sim for sim in self._situation_sims if self._sim_satisfies_requirement_for_bucks(sim)]
        if not qualified_sims:
            return
        now = services.time_service().sim_timeline.now
        for sim in qualified_sims:
            self._process_time_in_gathering_event(sim, now)
            self._sim_gathering_time_checks[sim] = now

    def _process_time_in_gathering_event(self, sim, now=None):
        if now is None:
            now = services.time_service().sim_timeline.now
        elapsed_time = now - self._sim_gathering_time_checks[sim]
        services.get_event_manager().process_event(test_events.TestEvent.TimeInClubGathering, sim_info=sim.sim_info, amount=int(elapsed_time.in_minutes()))

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_uint64(ClubGatheringKeys.ASSOCIATED_CLUB_ID, self.associated_club.club_id)
        if self._initial_disband_timer_handle is not None:
            current_time = services.time_service().sim_now
            disband_ticks = max((self._initial_disband_timer_handle.finishing_time - current_time).in_ticks(), 0)
        else:
            disband_ticks = 0
        writer.write_uint64(ClubGatheringKeys.DISBAND_TICKS, disband_ticks)
        if self._current_gathering_buff is not None:
            writer.write_uint64(ClubGatheringKeys.GATHERING_BUFF, self._current_gathering_buff.guid64)
        writer.write_uint64(ClubGatheringKeys.GATHERING_VIBE, self._current_gathering_vibe)
        if self._validity_household_id_override is not None:
            writer.write_uint64(ClubGatheringKeys.HOUSEHOLD_ID_OVERRIDE, self._validity_household_id_override)

    def _issue_requests(self):
        super()._issue_requests()
        request = AssociatedClubRequestFactory(self, callback_data=_RequestUserData(), job_type=self._default_job, request_priority=BouncerRequestPriority.EVENT_DEFAULT_JOB, user_facing=False, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(ClubGatheringSituation, exclusivity=BouncerExclusivityCategory.CLUB_GATHERING, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)
class ClubGatheringSituationState(SituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_event_register(TestEvent.InteractionStart)
        self._test_event_register(TestEvent.InteractionComplete)
        self._interaction_rule_status = defaultdict(lambda : {ClubRuleEncouragementStatus.DISCOURAGED: set(), ClubRuleEncouragementStatus.ENCOURAGED: set()})

    def handle_event(self, _, event, resolver):
        interaction = resolver.interaction
        if not interaction.visible:
            return
        sim_info = interaction.sim.sim_info
        if event == TestEvent.InteractionStart:
            club_service = services.get_club_service()
            (rule_status, _) = club_service.get_interaction_encouragement_status_and_rules_for_sim_info(sim_info, interaction.aop)
            if rule_status != ClubRuleEncouragementStatus.NO_EFFECT:
                self._interaction_rule_status[sim_info.sim_id][rule_status].add(interaction.id)
                if rule_status == ClubRuleEncouragementStatus.DISCOURAGED:
                    rule_breaking_buff_op = self.owner.rule_breaking_buff
                    sim_info.add_buff_from_op(rule_breaking_buff_op.buff_type, buff_reason=rule_breaking_buff_op.buff_reason)
        elif event == TestEvent.InteractionComplete:
            if sim_info.sim_id not in self._interaction_rule_status:
                return
            for interaction_set in self._interaction_rule_status[sim_info.sim_id].values():
                interaction_set.discard(interaction.id)
        interaction_rule_status = self._interaction_rule_status.get(sim_info.sim_id)
        if interaction_rule_status is None:
            return
        if interaction_rule_status[ClubRuleEncouragementStatus.DISCOURAGED]:
            rule_status = ClubRuleEncouragementStatus.DISCOURAGED
        elif interaction_rule_status[ClubRuleEncouragementStatus.ENCOURAGED]:
            rule_status = ClubRuleEncouragementStatus.ENCOURAGED
        else:
            rule_status = ClubRuleEncouragementStatus.NO_EFFECT
        op = SendClubInteractionRuleUpdate(rule_status)
        Distributor.instance().add_op(sim_info, op)
