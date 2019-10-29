from game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableReferenceimport servicesimport sims4.resourcesimport zone_types
class RelationshipTrackDecayLocker(HasTunableSingletonFactory, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'description': '\n        A modifier for locking the decay of a relationship track.\n        ', 'relationship_track': TunableReference(description='\n        The relationship track to lock.\n        ', manager=services.statistic_manager(), class_restrictions=('RelationshipTrack',))}
    tunable = (TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)),)

    def __init__(self, relationship_track, **kwargs):
        super().__init__(GameEffectType.RELATIONSHIP_TRACK_DECAY_LOCKER)
        self._track_type = relationship_track

    def apply_modifier(self, sim_info):

        def _all_sim_infos_loaded_callback(*arg, **kwargs):
            zone = services.current_zone()
            zone.unregister_callback(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, _all_sim_infos_loaded_callback)
            self._set_decay_lock_all_relationships(sim_info, lock=True)
            self._initialize_create_relationship_callback(sim_info)

        zone = services.current_zone()
        if zone.is_households_and_sim_infos_loaded or not zone.is_zone_running:
            zone.register_callback(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, _all_sim_infos_loaded_callback)
            return
        self._set_decay_lock_all_relationships(sim_info)
        self._initialize_create_relationship_callback(sim_info)

    def _initialize_create_relationship_callback(self, owner):
        tracker = owner.relationship_tracker
        tracker.add_create_relationship_listener(self._relationship_added_callback)

    def _set_decay_lock_all_relationships(self, owner, lock=True):
        tracker = owner.relationship_tracker
        sim_info_manager = services.sim_info_manager()
        for other_sim_id in tracker.target_sim_gen():
            other_sim_info = sim_info_manager.get(other_sim_id)
            if other_sim_info is None:
                pass
            else:
                track = tracker.get_relationship_track(other_sim_id, self._track_type, add=True)
                other_tracker = other_sim_info.relationship_tracker
                other_track = other_tracker.get_relationship_track(owner.id, self._track_type, add=True)
                if not track is None:
                    if other_track is None:
                        pass
                    elif lock:
                        track.add_decay_rate_modifier(0)
                        other_track.add_decay_rate_modifier(0)
                    else:
                        track.remove_decay_rate_modifier(0)
                        other_track.remove_decay_rate_modifier(0)

    def _relationship_added_callback(self, relationship):
        sim_a_track = relationship.get_track(self._track_type, add=True)
        if sim_a_track is not None:
            sim_a_track.add_decay_rate_modifier(0)

    def remove_modifier(self, sim_info, handle):
        tracker = sim_info.relationship_tracker
        tracker.remove_create_relationship_listener(self._relationship_added_callback)
        self._set_decay_lock_all_relationships(sim_info, lock=False)
