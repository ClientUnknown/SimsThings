from collections import namedtupleimport randomfrom protocolbuffers.Localization_pb2 import LocalizedStringTokenfrom bucks.club_bucks_tracker import ClubBucksTrackerfrom cas.cas import get_caspart_bodytypefrom clubs import club_tuningfrom clubs.club_enums import ClubGatheringStartSource, ClubHangoutSetting, ClubOutfitSettingfrom clubs.club_telemetry import club_telemetry_writer, TELEMETRY_HOOK_CLUB_JOIN, TELEMETRY_HOOK_CLUB_QUIT, TELEMETRY_FIELD_CLUB_IDfrom clubs.club_tuning import ClubTunablesfrom date_and_time import create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoDatafrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom services.persistence_service import save_unlock_callbackfrom sims.outfits.outfit_enums import CLOTHING_BODY_TYPES, OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Age, Genderfrom sims.sim_info_utils import sim_info_auto_finderfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import TunablePackSafeReferencefrom singletons import DEFAULTfrom world.region import get_region_instance_from_zone_idimport bucksimport build_buyimport gsi_handlersimport servicesimport sims4import telemetry_helperlogger = sims4.log.Logger('Clubs', default_owner='tastle')ClubCommodityData = namedtuple('ClubCommodityData', ('static_commodity', 'desire'))
class Club:
    CLUB_JOINED_DRAMA_NODE = TunablePackSafeReference(description='\n        The drama node that will be scheduled when a Sim is added to a club.\n        ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))

    def __init__(self, club_id, name, icon, description, encouragement_commodity, discouragement_commodity, encouragement_buff, discouragement_buff, social_encouragement_buff, leader=None, leader_id=None, member_ids=None, recent_member_ids=None, membership_criteria=None, rules=None, hangout_setting=ClubHangoutSetting.HANGOUT_NONE, hangout_venue=None, hangout_zone_id=0, invite_only=False, associated_color=None, associated_style=None, uniform_male_child=None, uniform_female_child=None, uniform_male_adult=None, uniform_female_adult=None, club_seed=None, bucks_tracker_data=None, male_adult_mannequin=None, male_child_mannequin=None, female_adult_mannequin=None, female_child_mannequin=None, outfit_setting=ClubOutfitSetting.NO_OUTFIT):
        self._name = name
        self._localized_custom_name = None
        self._description = description
        self._localized_custom_description = None
        self.club_id = club_id
        self.icon = icon
        self.leader = leader
        self.leader_id = leader_id
        self.members = []
        self._recent_member_ids = set(recent_member_ids) if recent_member_ids is not None else set()
        self.member_ids = member_ids
        self.encouragement_commodity = encouragement_commodity
        self.discouragement_commodity = discouragement_commodity
        self.encouragement_buff = encouragement_buff
        self.discouragement_buff = discouragement_buff
        self.social_encouragement_buff = social_encouragement_buff
        self.membership_criteria = []
        self.rules = []
        self.invite_only = invite_only
        self.set_associated_color(associated_color, distribute=False)
        self.set_associated_style(associated_style, distribute=False)
        self.uniform_male_child = uniform_male_child
        self.uniform_female_child = uniform_female_child
        self.uniform_male_adult = uniform_male_adult
        self.uniform_female_adult = uniform_female_adult
        self.club_seed = club_seed
        self.bucks_tracker = ClubBucksTracker(self)
        self._bucks_tracker_data = bucks_tracker_data
        self.male_adult_mannequin = male_adult_mannequin
        self.male_child_mannequin = male_child_mannequin
        self.female_adult_mannequin = female_adult_mannequin
        self.female_child_mannequin = female_child_mannequin
        self.outfit_setting = outfit_setting
        self.hangout_setting = hangout_setting
        self.hangout_venue = hangout_venue
        self.hangout_zone_id = hangout_zone_id
        self._gathering_auto_spawning_schedule = None
        self._gathering_end_time = None
        for criteria in membership_criteria:
            self.add_membership_criteria(criteria)
        for rule in rules:
            self.add_rule(rule)

    def __str__(self):
        name = ''
        if self._name is not None:
            name = self._name
        elif self.club_seed is not None:
            name = self.club_seed.__name__
        return name + '_' + str(self.club_id)

    @property
    def name(self):
        if self._localized_custom_name is None:
            self._localized_custom_name = LocalizationHelperTuning.get_raw_text(self._name)
        if self._name is not None and self._localized_custom_name is not None:
            return self._localized_custom_name
        if self.club_seed is not None:
            return self.club_seed.name
        return LocalizationHelperTuning.get_raw_text('')

    @name.setter
    def name(self, value):
        self._name = value
        self._localized_custom_name = None

    @property
    def description(self):
        if self._localized_custom_description is None:
            self._localized_custom_description = LocalizationHelperTuning.get_raw_text(self._description)
        return self._description is not None and self._localized_custom_description or self.club_seed.description

    @description.setter
    def description(self, value):
        self._description = value
        self._localized_custom_description = None

    @property
    def id(self):
        return self.club_id

    def set_associated_color(self, color, distribute=True):
        self.associated_color = color
        if distribute:
            self.outfit_setting = ClubOutfitSetting.COLOR
            services.get_club_service().distribute_club_update((self,))

    def set_associated_style(self, style, distribute=True):
        self.associated_style = style
        if distribute:
            self.outfit_setting = ClubOutfitSetting.STYLE
            services.get_club_service().distribute_club_update((self,))

    def set_outfit_setting(self, setting, distribute=True):
        if self.outfit_setting != ClubOutfitSetting.NO_OUTFIT and setting == ClubOutfitSetting.NO_OUTFIT:
            club_service = services.get_club_service()
            if club_service is not None:
                gathering = club_service.clubs_to_gatherings_map.get(self)
                if gathering is not None:
                    gathering.remove_all_club_outfits()
        self.outfit_setting = setting
        if distribute:
            services.get_club_service().distribute_club_update((self,))

    def member_should_spin_into_club_outfit(self, sim_info):
        for buff in ClubTunables.PROHIBIT_CLUB_OUTFIT_BUFFS:
            if sim_info.has_buff(buff):
                return False
        current_outfit = sim_info.get_current_outfit()
        if current_outfit[0] == OutfitCategory.BATHING:
            return False
        if self.outfit_setting == ClubOutfitSetting.OVERRIDE:
            return self.club_uniform_exists_for_category(sim_info, current_outfit[0])
        if self.outfit_setting == ClubOutfitSetting.NO_OUTFIT:
            return False
        elif self.outfit_setting == ClubOutfitSetting.STYLE and self.associated_style is None:
            return False
        return True

    def disband(self):
        services.get_club_service().remove_club(self)

    def is_zone_valid_for_gathering(self, zone_id):
        persistence_service = services.get_persistence_service()
        household_manager = services.household_manager()
        try:
            venue_key = build_buy.get_current_venue(zone_id)
        except RuntimeError:
            return False
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_type = venue_manager.get(venue_key)
        if venue_type is None:
            return False
        if not venue_type.allowed_for_clubs:
            return False
        if venue_type.is_residential:
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            if zone_data is None:
                return False
            lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
            if lot_data is None:
                return False
            household = household_manager.get(lot_data.lot_owner[0].household_id) if lot_data.lot_owner else None
            if household is None:
                return False
            elif not any(club_member in self.members for club_member in household):
                return False
        return True

    def get_hangout_zone_id(self, prefer_current=False):
        if self.hangout_setting == ClubHangoutSetting.HANGOUT_NONE:
            return 0
        if self.hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
            current_region = services.current_region()

            def is_valid_zone_id(zone_id):
                if not self.is_zone_valid_for_gathering(zone_id):
                    return False
                zone_region = get_region_instance_from_zone_id(zone_id)
                if zone_region is None:
                    return False
                elif not current_region.is_region_compatible(zone_region):
                    return False
                return True

            available_zone_ids = tuple(filter(is_valid_zone_id, services.venue_service().get_zones_for_venue_type_gen(self.hangout_venue)))
            if not available_zone_ids:
                return 0
            if prefer_current:
                current_zone_id = services.current_zone_id()
                if current_zone_id in available_zone_ids:
                    return current_zone_id
            return random.choice(available_zone_ids)
        return self.hangout_zone_id

    @save_unlock_callback
    def show_club_gathering_dialog(self, sim_info, *, flavor_text, start_source=ClubGatheringStartSource.DEFAULT, sender_sim_info=DEFAULT):
        zone_id = self.get_hangout_zone_id()
        if not zone_id:
            return False
        current_region = services.current_region()
        hangout_region = get_region_instance_from_zone_id(zone_id)
        if not current_region.is_region_compatible(hangout_region):
            return False
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_type = venue_manager.get(build_buy.get_current_venue(zone_id))

        def on_response(dialog):
            if not dialog.accepted:
                return
            persistence_service = services.get_persistence_service()
            if persistence_service.is_save_locked():
                return
            club_service = services.get_club_service()
            if club_service is None:
                return
            club_service.start_gathering(self, start_source=start_source, host_sim_id=sim_info.sim_id, invited_sims=(sim_info,), zone_id=zone_id, spawn_sims_during_zone_spin_up=True)

        zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
        lot_name = zone_data.name
        sender_sim_info = self.leader if sender_sim_info is DEFAULT else sender_sim_info
        flavor_text = flavor_text(sim_info, sender_sim_info, self)
        additional_tokens = (lot_name, venue_type.club_gathering_text(), flavor_text)
        self.show_club_notification(sim_info, ClubTunables.CLUB_GATHERING_DIALOG, target_sim_id=sender_sim_info.sim_id, additional_tokens=additional_tokens, on_response=on_response)

    def show_club_notification(self, sim_info, notification_type, target_sim_id=None, additional_tokens=(), on_response=None):
        notification = notification_type(sim_info, resolver=DoubleSimResolver(sim_info, self.leader), target_sim_id=target_sim_id)
        notification.show_dialog(additional_tokens=(self.name,) + tuple(additional_tokens), icon_override=IconInfoData(icon_resource=self.icon), on_response=on_response)

    def is_gathering_auto_start_available(self):
        if self._gathering_end_time is not None and self._gathering_end_time + create_time_span(minutes=ClubTunables.CLUB_GATHERING_AUTO_START_COOLDOWN) > services.time_service().sim_now:
            return False
        return True

    def get_gathering(self):
        club_service = services.get_club_service()
        if club_service is None:
            return
        return club_service.clubs_to_gatherings_map.get(self)

    def get_member_cap(self):
        cap = services.get_club_service().default_member_cap
        for (perk, increase) in club_tuning.ClubTunables.CLUB_MEMBER_CAPACITY_INCREASES.items():
            if self.bucks_tracker.is_perk_unlocked(perk):
                cap += increase
        return cap

    def get_leader_score_for_sim_info(self, sim_info, prioritize_npcs=True):
        if sim_info not in self.members:
            logger.error("Club {} attempting to compute leader score for SimInfo {} but they aren't a member.", self, sim_info)
            return
        else:
            if prioritize_npcs:
                selectable_sim_score = 0
                npc_sim_score = 1
            else:
                selectable_sim_score = 1
                npc_sim_score = 0
            if sim_info.is_selectable:
                return selectable_sim_score
        return npc_sim_score

    def reassign_leader(self, new_leader=None, prioritize_npcs=True, distribute=True):
        if new_leader not in self.members:
            new_leader = None
        if new_leader is None:
            new_leader = self._find_best_leader(prioritize_npcs=prioritize_npcs)
        if new_leader is None:
            self.disband()
            return
        if new_leader is self.leader:
            return
        self.leader = new_leader
        if distribute:
            services.get_club_service().distribute_club_update((self,))
        services.get_event_manager().process_event(TestEvent.LeaderAssigned, sim_info=self.leader, associated_clubs=(self,))

    def _find_best_leader(self, *, prioritize_npcs):
        if not self.members:
            return
        return max(self.members, key=lambda member: self.get_leader_score_for_sim_info(member, prioritize_npcs=prioritize_npcs))

    @sim_info_auto_finder
    def _get_member_sim_infos(self):
        return self.member_ids

    def can_sim_info_join(self, new_sim_info):
        if new_sim_info in self.members:
            return False
        if len(self.members) >= self.get_member_cap():
            return False
        club_service = services.get_club_service()
        if not club_service.can_sim_info_join_more_clubs(new_sim_info):
            return False
        elif not self.validate_sim_info(new_sim_info):
            return False
        return True

    def add_member(self, member, distribute=True):
        if member is None:
            logger.error('Attempting to add a None member to club {}.', self)
            return False
        if not member.can_instantiate_sim:
            return False
        if member in self.members:
            logger.error('Attempting to add {} as a member to club {} but they are already a member.', member, self)
            return False
        if not self.validate_sim_info(member):
            logger.error("Attempting to add {} as a member to club {} but they don't pass all the membership criteria.", member, self)
            return False
        if len(self.members) >= self.get_member_cap():
            logger.error("Attempting to add {} as a member to club {} but it's already at the maximum number of allowed members.", member, self)
            return False
        club_service = services.get_club_service()
        if not club_service.can_sim_info_join_more_clubs(member):
            logger.error("Attempting to add {} as a member to club {} but they've already joined the maximum number of allowed Clubs.", member, self)
            return False
        club_rule_mapping = club_service.club_rule_mapping
        for rule in self.rules:
            for affordance in rule.action():
                club_rule_mapping[member][affordance].add(rule)
        club_service._sim_infos_to_clubs_map[member].add(self)
        self.members.append(member)
        for buff in club_tuning.ClubTunables.BUFFS_NOT_IN_ANY_CLUB:
            member.remove_buff_by_type(buff)
        club_service.reset_sim_info_interaction_club_rewards_cache(sim_info=member)
        if distribute:
            club_service.distribute_club_update((self,))
        zone = services.current_zone()
        if zone.is_zone_running:
            self._recent_member_ids.add(member.sim_id)
            sim = member.get_sim_instance()
            if sim is not None:
                for group in sim.get_groups_for_sim_gen():
                    club_service.on_sim_added_to_social_group(sim, group)
            for other_member in self.members:
                if member is other_member:
                    pass
                else:
                    resolver = DoubleSimResolver(member, other_member)
                    ClubTunables.CLUB_MEMBER_LOOT.apply_to_resolver(resolver)
            with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_JOIN, sim_info=member) as hook:
                hook.write_int(TELEMETRY_FIELD_CLUB_ID, self.id)
            if member.is_selectable and member is not self.leader:
                self.show_club_notification(member, ClubTunables.CLUB_NOTIFICATION_JOIN)
                if self not in club_service.clubs_to_gatherings_map:
                    self.show_club_gathering_dialog(member, flavor_text=ClubTunables.CLUB_GATHERING_DIALOG_TEXT_JOIN)
            services.get_event_manager().process_event(TestEvent.ClubMemberAdded, sim_info=member, associated_clubs=(self,))
            services.get_event_manager().process_event(TestEvent.ClubMemberAdded, sim_info=self.leader, associate_clubs=(self,))
            if self.CLUB_JOINED_DRAMA_NODE is not None and member is not self.leader:
                additional_participants = {ParticipantType.AssociatedClubLeader: (self.leader,), ParticipantType.AssociatedClub: (self,)}
                additional_localization_tokens = (self,)
                resolver = SingleSimResolver(member, additional_participants, additional_localization_tokens)
                services.drama_scheduler_service().schedule_node(self.CLUB_JOINED_DRAMA_NODE, resolver)
            self.bucks_tracker.award_unlocked_perks(ClubTunables.CLUB_BUCKS_TYPE, member)
        return True

    def remove_member(self, member, distribute=True, can_reassign_leader=True, from_stop=False):
        if member not in self.members:
            logger.error("Attempting to remove {} from club {} but they aren't a member.", member, self)
            return
        club_service = services.get_club_service()
        club_rule_mapping = club_service.club_rule_mapping
        for rule in self.rules:
            for affordance in rule.action():
                club_rule_mapping[member][affordance].remove(rule)
                if not club_rule_mapping[member][affordance]:
                    del club_rule_mapping[member][affordance]
            if not club_rule_mapping[member]:
                del club_rule_mapping[member]
        club_service._sim_infos_to_clubs_map[member].remove(self)
        del club_service._sim_infos_to_clubs_map[member]
        if not from_stop:
            for buff in club_tuning.ClubTunables.BUFFS_NOT_IN_ANY_CLUB:
                member.add_buff(buff.buff_type)
        member_instance = member.get_sim_instance()
        current_gathering = club_service.sims_to_gatherings_map.get(member_instance)
        if (club_service._sim_infos_to_clubs_map[member] or current_gathering is not None) and current_gathering.associated_club is self:
            current_gathering.remove_sim_from_situation(member_instance)
        self.members.remove(member)
        self._recent_member_ids.discard(member.sim_id)
        if member is self.leader:
            self.leader = None
            if can_reassign_leader:
                self.reassign_leader(prioritize_npcs=not member.is_selectable, distribute=distribute)
        club_service.reset_sim_info_interaction_club_rewards_cache(sim_info=member)
        if distribute:
            club_service.distribute_club_update((self,))
        zone = services.current_zone()
        if zone.is_zone_running:
            self.validate_club_hangout()
            with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_QUIT, sim_info=member) as hook:
                hook.write_int(TELEMETRY_FIELD_CLUB_ID, self.id)
            services.get_event_manager().process_event(TestEvent.ClubMemberRemoved, sim_info=member, associated_clubs=(self,))

    def start_club_effects(self, member):
        member.add_buff(self.encouragement_buff, additional_static_commodities_to_add=(self.encouragement_commodity,))
        member.add_buff(self.discouragement_buff, additional_static_commodities_to_add=(self.discouragement_commodity,))
        member.add_buff(self.social_encouragement_buff)

    def stop_club_effects(self, member):
        member.remove_buff_by_type(self.encouragement_buff)
        member.remove_buff_by_type(self.discouragement_buff)
        member.remove_buff_by_type(self.social_encouragement_buff)

    def _validate_members(self, update_if_invalid=False):
        global_result = True
        for member in list(self.members):
            result = self.validate_sim_info(member, update_if_invalid=update_if_invalid)
            if global_result and not result:
                global_result = False
        return global_result

    def validate_sim_info(self, sim_info, update_if_invalid=False):
        if not sim_info.is_human:
            return False
        for criteria in self.membership_criteria:
            result = self._validate_member_against_criteria(sim_info, criteria, update_if_invalid=update_if_invalid)
            if not result:
                return False
        return True

    def _validate_member_against_criteria(self, member, criteria, update_if_invalid=False):
        result = criteria.test_sim_info(member)
        if result or update_if_invalid:
            self.remove_member(member)
        return result

    def add_membership_criteria(self, criteria):
        for member in self.members:
            self._validate_member_against_criteria(member, criteria, update_if_invalid=True)
        self.membership_criteria.append(criteria)

    def remove_membership_criteria(self, criteria):
        if criteria not in self.membership_criteria:
            logger.error('Attempting to remove Membership Criteria {} from club {} but it was never added.', criteria, self)
            return
        self.membership_criteria.remove(criteria)

    def add_rule(self, rule):
        if rule.action is None:
            return
        club_service = services.get_club_service()
        club_rule_mapping = club_service.club_rule_mapping
        for member in self.members:
            for affordance in rule.action():
                club_rule_mapping[member][affordance].add(rule)
        if rule.is_encouraged:
            static_commodity_data = ClubCommodityData(self.encouragement_commodity, 1)
        else:
            static_commodity_data = ClubCommodityData(self.discouragement_commodity, 1)
        for affordance in rule.action():
            affordance.add_additional_static_commodity_data(static_commodity_data)
            club_service.affordance_dirty_cache.add(affordance)
        rule.register_club(self)
        club_service.on_rule_added(rule)
        self.rules.append(rule)

    def remove_rule(self, rule):
        club_service = services.get_club_service()
        club_rule_mapping = club_service.club_rule_mapping
        for member in self.members:
            for affordance in rule.action():
                club_rule_mapping[member][affordance].remove(rule)
                if not club_rule_mapping[member][affordance]:
                    del club_rule_mapping[member][affordance]
            if not club_rule_mapping[member]:
                del club_rule_mapping[member]
        if rule.is_encouraged:
            static_commodity_data = ClubCommodityData(self.encouragement_commodity, 1)
        else:
            static_commodity_data = ClubCommodityData(self.discouragement_commodity, 1)
        for affordance in rule.action():
            affordance.remove_additional_static_commodity_data(static_commodity_data)
            club_service.affordance_dirty_cache.add(affordance)
        club_service.on_rule_removed(rule)
        self.rules.remove(rule)

    def is_gathering_auto_spawning_available(self):
        if self._gathering_auto_spawning_schedule is None:
            r = random.Random(self.club_id)
            schedule = r.choice(ClubTunables.CLUB_GATHERING_AUTO_START_SCHEDULES)
            self._gathering_auto_spawning_schedule = schedule(init_only=True)
        current_time = services.time_service().sim_now
        return self._gathering_auto_spawning_schedule.is_scheduled_time(current_time)

    def is_recent_member(self, sim_info):
        return sim_info.sim_id in self._recent_member_ids

    def get_club_outfit_parts(self, sim_info, outfit_category_and_index=(0, 0)):
        if outfit_category_and_index[0] == OutfitCategory.BATHING:
            return ((), ())
        to_add = ()
        to_remove = ()
        if self.outfit_setting == ClubOutfitSetting.STYLE and self.associated_style is not None:
            (to_add, to_remove) = sim_info.generate_club_outfit(list((self.associated_style,)), outfit_category_and_index, 1)
        elif self.outfit_setting == ClubOutfitSetting.COLOR and self.associated_color is not None:
            (to_add, to_remove) = sim_info.generate_club_outfit(list((self.associated_color,)), outfit_category_and_index, 0)
        elif self.outfit_setting == ClubOutfitSetting.OVERRIDE:
            (to_add, to_remove) = self.get_cas_parts_from_mannequin_data(sim_info, outfit_category_and_index)
        return (to_add, to_remove)

    def get_cas_parts_from_mannequin_data(self, sim_info, outfit_category_and_index):
        to_add = []
        to_remove = []
        mannequin_data = self.get_club_uniform_data(sim_info.age, sim_info.clothing_preference_gender)
        random_outfit = mannequin_data.get_random_outfit(outfit_categories=(outfit_category_and_index[0],))
        if random_outfit[0] == outfit_category_and_index[0] and mannequin_data.has_outfit(random_outfit):
            outfit_data = mannequin_data.get_outfit(*random_outfit)
            to_add.extend(part_id for part_id in outfit_data.part_ids if get_caspart_bodytype(part_id) in CLOTHING_BODY_TYPES)
        if to_add:
            for outfit in sim_info.get_outfits_in_category(outfit_category_and_index[0]):
                for part in outfit.part_ids:
                    body_type = get_caspart_bodytype(part)
                    if body_type in CLOTHING_BODY_TYPES and body_type not in outfit_data.body_types:
                        to_remove.append(part)
                break
        return (to_add, to_remove)

    def club_uniform_exists_for_category(self, sim_info, category):
        mannequin_data = self.get_club_uniform_data(sim_info.age, sim_info.clothing_preference_gender)
        return mannequin_data.has_outfit((category, 0))

    def on_remove(self, from_stop=False):
        for member in list(self.members):
            self.remove_member(member, distribute=False, can_reassign_leader=False, from_stop=from_stop)
        for criteria in list(self.membership_criteria):
            self.remove_membership_criteria(criteria)
        for rule in list(self.rules):
            self.remove_rule(rule)
        services.get_club_service().update_affordance_cache()

    def on_all_households_and_sim_infos_loaded(self, client):
        if self.member_ids is None:
            return
        self.load_club_bucks_tracker(self._bucks_tracker_data)
        self._bucks_tracker_data = None
        sim_info_manager = services.sim_info_manager()
        for member in self._get_member_sim_infos():
            self.add_member(member, distribute=False)
        self.leader = sim_info_manager.get(self.leader_id)
        if self.leader is None:
            self.reassign_leader(distribute=False)
        self.member_ids = None
        self.leader_id = None
        self.validate_club_hangout()

    def validate_club_hangout(self):
        is_valid = True
        if self.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
            if not self.is_zone_valid_for_gathering(self.hangout_zone_id):
                is_valid = False
        elif not self.hangout_venue.allowed_for_clubs:
            is_valid = False
        if not is_valid:
            self.hangout_setting = ClubHangoutSetting.HANGOUT_NONE
            services.get_club_service().distribute_club_update((self,))
        self._validate_club_gathering_location()

    def _validate_club_gathering_location(self):
        club_gathering = self.get_gathering()
        if club_gathering is None:
            return
        if club_gathering.is_validity_overridden():
            return
        if not self.is_zone_valid_for_gathering(services.current_zone_id()):
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(club_gathering.id)

    def on_gathering_ended(self, gathering):
        self._gathering_end_time = services.time_service().sim_now
        self._recent_member_ids.clear()

    def get_club_uniform_data(self, age:Age, gender:Gender, sim_id=0):
        if age != Age.CHILD and gender is Gender.MALE:
            if self.male_adult_mannequin is None:
                self.male_adult_mannequin = SimInfoBaseWrapper(sim_id=sim_id)
                if self.uniform_male_adult is not None:
                    resource = self.uniform_male_adult
                else:
                    resource = club_tuning.ClubTunables.DEFAULT_MANNEQUIN_DATA.male_adult
                self.male_adult_mannequin.load_from_resource(resource)
            return self.male_adult_mannequin
        if age != Age.CHILD and gender is Gender.FEMALE:
            if self.female_adult_mannequin is None:
                self.female_adult_mannequin = SimInfoBaseWrapper(sim_id=sim_id)
                if self.uniform_female_adult is not None:
                    resource = self.uniform_female_adult
                else:
                    resource = club_tuning.ClubTunables.DEFAULT_MANNEQUIN_DATA.female_adult
                self.female_adult_mannequin.load_from_resource(resource)
            return self.female_adult_mannequin
        if age is Age.CHILD and gender is Gender.MALE:
            if self.male_child_mannequin is None:
                self.male_child_mannequin = SimInfoBaseWrapper(sim_id=sim_id)
                if self.uniform_male_child is not None:
                    resource = self.uniform_male_child
                else:
                    resource = club_tuning.ClubTunables.DEFAULT_MANNEQUIN_DATA.male_child
                self.male_child_mannequin.load_from_resource(resource)
            return self.male_child_mannequin
        if age is Age.CHILD and gender is Gender.FEMALE:
            if self.female_child_mannequin is None:
                self.female_child_mannequin = SimInfoBaseWrapper(sim_id=sim_id)
                if self.uniform_female_child is not None:
                    resource = self.uniform_female_child
                else:
                    resource = club_tuning.ClubTunables.DEFAULT_MANNEQUIN_DATA.female_child
                self.female_child_mannequin.load_from_resource(resource)
            return self.female_child_mannequin
        logger.error('Trying to get the club uniform data for an unsupported Age and Gender: {} and {}', str(age), str(gender))

    def handle_club_bucks_earned(self, bucks_type, amount_earned, reason=None):
        if bucks_type != club_tuning.ClubTunables.CLUB_BUCKS_TYPE:
            return
        for member in self.members:
            services.get_event_manager().process_event(test_events.TestEvent.ClubBucksEarned, sim_info=member, amount=amount_earned)
        if gsi_handlers.club_bucks_archive_handlers.is_archive_enabled():
            gsi_handlers.club_bucks_archive_handlers.archive_club_bucks_reward(self.id, amount=amount_earned, reason=reason)

    def load_club_bucks_tracker(self, bucks_tracker_data):
        if bucks_tracker_data is not None:
            self.bucks_tracker.load_data(bucks_tracker_data)

    def save(self, club_data):
        club_data.club_id = self.club_id
        club_data.invite_only = self.invite_only
        club_data.member_cap = self.get_member_cap()
        if self.leader is not None:
            club_data.leader = self.leader.id
        elif self.leader_id is not None:
            club_data.leader = self.leader_id
        else:
            club_data.leader = 0
        if self._name:
            club_data.name = self._name
        if self._description:
            club_data.description = self._description
        if self.members:
            for member in self.members:
                club_data.members.append(member.id)
        elif self.member_ids:
            for member_id in self.member_ids:
                club_data.members.append(member_id)
        for recent_member_id in self._recent_member_ids:
            club_data.recent_members.append(recent_member_id)
        icon_proto = sims4.resources.get_protobuff_for_key(self.icon)
        club_data.icon = icon_proto
        club_data.hangout_setting = self.hangout_setting
        if self.hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
            club_data.venue_type = sims4.resources.get_protobuff_for_key(self.hangout_venue.resource_key)
        elif self.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
            club_data.hangout_zone_id = self.hangout_zone_id
        if self.club_seed is not None:
            seed_proto = sims4.resources.get_protobuff_for_key(self.club_seed.resource_key)
            club_data.club_seed = seed_proto
        if self.associated_color is not None:
            club_data.associated_color = self.associated_color
        if self.associated_style is not None:
            club_data.associated_style = self.associated_style
        for criteria in self.membership_criteria:
            with ProtocolBufferRollback(club_data.membership_criteria) as club_criteria:
                criteria.save(club_criteria)
        for rule in self.rules:
            with ProtocolBufferRollback(club_data.club_rules) as club_rule:
                club_rule.encouraged = rule.is_encouraged
                action_proto = sims4.resources.get_protobuff_for_key(rule.action.resource_key)
                club_rule.interaction_group = action_proto
                if rule.with_whom is not None:
                    rule.with_whom.save(club_rule.with_whom)
        self.bucks_tracker.save_data(club_data)
        adult_male_mannequin = self.get_club_uniform_data(Age.ADULT, Gender.MALE)
        club_data.club_uniform_adult_male.mannequin_id = adult_male_mannequin.id
        self.male_adult_mannequin.save_sim_info(club_data.club_uniform_adult_male)
        adult_female_mannequin = self.get_club_uniform_data(Age.ADULT, Gender.FEMALE)
        club_data.club_uniform_adult_female.mannequin_id = adult_female_mannequin.id
        self.female_adult_mannequin.save_sim_info(club_data.club_uniform_adult_female)
        child_male_mannequin = self.get_club_uniform_data(Age.CHILD, Gender.MALE)
        club_data.club_uniform_child_male.mannequin_id = child_male_mannequin.id
        self.male_child_mannequin.save_sim_info(club_data.club_uniform_child_male)
        female_child_mannequin = self.get_club_uniform_data(Age.CHILD, Gender.FEMALE)
        club_data.club_uniform_child_female.mannequin_id = female_child_mannequin.id
        self.female_child_mannequin.save_sim_info(club_data.club_uniform_child_female)
        club_data.outfit_setting = self.outfit_setting

    def populate_localization_token(self, token):
        token.type = LocalizedStringToken.STRING
        token.text_string = self.name

    def has_members(self):
        return len(self.members) > 0
