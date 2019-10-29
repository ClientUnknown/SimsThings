from drama_scheduler.drama_node import BaseDramaNode, DramaNodeParticipantOptionfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DoubleSimResolverfrom sims4.tuning.tunable import TunableReference, OptionalTunable, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_job import SituationJobfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4logger = sims4.log.Logger('SituationDramaNode', default_owner='bosee')
class SituationDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'situation_to_run': TunableReference(description='\n            The situation that this drama node will try and start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), tuning_group=GroupNames.SITUATION), 'sender_sim_info_job': OptionalTunable(description='\n            When enabled, this job will be assigned to sender sim.\n            A validation error will be thrown if sender_sim_info_job is set\n            but not sender_sim_info.\n            ', tunable=SituationJob.TunableReference(description='\n                The default job for the sender of this drama node.\n                ')), 'notification': OptionalTunable(description='\n            If enabled this is the notification that will be displayed after\n            the situation is started.\n            ', tunable=UiDialogNotification.TunableFactory(description='\n                The notification that displays when the situation is started.\n                ')), 'household_milestone': OptionalTunable(description='\n            If enabled, the household milestone will reset when the situation runs.\n            Only resets if the situation is run successfully. Useful for situations\n            that are spun up when a household milestone is unlocked.\n            ', tunable=TunableReference(pack_safe=True, manager=services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE))), 'homelot_only': Tunable(description='\n            If checked, the situation will only be permitted to run if the active\n            sims are on their homelot.\n            ', tunable_type=bool, default=False)}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.SITUATION

    @classproperty
    def spawn_sims_during_zone_spin_up(cls):
        return False

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.sender_sim_info_job is not None and cls.sender_sim_info.type == DramaNodeParticipantOption.DRAMA_PARTICIPANT_OPTION_NONE:
            logger.error('Setting sender sim info job but sender sim info is set to None for {}. Please make sure that sender sim info is set correctly.', cls)

    def _run(self):
        homelot_id = services.active_household().home_zone_id
        if self.homelot_only and homelot_id != services.current_zone_id():
            return False
        guest_list = self.situation_to_run.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        if self._sender_sim_info is not None and self.sender_sim_info_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(self._sender_sim_info.id, self.sender_sim_info_job, SituationInvitationPurpose.INVITED))
        situation_id = services.get_zone_situation_manager().create_situation(self.situation_to_run, guest_list=guest_list, spawn_sims_during_zone_spin_up=self.spawn_sims_during_zone_spin_up, user_facing=False)
        if self.household_milestone and situation_id:
            active_household_milestone_tracker = services.active_household().household_milestone_tracker
            active_household_milestone_tracker.reset_milestone(self.household_milestone)
        if self.notification is not None:
            dialog = self.notification(self._receiver_sim_info, DoubleSimResolver(self._sender_sim_info, self._receiver_sim_info), target_sim_id=self._sender_sim_info.id)
            dialog.show_dialog()
        return True
