from drama_scheduler.drama_node_types import DramaNodeTypefrom drama_scheduler.situation_drama_node import SituationDramaNodefrom event_testing.resolver import DoubleSimResolverfrom interactions.utils.loot import LootActionsfrom relationships.relationship_track import RelationshipTrackfrom sims4.tuning.tunable import TunableRange, TunableListfrom sims4.utils import classpropertyfrom weather.weather_event import WeatherEventimport servicesimport sims4logger = sims4.log.Logger('TutorialDramaNode', default_owner='nabaker')
class TutorialDramaNode(SituationDramaNode):
    INSTANCE_TUNABLES = {'weather_to_force': WeatherEvent.TunablePackSafeReference(description='\n            The weather that will exist for the duration of this drama node.\n            '), 'friendship_value': TunableRange(description='\n            The value to set the friendship between player sim and housemate.\n            ', tunable_type=int, maximum=100, minimum=-100, default=20), 'romance_value': TunableRange(description='\n            The value to set the romance between player sim and housemate.\n            ', tunable_type=int, maximum=100, minimum=-100, default=0), 'end_loots': TunableList(description='\n            Loots to apply when the tutorial drama node ends.\n            \n            Player sim is Actor.\n            Housemate sim is Targetsim.\n            ', tunable=LootActions.TunableReference(pack_safe=True))}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.TUTORIAL

    @classproperty
    def spawn_sims_during_zone_spin_up(cls):
        return True

    @classproperty
    def persist_when_active(cls):
        return True

    @property
    def _require_instanced_sim(self):
        return False

    def _run(self):
        super()._run()
        self._disable_non_tutorial_functionality()
        return False

    def get_player_sim_info(self):
        return self._receiver_sim_info

    def get_housemate_sim_info(self):
        return self._sender_sim_info

    def resume(self):
        super().resume()
        self._disable_non_tutorial_functionality()

    def end(self):
        drama_service = services.drama_scheduler_service()
        drama_service.set_enabled_state(True)
        if self._receiver_sim_info is not None:
            household = self._receiver_sim_info.household
            if household is not None:
                household.bills_manager.autopay_bills = False
            if self._sender_sim_info is not None:
                sim_info = self._sender_sim_info
                household = self._receiver_sim_info.household
                if sim_info in household:
                    client = services.client_manager().get_first_client()
                    if not client.set_active_sim_info(self._receiver_sim_info):
                        logger.error('Tutorial Drama node ended without being able to set player sim to active.')
                    client.remove_selectable_sim_info(sim_info)
                    household.remove_sim_info(sim_info)
                    sim_info.transfer_to_hidden_household()
                relationship = services.relationship_service().create_relationship(self._receiver_sim_info.sim_id, sim_info.sim_id)
                if relationship is not None:
                    relationship.relationship_track_tracker.set_longterm_tracks_locked(False)
        npc_hosted_situation_service = services.npc_hosted_situation_service()
        if npc_hosted_situation_service is not None:
            npc_hosted_situation_service.resume_welcome_wagon()
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            situation = situation_manager.get_situation_by_type(self.situation_to_run)
            if situation is not None:
                situation_manager.destroy_situation_by_id(situation.id)
        weather_service = services.weather_service()
        if weather_service is not None:
            weather_service.reset_forecasts()
        fire_service = services.fire_service
        if fire_service is not None:
            fire_service.fire_enabled = True
        resolver = DoubleSimResolver(self._receiver_sim_info, self._sender_sim_info)
        for loot_action in self.end_loots:
            loot_action.apply_to_resolver(resolver)
        drama_service.complete_node(self.uid)

    def _disable_non_tutorial_functionality(self):
        services.drama_scheduler_service().set_enabled_state(False)
        npc_hosted_situation_service = services.npc_hosted_situation_service()
        if npc_hosted_situation_service is not None:
            npc_hosted_situation_service.suspend_welcome_wagon()
        if self._receiver_sim_info is not None:
            household = self._receiver_sim_info.household
            if household is not None:
                household.bills_manager.autopay_bills = True
            if self._sender_sim_info is not None:
                if self._receiver_sim_info.age == self._sender_sim_info.age:
                    receiver_age_progress = self._receiver_sim_info.age_progress
                    if receiver_age_progress <= self._sender_sim_info.age_progress:
                        if receiver_age_progress == 0:
                            self._receiver_sim_info.age_progress = 0.1
                        else:
                            self._sender_sim_info.age_progress = 0
                relationship_tracker = self._receiver_sim_info.relationship_tracker
                sender_id = self._sender_sim_info.sim_id
                relationship = services.relationship_service().create_relationship(self._receiver_sim_info.sim_id, sender_id)
                relationship_tracker.add_relationship_score(sender_id, self.friendship_value, RelationshipTrack.FRIENDSHIP_TRACK)
                relationship_tracker.add_relationship_score(sender_id, self.romance_value, RelationshipTrack.ROMANCE_TRACK)
                relationship.relationship_track_tracker.set_longterm_tracks_locked(True)
        weather_service = services.weather_service()
        if weather_service is not None:
            weather_service.force_start_weather_event(self.weather_to_force, None)
            weather_service.update_weather_type(during_load=True)
        fire_service = services.fire_service
        if fire_service is not None:
            fire_service.fire_enabled = False
