from protocolbuffers import InteractionOps_pb2, Consts_pb2from audio.primitive import TunablePlayAudiofrom clock import ClockSpeedModefrom filters.tunable import TunableSimFilterfrom interactions.liability import Liabilityfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableReference, TunableSimMinutefrom sims4.tuning.tunable_base import ExportModesfrom world import regionimport distributorimport servicesimport sims4
class TravelTuning:
    ENTER_LOT_AFFORDANCE = TunableReference(services.affordance_manager(), description='SI to push when sim enters the lot.')
    EXIT_LOT_AFFORDANCE = TunableReference(services.affordance_manager(), description='SI to push when sim is exiting the lot.')
    NPC_WAIT_TIME = TunableSimMinute(15, description='Delay in sim minutes before pushing the ENTER_LOT_AFFORDANCE on a NPC at the spawn point if they have not moved.')
    TRAVEL_AVAILABILITY_SIM_FILTER = TunableSimFilter.TunableReference(description='Sim Filter to show what Sims the player can travel with to send to Game Entry.')
    TRAVEL_SUCCESS_AUDIO_STING = TunablePlayAudio(description='\n        The sound to play when we finish loading in after the player has traveled.\n        ')
    NEW_GAME_AUDIO_STING = TunablePlayAudio(description='\n        The sound to play when we finish loading in from a new game, resume, or\n        household move in.\n        ')
    GO_HOME_INTERACTION = TunableReference(description='\n        The interaction to push a Sim to go home.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
TRAVEL_SIM_LIABILITY = 'TravelSimLiability'
class TravelSimLiability(Liability):

    def __init__(self, interaction, sim_info, to_zone_id, expecting_dialog_response=False, is_attend_career=False, additional_sims=(), **kwargs):
        super().__init__(**kwargs)
        self.interaction = interaction
        self.expecting_dialog_response = expecting_dialog_response
        self.sim_info = sim_info
        self.to_zone_id = to_zone_id
        self.is_attend_career = is_attend_career
        self.additional_sims = additional_sims

    def should_transfer(self, continuation):
        return False

    def release(self):
        if self.interaction is not None:
            sim = self.sim_info.get_sim_instance()
            if self.interaction.allow_outcomes and not self.expecting_dialog_response:
                self._travel_sim()
            elif sim is not None and self.expecting_dialog_response:
                sim.fade_in()

    def _attend_career(self):
        career = self.sim_info.career_tracker.career_currently_within_hours
        if career is not None:
            career.attend_work()

    def _travel_sim(self):
        client = services.client_manager().get_first_client()
        self.sim_info.inject_into_inactive_zone(self.to_zone_id, skip_instanced_check=True)
        for sim in self.additional_sims:
            sim.sim_info.inject_into_inactive_zone(self.to_zone_id, skip_instanced_check=True)
            sim.sim_info.save_sim()
            sim.schedule_destroy_asap(post_delete_func=client.send_selectable_sims_update, source=self, cause='Destroying sim in travel liability')
        sim = self.sim_info.get_sim_instance()
        if sim is not None:
            next_sim_info = client.selectable_sims.get_next_selectable(self.sim_info)
            next_sim = next_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if next_sim is not sim:
                if self.is_attend_career:
                    self._attend_career()
                if sim.is_selected:
                    client.set_next_sim_or_none()
                self.sim_info.save_sim()
                sim.schedule_destroy_asap(post_delete_func=client.send_selectable_sims_update, source=self, cause='Destroying sim in travel liability')
            else:
                sim.fade_in()

    def travel_player(self):
        sim = self.sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        travel_info = InteractionOps_pb2.TravelSimsToZone()
        travel_info.zone_id = self.to_zone_id
        travel_info.sim_ids.append(sim.id)
        self.interaction = None
        if self.is_attend_career:
            self._attend_career()
        travel_group = self.sim_info.travel_group
        if travel_group is not None and not any(sim_info is not self.sim_info and sim_info in self.sim_info.household for sim_info in travel_group):
            dest_region = region.get_region_instance_from_zone_id(self.to_zone_id)
            current_region = services.current_region()
            if not current_region.is_region_compatible(dest_region):
                services.travel_group_manager().destroy_travel_group_and_release_zone(travel_group, last_sim_info=self.sim_info)
        rabbit_hole_service = services.get_rabbit_hole_service()
        if rabbit_hole_service.is_in_rabbit_hole(sim.sim_id):
            rabbit_hole_service.set_ignore_travel_cancel_for_sim_id_in_rabbit_hole(sim.sim_id)
        sim.queue.cancel_all()
        for sim in self.additional_sims:
            sim.queue.cancel_all()
            travel_info.sim_ids.append(sim.sim_id)
        distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_TRAVEL_SIMS_TO_ZONE, travel_info)
        services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)

    def travel_dialog_response(self, dialog):
        if dialog.accepted:
            self.travel_player()
        else:
            sim = self.sim_info.get_sim_instance()
            if sim is not None:
                sim.fade_in()
