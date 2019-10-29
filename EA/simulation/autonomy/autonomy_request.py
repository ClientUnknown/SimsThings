import collectionsimport itertoolsimport timefrom caches import cachedimport autonomy.autonomy_utilimport enumimport interactionsimport servicesimport sims4.logimport singletonslogger = sims4.log.Logger('Autonomy', default_owner='rez')
class AutonomyPostureBehavior(enum.Int, export=False):
    FULL = 0
    IGNORE_SI_STATE = 1

class AutonomyDistanceEstimationBehavior(enum.Int, export=False):
    FULL = 0
    ALLOW_UNREACHABLE_LOCATIONS = 1
    IGNORE_DISTANCE = 2
    FINAL_PATH = 3
AutonomyRequestGsiArchive = collections.namedtuple('AutonomyRequestGsiArchive', ['key', 'value'])
class AutonomyRequest:

    def __init__(self, sim, autonomy_mode=None, commodity_list=None, static_commodity_list=None, skipped_static_commodities=None, object_list=None, ignored_object_list=None, affordance_list=None, sleep_element=None, context=None, is_script_request=False, ignore_user_directed_and_autonomous=False, posture_behavior=AutonomyPostureBehavior.FULL, distance_estimation_behavior=AutonomyDistanceEstimationBehavior.FULL, record_test_result=None, constraint=None, consider_scores_of_zero=False, skipped_affordance_list=None, ignore_lockouts=False, apply_opportunity_cost=True, push_super_on_prepare=False, radius_to_consider=0, off_lot_autonomy_rule_override=None, autonomy_mode_label_override=None, test_connectivity_to_target_object=False, **interaction_parameters):
        logger.assert_raise(autonomy_mode is not None, 'autonomy_mode cannot be None in the AutonomyRequest.')
        self._sim_ref = sim.ref()
        self.object_list = object_list
        self.ignored_object_list = ignored_object_list
        self.affordance_list = affordance_list
        self.skipped_affordance_list = skipped_affordance_list
        self.constraint = constraint
        self.sleep_element = sleep_element
        self.is_script_request = is_script_request
        self.ignore_user_directed_and_autonomous = ignore_user_directed_and_autonomous
        self.posture_behavior = posture_behavior
        self.distance_estimation_behavior = distance_estimation_behavior
        self.consider_scores_of_zero = consider_scores_of_zero
        self.record_test_result = record_test_result
        self.ignore_lockouts = ignore_lockouts
        self.apply_opportunity_cost = apply_opportunity_cost
        self.push_super_on_prepare = push_super_on_prepare
        self.radius_to_consider_squared = radius_to_consider*radius_to_consider
        self.off_lot_autonomy_rule_override = off_lot_autonomy_rule_override
        self.test_connectivity_to_target_object = test_connectivity_to_target_object
        self.valid = True
        self.kwargs = interaction_parameters
        self._interactions_to_invalidate = []
        self.valid_interactions = None
        self.gsi_data = None
        self.similar_aop_cache = {}
        if context is None:
            self.context = interactions.context.InteractionContext(self.sim, interactions.context.InteractionContext.SOURCE_AUTONOMY, interactions.priority.Priority.Low, client=None, pick=None)
        else:
            self.context = context
        if commodity_list:
            if static_commodity_list:
                commodity_list = set(commodity_list)
                static_commodity_list = set(static_commodity_list)
                all_commodities = commodity_list.union(static_commodity_list)
            else:
                commodity_list = set(commodity_list)
                static_commodity_list = None
                all_commodities = commodity_list
        elif static_commodity_list:
            static_commodity_list = set(static_commodity_list)
            commodity_list = None
            all_commodities = static_commodity_list
        else:
            commodity_list = None
            static_commodity_list = None
            all_commodities = None
        if skipped_static_commodities:
            self.skipped_static_commodities = set(skipped_static_commodities)
        else:
            self.skipped_static_commodities = None
        self.commodity_list = commodity_list
        self.static_commodity_list = static_commodity_list
        self.all_commodities = all_commodities
        self.interactions_to_invalidate = []
        self.timestamp = services.time_service().sim_now
        self.autonomy_mode = autonomy_mode(self)
        self.autonomy_mode_label = autonomy_mode_label_override or str(self.autonomy_mode)
        self.autonomy_ping_request_record = None
        self.skip_adding_request_record = False

    def __repr__(self):
        return '<{}Request for {!s}>'.format(self.autonomy_mode_label, self.sim)

    @property
    def sim(self):
        return self._sim_ref()

    @property
    def has_commodities(self):
        if self.all_commodities:
            return True
        return False

    def on_interaction_created(self, interaction):
        self._interactions_to_invalidate.append(interaction)

    def invalidate_created_interactions(self, excluded_si=None):
        for interaction in self._interactions_to_invalidate:
            if not interaction.is_super:
                pass
            elif interaction is excluded_si:
                pass
            else:
                interaction.invalidate()
        self._interactions_to_invalidate.clear()

    @cached
    def _check_object_connectivity_and_rules(self, obj, autonomy_rule):
        if not self.sim.autonomy_component.get_autonomous_availability_of_object(obj, autonomy_rule):
            return False
        elif self.test_connectivity_to_target_object and not obj.is_connected(self.sim):
            return False
        return True

    def _check_sim_relbits_commodity_flags(self, target_sim, motives):
        relationship_service = services.relationship_service()
        if motives is singletons.DEFAULT:
            return any(relbit.commodity_flags() for relbit in relationship_service.get_all_bits(self.sim.id, target_sim.id))
        else:
            return any(relbit.commodity_flags() & motives for relbit in relationship_service.get_all_bits(self.sim.id, target_sim.id))

    def objects_to_score_gen(self, motives:set=singletons.DEFAULT):
        provided_affordance_datas = []
        for provided_affordance_data in itertools.chain(self.sim.sim_info.get_target_provided_affordances_data_gen(), self.sim.sim_info.trait_tracker.get_cached_target_provided_affordances_data_gen(), self.sim.sim_info.commodity_tracker.get_cached_target_provided_affordances_data_gen()):
            if provided_affordance_data.affordance.commodity_flags & motives:
                provided_affordance_datas.append(provided_affordance_data)

        def is_valid_to_score(obj):
            if self.ignored_object_list and obj in self.ignored_object_list:
                return False
            elif motives is singletons.DEFAULT and obj.commodity_flags or (motives and obj.commodity_flags & motives or any(provided_affordance_data.object_filter.is_object_valid(obj) for provided_affordance_data in provided_affordance_datas)) or obj.is_sim and self._check_sim_relbits_commodity_flags(obj, motives):
                return True
            return False

        if self.object_list:
            for obj in self.object_list:
                if is_valid_to_score(obj):
                    yield obj
        else:
            autonomy_rule = self.sim.get_off_lot_autonomy_rule() if self.off_lot_autonomy_rule_override is None else self.off_lot_autonomy_rule_override
            for obj in services.object_manager().valid_objects():
                if not is_valid_to_score(obj) or self._check_object_connectivity_and_rules(obj, autonomy_rule):
                    yield obj
            for obj in self.sim.inventory_component:
                if is_valid_to_score(obj):
                    yield obj

    def get_gsi_data(self):
        archive = [AutonomyRequestGsiArchive('Sim', str(self.sim)), AutonomyRequestGsiArchive('All Commodities', [str(stat) for stat in self.all_commodities] if self.all_commodities is not None else 'None'), AutonomyRequestGsiArchive('Commodity List', [str(stat) for stat in self.commodity_list] if self.commodity_list is not None else 'None'), AutonomyRequestGsiArchive('Static Commodity List', [str(stat) for stat in self.static_commodity_list] if self.static_commodity_list is not None else 'None'), AutonomyRequestGsiArchive('Skipped Static Commodities', [str(stat) for stat in self.skipped_static_commodities] if self.skipped_static_commodities is not None else 'None'), AutonomyRequestGsiArchive('Object List', [str(obj) for obj in self.object_list] if self.object_list is not None else 'None'), AutonomyRequestGsiArchive('Ignored Object List', [str(obj) for obj in self.ignored_object_list] if self.ignored_object_list is not None else 'None'), AutonomyRequestGsiArchive('Affordance List', [str(affordance) for affordance in self.affordance_list] if self.affordance_list is not None else 'None'), AutonomyRequestGsiArchive('Skipped Affordance List', [str(affordance) for affordance in self.skipped_affordance_list] if self.skipped_affordance_list is not None else 'None'), AutonomyRequestGsiArchive('Is Script Request?', 'True' if self.is_script_request else 'False'), AutonomyRequestGsiArchive('Ignore User Directed & Autonomous', 'True' if self.ignore_user_directed_and_autonomous else 'False'), AutonomyRequestGsiArchive('Posture Behavior', str(self.posture_behavior)), AutonomyRequestGsiArchive('Distance Estimation Behavior', str(self.distance_estimation_behavior)), AutonomyRequestGsiArchive('Consider Scores of Zero?', 'True' if self.consider_scores_of_zero else 'False'), AutonomyRequestGsiArchive('Ignore Lockouts?', 'True' if self.ignore_lockouts else 'False'), AutonomyRequestGsiArchive('Apply Opportunity Cost?', 'True' if self.apply_opportunity_cost else 'False'), AutonomyRequestGsiArchive('Push Super on Prepare?', 'True' if self.push_super_on_prepare else 'False'), AutonomyRequestGsiArchive('Radius to Consider Squared', self.radius_to_consider_squared), AutonomyRequestGsiArchive('Off Lot Autonomy Override', str(self.off_lot_autonomy_rule_override) if self.off_lot_autonomy_rule_override is not None else 'None'), AutonomyRequestGsiArchive('Context', str(self.context))]
        return archive

    def create_autonomy_ping_request_record(self):
        if not autonomy.autonomy_util.g_autonomy_profile_data:
            return
        sim = self.sim
        self.autonomy_ping_request_record = autonomy.autonomy_util.AutonomyPingRequestRecord(sim.sim_id, sim.sim_info.first_name, sim.sim_info.last_name, self.autonomy_mode_label, services.time_service().sim_now, sim.is_npc)

    def add_record_to_profiling_data(self):
        if self.autonomy_ping_request_record is not None:
            if self.skip_adding_request_record:
                return
            self.autonomy_ping_request_record.add_record_to_profiling_data()

    def on_end_of_time_slicing(self, time_slice_start_time):
        if self.autonomy_ping_request_record is not None:
            self.autonomy_ping_request_record.total_time_slicing += time.time() - time_slice_start_time

    def on_end_of_calculate_route_time(self, time_slice_start_time):
        if self.autonomy_ping_request_record is not None:
            self.autonomy_ping_request_record.total_distance_estimation += time.time() - time_slice_start_time

class PrerollAutonomyRequest(AutonomyRequest):

    def objects_to_score_gen(self, motives:set=singletons.DEFAULT):
        if self.object_list:
            for obj in self.object_list:
                if motives is singletons.DEFAULT or not obj.preroll_commodity_flags & motives or not self.ignored_object_list or obj not in self.ignored_object_list:
                    yield obj
        else:
            object_manager = services.object_manager()
            autonomy_rule = self.sim.get_off_lot_autonomy_rule() if self.off_lot_autonomy_rule_override is None else self.off_lot_autonomy_rule_override
            for obj in object_manager.valid_objects():
                if not self.ignored_object_list or obj in self.ignored_object_list:
                    pass
                else:
                    commodity_flags = obj.preroll_commodity_flags
                    if not motives is not singletons.DEFAULT or commodity_flags.isdisjoint(motives):
                        pass
                    elif not self._check_object_connectivity_and_rules(obj, autonomy_rule):
                        pass
                    else:
                        yield obj
