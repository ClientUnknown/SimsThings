import operatorimport randomfrom gsi_handlers.relationship_culling_handlers import RelationshipGSIDatafrom objects import ALL_HIDDEN_REASONSfrom sims4.log import Loggerfrom sims4.tuning.tunable import Tunable, TunableTuplefrom story_progression.story_progression_action import _StoryProgressionActionfrom tunable_time import TunableTimeOfDayimport gsi_handlersimport performanceimport servicesimport sims4import telemetry_helperlogger = Logger('RelationshipCulling', default_owner='johnwilkinson')TELEMETRY_GROUP_STORY_PROGRESSION = 'STRY'TELEMETRY_HOOK_CULL_REL_BEFORE = 'CRBF'TELEMETRY_HOOK_CULL_REL_AFTER = 'CRAF'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_STORY_PROGRESSION)
class StoryProgressionRelationshipCulling(_StoryProgressionAction):
    PLAYED_NPC_TO_PLAYED_NPC_MAX_RELATIONSHIPS = Tunable(description='\n        The max number of relationships that a played NPC is allowed to have\n        with other NPCs. This is for sims that have been played in the past,\n        but are not part of the active household now, and only operates on\n        relationships with other NPCs.\n        ', tunable_type=int, default=20)
    CULLING_BUFFER_AMOUNT = Tunable(description='\n        When relationships are culled from an NPC relationship tracker due to \n        the number of relationships exceeding the cap, this is how much below\n        the cap the number of relationships will be after the culling.\n        ', tunable_type=int, default=5)
    PLAYED_NPC_REL_DEPTH_CULLING_THRESHOLD = Tunable(description='\n        The relationship depth below which an NPC relationship will be culled.\n        This is for sims that have been played in the past, but are not part of\n        the active household now, and only operates on relationships with other NPCs.\n        ', tunable_type=int, default=30)
    FACTORY_TUNABLES = {'time_of_day': TunableTuple(description='\n            Only run this action when it is between a certain time of day.\n            ', start_time=TunableTimeOfDay(default_hour=2), end_time=TunableTimeOfDay(default_hour=5))}

    def should_process(self, options):
        current_time = services.time_service().sim_now
        if not current_time.time_between_day_times(self.time_of_day.start_time, self.time_of_day.end_time):
            return False
        return True

    def process_action(self, story_progression_flags):
        self.trigger_npc_relationship_culling()

    @classmethod
    def _trigger_relationship_telemetry(cls, hook_name, culling_event_id):
        metrics = performance.performance_commands.get_relationship_metrics()
        with telemetry_helper.begin_hook(writer, hook_name) as hook:
            hook.write_int('clid', culling_event_id)
            hook.write_int('rels', metrics.rels)
            hook.write_int('ract', metrics.rels_active)
            hook.write_int('rpla', metrics.rels_played)
            hook.write_int('runp', metrics.rels_unplayed)
            hook.write_int('rbow', metrics.rel_bits_one_way)
            hook.write_int('rbbi', metrics.rel_bits_bi)

    @classmethod
    def _add_relationship_data_to_list(cls, output_list, sim_info, rel_id, active_household_id, culled_status, reason=''):
        target_sim_info = services.sim_info_manager().get(rel_id)
        total_depth = sim_info.relationship_tracker.get_relationship_depth(rel_id)
        rel_bits = sim_info.relationship_tracker.get_depth_sorted_rel_bit_list(rel_id)
        formated_rel_bits = list()
        for rel_bit in rel_bits:
            bit_depth = rel_bit.depth
            rel_bit_string = str(rel_bit)
            rel_bit_string = rel_bit_string.replace("<class 'sims4.tuning.instances.", '')
            rel_bit_string = rel_bit_string.replace('>', '')
            rel_bit_string = rel_bit_string.replace("'", '')
            rel_bit_string += ' ({})'.format(bit_depth)
            formated_rel_bits.append(rel_bit_string)
        output_list.append(RelationshipGSIData(sim_info, target_sim_info, total_depth, formated_rel_bits, culled_status, reason))

    @classmethod
    def trigger_npc_relationship_culling(cls):
        culling_event_id = int(random.random()*1000)
        cls._trigger_relationship_telemetry(TELEMETRY_HOOK_CULL_REL_BEFORE, culling_event_id)
        cls._do_npc_relationship_culling()
        cls._trigger_relationship_telemetry(TELEMETRY_HOOK_CULL_REL_AFTER, culling_event_id)

    @classmethod
    def _do_npc_relationship_culling(cls):
        CULLED = 'Culled'
        NOT_CULLED = 'Not Culled'
        UNPLAYED_TO_UNPLAYED = 'Unplayed_to_Unplayed'
        BELOW_DEPTH = 'Below_Depth_Threshold'
        MAX_CAP = 'Over_Max_Cap'
        active_sim_ids = frozenset(sim_info.id for sim_info in services.active_household())
        active_household_id = services.active_household_id()
        gsi_enabled = gsi_handlers.relationship_culling_handlers.archiver.enabled
        if gsi_enabled:
            relationship_data = list()
            culled_relationship_data = list()
            total_culled_count = 0
        for sim_info in sorted(services.sim_info_manager().values(), key=operator.attrgetter('is_player_sim', 'is_played_sim')):
            if sim_info.household.id == active_household_id or sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if gsi_enabled:
                    for rel_id in sim_info.relationship_tracker.target_sim_gen():
                        cls._add_relationship_data_to_list(relationship_data, sim_info, rel_id, active_household_id, NOT_CULLED)
                    is_player_sim = sim_info.is_player_sim
                    num_to_cull = 0
                    ids_to_cull_with_reasons = set()
                    if is_player_sim:
                        sorted_relationships = sorted(sim_info.relationship_tracker, key=lambda rel: rel.get_relationship_depth(sim_info.sim_id))
                        num_over_cap = len(sorted_relationships) - cls.PLAYED_NPC_TO_PLAYED_NPC_MAX_RELATIONSHIPS
                        if num_over_cap > 0:
                            num_to_cull = num_over_cap + cls.CULLING_BUFFER_AMOUNT
                        for rel in sorted_relationships:
                            if not rel.get_other_sim_id(sim_info.sim_id) in active_sim_ids:
                                if not rel.can_cull_relationship(consider_convergence=False):
                                    pass
                                elif rel.get_relationship_depth(sim_info.sim_id) < cls.PLAYED_NPC_REL_DEPTH_CULLING_THRESHOLD:
                                    ids_to_cull_with_reasons.add((rel.get_other_sim_id(sim_info.sim_id), BELOW_DEPTH))
                                    num_to_cull -= 1
                                elif num_to_cull > 0:
                                    ids_to_cull_with_reasons.add((rel.get_other_sim_id(sim_info.sim_id), MAX_CAP))
                                    num_to_cull -= 1
                                else:
                                    break
                    else:
                        for rel in sim_info.relationship_tracker:
                            if rel.get_other_sim_id(sim_info.sim_id) in active_sim_ids:
                                pass
                            else:
                                target_sim_info = rel.get_other_sim_info(sim_info.sim_id)
                                if target_sim_info is not None and target_sim_info.is_player_sim:
                                    pass
                                elif not rel.can_cull_relationship(consider_convergence=False):
                                    pass
                                else:
                                    ids_to_cull_with_reasons.add((rel.get_other_sim_id(sim_info.sim_id), UNPLAYED_TO_UNPLAYED))
                    if num_to_cull > 0:
                        logger.warn('Relationship Culling could not find enough valid relationships to cull to bring the total number below the cap. Cap exceeded by: {}, Sim {}', num_to_cull, sim_info)
                    for (rel_id, reason) in ids_to_cull_with_reasons:
                        if gsi_enabled:
                            cls._add_relationship_data_to_list(culled_relationship_data, sim_info, rel_id, active_household_id, CULLED, reason=reason)
                            total_culled_count += 1
                        sim_info.relationship_tracker.destroy_relationship(rel_id)
                    if gsi_enabled:
                        for rel_id in sim_info.relationship_tracker.target_sim_gen():
                            cls._add_relationship_data_to_list(relationship_data, sim_info, rel_id, active_household_id, NOT_CULLED)
            else:
                is_player_sim = sim_info.is_player_sim
                num_to_cull = 0
                ids_to_cull_with_reasons = set()
                if is_player_sim:
                    sorted_relationships = sorted(sim_info.relationship_tracker, key=lambda rel: rel.get_relationship_depth(sim_info.sim_id))
                    num_over_cap = len(sorted_relationships) - cls.PLAYED_NPC_TO_PLAYED_NPC_MAX_RELATIONSHIPS
                    if num_over_cap > 0:
                        num_to_cull = num_over_cap + cls.CULLING_BUFFER_AMOUNT
                    for rel in sorted_relationships:
                        if not rel.get_other_sim_id(sim_info.sim_id) in active_sim_ids:
                            if not rel.can_cull_relationship(consider_convergence=False):
                                pass
                            elif rel.get_relationship_depth(sim_info.sim_id) < cls.PLAYED_NPC_REL_DEPTH_CULLING_THRESHOLD:
                                ids_to_cull_with_reasons.add((rel.get_other_sim_id(sim_info.sim_id), BELOW_DEPTH))
                                num_to_cull -= 1
                            elif num_to_cull > 0:
                                ids_to_cull_with_reasons.add((rel.get_other_sim_id(sim_info.sim_id), MAX_CAP))
                                num_to_cull -= 1
                            else:
                                break
                else:
                    for rel in sim_info.relationship_tracker:
                        if rel.get_other_sim_id(sim_info.sim_id) in active_sim_ids:
                            pass
                        else:
                            target_sim_info = rel.get_other_sim_info(sim_info.sim_id)
                            if target_sim_info is not None and target_sim_info.is_player_sim:
                                pass
                            elif not rel.can_cull_relationship(consider_convergence=False):
                                pass
                            else:
                                ids_to_cull_with_reasons.add((rel.get_other_sim_id(sim_info.sim_id), UNPLAYED_TO_UNPLAYED))
                if num_to_cull > 0:
                    logger.warn('Relationship Culling could not find enough valid relationships to cull to bring the total number below the cap. Cap exceeded by: {}, Sim {}', num_to_cull, sim_info)
                for (rel_id, reason) in ids_to_cull_with_reasons:
                    if gsi_enabled:
                        cls._add_relationship_data_to_list(culled_relationship_data, sim_info, rel_id, active_household_id, CULLED, reason=reason)
                        total_culled_count += 1
                    sim_info.relationship_tracker.destroy_relationship(rel_id)
                if gsi_enabled:
                    for rel_id in sim_info.relationship_tracker.target_sim_gen():
                        cls._add_relationship_data_to_list(relationship_data, sim_info, rel_id, active_household_id, NOT_CULLED)
        if gsi_enabled:
            gsi_handlers.relationship_culling_handlers.archive_relationship_culling(total_culled_count, relationship_data, culled_relationship_data)
