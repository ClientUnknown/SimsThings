from _collections import defaultdictfrom collections import Counterfrom contextlib import contextmanagerimport randomfrom protocolbuffers import Clubs_pb2, Lot_pb2from autonomy.autonomy_modifier import AutonomyModifierfrom broadcasters.broadcaster_request import BroadcasterRequestfrom buffs.buff import Bufffrom clubs import club_tuning, UnavailableClubCriteriaErrorfrom clubs.club import Club, ClubOutfitSettingfrom clubs.club_enums import ClubRuleEncouragementStatus, ClubGatheringKeys, ClubGatheringStartSource, ClubHangoutSettingfrom clubs.club_telemetry import club_telemetry_writer, TELEMETRY_HOOK_CLUB_CREATE, TELEMETRY_FIELD_CLUB_ID, TELEMETRY_HOOK_CLUB_COUNT, TELEMETRY_FIELD_CLUB_TOTALCLUBS, TELEMETRY_HOOK_CLUB_OVERVIEW, TELEMETRY_FILED_CLUB_PCS, TELEMETRY_FIELD_CLUB_NPCS, TELEMETRY_FIELD_CLUB_BUCKSAMOUNT, TELEMETRY_FIELD_CLUB_NUMRULES, TELEMETRY_FIELD_CLUB_HANGOUTVENUE, TELEMETRY_FIELD_CLUB_HANGOUTLOT, TELEMETRY_FIELD_CLUB_HANGOUTSETTINGfrom clubs.club_tuning import ClubTunablesfrom distributor.ops import SendClubInfo, SendClubBuildingInfo, SendClubMembershipCriteriaValidation, SendClubValdiation, ShowClubInfoUIfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.test_events import TestEventfrom filters.tunable import ClubMembershipFilterTermfrom game_effect_modifier.game_effect_modifiers import GameEffectModifiersfrom id_generator import generate_object_idfrom interactions import ParticipantTypefrom interactions.club_buck_liability import ClubBucksLiabilityfrom interactions.context import InteractionSourcefrom objects import ALL_HIDDEN_REASONSfrom server.pick_info import PickTypefrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims4 import PropertyStreamWriterfrom sims4.common import Packfrom sims4.resources import get_protobuff_for_keyfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom singletons import DEFAULTfrom situations.bouncer.bouncer_types import BouncerRequestPriority, RequestSpawningOptionfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom statistics.static_commodity import StaticCommodityfrom world.region import get_region_instance_from_zone_id, Regionimport build_buyimport enumimport game_servicesimport persistence_error_typesimport servicesimport sims4import telemetry_helperlogger = sims4.log.Logger('Clubs', default_owner='tastle')
class ClubMessageType(enum.Int, export=False):
    ADD = 0
    REMOVE = 1
    UPDATE = 2

