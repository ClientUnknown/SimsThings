import randomfrom drama_scheduler.drama_node import BaseDramaNode, _DramaParticipant, CooldownOptionfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DoubleSimResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom gsi_handlers.drama_handlers import GSIRejectedDramaNodeScoringDatafrom interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, OptionalTunable, Tunable, TunableTuple, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.npc_hosted_situations import NPCHostedSituationDialogfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom ui.ui_dialog_picker import SimPickerRowimport build_buyimport servicesimport sims4.resourcesimport telemetry_helperlogger = sims4.log.Logger('DramaNode', default_owner='jjacobson')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_SITUATION_INVITED = 'INVI'TELEMETRY_HOOK_SITUATION_ACCEPTED = 'ACCE'TELEMETRY_HOOK_SITUATION_REJECTED = 'REJE'TELEMETRY_SITUATION_TYPE_ID = 'type'TELEMETRY_GUEST_COUNT = 'gcou'TELEMETRY_CHOSEN_ZONE = 'czon'telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)ZONE_ID_TOKEN = 'zone_id'STREET_TOKEN = 'street'
class NPCInviteSituationDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'sender_sim_info': _DramaParticipant(description='\n            Tuning for selecting the sending sim.\n            \n            The sending sim is considered the sim who will be sending this\n            DramaNode.\n            ', excluded_options=('no_participant',), tuning_group=GroupNames.PARTICIPANT), '_situation_to_run': TunableReference(description='\n            The situation that this drama node will try and start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), tuning_group=GroupNames.SITUATION), '_NPC_host_job': OptionalTunable(description='\n            If enabled then the NPC host will be assigned this specific job in\n            the situation.\n            ', tunable=TunableReference(description='\n                The job that will be assigned to the NPC host of an NPC hosted\n                situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=GroupNames.SITUATION), '_use_alternate_host': OptionalTunable(description='\n            If enabled then we will find a different host Sim for this\n            situation rather than using the Sending Sim as the host.\n            ', tunable=TunableReference(description='\n                The filter that we will use to fine and potentially\n                generate a new host Sim for this situation.  This will\n                be run off of the sending Sim as the requesting Sim unless\n                NPC Hosted Situation Use Player Sim As Filter Requester\n                has been checked.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)), tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_start_messages': TunableList(description="\n        \tA List of tests and UiDialogs that should be considered for showing\n\t\t\tas an npc invite. \n\t\t\t\n\t\t\tIf more than one dialog passes all of it's tests\n\t\t\tthen one dialog will be chosen at random.\n            ", tunable=TunableTuple(description='\n            \tA combination of UiDialog and test where if the tuned tests pass\n\t\t\t\tthen the dialog will be considered as a choice to be displayed. \n\t\t\t\tAfter all choices have been tested one of the dialogs will be\n\t\t\t\tchosen at random.\n                ', dialog=NPCHostedSituationDialog.TunableFactory(description='\n                    The message that will be displayed when this situation\n                    tries to start for the initiating sim.\n                    '), tests=TunableTestSet()), tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_player_job': OptionalTunable(description='\n            The job that the player will be put into when they they are\n            invited into an NPC hosted version of this event.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_use_player_sim_as_filter_requester': Tunable(description='\n            If checked then when gathering sims for an NPC hosted situation\n            the filter system will look at households and and relationships\n            relative to the player sim rather than the NPC host.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_host_event_at_NPCs_residence': Tunable(description="\n            If checked then the situation will be started at the NPC host's\n            residence rather than just choosing a venue type.  If the NPC\n            host does not have a residence, then we use the venue type as\n            a backup.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_scoring_enabled': Tunable(description='\n            If checked then the NPC hosted situation will start with\n            scoring enabled.  If unchecked the situation will have scoring\n            disabled and no rewards will be given.  If you check the Hidden\n            Scoring Override then the and leave this unchecked then the\n            event will look like an event with no score, but score will\n            still be tracked and rewards will still be given.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_require_predefined_guest_list': Tunable(description='\n            If checked then the situation will not start if there is no\n            predefined guest list.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_user_facing': Tunable(description='\n            If checked then the situation will be user facing.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.SITUATION), '_show_dialog_venue_type': Tunable(description='\n            If checked then we show the name and icon of the venue you will\n            travel to.\n            ', tunable_type=bool, default=True)}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.SITUATION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_id = None
        self._street = None
        self._chosen_dialog = None

    def _get_zone_id(self):
        if self._zone_id is not None and self._situation_to_run.is_venue_location_valid(self._zone_id):
            return self._zone_id
        self._zone_id = None
        if self._street is not None:
            lot_id = self._street.get_lot_to_travel_to()
            if lot_id is None:
                return services.current_zone_id()
            persistence_service = services.get_persistence_service()
            self._zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
            return self._zone_id
        if self._host_event_at_NPCs_residence:
            zone_id = self._sender_sim_info.vacation_or_home_zone_id
            if zone_id is not None:
                self._zone_id = zone_id
                return self._zone_id
        if self._situation_to_run.has_venue_location():
            zone_id = self._situation_to_run.get_venue_location()
            if zone_id is not None:
                self._zone_id = zone_id
        return self._zone_id

    def _get_resolver(self):
        resolver = super()._get_resolver()
        resolver.set_additional_participant(ParticipantType.PickedZoneId, (self._get_zone_id(),))
        return resolver

    def _get_host(self, additional_sims_to_bring):
        if self._use_alternate_host is None:
            return self._sender_sim_info
        blacklist = {sim_info.id for sim_info in additional_sims_to_bring}
        blacklist.add(self._sender_sim_info.id)
        blacklist.intersection_update({sim_info.id for sim_info in services.active_household()})
        if self._NPC_hosted_situation_use_player_sim_as_filter_requester:
            requesting_sim_info = self._receiver_sim_info
        else:
            requesting_sim_info = self._sender_sim_info
        host = services.sim_filter_service().submit_matching_filter(sim_filter=self._use_alternate_host, requesting_sim_info=requesting_sim_info, blacklist_sim_ids=blacklist, allow_yielding=False)
        if not host:
            return
        return next(iter(host)).sim_info

    def _create_situation(self, additional_sims_to_bring=()):
        guest_list = self._situation_to_run.get_predefined_guest_list()
        if guest_list is None:
            if self._require_predefined_guest_list:
                return
            host_sim_info = self._get_host(additional_sims_to_bring)
            if host_sim_info is None:
                return
            guest_list = SituationGuestList(invite_only=True, host_sim_id=host_sim_info.id)
        else:
            host_sim_info = self._get_host(additional_sims_to_bring)
            if host_sim_info is None:
                return
        if self._NPC_hosted_situation_player_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(self._receiver_sim_info.id, self._NPC_hosted_situation_player_job, SituationInvitationPurpose.INVITED))
        if self._NPC_host_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(host_sim_info.id, self._NPC_host_job, SituationInvitationPurpose.INVITED))
        if additional_sims_to_bring:
            additional_sims_job = self._chosen_dialog.bring_other_sims.situation_job
            for sim_info in additional_sims_to_bring:
                guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(sim_info.id, additional_sims_job, SituationInvitationPurpose.INVITED))
        if self._NPC_hosted_situation_use_player_sim_as_filter_requester:
            guest_list.filter_requesting_sim_id = self._receiver_sim_info.id
        services.get_zone_situation_manager().create_situation(self._situation_to_run, guest_list=guest_list, zone_id=self._get_zone_id(), scoring_enabled=self._NPC_hosted_situation_scoring_enabled, user_facing=self._user_facing)
        with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_ACCEPTED, sim_info=self._receiver_sim_info) as hook:
            hook.write_guid(TELEMETRY_SITUATION_TYPE_ID, self._situation_to_run.guid64)
            hook.write_int(TELEMETRY_GUEST_COUNT, len(additional_sims_to_bring))

    def _handle_picker_dialog(self, dialog):
        if not dialog.accepted:
            with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_REJECTED, sim_info=self._receiver_sim_info) as hook:
                hook.write_guid('type', self._situation_to_run.guid64)
        else:
            picked_sims = dialog.get_result_tags()
            self._create_situation(additional_sims_to_bring=picked_sims)
        services.drama_scheduler_service().complete_node(self.uid)

    def _handle_dialog(self, dialog):
        if dialog.accepted or dialog.response != NPCHostedSituationDialog.BRING_OTHER_SIMS_RESPONSE_ID:
            with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_REJECTED, sim_info=self._receiver_sim_info) as hook:
                hook.write_guid(TELEMETRY_SITUATION_TYPE_ID, self._situation_to_run.guid64)
            services.drama_scheduler_service().complete_node(self.uid)
            return
        if dialog.response == NPCHostedSituationDialog.BRING_OTHER_SIMS_RESPONSE_ID:
            bring_other_sims_data = self._chosen_dialog.bring_other_sims
            picker_dialog = bring_other_sims_data.picker_dialog(self._receiver_sim_info, resolver=self._get_resolver())
            blacklist = {sim_info.id for sim_info in self._sender_sim_info.household.sim_info_gen()}
            blacklist.add(self._receiver_sim_info.id)
            results = services.sim_filter_service().submit_filter(bring_other_sims_data.travel_with_filter, callback=None, requesting_sim_info=self._receiver_sim_info, blacklist_sim_ids=blacklist, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
            for result in results:
                picker_dialog.add_row(SimPickerRow(result.sim_info.sim_id, tag=result.sim_info))
            picker_dialog.show_dialog(on_response=self._handle_picker_dialog)
            return
        self._create_situation()
        services.drama_scheduler_service().complete_node(self.uid)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def _run(self):
        zone_id = self._get_zone_id()
        with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_INVITED, sim_info=self._receiver_sim_info) as hook:
            hook.write_guid(TELEMETRY_SITUATION_TYPE_ID, self._situation_to_run.guid64)
            hook.write_int(TELEMETRY_CHOSEN_ZONE, zone_id)
        additional_tokens = []
        if zone_id == 0:
            logger.error('Drama Node {} trying to be run with zone id of 0.  This is probably an issue with getting the zone id from the street.', self)
            zone_id = services.current_zone_id()
        venue_type_id = build_buy.get_current_venue(zone_id)
        if venue_type_id is not None:
            venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
            venue_type = venue_manager.get(venue_type_id)
            if venue_type is not None:
                additional_tokens.append(venue_type.display_name)
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is not None:
            additional_tokens.append(zone_data.name)
        self._choose_dialog()
        dialog = self._chosen_dialog(self._receiver_sim_info, target_sim_id=self._sender_sim_info.id, resolver=self._get_resolver())
        if self._chosen_dialog is None:
            return False
        dialog_zone_id = zone_id if self._show_dialog_venue_type else None
        dialog.show_dialog(on_response=self._handle_dialog, zone_id=dialog_zone_id, additional_tokens=additional_tokens)
        return False

    def _choose_dialog(self):
        choices = []
        resolver = DoubleSimResolver(self._receiver_sim_info, self._sender_sim_info)
        for dialog_data in self._NPC_hosted_situation_start_messages:
            if dialog_data.tests.run_tests(resolver):
                choices.append(dialog_data.dialog)
        if choices:
            self._chosen_dialog = random.choice(choices)

    def _test(self, resolver, skip_run_tests=False):
        if self._get_zone_id() is None:
            return TestResult(False, 'Cannot run because there is no zone to run this at.')
        if self._sender_sim_info is None:
            return TestResult(False, 'Cannot run because there is no sender sim info.')
        if not skip_run_tests:
            if services.get_zone_situation_manager().is_user_facing_situation_running(global_user_facing_only=True):
                return TestResult(False, 'Did not start NPC Hosted Situation because user facing situation was running.')
            if services.get_persistence_service().is_save_locked():
                return TestResult(False, 'Could not start situation since the game is save locked.')
        result = super()._test(resolver, skip_run_tests=skip_run_tests)
        if not result:
            return result
        return TestResult.TRUE

    def _setup(self, *args, street_override=None, gsi_data=None, zone_id=None, **kwargs):
        result = super()._setup(*args, gsi_data=gsi_data, **kwargs)
        if not result:
            return result
        else:
            if zone_id is not None:
                self._zone_id = zone_id
            if street_override is not None:
                self._street = street_override
            if self._get_zone_id() is None:
                if gsi_data is not None:
                    gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), 'There is no valid zone found when trying to setup this drama node.'))
                return False
        return True

    def cleanup(self, from_service_stop=False):
        super().cleanup(from_service_stop=from_service_stop)
        self._zone_id = None
        self._street = None

    def _save_custom_data(self, writer):
        if self._zone_id is not None:
            writer.write_uint64(ZONE_ID_TOKEN, self._zone_id)
        if self._street is not None:
            writer.write_uint64(STREET_TOKEN, self._street.guid64)

    def _load_custom_data(self, reader):
        self._zone_id = reader.read_uint64(ZONE_ID_TOKEN, None)
        street_id = reader.read_uint64(STREET_TOKEN, None)
        if street_id is not None:
            self._street = services.street_manager().get(street_id)
        return True
lock_instance_tunables(NPCInviteSituationDramaNode, cooldown_option=CooldownOption.ON_RUN)