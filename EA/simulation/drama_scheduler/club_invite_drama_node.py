import randomfrom drama_scheduler.drama_node import BaseDramaNode, _DramaParticipant, CooldownOptionfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.results import TestResultfrom gsi_handlers.drama_handlers import GSIRejectedDramaNodeScoringDatafrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom ui.ui_dialog import UiDialogOkCancelimport services
class ClubInviteBaseDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'sender_sim_info': _DramaParticipant(description='\n            Specify who the sending Sim must be. This is the Sim that will "text"\n            the Drama Node owner.\n            ', excluded_options=('no_participant',), tuning_group=GroupNames.PARTICIPANT), 'dialog': UiDialogOkCancel.TunableFactory(description='\n            The dialog that is displayed to the player Sim once this Drama Node\n            executes. Upon acceptance, the behavior specific to this Drama Node\n            executes.\n            ')}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.CLUB

    def _setup(self, *args, gsi_data=None, **kwargs):
        result = super()._setup(*args, gsi_data=gsi_data, **kwargs)
        if not result:
            return result
        club_service = services.get_club_service()
        if club_service is None:
            if gsi_data is not None:
                gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), 'Club service is None.'))
            return False
        clubs = self._get_possible_clubs()
        if not clubs:
            if gsi_data is not None:
                gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), 'No possible clubs found.'))
            return False
        club = random.choice(clubs)
        self._club_id = club.club_id
        return True

    def _get_possible_clubs(self):
        raise NotImplementedError

    def _test(self, resolver, skip_run_tests=False):
        if self._club_id is None:
            return TestResult(False, 'Cannot run because there is no chosen node.')
        if self._sender_sim_info is None:
            return TestResult(False, 'Cannot run because there is no sender sim info.')
        if not skip_run_tests:
            club = services.get_club_service().get_club_by_id(self._club_id)
            if club is None:
                return TestResult(False, 'Cannot run because the club no longer exists.')
            result = self._test_club(club)
            if not result:
                return result
        return super()._test(resolver, skip_run_tests=skip_run_tests)

    def _test_club(self, club):
        raise NotImplementedError

    def _run(self):

        def on_response(dialog):
            if dialog.accepted:
                club = services.get_club_service().get_club_by_id(self._club_id)
                self._run_club_behavior(club)
            services.drama_scheduler_service().complete_node(self.uid)

        dialog = self.dialog(self._receiver_sim_info, target_sim_id=self._sender_sim_info.id, resolver=self._get_resolver())
        club = services.get_club_service().get_club_by_id(self._club_id)
        dialog.show_dialog(on_response=on_response, additional_tokens=(club.name,))
        return False

    def _run_club_behavior(self, club):
        raise NotImplementedError
lock_instance_tunables(ClubInviteBaseDramaNode, cooldown_option=CooldownOption.ON_RUN)
class ClubInviteDramaNode(ClubInviteBaseDramaNode):

    def _get_possible_clubs(self):
        club_service = services.get_club_service()
        return tuple(club for club in club_service.get_clubs_for_sim_info(self._sender_sim_info) if self._test_club(club))

    def _test_club(self, club):
        if self._sender_sim_info not in club.members:
            return TestResult(False, 'Cannot run because the sender Sim is no longer in the chosen Club.')
        if not club.can_sim_info_join(self._receiver_sim_info):
            return TestResult(False, 'Cannot run because the receiver Sim can no longer join the chosen Club')
        return TestResult.TRUE

    def _run_club_behavior(self, club):
        if club.can_sim_info_join(self._receiver_sim_info):
            club.add_member(self._receiver_sim_info)

class ClubInviteRequestDramaNode(ClubInviteBaseDramaNode):
    INSTANCE_TUNABLES = {'invite_only': OptionalTunable(description='\n            If specified, then only Clubs of the appropriate invite exclusivity\n            type are valid for this Drama Node.\n            ', tunable=Tunable(description='\n                If checked, only invite-only Clubs are valid. If unchecked, only\n                open membership Clubs are valid.\n                ', tunable_type=bool, default=True))}

    def _get_possible_clubs(self):
        club_service = services.get_club_service()
        return tuple(club for club in club_service.get_clubs_for_sim_info(self._receiver_sim_info) if self._test_club(club))

    def _test_club(self, club):
        if self._receiver_sim_info is not club.leader:
            return TestResult(False, 'Cannot run because the receiver Sim is no longer the leader of the chosen Club')
        if not club.can_sim_info_join(self._sender_sim_info):
            return TestResult(False, 'Cannot run because the sender Sim can no longer join the chosen Club')
        if self.invite_only is not None and club.invite_only != self.invite_only:
            return TestResult(False, 'Cannot run because the chosen Club is not of the correct invite exclusivity type')
        return TestResult.TRUE

    def _run_club_behavior(self, club):
        if club.can_sim_info_join(self._sender_sim_info):
            club.add_member(self._sender_sim_info)