class ClubService(Service):
    CLUB_VALIDATION_EVENTS = (TestEvent.CareerEvent, TestEvent.AgedUp, TestEvent.SpouseEvent, TestEvent.SimoleonsEarned, TestEvent.OnExitBuildBuy)

    def __init__(self):
        self._clubs = set()
        self._sim_infos_to_clubs_map = defaultdict(set)
        self.clubs_to_gatherings_map = dict()
        self.sims_to_gatherings_map = dict()
        self._has_seeded_clubs = False
        self._club_static_commodities = set()
        self.club_rule_mapping = defaultdict(lambda : defaultdict(set))
        self._affordance_broadcaster_map = Counter()
        self.broadcaster_extra = type('Club_Rule_Broadcaster', (BroadcasterRequest, object), {'broadcaster_types': lambda *_, **__: [club_tuning.ClubTunables.CLUB_RULE_BROADCASTER], 'participant': ParticipantType.Actor, 'offset_time': None})
        self.club_filter_term = ClubMembershipFilterTerm(invert_score=False, minimum_filter_score=0)
        self.sim_info_interacton_club_rewards = defaultdict(lambda : defaultdict(lambda : defaultdict()))
        self.affordance_dirty_cache = set()
        self._deferred_distribution_ops = None

    @classproperty
    def required_packs(cls):
        return (Pack.EP02,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_CLUB_SERVICE

    @property
    def clubs(self):
        return self._clubs

    @property
    def default_member_cap(self):
        return club_tuning.ClubTunables.DEFAULT_MEMBER_CAP

    def start(self):
        services.get_event_manager().register(self, self.CLUB_VALIDATION_EVENTS)

    def stop(self):
        services.get_event_manager().unregister(self, self.CLUB_VALIDATION_EVENTS)

    def on_all_households_and_sim_infos_loaded(self, client):
        with self.defer_club_distribution():
            for club in tuple(self.clubs):
                club.on_all_households_and_sim_infos_loaded(client)
            self.remove_invalid_clubs()
            self.distribute_club_add(self.clubs)

    def on_zone_load(self):
        services.venue_service().on_venue_type_changed.register(self._validate_club_hangout)
        if not game_services.service_manager.is_traveling:
            return
        with self.defer_club_distribution():
            self.distribute_club_add(self.clubs)

    def on_zone_unload(self):
        if not services.game_services.service_manager.is_traveling:
            for club in tuple(self._clubs):
                self.remove_club(club, from_stop=True)
        with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_COUNT) as hook:
            hook.write_int(TELEMETRY_FIELD_CLUB_TOTALCLUBS, len(self.clubs))
        for club in self.clubs:
            pc_count = sum(1 for sim_info in club.members if sim_info.is_selectable)
            if pc_count > 0:
                npc_count = sum(1 for sim_info in club.members if not sim_info.is_selectable)
                self._send_club_overview_telemetry(club, pc_count=pc_count, npc_count=npc_count)
        services.venue_service().on_venue_type_changed.unregister(self._validate_club_hangout)

    def get_club_by_seed(self, club_seed):
        for club in self._clubs:
            if club.club_seed is club_seed:
                return club

    def get_club_by_id(self, club_id):
        for club in self._clubs:
            if club.club_id == club_id:
                return club

    def _get_sim_filter_gsi_name(self, sim_match_filter_request_type, sim_info=None):
        if sim_match_filter_request_type == True:
            return 'Request to check if {} matches filter from {}'.format(sim_info, self)
        else:
            return str(self)

    def start_gathering(self, club, start_source=ClubGatheringStartSource.DEFAULT, host_sim_id=0, invited_sims=(), zone_id=DEFAULT, ignore_zone_validity=False, **kwargs):
        if club not in self.clubs:
            return
        club_gathering = self.clubs_to_gatherings_map.get(club)
        if club_gathering is not None:
            return
        current_zone_id = services.current_zone_id()
        zone_id = current_zone_id if zone_id is DEFAULT else zone_id
        if ignore_zone_validity or not club.is_zone_valid_for_gathering(zone_id):
            return
        if zone_id != current_zone_id:
            for sim_info in invited_sims:
                career = sim_info.career_tracker.get_at_work_career()
                if career is not None:
                    career_interaction = career.get_interaction()

                    def on_response(left_work_early):
                        nonlocal invited_sims
                        if not left_work_early:
                            if sim_info.sim_id == host_sim_id:
                                return
                            invited_sims = tuple(s for s in invited_sims if s is not sim_info)

                        def _rerequest_gathering(*_, **__):
                            self.start_gathering(club, start_source=start_source, host_sim_id=host_sim_id, invited_sims=invited_sims, zone_id=zone_id, ignore_zone_validity=ignore_zone_validity, **kwargs)

                        if career_interaction is None:
                            _rerequest_gathering()
                        else:
                            career_interaction.add_exit_function(_rerequest_gathering)

                    career.leave_work_early(on_response=on_response)
                    return
        init_writer = PropertyStreamWriter()
        init_writer.write_uint64(ClubGatheringKeys.ASSOCIATED_CLUB_ID, club.id)
        init_writer.write_uint64(ClubGatheringKeys.START_SOURCE, start_source)
        if ignore_zone_validity:
            init_writer.write_uint64(ClubGatheringKeys.HOUSEHOLD_ID_OVERRIDE, services.active_household_id())
        for sim_info in invited_sims:
            sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            club_gathering = self.sims_to_gatherings_map.get(sim)
            if club_gathering is not None:
                club_gathering.remove_sim_from_situation(sim)
        club_gathering_default_job = ClubTunables.DEFAULT_CLUB_GATHERING_SITUATION.default_job()
        guest_list = SituationGuestList(invite_only=True, host_sim_id=host_sim_id)
        sim_filter_service = services.sim_filter_service()
        for sim_info in club.members:
            if sim_info not in invited_sims and not sim_filter_service.does_sim_match_filter(sim_info.sim_id, sim_filter=club_gathering_default_job.filter, gsi_source_fn=lambda : self._get_sim_filter_gsi_name(True, sim_info=sim_info)):
                pass
            else:
                guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, club_gathering_default_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH, expectation_preference=True))
        if zone_id != current_zone_id:
            persistence_service = services.get_persistence_service()
            if persistence_service.is_save_locked():
                return
        situation_manager = services.get_zone_situation_manager()
        situation_manager.create_situation(ClubTunables.DEFAULT_CLUB_GATHERING_SITUATION, guest_list=guest_list, user_facing=False, custom_init_writer=init_writer, zone_id=zone_id, **kwargs)

    def on_gathering_started(self, gathering):
        current_gathering_for_club = self.clubs_to_gatherings_map.get(gathering.associated_club)
        if current_gathering_for_club is not None and current_gathering_for_club is not gathering:
            logger.error('Attempting to start gathering {} for Club {}, but that club already has a different gathering {}.', gathering, gathering.associated_club, current_gathering_for_club)
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(gathering.id)
            return
        self.clubs_to_gatherings_map[gathering.associated_club] = gathering

    def on_gathering_ended(self, gathering):
        stored_gathering = self.clubs_to_gatherings_map.get(gathering.associated_club)
        if stored_gathering is None:
            logger.error("Attempting to end Gathering {} for Club {} but the Club Service doesn't think it exists.", gathering, gathering.associated_club)
        if gathering.id == stored_gathering.id:
            del self.clubs_to_gatherings_map[gathering.associated_club]
        gathering.associated_club.on_gathering_ended(gathering)

    def on_sim_added_to_gathering(self, sim, gathering):
        current_gathering_for_sim = self.sims_to_gatherings_map.get(sim)
        if current_gathering_for_sim is not None and current_gathering_for_sim is not gathering:
            logger.error('Attempting to add Sim {} to gathering {}, but it is already in a different gathering {}.', sim, gathering, current_gathering_for_sim)
            return
        self.sims_to_gatherings_map[sim] = gathering
        gathering.associated_club.start_club_effects(sim)

    def on_sim_removed_from_gathering(self, sim, gathering):
        if sim not in self.sims_to_gatherings_map:
            logger.error("Attempting to remove Sim {} from gathering {} but the Club Service doesn't think they were a part of it.", sim, gathering)
        del self.sims_to_gatherings_map[sim]
        gathering.associated_club.stop_club_effects(sim)

    def on_sim_added_to_social_group(self, sim, group):
        if not group.is_visible:
            return
        club_counter = Counter()
        ensemble_service = services.ensemble_service()
        for group_sim in group:
            if group_sim in self.sims_to_gatherings_map:
                pass
            else:
                ensemble = ensemble_service.get_visible_ensemble_for_sim(group_sim)
                if ensemble is not None:
                    pass
                else:
                    club_counter.update({club: 1 for club in self.get_clubs_for_sim_info(group_sim.sim_info)})
        for (club, count) in club_counter.most_common():
            if count < ClubTunables.CLUB_GATHERING_AUTO_START_GROUP_SIZE:
                break
            if club in self.clubs_to_gatherings_map:
                pass
            elif not club.is_gathering_auto_start_available():
                pass
            else:
                self.start_gathering(club)
                break

    def on_sim_killed_or_culled(self, sim_info):
        for club in tuple(self.get_clubs_for_sim_info(sim_info)):
            club.remove_member(sim_info)

    def handle_event(self, sim_info, event_type, resolver):
        for club in tuple(self.get_clubs_for_sim_info(sim_info)):
            if club.validate_sim_info(sim_info, update_if_invalid=True) or sim_info.is_selectable:
                club.show_club_notification(sim_info, ClubTunables.CLUB_NOTIFICATION_INVALID)

    def get_clubs_for_sim_info(self, sim_info):
        return frozenset(self._sim_infos_to_clubs_map.get(sim_info, ()))

    def can_sim_info_join_more_clubs(self, sim_info):
        return len(self._sim_infos_to_clubs_map.get(sim_info, set())) < club_tuning.ClubTunables.MAX_CLUBS_PER_SIM

    def get_interaction_encouragement_status_and_rules_for_sim_info(self, sim_info, aop_or_interaction):
        interaction_type = aop_or_interaction.affordance.get_interaction_type()
        NO_EFFECT = (ClubRuleEncouragementStatus.NO_EFFECT, [])
        if sim_info not in self.club_rule_mapping or interaction_type not in self.club_rule_mapping[sim_info]:
            return NO_EFFECT
        encouraged_rules = []
        discouraged_rules = []
        club_gathering = self.sims_to_gatherings_map.get(sim_info.get_sim_instance())
        if club_gathering is None:
            return NO_EFFECT
        for rule in self.club_rule_mapping[sim_info][interaction_type]:
            if rule.club is not club_gathering.associated_club:
                pass
            elif not self._does_rule_pass_tests(sim_info, rule, aop_or_interaction):
                pass
            elif not rule.is_encouraged:
                discouraged_rules.append(rule)
            elif not discouraged_rules:
                encouraged_rules.append(rule)
        if discouraged_rules:
            return (ClubRuleEncouragementStatus.DISCOURAGED, discouraged_rules)
        elif encouraged_rules:
            return (ClubRuleEncouragementStatus.ENCOURAGED, encouraged_rules)
        return NO_EFFECT

    def interaction_is_encouraged_for_sim_info(self, sim_info, aop):
        (encouragement, _) = self.get_interaction_encouragement_status_and_rules_for_sim_info(sim_info, aop)
        return encouragement == ClubRuleEncouragementStatus.ENCOURAGED

    def get_encouragment_mapping_for_sim_info(self, sim_info, aop):
        interaction_type = aop.affordance.get_interaction_type()
        if sim_info in self.sim_info_interacton_club_rewards and interaction_type in self.sim_info_interacton_club_rewards[sim_info]:
            return self.sim_info_interacton_club_rewards[sim_info][interaction_type]
        if sim_info not in self.club_rule_mapping or interaction_type not in self.club_rule_mapping[sim_info]:
            return {}
        club_reward_mapping = {}
        (encouragement, rules) = self.get_interaction_encouragement_status_and_rules_for_sim_info(sim_info, aop)
        if encouragement is ClubRuleEncouragementStatus.ENCOURAGED:
            for rule in rules:
                reward = rule.action.club_bucks_reward
                club_reward_mapping[rule.club] = max(club_reward_mapping.get(rule.club, 0), reward)
        self.sim_info_interacton_club_rewards[sim_info][interaction_type] = club_reward_mapping
        return club_reward_mapping

    def get_front_page_bonus_for_mixer(self, sim_info, aop):
        sim = sim_info.get_sim_instance()
        if sim is not None and sim in self.sims_to_gatherings_map and self.interaction_is_encouraged_for_sim_info(sim_info, aop):
            return club_tuning.ClubTunables.FRONT_PAGE_SCORE_BONUS_FOR_ENCOURAGED_MIXER
        return 0

    def reset_sim_info_interaction_club_rewards_cache(self, sim_info=None):
        if sim_info is None:
            self.sim_info_interacton_club_rewards.clear()
        elif sim_info in self.sim_info_interacton_club_rewards:
            self.sim_info_interacton_club_rewards[sim_info].clear()

    def _does_rule_pass_tests(self, sim_info, rule, aop_or_interaction):
        if aop_or_interaction.target is not None and aop_or_interaction.target.is_sim:
            target_sim_info = aop_or_interaction.target.sim_info
            if rule.with_whom is not None and target_sim_info is not sim_info and not rule.with_whom.test_sim_info(target_sim_info):
                return False
        return True

    def create_rewards_buck_liability(self, sim_info, interaction):
        if any(isinstance(liability, ClubBucksLiability) for liability in interaction.liabilities):
            return
        elif self.interaction_is_encouraged_for_sim_info(sim_info, interaction.aop):
            return ClubBucksLiability(interaction)

    def get_interaction_score_multiplier(self, interaction, sim=DEFAULT):
        sim = interaction.sim if sim is DEFAULT else sim
        base_multiplier = 1
        sim_info = sim.sim_info
        if sim_info not in self.club_rule_mapping:
            return base_multiplier
        interaction_type = interaction.affordance.get_interaction_type()
        if interaction_type not in self.club_rule_mapping[sim_info]:
            return base_multiplier
        club_rules = self.club_rule_mapping[sim_info].get(interaction_type)
        if not club_rules:
            return base_multiplier
        (encouragement, _) = self.get_interaction_encouragement_status_and_rules_for_sim_info(sim_info, interaction)
        if encouragement == ClubRuleEncouragementStatus.DISCOURAGED:
            return ClubTunables.CLUB_DISCOURAGEMENT_MULTIPLIER
        if encouragement == ClubRuleEncouragementStatus.ENCOURAGED:
            if interaction.affordance.is_super:
                return ClubTunables.CLUB_ENCOURAGEMENT_MULTIPLIER
            else:
                return ClubTunables.CLUB_ENCOURAGEMENT_SUBACTION_MULTIPLIER
        return base_multiplier

    def provided_clubs_and_interactions_for_phone_gen(self, context):
        if context.sim is None:
            return
        for club in self.get_clubs_for_sim_info(context.sim.sim_info):
            for affordance in club_tuning.ClubTunables.CLUB_PHONE_SUPER_INTERACTIONS:
                yield from affordance.potential_interactions(None, context, associated_club=club)

    def provided_clubs_and_interactions_gen(self, context, target=None):
        if context.sim is None:
            return
        if context.pick is not None:
            target = context.pick.target
            pick_type = context.pick.pick_type
        else:
            if target is None:
                return
            if target.is_sim:
                pick_type = PickType.PICK_SIM
            else:
                return
        if target is None or target is context.sim:
            return
        actor_clubs = self.get_clubs_for_sim_info(context.sim.sim_info)
        if target.is_sim:
            target_clubs = self.get_clubs_for_sim_info(target.sim_info)
            unique_clubs = actor_clubs.union(target_clubs)
            return
        else:
            unique_clubs = actor_clubs
        for club in unique_clubs:
            for affordance in club_tuning.ClubTunables.CLUB_SUPER_INTERACTIONS:
                if affordance.ASSOCIATED_PICK_TYPE != pick_type:
                    pass
                elif not context.source == InteractionSource.AUTONOMY or not affordance.allow_autonomous:
                    pass
                elif any(si.get_interaction_type() is affordance and (si.associated_club is club and target in si.get_potential_mixer_targets()) for si in context.sim.si_state):
                    pass
                else:
                    yield (club, affordance)

    def generate_members_for_membership_criteria(self, number_of_members, admission_criteria):

        def _is_valid_member(sim_info):
            if sim_info.household is None:
                return False
            if not sim_info.is_human:
                return False
            elif not all(criteria.test_sim_info(sim_info) for criteria in admission_criteria):
                return False
            return True

        allowed_sim_ids = tuple(sim_info.sim_id for sim_info in services.sim_info_manager().get_all() if _is_valid_member(sim_info))
        if not allowed_sim_ids:
            return ()
        member_filter = club_tuning.ClubTunables.CLUB_MEMBER_SIM_FILTER()
        members = services.sim_filter_service().submit_matching_filter(sim_filter=member_filter, sim_constraints=allowed_sim_ids, number_of_sims_to_find=number_of_members, allow_yielding=False, gsi_source_fn=lambda : self._get_sim_filter_gsi_name(False))
        members = [member.sim_info for member in members]
        return members

    def on_rule_added(self, rule):
        for affordance in rule.action():
            if affordance not in self._affordance_broadcaster_map:
                affordance.add_additional_basic_extra(self.broadcaster_extra)
            self._affordance_broadcaster_map[affordance] += 1
        self.reset_sim_info_interaction_club_rewards_cache()

    def on_rule_removed(self, rule):
        for affordance in rule.action():
            self._affordance_broadcaster_map[affordance] -= 1
            if self._affordance_broadcaster_map[affordance] <= 0:
                del self._affordance_broadcaster_map[affordance]
                affordance.remove_additional_basic_extra(self.broadcaster_extra)
        self.reset_sim_info_interaction_club_rewards_cache()

    def refresh_safe_seed_data_for_club(self, club):
        club_seed = club.club_seed
        club.associated_color = club_seed.associated_color
        club.associated_style = club_seed.associated_style
        club.invite_only = club_seed.invite_only
        club.icon = club_seed.icon
        (club.hangout_setting, club.hangout_venue, club.hangout_zone_id) = club_seed.hangout.get_hangout_data()
        for rule in list(club.rules):
            club.remove_rule(rule)
        for rule in club_seed.club_rules:
            club.add_rule(rule())
        self.update_affordance_cache()
        self.distribute_club_update((club,))

    def _load_specific_criteria(self, criteria_data, for_rule=False):
        criteria = club_tuning.CATEGORY_TO_CRITERIA_MAPPING[criteria_data.category]
        criteria_infos = list(criteria_data.criteria_infos)
        if not criteria.is_multi_select:
            if not criteria_infos:
                return
            criteria_info = criteria_infos[0]
            if criteria_info.resource_value or criteria_info.enum_value or not criteria_info.resource_id:
                return
        try:
            club_criteria = criteria(criteria_infos=criteria_infos, criteria_id=criteria_data.criteria_id)
        except UnavailableClubCriteriaError:
            club_criteria = None
        return club_criteria

    def _load_membership_criteria(self, saved_criterias):
        membership_criteria = []
        for criteria_data in saved_criterias:
            criteria = self._load_specific_criteria(criteria_data)
            if criteria is not None:
                membership_criteria.append(criteria)
        return membership_criteria

    def _load_rules(self, saved_rules):
        action_manager = services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP)
        club_rules = []
        for rule in saved_rules:
            action_category = action_manager.get(rule.interaction_group.instance)
            if rule.HasField('with_whom'):
                with_whom = lambda : self._load_specific_criteria(rule.with_whom, for_rule=True)
            else:
                with_whom = None
            if rule.encouraged:
                restriction = ClubRuleEncouragementStatus.ENCOURAGED
            else:
                restriction = ClubRuleEncouragementStatus.DISCOURAGED
            new_rule = club_tuning.ClubRule(action=action_category, with_whom=with_whom, restriction=restriction)
            club_rules.append(new_rule)
        return club_rules

    def _load_mannequin_data(self, saved_mannequin):
        sim_info = SimInfoBaseWrapper(sim_id=saved_mannequin.mannequin_id)
        persistence_service = services.get_persistence_service()
        if persistence_service is not None:
            persisted_data = persistence_service.get_mannequin_proto_buff(saved_mannequin.mannequin_id)
            if persisted_data is not None:
                saved_mannequin = persisted_data
        sim_info.load_sim_info(saved_mannequin)
        return sim_info

    def create_club(self, club_seed=None, seed_members=None, club_data=None, from_load=False, refresh_cache=True):
        if club_data is not None and club_data.club_id:
            club_id = club_data.club_id
        else:
            club_id = generate_object_id()
        if club_seed is not None:
            leader_id = None
            member_ids = None
            recent_member_ids = None
            membership_criteria = [criteria() for criteria in club_seed.membership_criteria]
            if seed_members:
                (leader, members) = seed_members
            else:
                number_of_members = random.randint(club_seed.initial_number_of_memebers.lower_bound, club_seed.initial_number_of_memebers.upper_bound)
                members = self.generate_members_for_membership_criteria(number_of_members, membership_criteria)
                if members and len(members) < number_of_members:
                    return
                leader = random.choice(members)
            name = None
            description = None
            icon = club_seed.icon
            invite_only = club_seed.invite_only
            associated_color = club_seed.associated_color
            associated_style = club_seed.associated_style
            uniform_male_child = club_seed.uniform_male_child
            uniform_female_child = club_seed.uniform_female_child
            uniform_male_adult = club_seed.uniform_male_adult
            uniform_female_adult = club_seed.uniform_female_adult
            club_rules = [rule() for rule in club_seed.club_rules]
            bucks_tracker_data = None
            male_adult_mannequin = None
            male_child_mannequin = None
            female_adult_mannequin = None
            female_child_mannequin = None
            outfit_setting = club_seed.club_outfit_setting
            (hangout_setting, hangout_venue, hangout_zone_id) = club_seed.hangout.get_hangout_data()
        elif club_data is not None:
            if from_load:
                leader = None
                members = None
                leader_id = club_data.leader
                member_ids = [member_id for member_id in club_data.members]
                bucks_tracker_data = club_data
                male_adult_mannequin = None
                if club_data.HasField('club_uniform_adult_male'):
                    male_adult_mannequin = self._load_mannequin_data(club_data.club_uniform_adult_male)
                male_child_mannequin = None
                if club_data.HasField('club_uniform_child_male'):
                    male_child_mannequin = self._load_mannequin_data(club_data.club_uniform_child_male)
                female_adult_mannequin = None
                if club_data.HasField('club_uniform_adult_female'):
                    female_adult_mannequin = self._load_mannequin_data(club_data.club_uniform_adult_female)
                female_child_mannequin = None
                if club_data.HasField('club_uniform_child_female'):
                    female_child_mannequin = self._load_mannequin_data(club_data.club_uniform_child_female)
                outfit_setting = club_data.outfit_setting
            else:
                sim_info_manager = services.sim_info_manager()
                leader = sim_info_manager.get(club_data.leader)
                members = [sim_info_manager.get(member_id) for member_id in club_data.members]
                leader_id = None
                member_ids = None
                bucks_tracker_data = None
                male_adult_mannequin = None
                male_child_mannequin = None
                female_adult_mannequin = None
                female_child_mannequin = None
                outfit_setting = ClubOutfitSetting.NO_OUTFIT
            name = club_data.name if club_data.name else None
            description = club_data.description
            invite_only = club_data.invite_only
            associated_color = club_data.associated_color
            associated_style = club_data.associated_style
            uniform_male_child = None
            uniform_female_child = None
            uniform_male_adult = None
            uniform_female_adult = None
            membership_criteria = self._load_membership_criteria(club_data.membership_criteria)
            club_rules = self._load_rules(club_data.club_rules)
            icon = sims4.resources.Key(club_data.icon.type, club_data.icon.instance, club_data.icon.group)
            venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
            club_seed_manager = services.get_instance_manager(sims4.resources.Types.CLUB_SEED)
            hangout_setting = club_data.hangout_setting
            hangout_venue = None
            hangout_zone_id = 0
            if hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
                hangout_venue = venue_manager.get(club_data.venue_type.instance)
                if hangout_venue is None:
                    hangout_setting = ClubHangoutSetting.HANGOUT_NONE
            elif hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
                hangout_zone_id = club_data.hangout_zone_id
            club_seed = club_seed_manager.get(club_data.club_seed.instance)
            recent_member_ids = [recent_member_id for recent_member_id in club_data.recent_members]
        else:
            logger.error('Attempting to create a club with neither a ClubSeed or a piece of club_data.')
            return
        encouragement_name = 'Club_Encouragement_' + str(club_id)
        discouragement_name = 'Club_Discouragement_' + str(club_id)
        social_encouragement_name = 'Club_Social_Encouragement_' + str(club_id)
        encouragement_commodity = type(encouragement_name, (StaticCommodity, object), {'ad_data': club_tuning.ClubTunables.CLUB_ENCOURAGEMENT_AD_DATA})
        discouragement_commodity = type(discouragement_name, (StaticCommodity, object), {'ad_data': club_tuning.ClubTunables.CLUB_DISCOURAGEMENT_AD_DATA})
        encouragement_buff = type(encouragement_name, (Buff, object), {'visible': False})
        discouragement_buff = type(discouragement_name, (Buff, object), {'visible': False})
        social_autonomy_mod = AutonomyModifier(relationship_score_multiplier_with_buff_on_target={encouragement_buff: club_tuning.ClubTunables.CLUB_RELATIONSHIP_SCORE_MULTIPLIER})
        social_game_effect_mod = type('Club_Autonomy_Mod', (GameEffectModifiers, object), {'_game_effect_modifiers': [social_autonomy_mod]})
        social_encouragement_buff = type(social_encouragement_name, (Buff, object), {'visible': False, 'game_effect_modifier': social_game_effect_mod})
        new_club = Club(club_id, name, icon, description, encouragement_commodity, discouragement_commodity, encouragement_buff, discouragement_buff, social_encouragement_buff, leader=leader, leader_id=leader_id, member_ids=member_ids, recent_member_ids=recent_member_ids, membership_criteria=membership_criteria, rules=club_rules, hangout_setting=hangout_setting, hangout_venue=hangout_venue, hangout_zone_id=hangout_zone_id, invite_only=invite_only, uniform_male_child=uniform_male_child, associated_color=associated_color, uniform_female_child=uniform_female_child, uniform_male_adult=uniform_male_adult, uniform_female_adult=uniform_female_adult, club_seed=club_seed, bucks_tracker_data=bucks_tracker_data, male_adult_mannequin=male_adult_mannequin, male_child_mannequin=male_child_mannequin, female_adult_mannequin=female_adult_mannequin, female_child_mannequin=female_child_mannequin, outfit_setting=outfit_setting, associated_style=associated_style)
        if refresh_cache:
            self.update_affordance_cache()
        self.add_club(new_club, from_load=from_load)
        if members is not None:
            for member in members:
                new_club.add_member(member)
            if new_club.leader is None:
                new_club.reassign_leader()
        return new_club

    def add_club(self, club, from_load=False):
        if club in self._clubs:
            logger.error('Attempting to double-add a club to the ClubService: {}', club)
            return
        self._clubs.add(club)
        self._club_static_commodities.add(club.encouragement_commodity)
        self._club_static_commodities.add(club.discouragement_commodity)
        if not from_load:
            club.bucks_tracker.try_modify_bucks(ClubTunables.CLUB_BUCKS_TYPE, ClubTunables.INITIAL_AMOUNT_OF_CLUB_BUCKS, reason=None if from_load else 'Creating Club')
            if club.club_seed is not None:
                for perk in club.club_seed.unlocked_rewards:
                    club.bucks_tracker.unlock_perk(perk)
            else:
                for perk in club_tuning.ClubTunables.DEFAULT_USER_CLUB_PERKS:
                    club.bucks_tracker.unlock_perk(perk)
            self.distribute_club_add((club,))

    def remove_club(self, club, from_stop=False):
        if club not in self._clubs:
            logger.error('Attempting to remove a club from the ClubService that was never added: {}', club)
            return
        self._clubs.remove(club)
        self._club_static_commodities.remove(club.encouragement_commodity)
        self._club_static_commodities.remove(club.discouragement_commodity)
        club.on_remove(from_stop=from_stop)
        self.distribute_club_remove((club,))
        if from_stop:
            return
        if len(self._clubs) >= club_tuning.ClubTunables.MINIMUM_REQUIRED_CLUBS:
            return
        shuffled_seeds = list(club_tuning.ClubTunables.CLUB_SEEDS_SECONDARY)
        random.shuffle(shuffled_seeds)
        for seed in shuffled_seeds:
            if any(existing_club.club_seed is seed for existing_club in self._clubs):
                pass
            else:
                self.create_club(club_seed=seed, refresh_cache=False)
                if len(self._clubs) >= club_tuning.ClubTunables.MINIMUM_REQUIRED_CLUBS:
                    break
        self.update_affordance_cache()

    def _validate_club_hangout(self):
        for club in self.clubs:
            club.validate_club_hangout()

    def on_finish_waiting_for_sim_spawner_service(self):
        current_zone_id = services.current_zone_id()
        household = services.active_household()
        if household.home_zone_id == current_zone_id:
            return
        travel_group = household.get_travel_group()
        if travel_group is not None and travel_group.zone_id == current_zone_id:
            return
        if services.get_zone_situation_manager().is_user_facing_situation_running(global_user_facing_only=True):
            return
        sim_info_manager = services.sim_info_manager()
        traveled_sims = sim_info_manager.get_traveled_to_zone_sim_infos()
        if len(traveled_sims) <= 1:
            return
        common_clubs = None
        for sim_info in traveled_sims:
            if common_clubs is None:
                common_clubs = self.get_clubs_for_sim_info(sim_info)
            else:
                common_clubs = self.get_clubs_for_sim_info(sim_info).intersection(common_clubs)
            if not common_clubs:
                break
        common_clubs = set(common_clubs)
        for club in tuple(common_clubs):
            if not club.is_zone_valid_for_gathering(current_zone_id):
                common_clubs.remove(club)
        if common_clubs and len(traveled_sims) >= ClubTunables.CLUB_GATHERING_TRAVEL_AUTO_START_GROUP_SIZE:
            club = random.sample(common_clubs, 1)[0]
            self.start_gathering(club)
            op = ShowClubInfoUI(club.id)
            Distributor.instance().add_op_with_no_owner(op)
        else:
            services.ensemble_service().create_travel_ensemble_if_neccessary(traveled_sims)

    def send_club_building_info(self):
        persistence_service = services.get_persistence_service()
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        criterias = []
        for category in club_tuning.ClubCriteriaCategory:
            criteria_cls = club_tuning.CATEGORY_TO_CRITERIA_MAPPING[category]
            if criteria_cls.test():
                criteria_proto = Clubs_pb2.ClubCriteria()
                criteria_proto.category = category
                criteria_cls.populate_possibilities(criteria_proto)
                criterias.append(criteria_proto)
        active_household = services.active_household()
        if active_household is None:
            return
        home_region = get_region_instance_from_zone_id(active_household.home_zone_id)
        if home_region is None:
            return
        current_region = services.current_region()
        available_lots = []
        for zone_data in persistence_service.zone_proto_buffs_gen():
            venue_type = venue_manager.get(build_buy.get_current_venue(zone_data.zone_id))
            if not venue_type is None:
                if not venue_type.allowed_for_clubs:
                    pass
                else:
                    neighborhood_data = persistence_service.get_neighborhood_proto_buff(zone_data.neighborhood_id)
                    region_instance = Region.REGION_DESCRIPTION_TUNING_MAP.get(neighborhood_data.region_id)
                    if home_region.is_region_compatible(region_instance) or not current_region.is_region_compatible(region_instance):
                        pass
                    elif venue_type.is_residential:
                        lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
                        if lot_data is None:
                            pass
                        elif lot_data.lot_owner:
                            if lot_data.lot_owner[0].household_id != services.active_household_id():
                                pass
                            else:
                                location_data = Lot_pb2.LotInfoItem()
                                location_data.zone_id = zone_data.zone_id
                                location_data.name = zone_data.name
                                location_data.world_id = zone_data.world_id
                                location_data.lot_template_id = zone_data.lot_template_id
                                location_data.lot_description_id = zone_data.lot_description_id
                                location_data.venue_type = get_protobuff_for_key(venue_type.resource_key)
                                available_lots.append(location_data)
                    else:
                        location_data = Lot_pb2.LotInfoItem()
                        location_data.zone_id = zone_data.zone_id
                        location_data.name = zone_data.name
                        location_data.world_id = zone_data.world_id
                        location_data.lot_template_id = zone_data.lot_template_id
                        location_data.lot_description_id = zone_data.lot_description_id
                        location_data.venue_type = get_protobuff_for_key(venue_type.resource_key)
                        available_lots.append(location_data)
        op = SendClubBuildingInfo(criterias, available_lots)
        Distributor.instance().add_op_with_no_owner(op)

    def send_club_criteria_validation(self, sim_ids, criteria_data):
        sim_info_manager = services.sim_info_manager()
        criterias = [self._load_specific_criteria(data) for data in criteria_data.criterias]
        failure_pairs = []
        for sim_id in sim_ids:
            sim_info = sim_info_manager.get(sim_id)
            failed_criterias = []
            for criteria in criterias:
                if criteria is None:
                    pass
                elif not criteria.test_sim_info(sim_info):
                    failed_criterias.append(criteria.criteria_id)
            if failed_criterias:
                failure_pairs.append((sim_id, failed_criterias))
        op = SendClubMembershipCriteriaValidation(failure_pairs)
        Distributor.instance().add_op_with_no_owner(op)

    def send_club_validation(self, sim_id, club_ids):
        sim_info_manager = services.sim_info_manager()
        failed_club_ids = []
        sim_info = sim_info_manager.get(sim_id)
        for club_id in club_ids:
            club = self.get_club_by_id(club_id)
            if not club.validate_sim_info(sim_info):
                failed_club_ids.append(club_id)
        op = SendClubValdiation(sim_id, failed_club_ids)
        Distributor.instance().add_op_with_no_owner(op)

    def create_club_from_new_data(self, club_data):
        club = self.create_club(club_data=club_data, from_load=False)
        club.show_club_notification(services.active_sim_info(), ClubTunables.CLUB_NOTIFICATION_CREATE)
        with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_CREATE) as hook:
            hook.write_int(TELEMETRY_FIELD_CLUB_ID, club.id)
        return club

    def update_club_from_data(self, club_data):
        club = self.get_club_by_id(club_data.club_id)
        if club is None:
            logger.error('Attempting to update Club (ID: {}) but no Club with this ID exists.', club_data.club_id)
            return
        club.name = club_data.name
        club.description = club_data.description
        club.invite_only = club_data.invite_only
        club.associated_color = club_data.associated_color
        club.icon = sims4.resources.Key(club_data.icon.type, club_data.icon.instance, club_data.icon.group)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        club.hangout_setting = club_data.hangout_setting
        if club.hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
            club.hangout_venue = venue_manager.get(club_data.venue_type.instance)
        elif club.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
            club.hangout_zone_id = club_data.hangout_zone_id
        membership_criteria = self._load_membership_criteria(club_data.membership_criteria)
        for existing_criteria in tuple(club.membership_criteria):
            club.remove_membership_criteria(existing_criteria)
        for new_criteria in membership_criteria:
            club.add_membership_criteria(new_criteria)
        club_rules = self._load_rules(club_data.club_rules)
        for existing_rule in tuple(club.rules):
            club.remove_rule(existing_rule)
        for new_rule in club_rules:
            club.add_rule(new_rule)
        self.update_affordance_cache()
        sim_info_manager = services.sim_info_manager()
        updated_members = [sim_info_manager.get(member_id) for member_id in club_data.members]
        for existing_member in tuple(club.members):
            if existing_member not in updated_members:
                club.remove_member(existing_member, distribute=False, can_reassign_leader=False)
        for updated_member in updated_members:
            if updated_member not in club.members:
                club.add_member(updated_member, distribute=False)
        if club.leader is None or club_data.leader != club.leader.id:
            new_leader = sim_info_manager.get(club_data.leader)
            club.reassign_leader(new_leader=new_leader)
        self.distribute_club_update((club,))

    @contextmanager
    def defer_club_distribution(self):
        try:
            self._deferred_distribution_ops = defaultdict(set)
            yield None
        finally:
            self._deferred_distribution_ops[ClubMessageType.UPDATE] -= self._deferred_distribution_ops[ClubMessageType.ADD]
            self._deferred_distribution_ops[ClubMessageType.ADD] -= self._deferred_distribution_ops[ClubMessageType.REMOVE]
            self._deferred_distribution_ops[ClubMessageType.UPDATE] -= self._deferred_distribution_ops[ClubMessageType.REMOVE]
            for (message_type, clubs) in self._deferred_distribution_ops.items():
                if not clubs:
                    pass
                else:
                    op = SendClubInfo(clubs, message_type)
                    Distributor.instance().add_op_with_no_owner(op)
            self._deferred_distribution_ops = None

    def distribute_club_add(self, clubs):
        if self._deferred_distribution_ops is None:
            op = SendClubInfo(clubs, ClubMessageType.ADD)
            Distributor.instance().add_op_with_no_owner(op)
        else:
            self._deferred_distribution_ops[ClubMessageType.ADD].update(clubs)

    def distribute_club_remove(self, clubs):
        if self._deferred_distribution_ops is None:
            op = SendClubInfo(clubs, ClubMessageType.REMOVE)
            Distributor.instance().add_op_with_no_owner(op)
        else:
            self._deferred_distribution_ops[ClubMessageType.REMOVE].update(clubs)

    def distribute_club_update(self, clubs):
        if self._deferred_distribution_ops is None:
            clubs = tuple(club for club in clubs if club in self._clubs)
            if clubs:
                op = SendClubInfo(clubs, ClubMessageType.UPDATE)
                Distributor.instance().add_op_with_no_owner(op)
        else:
            self._deferred_distribution_ops[ClubMessageType.UPDATE].update(clubs)

    def update_affordance_cache(self):
        with services.object_manager().batch_commodity_flags_update():
            for affordance in self.affordance_dirty_cache:
                affordance.trigger_refresh_static_commodity_cache()
        self.affordance_dirty_cache.clear()

    def _send_club_overview_telemetry(self, club, pc_count=0, npc_count=0):
        with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_OVERVIEW) as hook:
            hook.write_int(TELEMETRY_FIELD_CLUB_ID, club.id)
            hook.write_int(TELEMETRY_FILED_CLUB_PCS, pc_count)
            hook.write_int(TELEMETRY_FIELD_CLUB_NPCS, npc_count)
            hook.write_int(TELEMETRY_FIELD_CLUB_BUCKSAMOUNT, club.bucks_tracker.get_bucks_amount_for_type(club_tuning.ClubTunables.CLUB_BUCKS_TYPE))
            hook.write_int(TELEMETRY_FIELD_CLUB_NUMRULES, len(club.rules))
            hook.write_int(TELEMETRY_FIELD_CLUB_HANGOUTVENUE, club.hangout_venue.guid64 if club.hangout_venue is not None else 0)
            zone_data = services.get_persistence_service().get_zone_proto_buff(club.hangout_zone_id)
            hook.write_int(TELEMETRY_FIELD_CLUB_HANGOUTLOT, zone_data.lot_description_id if zone_data is not None else 0)
            hook.write_int(TELEMETRY_FIELD_CLUB_HANGOUTSETTING, club.hangout_setting)

    def save(self, save_slot_data=None, **kwargs):
        club_service_data = save_slot_data.gameplay_data.club_service
        club_service_data.Clear()
        club_service_data.has_seeded_clubs = self._has_seeded_clubs
        for club in self._clubs:
            with ProtocolBufferRollback(club_service_data.clubs) as clubs_data:
                club.save(clubs_data)

    def load(self, **_):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        club_service_data = save_slot_data_msg.gameplay_data.club_service
        self._has_seeded_clubs = club_service_data.has_seeded_clubs
        for club_data in club_service_data.clubs:
            self.create_club(club_data=club_data, from_load=True, refresh_cache=False)
        self.update_affordance_cache()

    def remove_invalid_clubs(self):
        clubs_to_remove = list()
        for club in self._clubs:
            if not club.has_members():
                clubs_to_remove.append(club)
        for club in clubs_to_remove:
            self.remove_club(club)
