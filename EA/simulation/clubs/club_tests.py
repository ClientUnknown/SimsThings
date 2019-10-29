from collections import namedtupleimport itertoolsfrom clubs.club_enums import ClubRuleEncouragementStatusfrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom relationships.relationship_tests import TunableRelationshipTestfrom sims4.tuning.tunable import TunableEnumEntry, TunableSingletonFactory, OptionalTunable, TunableVariant, HasTunableSingletonFactory, TunableThreshold, Tunable, AutoFactoryInitimport event_testing.test_baseimport servicesimport sims4logger = sims4.log.Logger('Clubs', default_owner='tastle')MEMBER = 'member'LEADER = 'leader'NOT_MEMBER = 'not member'NOT_LEADER = 'not leader'
class ClubGatheringTest(event_testing.test_base.BaseTest):
    CLUB_USE_ASSOCIATED = 1
    CLUB_USE_ANY = 2
    CLUB_FROM_EVENT_DATA = 3
    FACTORY_TUNABLES = {'club': TunableVariant(description='\n            Define the Club to run this test against.\n            ', locked_args={'use_club_from_resolver': CLUB_USE_ASSOCIATED, 'use_any_club': CLUB_USE_ANY, 'from_event_data': CLUB_FROM_EVENT_DATA}, default='use_club_from_resolver'), 'subject': TunableEnumEntry(description='\n            The subject whose Club Gathering status to check.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The target whose Club Gathering status to check.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'club_gathering_status': OptionalTunable(TunableVariant(description='\n            If enabled, require the associated Club to either have a Gathering\n            going on or not.\n            ', locked_args={'Gathering Exists': True, 'No Gathering Exists': False})), 'subject_club_gathering_status': OptionalTunable(TunableVariant(description='\n            If enabled, require the tuned "subject" to either be or not be in a\n            Club Gathering for the associated Club.\n            ', locked_args={'In Gathering': True, 'Not In Gathering': False})), 'target_club_gathering_status': OptionalTunable(TunableVariant(description='\n            If enabled, require the tuned "target" to either be or not be in a\n            Club Gathering for the associated Club.\n            ', locked_args={'In Gathering': True, 'Not In Gathering': False}))}

    def __init__(self, club, subject, target, club_gathering_status, subject_club_gathering_status, target_club_gathering_status, **kwargs):
        super().__init__(**kwargs)
        self.club = club
        self.subject = subject
        self.target = target
        self.club_gathering_status = club_gathering_status
        self.subject_club_gathering_status = subject_club_gathering_status
        self.target_club_gathering_status = target_club_gathering_status

    def get_expected_args(self):
        expected_args = {'test_subjects': self.subject, 'test_targets': self.target}
        if self.club == self.CLUB_USE_ASSOCIATED:
            expected_args['associated_clubs'] = ParticipantType.AssociatedClub
        elif self.club == self.CLUB_FROM_EVENT_DATA:
            expected_args['associated_clubs'] = event_testing.test_constants.FROM_EVENT_DATA
        return expected_args

    def test_gathering(self, club_to_test, test_subjects, test_targets):
        club_service = services.get_club_service()
        if club_service is not None:
            gathering = club_service.clubs_to_gatherings_map.get(club_to_test, None)
        else:
            gathering = None
        if self.club_gathering_status is not None:
            if gathering is None and self.club_gathering_status:
                return TestResult(False, 'There is no Gathering for Club {} but there should be.', club_to_test, tooltip=self.tooltip)
            if gathering is not None and not self.club_gathering_status:
                return TestResult(False, "There is a Gathering for Club {} but shouldn't be.", club_to_test, tooltip=self.tooltip)
        gathering_members = list(gathering.all_sims_in_situation_gen()) if gathering is not None else ()
        if self.subject_club_gathering_status is not None:
            for subject in test_subjects:
                sim_inst = subject.get_sim_instance()
                if (sim_inst is None or sim_inst not in gathering_members) and self.subject_club_gathering_status:
                    return TestResult(False, 'Subject {} not in Gathering for Club {} but should be.', subject, club_to_test, tooltip=self.tooltip)
                if sim_inst is not None and sim_inst in gathering_members and not self.subject_club_gathering_status:
                    return TestResult(False, "Subject {} in Gathering for Club {} but shouldn't be.", subject, club_to_test, tooltip=self.tooltip)
        if self.target_club_gathering_status is not None:
            for target in test_targets:
                sim_inst = target.get_sim_instance()
                if (sim_inst is None or sim_inst not in gathering_members) and self.target_club_gathering_status:
                    return TestResult(False, 'Target {} not in Gathering for Club {} but should be.', target, club_to_test, tooltip=self.tooltip)
                if sim_inst is not None and sim_inst in gathering_members and not self.target_club_gathering_status:
                    return TestResult(False, "Target {} in Gathering for Club {} but shouldn't be.", target, club_to_test, tooltip=self.tooltip)
        return TestResult.TRUE

    def __call__(self, test_subjects=None, test_targets=None, associated_clubs=None):
        club_service = services.get_club_service()
        if club_service is None:
            associated_clubs = (None,)
        if self.club == self.CLUB_USE_ASSOCIATED or self.club == self.CLUB_FROM_EVENT_DATA:
            if associated_clubs is None:
                logger.error('Attempting to run a ClubTest but there is no associated Club.')
                return TestResult(False, 'Attempting to run a ClubTest but there is no associated Club.', tooltip=self.tooltip)
            clubs_to_test = list(associated_clubs)
        elif self.club == self.CLUB_USE_ANY:

            def get_clubs_for_subject(subject):
                if club_service is not None:
                    return set(club_service.get_clubs_for_sim_info(subject))
                return set()

            clubs_to_test = None
            for subject in itertools.chain(test_subjects, test_targets):
                subject_clubs = get_clubs_for_subject(subject)
                clubs_to_test = subject_clubs if clubs_to_test is None else clubs_to_test & subject_clubs
        if not clubs_to_test:
            return self.test_gathering(None, test_subjects, test_targets)
        if not any(self.test_gathering(club, test_subjects, test_targets) for club in clubs_to_test):
            return TestResult(False, 'Subjects {} or Targets {} failed the club gatherings test for {}.', test_subjects, test_targets, clubs_to_test)
        else:
            return TestResult.TRUE
TunableClubGatheringTest = TunableSingletonFactory.create_auto_factory(ClubGatheringTest)
class ClubTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    _AffordanceData = namedtuple('_AffordanceData', ('affordance', 'target'))
    CLUB_USE_ASSOCIATED = 1
    CLUB_USE_ANY = 2
    CLUB_FROM_EVENT_DATA = 3
    AFFORDANCE_RULE_ENCOURAGED = 1
    AFFORDANCE_RULE_DISCOURAGED = 2
    AFFORDANCE_RULE_NOT_ENCOURAGED = 3
    AFFORDANCE_RULE_NOT_DISCOURAGED = 4
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject whose Club status to check.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'require_common_club': OptionalTunable(description='\n            If enabled, then there must be a common Club that both the subject\n            Sim and this specified Sim are in. If the club type is set to "Use\n            Club from Resolver", then both Sims must be in that Club. If the\n            club type is set to "Use Any Club", then there must be one club both\n            the subject Sim and this Sim are in.\n            ', tunable=TunableEnumEntry(description='\n                The Sim to test against for a common Club. If a multi-Sim\n                participant is specified, the union of their clubs is\n                considered, i.e. the test passes if at least one Sim satisfies\n                the requirements.\n                ', tunable_type=ParticipantType, default=ParticipantType.TargetSim)), 'club': TunableVariant(description='\n            Define the Club to run this test against.\n            ', locked_args={'use_club_from_resolver': CLUB_USE_ASSOCIATED, 'use_any_club': CLUB_USE_ANY, 'from_event_data': CLUB_FROM_EVENT_DATA}, default='use_club_from_resolver'), 'club_status': OptionalTunable(TunableVariant(description='\n            In enabled, require the tuned "subject" to either be or not be a\n            member of this interaction\'s associated Club.\n            ', locked_args={'Member': MEMBER, 'Not Member': NOT_MEMBER, 'Leader': LEADER, 'Not Leader': NOT_LEADER})), 'recent_member_status': OptionalTunable(description='\n            If specified, the Sim must satisfy recent member status\n            requirements.\n            ', tunable=Tunable(description='\n                Whether or not the Sim must be a recent member of the Club in\n                order to pass this test.\n                ', tunable_type=bool, default=True)), 'room_for_new_members': OptionalTunable(TunableVariant(description='\n            If enabled, require the associated Club to either have room for new\n            members or not have room for new members.\n            ', locked_args={'Has Room': True, 'Has No Room': False})), 'invite_only': OptionalTunable(Tunable(description='\n            If enabled, require the associated Club to either be invite only or\n            be open to everyone.\n            ', tunable_type=bool, default=True)), 'subject_relationship_with_leader': OptionalTunable(description='\n            If enabled, the tuned subject is required to have a specific\n            relationship with the leader. If the subject and the leader match,\n            the test fails.\n            ', tunable=TunableRelationshipTest(locked_args={'subject': None, 'target_sim': None, 'num_relations': 1, 'tooltip': None})), 'subject_passes_membership_criteria': OptionalTunable(TunableVariant(description='\n            If enabled, require the tuned "subject" to either pass this\n            associated Club\'s membership criteria or not pass the membership\n            criteria.\n            ', locked_args={'Passes Criteria': True, 'Does Not Pass Criteria': False})), 'subject_can_join_more_clubs': OptionalTunable(TunableVariant(description='\n            If enabled, require the tuned "subject" to be allowed to join more\n            Clubs or not.\n            \n            The maximum number of Clubs per Sim is set in\n            club_tuning.ClubTunables in the "MAX_CLUBS_PER_SIM" tunable.\n            ', locked_args={'Can Join More Clubs': True, 'Cannot Join More Clubs': False})), 'required_sim_count': OptionalTunable(description='\n            If enabled then this test will only pass if the group has a number \n            of members that passes the tuned threshold.\n            ', tunable=TunableThreshold(description='\n                The member requirement for this test to pass.\n                ')), 'affordance_rule': OptionalTunable(description='\n            If set, then the affordance being tested (should one exist) must\n            satisfy this rule requirement.\n            ', tunable=TunableVariant(description='\n                The rule requirement that the affordance must satisfy.\n                ', locked_args={'is_encouraged': AFFORDANCE_RULE_ENCOURAGED, 'is_discouraged': AFFORDANCE_RULE_DISCOURAGED, 'is_not_encouraged': AFFORDANCE_RULE_NOT_ENCOURAGED, 'is_not_discouraged': AFFORDANCE_RULE_NOT_DISCOURAGED}, default='is_encouraged')), 'pass_if_any_clubs_pass': Tunable(description='\n            If checked then this test will pass if any of the clubs match the\n            requirements otherwise we require all clubs to meet the\n            requirements.\n            ', tunable_type=bool, default=False)}
    test_events = (TestEvent.ClubMemberAdded, TestEvent.LeaderAssigned)

    def get_expected_args(self):
        expected_args = {'test_subjects': self.subject}
        if self.club == self.CLUB_USE_ASSOCIATED:
            expected_args['associated_clubs'] = ParticipantType.AssociatedClub
        elif self.club == self.CLUB_FROM_EVENT_DATA:
            expected_args['associated_clubs'] = event_testing.test_constants.FROM_EVENT_DATA
        if self.require_common_club is not None:
            expected_args['common_test_subjects'] = self.require_common_club
        if self.affordance_rule is not None:
            expected_args['affordance'] = ParticipantType.Affordance
            expected_args['affordance_targets'] = ParticipantType.Object
        return expected_args

    def _club_test_enabled(self):
        if self.recent_member_status is not None or (self.room_for_new_members is not None or (self.invite_only is not None or (self.subject_passes_membership_criteria is not None or (self.subject_relationship_with_leader is not None or self.required_sim_count)))) or self.affordance_rule:
            return True
        return False

    def _club_status_test(self, subject, clubs):
        if self.club_status is None:
            return TestResult.TRUE
        if not clubs:
            if self.club_status == NOT_MEMBER or self.club_status == NOT_LEADER:
                return TestResult.TRUE
            return TestResult(False, 'Subject {} is not a member or leader of any clubs', subject, tooltip=self.tooltip)
        passing_clubs = 0
        for club in clubs:
            in_members_list = subject in club.members
            is_leader = subject is club.leader
            if self.club_status == MEMBER and not in_members_list:
                if self.pass_if_any_clubs_pass:
                    pass
                else:
                    return TestResult(False, 'Subject {} not a member of Club {} but should be.', subject, club, tooltip=self.tooltip)
                    if self.club_status == NOT_MEMBER and in_members_list:
                        if self.pass_if_any_clubs_pass:
                            pass
                        else:
                            return TestResult(False, "Subject {} is a member of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                            if self.club_status == LEADER and not is_leader:
                                if self.pass_if_any_clubs_pass:
                                    pass
                                else:
                                    return TestResult(False, 'Subject {} is not the leader of Club {} but should be.', subject, club, tooltip=self.tooltip)
                                    if self.club_status == NOT_LEADER and is_leader:
                                        if self.pass_if_any_clubs_pass:
                                            pass
                                        else:
                                            return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                                            passing_clubs += 1
                                    passing_clubs += 1
                            if self.club_status == NOT_LEADER and is_leader:
                                if self.pass_if_any_clubs_pass:
                                    pass
                                else:
                                    return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                                    passing_clubs += 1
                            passing_clubs += 1
                    if self.club_status == LEADER and not is_leader:
                        if self.pass_if_any_clubs_pass:
                            pass
                        else:
                            return TestResult(False, 'Subject {} is not the leader of Club {} but should be.', subject, club, tooltip=self.tooltip)
                            if self.club_status == NOT_LEADER and is_leader:
                                if self.pass_if_any_clubs_pass:
                                    pass
                                else:
                                    return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                                    passing_clubs += 1
                            passing_clubs += 1
                    if self.club_status == NOT_LEADER and is_leader:
                        if self.pass_if_any_clubs_pass:
                            pass
                        else:
                            return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                            passing_clubs += 1
                    passing_clubs += 1
            if self.club_status == NOT_MEMBER and in_members_list:
                if self.pass_if_any_clubs_pass:
                    pass
                else:
                    return TestResult(False, "Subject {} is a member of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                    if self.club_status == LEADER and not is_leader:
                        if self.pass_if_any_clubs_pass:
                            pass
                        else:
                            return TestResult(False, 'Subject {} is not the leader of Club {} but should be.', subject, club, tooltip=self.tooltip)
                            if self.club_status == NOT_LEADER and is_leader:
                                if self.pass_if_any_clubs_pass:
                                    pass
                                else:
                                    return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                                    passing_clubs += 1
                            passing_clubs += 1
                    if self.club_status == NOT_LEADER and is_leader:
                        if self.pass_if_any_clubs_pass:
                            pass
                        else:
                            return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                            passing_clubs += 1
                    passing_clubs += 1
            if self.club_status == LEADER and not is_leader:
                if self.pass_if_any_clubs_pass:
                    pass
                else:
                    return TestResult(False, 'Subject {} is not the leader of Club {} but should be.', subject, club, tooltip=self.tooltip)
                    if self.club_status == NOT_LEADER and is_leader:
                        if self.pass_if_any_clubs_pass:
                            pass
                        else:
                            return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                            passing_clubs += 1
                    passing_clubs += 1
            if self.club_status == NOT_LEADER and is_leader:
                if self.pass_if_any_clubs_pass:
                    pass
                else:
                    return TestResult(False, "Subject {} is the leader of Club {} but shouldn't be.", subject, club, tooltip=self.tooltip)
                    passing_clubs += 1
            passing_clubs += 1
        if self.pass_if_any_clubs_pass and passing_clubs == 0:
            return TestResult(False, 'Subject {} not in any clubs that pass the criteria.', subject, tooltip=self.tooltip)
        return TestResult.TRUE

    def _test_club(self, subject, club, affordance_data=None):
        club_service = services.get_club_service()
        if self.recent_member_status is not None:
            is_recent_member = club.is_recent_member(subject)
            if self.recent_member_status != is_recent_member:
                return TestResult(False, "Subject {}'s recent member status in {} is {}, but the required status is {}", subject, club, is_recent_member, self.recent_member_status, tooltip=self.tooltip)
        if self.room_for_new_members is not None:
            club_has_room = len(club.members) < club.get_member_cap()
            if self.room_for_new_members and not club_has_room:
                return TestResult(False, 'Club {} has no room for new members but is required to.', club, tooltip=self.tooltip)
            if self.room_for_new_members or club_has_room:
                return TestResult(False, 'Club {} has room for new members but is required not to.', club, tooltip=self.tooltip)
        if self.invite_only is not None and club.invite_only != self.invite_only:
            return TestResult(False, "Club {}'s invite_only status is expected to be {} but isn't.", club, self.invite_only, tooltip=self.tooltip)
        if self.subject_passes_membership_criteria is not None:
            subject_result = club.validate_sim_info(subject)
            if subject_result and not self.subject_passes_membership_criteria:
                return TestResult(False, 'Subject {} passes the membership criteria for Club {} but is required not to.', subject, club, tooltip=self.tooltip)
            if subject_result or self.subject_passes_membership_criteria:
                return TestResult(False, 'Subject {} does not pass the membership criteria for Club {} but is required to.', subject, club, tooltip=self.tooltip)
        if self.subject_relationship_with_leader is not None:
            if subject is club.leader:
                return TestResult(False, 'Subject {} requires relationship with the leader, but is the leader of Club {}', subject, club, tooltip=self.tooltip)
            relationship_test_result = self.subject_relationship_with_leader(source_sims=(subject,), target_sims=(club.leader,))
            if not relationship_test_result:
                return relationship_test_result
        if self.required_sim_count is not None and not self.required_sim_count.compare(len(club.members)):
            return TestResult(False, "The club {} doesn't meet the required sim count of {}", club, self.required_sim_count, tooltip=self.tooltip)
        if self.affordance_rule is not None:
            if club_service is None:
                return TestResult(False, 'Affordance {} does not satisfy the required Club rules requirements. There is no club service.', affordance_data.affordance, tooltip=self.tooltip)
            (rule_status, _) = club_service.get_interaction_encouragement_status_and_rules_for_sim_info(subject, affordance_data)
            if self.affordance_rule == self.AFFORDANCE_RULE_ENCOURAGED:
                if rule_status != ClubRuleEncouragementStatus.ENCOURAGED:
                    return TestResult(False, 'Affordance {} does not satisfy the required Club rules requirements', affordance_data.affordance, tooltip=self.tooltip)
            elif self.affordance_rule == self.AFFORDANCE_RULE_DISCOURAGED:
                if rule_status != ClubRuleEncouragementStatus.DISCOURAGED:
                    return TestResult(False, 'Affordance {} does not satisfy the required Club rules requirements', affordance_data.affordance, tooltip=self.tooltip)
            elif self.affordance_rule == self.AFFORDANCE_RULE_NOT_ENCOURAGED:
                if rule_status == ClubRuleEncouragementStatus.ENCOURAGED:
                    return TestResult(False, 'Affordance {} does not satisfy the required Club rules requirements', affordance_data.affordance, tooltip=self.tooltip)
            elif self.affordance_rule == self.AFFORDANCE_RULE_NOT_DISCOURAGED and rule_status == ClubRuleEncouragementStatus.DISCOURAGED:
                return TestResult(False, 'Affordance {} does not satisfy the required Club rules requirements', affordance_data.affordance, tooltip=self.tooltip)
        return TestResult.TRUE

    def __call__(self, test_subjects=(), associated_clubs=(), common_test_subjects=(), affordance=None, affordance_targets=()):
        club_service = services.get_club_service()

        def get_clubs_for_subject(subject):
            if self.club == self.CLUB_USE_ANY or associated_clubs is None:
                if club_service is not None:
                    return tuple(club_service.get_clubs_for_sim_info(subject))
                return ()
            elif self.club == self.CLUB_USE_ASSOCIATED or self.club == self.CLUB_FROM_EVENT_DATA:
                return associated_clubs
            return ()

        for subject in test_subjects:
            if self.subject_can_join_more_clubs is not None:
                can_join_new_club = club_service.can_sim_info_join_more_clubs(subject) if club_service is not None else False
                if can_join_new_club and not self.subject_can_join_more_clubs:
                    return TestResult(False, "Subject {} is allowed to join more Clubs but shouldn't be.", subject, tooltip=self.tooltip)
                if can_join_new_club or self.subject_can_join_more_clubs:
                    return TestResult(False, 'Subject {} is not allowed to join more Clubs but should be.', subject, tooltip=self.tooltip)
            clubs = get_clubs_for_subject(subject)
            result = self._club_status_test(subject, clubs)
            if not result:
                return result
            if common_test_subjects:
                common_test_clubs = set(club for s in common_test_subjects for club in get_clubs_for_subject(s))
                if not set(clubs) & common_test_clubs:
                    return TestResult(False, "Subject {} and {} don't share an appropriate common Club", subject, common_test_subjects, tooltip=self.tooltip)
            affordance_data = self._AffordanceData(affordance, next(iter(affordance_targets), None))
            if not (self._club_test_enabled() and any(self._test_club(subject, club, affordance_data=affordance_data) for club in clubs)):
                return TestResult(False, 'Subject {} fails Club test for {}', subject, clubs, tooltip=self.tooltip)
        return TestResult.TRUE
