import itertoolsfrom audio.primitive import play_tunable_audiofrom fame.fame_tuning import FameTunablesfrom filters.sim_filter_service import SimFilterGlobalBlacklistReasonfrom interactions.si_restore import SuperInteractionRestorerfrom interactions.social.greeting_socials import greetingsfrom objects import ALL_HIDDEN_REASONSfrom objects.object_manager import DistributableObjectManagerfrom services.relgraph_service import RelgraphServicefrom sims.genealogy_tracker import genealogy_cachingfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_firemeter import SimInfoFireMeterfrom sims.sim_info_gameplay_options import SimInfoGameplayOptionsfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_telemetry import SimInfoTelemetryManagerfrom sims.sim_info_types import SimZoneSpinUpActionfrom sims4.callback_utils import CallableListfrom sims4.collections import enumdictfrom sims4.utils import classpropertyfrom ui import ui_tuningfrom world.travel_tuning import TravelTuningimport cachesimport clubsimport game_servicesimport interactions.utils.routingimport persistence_error_typesimport servicesimport sims.householdimport sims.sim_info_typesimport sims4.logimport worldwith sims4.reload.protected(globals()):
    SIM_INFO_CAP_PER_LOD = Nonelogger = sims4.log.Logger('SimInfoManager', default_owner='manus')relationship_setup_logger = sims4.log.Logger('DefaultRelSetup', default_owner='manus')
class SimInfoManager(DistributableObjectManager):
    SIM_INFO_CAP = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim_infos_saved_in_zone = []
        self._sim_infos_saved_in_plex_group = []
        self._sim_infos_saved_in_open_street = []
        self._sims_traveled_to_zone = []
        self._sim_infos_injected_into_zone = []
        self._sim_info_to_spin_up_action = None
        self._startup_time = None
        self._sim_ids_to_skip_preroll = set()
        self.on_sim_info_removed = CallableList()
        self._firemeter = None
        self._sim_info_telemetry_manager = SimInfoTelemetryManager()
        self._start_all_sims_opted_out_of_fame = False
        self._sim_info_cap_override = None

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_SIM_INFO_MANAGER

    def get_num_sim_infos_with_criteria(self, predicate):
        return sum(1 for sim_info in self.objects if predicate(sim_info))

    def get_num_sim_infos_with_lod(self, lod):
        return sum(1 for sim_info in self.objects if sim_info.lod == lod)

    def get_sim_infos_with_lod(self, lod):
        return set(sim_info for sim_info in self.objects if sim_info.lod == lod)

    def flush_to_client_on_teardown(self):
        for sim_info in self.objects:
            sim_info.flush_to_client_on_teardown()
        if self._firemeter is not None:
            self._firemeter.shutdown()
            self._firemeter = None

    def add_sim_info_if_not_in_manager(self, sim_info):
        if sim_info.id in self._objects:
            pass
        else:
            self.add(sim_info)

    def save(self, zone_data=None, open_street_data=None, **kwargs):
        self._sim_info_telemetry_manager.save()
        for sim_info in self.get_all():
            if sim_info.account_id is not None:
                sim_info.save_sim(full_service=True)

    def load(self, zone_data=None):
        self._sim_info_telemetry_manager.load()

    def load_options(self, options_proto):
        self.set_start_all_sims_opted_out_of_fame(options_proto.start_all_sims_opted_out_of_fame)

    def save_options(self, options_proto):
        options_proto.start_all_sims_opted_out_of_fame = self._start_all_sims_opted_out_of_fame

    def on_zone_unload(self):
        for sim_info in self.get_all():
            logger.assert_log(sim_info.account_id is not None, 'Bad assumption that sim info account can not be None: {}', sim_info)
            sim_info.on_zone_unload()

    def on_zone_load(self):
        zone = services.current_zone()
        plexes_in_group = services.get_plex_service().get_plex_zones_in_group(zone.id)
        for sim_info in tuple(self.values()):
            sim_info.on_zone_load()
            if sim_info.sim_id in self._sims_traveled_to_zone:
                sim_info._serialization_option = sims.sim_info_types.SimSerializationOption.UNDECLARED
            elif sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.LOT:
                if sim_info.zone_id == zone.id:
                    self._sim_infos_saved_in_zone.append(sim_info)
                elif sim_info.zone_id in plexes_in_group:
                    self._sim_infos_saved_in_plex_group.append(sim_info)
                    if sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.UNDECLARED:
                        if sim_info.zone_id == zone.id and sim_info.is_baby and sim_info.lives_here:
                            self._sim_infos_injected_into_zone.append(sim_info)
                            if sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.OPEN_STREETS and sim_info.world_id == zone.open_street_id:
                                self._sim_infos_saved_in_open_street.append(sim_info)
                    elif sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.OPEN_STREETS and sim_info.world_id == zone.open_street_id:
                        self._sim_infos_saved_in_open_street.append(sim_info)
            elif sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.UNDECLARED:
                if sim_info.zone_id == zone.id and sim_info.is_baby and sim_info.lives_here:
                    self._sim_infos_injected_into_zone.append(sim_info)
                    if sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.OPEN_STREETS and sim_info.world_id == zone.open_street_id:
                        self._sim_infos_saved_in_open_street.append(sim_info)
            elif sim_info.serialization_option == sims.sim_info_types.SimSerializationOption.OPEN_STREETS and sim_info.world_id == zone.open_street_id:
                self._sim_infos_saved_in_open_street.append(sim_info)

    def on_all_households_and_sim_infos_loaded(self, client):
        for sim_info in tuple(self.values()):
            sim_info.on_all_households_and_sim_infos_loaded()

    def add_sims_to_zone(self, sim_list):
        self._sims_traveled_to_zone.extend(sim_list)
        if game_services.service_manager.is_traveling:
            for sim_id in sim_list:
                sim_info = self.get(sim_id)
                if sim_info is not None:
                    sim_info.load_for_travel_to_current_zone()

    def remove_sim_from_traveled_sims(self, sim_id):
        self._sims_traveled_to_zone.remove(sim_id)

    def on_spawn_sims_for_zone_spin_up(self, client):
        traveled_sim_infos = []
        for sim_id in tuple(self._sims_traveled_to_zone):
            if sim_id == 0:
                self._sims_traveled_to_zone.remove(sim_id)
            else:
                sim_info = self.get(sim_id)
                if sim_info is None:
                    logger.error('sim id {} for traveling did not spawn because sim info does not exist.', sim_id, owner='msantander')
                else:
                    traveled_sim_infos.append(sim_info)
        narrative_service = services.narrative_service()
        if not narrative_service.should_suppress_travel_sting():
            lot_tuning = world.lot_tuning.LotTuningMaps.get_lot_tuning()
            if lot_tuning is not None and lot_tuning.audio_sting is not None:
                sting = lot_tuning.audio_sting(None)
                sting.start()
            elif traveled_sim_infos:
                play_tunable_audio(TravelTuning.TRAVEL_SUCCESS_AUDIO_STING)
            else:
                play_tunable_audio(TravelTuning.NEW_GAME_AUDIO_STING)
        services.current_zone().venue_service.process_traveled_and_persisted_and_resident_sims_during_zone_spin_up(traveled_sim_infos, self._sim_infos_saved_in_zone, self._sim_infos_saved_in_plex_group, self._sim_infos_saved_in_open_street, self._sim_infos_injected_into_zone)

    def _update_greeting_relationships_on_zone_spinup(self):
        instanced_sims = list(self.instanced_sims_gen())
        for sim in instanced_sims:
            sim_info = sim.sim_info
            traveled_sim_infos = self.get_traveled_to_zone_sim_infos()
            if sim_info in traveled_sim_infos:
                for other_sim in instanced_sims:
                    other_sim_info = other_sim.sim_info
                    if sim_info is other_sim_info:
                        pass
                    elif other_sim_info in traveled_sim_infos:
                        greetings.add_greeted_rel_bit(sim_info, other_sim_info)
                    else:
                        greetings.remove_greeted_rel_bit(sim_info, other_sim_info)
            elif sim_info in self._sim_infos_injected_into_zone:
                for other_sim in instanced_sims:
                    other_sim_info = other_sim.sim_info
                    if sim_info is other_sim_info:
                        pass
                    else:
                        greetings.remove_greeted_rel_bit(sim_info, other_sim_info)

    def on_spawn_sim_for_zone_spin_up_completed(self, client):
        relgraph_initializable = RelgraphService.RELGRAPH_ENABLED and not RelgraphService.is_relgraph_initialized()
        for sim_info in self.values():
            instanced_sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if instanced_sim is None:
                if sim_info.commodity_tracker is not None:
                    sim_info.commodity_tracker.start_low_level_simulation()
            elif sim_info.is_baby:
                instanced_sim.enable_baby_state()
            if relgraph_initializable:
                sim_info.push_to_relgraph()
        if not game_services.service_manager.is_traveling:
            with genealogy_caching():
                self.set_default_genealogy()
                if relgraph_initializable:
                    for sim_info in self.values():
                        sim_info.set_relgraph_family_edges()
        relationship_service = services.relationship_service()
        for sim_info in client.selectable_sims:
            relationship_service.send_relationship_info(sim_info.sim_id)
        for sim_info in itertools.chain(self._sim_infos_saved_in_zone, self._sim_infos_saved_in_open_street, self._sim_infos_injected_into_zone):
            if sim_info.is_baby or sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                if not sim_info.lives_here:
                    sim_info.inject_into_inactive_zone(sim_info.vacation_or_home_zone_id)
                else:
                    sim_info.inject_into_inactive_zone(0)
        RelgraphService.relgraph_cull(self.values())
        self._update_greeting_relationships_on_zone_spinup()

    def update_greeted_relationships_on_spawn(self, sim_info):
        for other_sim in self.instanced_sims_gen():
            other_sim_info = other_sim.sim_info
            if other_sim_info is sim_info:
                pass
            else:
                greetings.remove_greeted_rel_bit(sim_info, other_sim_info)

    def try_set_sim_fame_option_to_global_option(self, sim_info):
        if not sim_info.get_gameplay_option(SimInfoGameplayOptions.FREEZE_FAME):
            tracker = sim_info.get_tracker(FameTunables.FAME_RANKED_STATISTIC)
            if tracker is not None:
                ranked_stat_inst = tracker.get_statistic(FameTunables.FAME_RANKED_STATISTIC, add=True)
                if ranked_stat_inst.get_value() <= ranked_stat_inst.min_value + 1:
                    sim_info.allow_fame = not self._start_all_sims_opted_out_of_fame

    def set_start_all_sims_opted_out_of_fame(self, start_opted_out):
        self._start_all_sims_opted_out_of_fame = start_opted_out
        for sim_info in self.values():
            self.try_set_sim_fame_option_to_global_option(sim_info)

    def set_default_genealogy(self, sim_infos=None):

        def get_spouse(sim_info):
            spouse = None
            spouse_id = sim_info.spouse_sim_id
            if spouse_id is not None:
                spouse = self.get(spouse_id)
            return spouse

        if sim_infos is None:
            sim_infos = self.values()
            reciprocal = False
        else:
            reciprocal = True
        depth = 3
        with genealogy_caching():
            for sim_info in sim_infos:
                extended_family = set()
                candidates = set([sim_info])
                spouse = get_spouse(sim_info)
                if spouse is not None:
                    candidates.add(spouse)
                    extended_family.add(spouse)
                for _ in range(depth):
                    new_candidates = set()
                    for _id in itertools.chain.from_iterable(x.genealogy.get_immediate_family_sim_ids_gen() for x in candidates):
                        family_member = self.get(_id)
                        if family_member is not None and family_member not in extended_family:
                            new_candidates.add(family_member)
                            spouse = get_spouse(family_member)
                            if spouse is not None and family_member not in extended_family:
                                new_candidates.add(spouse)
                    candidates = new_candidates
                    extended_family.update(candidates)
                extended_family -= set([sim_info])
                if reciprocal:
                    for family_member in extended_family:
                        sim_info.add_family_link(family_member)
                        family_member.add_family_link(sim_info)
                else:
                    for family_member in extended_family:
                        sim_info.add_family_link(family_member)
        relationship_setup_logger.info('set_default_genealogy updated genealogy links for {} sim_infos.', len(sim_infos))

    def get_traveled_to_zone_sim_infos(self):
        result = []
        for sim_id in self._sims_traveled_to_zone:
            sim_info = self.get(sim_id)
            if sim_info is None:
                logger.error('Game does not know sim_info (id {}) who was travelling.', sim_id)
            else:
                result.append(sim_info)
        return result

    def get_sim_infos_saved_in_zone(self):
        return list(self._sim_infos_saved_in_zone)

    def get_sim_infos_saved_in_plex_group(self):
        return list(self._sim_infos_saved_in_plex_group)

    def get_sim_infos_saved_in_open_streets(self):
        return list(self._sim_infos_saved_in_open_street)

    def instantiatable_sims_info_gen(self):
        for info in self.get_all():
            if info.can_instantiate_sim:
                yield info

    def instanced_sims_gen(self, allow_hidden_flags=0):
        for info in self.get_all():
            sim = info.get_sim_instance(allow_hidden_flags=allow_hidden_flags)
            if sim is not None:
                yield sim

    def instanced_sims_on_active_lot_gen(self, allow_hidden_flags=0, include_spawn_point=False):
        for sim in self.instanced_sims_gen(allow_hidden_flags=allow_hidden_flags):
            if sim.is_on_active_lot(include_spawn_point=include_spawn_point):
                yield sim

    def instanced_sim_info_including_baby_gen(self, allow_hidden_flags=0):
        object_manager = services.object_manager()
        for sim_info in self.get_all():
            if sim_info.is_baby:
                sim_or_baby = object_manager.get(sim_info.id)
            else:
                sim_or_baby = sim_info.get_sim_instance(allow_hidden_flags=allow_hidden_flags)
            if sim_or_baby is not None:
                yield sim_info

    def get_player_npc_sim_count(self):
        npc = 0
        player = 0
        for sim in self.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
            if sim.is_selectable:
                player += 1
            elif sim.sim_info.is_npc:
                npc += 1
        return (player, npc)

    def are_npc_sims_in_open_streets(self):
        return any(s.is_npc and not s.is_on_active_lot() for s in self.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS))

    def get_sim_info_by_name(self, first_name, last_name):
        first_name = first_name.lower()
        last_name = last_name.lower()
        for info in self.get_all():
            if info.first_name.lower() == first_name and info.last_name.lower() == last_name:
                return info

    def auto_satisfy_sim_motives(self):
        for sim in self.instanced_sims_gen():
            statistics = list(sim.commodities_gen())
            for statistic in statistics:
                if not statistic.has_auto_satisfy_value():
                    pass
                else:
                    statistic.set_to_auto_satisfy_value()

    def handle_event(self, sim_info, event, resolver):
        self._sim_started_startup_interaction(sim_info, event, resolver)

    def _run_preroll_autonomy(self):
        used_target_list = []
        for sim_info in self.get_sims_for_spin_up_action(SimZoneSpinUpAction.PREROLL):
            sim = sim_info.get_sim_instance()
            if sim is None:
                pass
            else:
                caches.clear_all_caches()
                sim.set_allow_route_instantly_when_hitting_marks(True)
                (interaction_started, interaction_target) = sim.run_preroll_autonomy(used_target_list)
                if interaction_started:
                    logger.debug('sim: {} started interaction:{} as part of preroll autonomy.', sim, interaction_started)
                    if interaction_target is not None and not interaction_target.allow_preroll_multiple_targets:
                        used_target_list.append(interaction_target)
                        logger.debug('sim: {} failed to choose interaction as part of preroll autonomy.', sim)
                else:
                    logger.debug('sim: {} failed to choose interaction as part of preroll autonomy.', sim)

    def _run_startup_interactions(self, create_startup_interactions_function):
        try:
            create_startup_interactions_function()
        except Exception as e:
            logger.exception('Exception raised while trying to startup interactions.', exc=e)

    def schedule_sim_spin_up_action(self, sim_info, action):
        if self._sim_info_to_spin_up_action is None:
            return
        if sim_info in self._sim_info_to_spin_up_action:
            logger.error('Setting spin up action twice for Sim:{} first:{} second:{}', sim_info, self._sim_info_to_spin_up_action[sim_info], action)
        self._sim_info_to_spin_up_action[sim_info] = action

    def get_sims_for_spin_up_action(self, action):
        if self._sim_info_to_spin_up_action is None:
            return
        results = []
        for (sim_info, scheduled_action) in self._sim_info_to_spin_up_action.items():
            if scheduled_action == action:
                results.append(sim_info)
        return results

    def restore_sim_si_state(self):
        super_interaction_restorer = SuperInteractionRestorer()
        super_interaction_restorer.restore_sim_si_state()

    def verify_travel_sims_outfits(self):
        for traveled_sim_id in self._sims_traveled_to_zone:
            sim_info = self.get(traveled_sim_id)
            if sim_info is not None and sim_info.get_current_outfit()[0] == OutfitCategory.BATHING:
                sim_info.set_current_outfit((OutfitCategory.EVERYDAY, 0))

    def run_preroll_autonomy(self):
        self._run_startup_interactions(self._run_preroll_autonomy)
        self.verify_travel_sims_outfits()

    def push_sims_to_go_home(self):
        go_home_affordance = ui_tuning.UiTuning.GO_HOME_INTERACTION
        if go_home_affordance is None:
            return
        for sim_info in self.get_sims_for_spin_up_action(SimZoneSpinUpAction.PUSH_GO_HOME):
            sim = sim_info.get_sim_instance()
            if sim is not None:
                tolerance = sim.get_off_lot_autonomy_rule().tolerance
                if not sim.is_on_active_lot(tolerance=tolerance):
                    context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High)
                    if sim.push_super_affordance(go_home_affordance, None, context):
                        logger.debug('sim: {} pushed to go home.', sim, owner='sscholl')
                    else:
                        logger.warn('Failed to push sim to go home from open street: {}', sim_info, owner='msantander')

    def set_aging_enabled_on_all_sims(self, is_aging_enabled_for_sim_info_fn, update_callbacks=True):
        for sim_info in self.objects:
            sim_info.set_aging_enabled(is_aging_enabled_for_sim_info_fn(sim_info), update_callbacks=update_callbacks)

    def set_aging_speed_on_all_sims(self, speed):
        for sim_info in self.objects:
            sim_info.set_aging_speed(speed)

    def set_sim_to_skip_preroll(self, sim_id):
        self._sim_ids_to_skip_preroll.add(sim_id)

    def trigger_firemeter(self):
        if self._firemeter is not None:
            self._firemeter.trigger()

    def on_loading_screen_animation_finished(self):
        for sim_info in self.objects:
            sim_info.on_loading_screen_animation_finished()
        daycare_service = services.daycare_service()
        if daycare_service is not None:
            daycare_service.on_loading_screen_animation_finished()
        self._sims_traveled_to_zone.clear()
        self._sim_infos_saved_in_open_street.clear()
        self._sim_infos_saved_in_plex_group.clear()
        self._sim_infos_saved_in_zone.clear()
        self._sim_ids_to_skip_preroll.clear()
        self._sim_infos_injected_into_zone.clear()
        self._sim_info_to_spin_up_action = None
        self._firemeter = SimInfoFireMeter()

    def on_client_connect(self, client):
        self._sim_info_to_spin_up_action = {}

    def is_sim_id_valid(self, sim_id):
        sim = self.get(sim_id)
        return sim is not None and sim.can_instantiate_sim

    def on_sim_info_created(self):
        self._sim_info_telemetry_manager.on_sim_info_created()

    def remove_permanently(self, sim_info):
        sim_id = sim_info.id
        sim_filter_service = services.sim_filter_service()
        try:
            sim_filter_service.add_sim_id_to_global_blacklist(sim_id, SimFilterGlobalBlacklistReason.SIM_INFO_BEING_REMOVED)
            clubs.on_sim_killed_or_culled(sim_info)
            sim_info.relationship_tracker.destroy_all_relationships()
            self.remove(sim_info)
            self.on_sim_info_removed(sim_info)
        finally:
            sim_filter_service.remove_sim_id_from_global_blacklist(sim_id, SimFilterGlobalBlacklistReason.SIM_INFO_BEING_REMOVED)

    def _recalculate_sim_info_cap(self):
        total = sims.household.Household.MAXIMUM_SIZE
        for lod in SimInfoLODLevel:
            if self._sim_info_cap_override is None:
                cap_count = SIM_INFO_CAP_PER_LOD.get(lod)
            else:
                cap_count = self._sim_info_cap_override.get(lod, SIM_INFO_CAP_PER_LOD.get(lod))
            if cap_count is not None:
                total += cap_count
        self.SIM_INFO_CAP = total

    def get_sim_info_cap_override(self):
        return self._sim_info_cap_override

    def get_sim_info_cap_override_per_lod(self, sim_info_lod):
        if self._sim_info_cap_override is None:
            return
        return self._sim_info_cap_override.get(sim_info_lod, None)

    def set_sim_info_cap_override(self, sim_info_lod, new_cap_level):
        if self._sim_info_cap_override is None:
            self._sim_info_cap_override = enumdict(SimInfoLODLevel)
        self._sim_info_cap_override[sim_info_lod] = new_cap_level
        self._recalculate_sim_info_cap()

    def clear_sim_info_cap_override_for_lod(self, sim_info_lod):
        if self._sim_info_cap_override is None:
            return
        if sim_info_lod not in self._sim_info_cap_override:
            return
        del self._sim_info_cap_override[sim_info_lod]
        self._recalculate_sim_info_cap()
