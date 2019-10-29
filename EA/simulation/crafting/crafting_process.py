import functoolsimport randomfrom protocolbuffers import Sims_pb2, Consts_pb2from autonomy.autonomy_modifier import UNLIMITED_AUTONOMY_RULEfrom carry.carry_interactions import CarryCancelInteractionfrom crafting import crafting_handlersfrom crafting.crafting_ingredients import IngredientTuningfrom crafting.crafting_tunable import CraftingTuningfrom crafting.recipe import Phase, Recipefrom distributor.shared_messages import add_message_if_selectablefrom distributor.system import Distributorfrom event_testing.resolver import SingleActorAndObjectResolver, SingleSimResolverfrom event_testing.results import ExecuteResult, TestResult, EnqueueResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionBucketType, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom interactions.utils.loot import LootOperationListfrom objects.components import ComponentContainerfrom objects.components.name_component import NameComponentfrom objects.components.statistic_component import StatisticComponentfrom sims.funds import get_funds_for_sourcefrom sims.sim_info_name_data import SimInfoNameDatafrom sims4.localization import LocalizationHelperTuningfrom sims4.repr_utils import standard_reprfrom sims4.utils import classproperty, staticproperty, constpropertyfrom singletons import DEFAULTimport algosimport autonomyimport distributorimport gsi_handlersimport mtximport objects.components.typesimport servicesimport sims4.logimport sims4.reloadimport sims4.resourcesimport telemetry_helper_normal_logger = sims4.log.Logger('Crafting')logger = _normal_loggerTELEMETRY_GROUP_CRAFTING = 'CRAF'TELEMETRY_HOOK_CRAFTING_START = 'STRT'TELEMETRY_HOOK_CRAFTING_END = 'CEND'TELEMETRY_HOOK_INGREDIENTS_USED = 'CING'TELEMETRY_FIELD_RECIPE_NAME = 'rena'TELEMETRY_FIELD_RECIPE_QUALITY = 'qual'TELEMETRY_FIELD_RECIPE_COMPLETE = 'comp'TELEMETRY_FIELD_INGREDIENTS_QUANTITY = 'quan'crafting_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CRAFTING)with sims4.reload.protected(globals()):
    shorten_all_phases = FalseCRAFTING_QUALITY_LIABILITY = 'CraftingQuality'
class CraftingQualityLiability(Liability):

    @staticproperty
    def CRAFTING_STATISTICS():
        return (CraftingTuning.QUALITY_STATISTIC, CraftingTuning.TURN_STATISTIC)

    def __init__(self, crafting_process, created_by=None, **kwargs):
        super().__init__(**kwargs)
        self._crafting_process = crafting_process
        self._created_by = created_by
        self._handles = {}
        for stat_type in self.CRAFTING_STATISTICS:
            tracker = crafting_process.get_tracker(stat_type)
            if tracker not in self._handles:
                self._handles[tracker] = tracker.add_watcher(self._on_stat_change)
        sim = self._crafting_process.crafter
        if sim is not None:
            with telemetry_helper.begin_hook(crafting_telemetry_writer, TELEMETRY_HOOK_CRAFTING_START, sim_info=sim.sim_info) as hook:
                hook.write_localized_string(TELEMETRY_FIELD_RECIPE_NAME, self._crafting_process.recipe.get_recipe_name(sim))

    def _on_stat_change(self, stat_type, old_value, new_value):
        if stat_type in self.CRAFTING_STATISTICS:
            self.send_quality_update()

    def get_quality_state_and_value(self):
        quality_stats_value = self._crafting_process.crafting_quality
        quality_state = CraftingTuning.get_quality_state_value(CraftingTuning.QUALITY_STATISTIC, quality_stats_value)
        return (quality_state.state_star_number, quality_stats_value)

    def send_quality_update(self, liabilty_release=False):
        crafting_process = self._crafting_process
        sim = crafting_process.crafter
        if sim is not None:
            liability_data = Sims_pb2.CraftingLiabilityUpdate()
            liability_data.core_data.type = Sims_pb2.InteractionLiabilityUpdate.CRAFTING_QUALITY
            liability_data.core_data.sim_id = crafting_process.crafter_sim_id
            liability_data.core_data.liabilty_release = liabilty_release
            if not liabilty_release:
                quality_value = crafting_process.crafting_quality
                liability_data.quality_statistic_value = int(quality_value)
                quality_state = CraftingTuning.get_quality_state_value(CraftingTuning.QUALITY_STATISTIC, liability_data.quality_statistic_value)
                if quality_state is not None:
                    liability_data.crafting_item_name = quality_state.state_string(crafting_process.recipe.get_recipe_name(crafting_process.crafter))
                    liability_data.crafting_quality = quality_state.state_star_number
                else:
                    liability_data.crafting_item_name = crafting_process.recipe.get_recipe_name(crafting_process.crafter)
                phase = crafting_process.phase
                if phase.is_visible:
                    if phase.phase_display_name is not None:
                        liability_data.phase_name = phase.phase_display_name
                    liability_data.phase_index = crafting_process.phase_index
                    liability_data.total_phases = crafting_process.recipe.total_visible_phases
                    liability_data.turn_index = crafting_process.get_progress()
                    liability_data.total_turns = crafting_process.get_turns_in_current_phase()
            add_message_if_selectable(sim, Consts_pb2.MSG_SIM_CRAFTING_LIABILITY_UPDATE, liability_data, False)

    def on_add(self, interaction):
        current_interaction = self._crafting_process._current_crafting_interaction
        interaction.mood_list = self._crafting_process.recipe.mood_list
        if current_interaction != interaction:
            if current_interaction is not None:
                logger.warn('{} already running on process. \nReplaced with new interaction: {}. \nCraftingQualityLiability created by: {}'.format(current_interaction, interaction, self._created_by), owner='cjiang', trigger_breakpoint=True)
            self._crafting_process._current_crafting_interaction = interaction
        self.send_quality_update()

    def transfer(self, interaction):
        self._crafting_process._current_crafting_interaction = interaction

    def release(self):
        for (tracker, handle) in self._handles.items():
            tracker.remove_watcher(handle)
        self.send_quality_update(liabilty_release=True)
        self._crafting_process._current_crafting_interaction = None
        sim = self._crafting_process.crafter
        if sim is not None:
            with telemetry_helper.begin_hook(crafting_telemetry_writer, TELEMETRY_HOOK_CRAFTING_END, sim_info=sim.sim_info) as hook:
                hook.write_localized_string(TELEMETRY_FIELD_RECIPE_NAME, self._crafting_process.recipe.get_recipe_name(sim))
                hook.write_int(TELEMETRY_FIELD_RECIPE_QUALITY, self._crafting_process.crafting_quality)
                hook.write_bool(TELEMETRY_FIELD_RECIPE_COMPLETE, self._crafting_process.is_complete)

def _record_test_result(aop, autonomy_step, test_result):
    if test_result is None:
        explanation = ''
    else:
        explanation = test_result.reason
    if autonomy_step.startswith('_'):
        autonomy_step = 'failed ' + autonomy_step + ' check'
    if autonomy_step and aop is not None:
        message = 'Autonomy rejected AOP: {!s:40}\t{!s:40}\t{:20}\t{}'.format(aop.target, aop.affordance.__name__, autonomy_step, explanation)
    else:
        message = 'Autonomy rejected obj: {:20}\t{}'.format(autonomy_step, explanation)
    logger.debug(message)

class CraftingProcess(ComponentContainer):

    @staticmethod
    def _create_autonomy_request(sim, context, mode, affordance_list=None, required_objects=None, super_affordance=None, **kwargs):
        if super_affordance is not None:
            affordance_list = (super_affordance,)
        if required_objects:
            required_objects = list(set().union(*(obj.ancestry_gen() for obj in required_objects if obj is not None)))
        use_large_cost = False
        ignore_lockouts = False
        if context.priority >= Priority.High:
            use_large_cost = True
            ignore_lockouts = True
        autonomy_distance_estimation_behavior = autonomy.autonomy_request.AutonomyDistanceEstimationBehavior.ALLOW_UNREACHABLE_LOCATIONS if use_large_cost else autonomy.autonomy_request.AutonomyDistanceEstimationBehavior.FULL
        return autonomy.autonomy_request.AutonomyRequest(sim, commodity_list=None, static_commodity_list=(CraftingTuning.STATIC_CRAFTING_COMMODITY,), skipped_static_commodities=None, object_list=required_objects, affordance_list=affordance_list, channel=None, context=context, autonomy_mode=mode, ignore_user_directed_and_autonomous=True, is_script_request=True, consider_scores_of_zero=True, ignore_lockouts=ignore_lockouts, apply_opportunity_cost=False, record_test_result=_record_test_result, distance_estimation_behavior=autonomy_distance_estimation_behavior, off_lot_autonomy_rule_override=UNLIMITED_AUTONOMY_RULE, autonomy_mode_label_override='CraftingRequest', **kwargs)

    def __init__(self, sim=None, crafter=None, recipe:Recipe=None, cost=None, paying_sim=None, reserved_ingredients=None, original_target=None, orderer_ids=None, ingredient_quality_bonus=None, funds_source=None):
        super().__init__()
        self.add_component(StatisticComponent(self))
        self.add_component(NameComponent(self, allow_name=True, allow_description=True))
        self.custom_name = None
        self.custom_description = None
        self.recipe = recipe
        self._cost = cost
        self._paying_sim = paying_sim
        self._funds_source = funds_source
        self._reserved_ingredients = reserved_ingredients if reserved_ingredients is not None else []
        self._crafter_sim_id = None
        self._crafter_info_data = None
        self.crafter = crafter
        self._interaction_quality_multiplier = 1
        self._current_ico_ref = None
        self._previous_ico_ref = None
        self._phase = None
        self._previous_phase = None
        self.orders = []
        self.multiple_order_process = False
        if orderer_ids is not None:
            for sim_id in orderer_ids:
                self.orders.append((sim_id, recipe))
        elif sim is not None:
            self.orders.append((sim_id, recipe))
        self._current_crafting_interaction = None
        self.inscription = None
        self._total_turns = self.get_accumulated_turns_for_all_phases()
        self._current_turn = 0
        self._ingredient_quality_bonus = ingredient_quality_bonus
        self._original_target_ref = original_target.ref() if original_target is not None else None
        self.crafted_value = None
        self.ready_to_serve = False
        self.linked_process = None
        self.show_crafted_by_text = True

    def __repr__(self):
        return standard_repr(self, recipe=self.recipe)

    @property
    def original_target(self):
        if self._original_target_ref is not None:
            return self._original_target_ref()

    @classmethod
    def recipe_test(cls, target, context, recipe, crafting_sim, price, paying_sim=None, build_error_list=True, first_phase=DEFAULT, from_resume=False, from_autonomy=False, funds_source=None):
        enabled = True
        error_list = []
        if crafting_sim is None:
            return RecipeTestResult(enabled=False, visible=False, errors=error_list)
        if recipe.entitlement is not None and not mtx.is_displayable(recipe.entitlement):
            return RecipeTestResult(enabled=False, visible=False, errors=error_list)
        if first_phase is not DEFAULT:
            first_phases = set([first_phase])
        else:
            paying_sim = crafting_sim if paying_sim is None else paying_sim
            if funds_source is None:
                source_funds = paying_sim.family_funds
            else:
                source_funds = get_funds_for_source(funds_source.funds_source, sim=paying_sim)
            if source_funds.money < price:
                enabled = False
                error_list.append(CraftingTuning.INSUFFICIENT_FUNDS_TOOLTIP(paying_sim))
            first_phases = set(recipe.first_phases)
        if not first_phases:
            logger.error('No first phases defined in recipe tuning: {}', recipe.__name__)
            return RecipeTestResult(enabled=False, visible=False, errors=error_list)
        dest_phases = set()
        available_phases = set()
        for phase in recipe.phases.values():
            if cls.phase_completable(phase, crafting_sim, context, target, from_autonomy=from_autonomy):
                available_phases.add(phase)
            if not phase.next_phases:
                dest_phases.add(phase)
        if not dest_phases:
            logger.error('No destination phases (those with no next phases) defined in recipe tuning: {}', recipe.__name__)
            return RecipeTestResult(enabled=False, visible=False, errors=error_list)
        available_first_phases = first_phases & available_phases
        available_dest_phases = dest_phases & available_phases

        def dijkstra_adj_available_nodes(current):
            for phase in current.next_phases:
                if phase in available_phases:
                    yield phase

        def dijkstra_adj_nodes_gen(current):
            for phase in current.next_phases:
                yield phase

        def dijkstra_distance_function(current, adjacent):
            if adjacent is None or adjacent in available_phases:
                return 0
            return 1

        path = algos.shortest_path(available_first_phases, available_dest_phases.__contains__, dijkstra_adj_available_nodes)
        if not path:
            enabled = False
            if build_error_list:
                type_requirements = set()
                path = algos.shortest_path(first_phases, dest_phases.__contains__, dijkstra_adj_nodes_gen, dijkstra_distance_function)
                if path:
                    for short_phase in path:
                        if short_phase in available_phases:
                            pass
                        else:
                            type_requirement = getattr(short_phase.super_affordance, 'crafting_type_requirement', None)
                            if type_requirement is not None and type_requirement.unavailable_tooltip is not None:
                                type_requirements.add(type_requirement)
                else:
                    logger.error('No valid paths through phases defined in recipe tuning: {}', recipe.__name__)
                    return RecipeTestResult(enabled=False, visible=False, errors=error_list)
                error_list.extend(type_requirement.unavailable_tooltip() for type_requirement in type_requirements)
        skill_test = recipe.skill_test
        resolver_target = target.sim_info if target.is_sim else target
        resolver = SingleActorAndObjectResolver(crafting_sim.sim_info, resolver_target, cls)
        if skill_test is not None:
            skill_result = resolver(skill_test)
            if not skill_result:
                if recipe.hidden_until_unlock and not from_resume:
                    return RecipeTestResult(enabled=False, visible=False, errors=error_list)
                enabled = False
                if skill_result.tooltip is not None:
                    error_list.append(skill_result.tooltip(crafting_sim, target))
        utility_info = recipe.utility_info
        if utility_info is not None:
            household = services.owning_household_of_active_lot()
            if household is not None:
                utility_result = services.utilities_manager(household.id).test_utility_info(utility_info)
                if not utility_result:
                    if utility_result.tooltip is not None:
                        error_list.append(utility_result.tooltip())
                    enabled = False
        if not (from_resume and recipe.additional_tests_ignored_on_resume):
            additional_tests = recipe.additional_tests
            if additional_tests:
                additional_result = additional_tests.run_tests(resolver)
                if not additional_result:
                    if recipe.hidden_until_unlock and not from_resume:
                        return RecipeTestResult(enabled=False, visible=False, errors=error_list)
                    enabled = False
                    if additional_result.tooltip is not None:
                        error_list.append(additional_result.tooltip(crafting_sim, target))
                else:
                    return RecipeTestResult(enabled=enabled, visible=True, errors=error_list, influence_by_active_mood=additional_result.influence_by_active_mood)
        return RecipeTestResult(enabled=enabled, visible=True, errors=error_list)

    @classmethod
    def phase_completable(cls, phase, sim, context, crafting_ico, from_autonomy=False):
        if phase.super_affordance.immediate:
            return True
        crafting_type_requirement = getattr(phase.super_affordance, 'crafting_type_requirement', None)
        if crafting_type_requirement is None:
            return True
        ref_count = services.object_manager().crafting_cache.get_ref_count(crafting_type_requirement, from_autonomy=from_autonomy)
        if crafting_ico is not None:
            parent_obj = crafting_ico.parent
            if parent_obj.state_component is None or parent_obj.state_component.is_object_usable():
                ref_count += 1
        if not ref_count:
            return False
        else:
            if context.source == InteractionContext.SOURCE_AUTONOMY:
                ref_count -= sim.get_autonomous_crafting_lockout_ref_count(crafting_type_requirement)
            if ref_count > 0:
                return True
        return False

    @constproperty
    def is_sim():
        return False

    @constproperty
    def is_part():
        return False

    @property
    def is_downloaded(self):
        return False

    def update_object_tooltip(self):
        pass

    def resume_test(self, target, context) -> TestResult:
        if self.phase is None:
            return TestResult(False, 'The crafting process is complete.')
        if self._current_crafting_interaction is not None:
            return TestResult(False, 'Crafting already in progress.')
        if not self.recipe.resumable:
            return TestResult(False, 'Recipe {} is not resumable'.format(self.recipe))
        if context.source == InteractionContext.SOURCE_AUTONOMY:
            sim = context.sim
            context = context._clone()
            if context.carry_target != target:
                context.carry_target = None
            (scored_interactions, _, autonomy_requests) = self._find_phase_affordances([self.phase], sim, context, target, display_errors=False)
            if not scored_interactions:
                return TestResult(False, 'Crafting cannot currently find any valid interaction for resume')
        return TestResult.TRUE

    def pay_for_item(self):
        if self._cost is not None and self._paying_sim is not None:
            if self._funds_source is None:
                self._paying_sim.household.funds.try_remove(self._cost, Consts_pb2.TELEMETRY_INTERACTION_COST)
            else:
                self._funds_source.try_remove_funds(self._paying_sim, self._cost)
        self._cost = None
        self._paying_sim = None
        if self._reserved_ingredients:
            with telemetry_helper.begin_hook(crafting_telemetry_writer, TELEMETRY_HOOK_INGREDIENTS_USED, sim_info=self.crafter.sim_info if self.crafter is not None else None) as hook:
                hook.write_int(TELEMETRY_FIELD_INGREDIENTS_QUANTITY, len(self._reserved_ingredients))
                if self.crafter is not None:
                    hook.write_localized_string(TELEMETRY_FIELD_RECIPE_NAME, self.recipe.get_recipe_name(self.crafter))
        should_save_ingredients = False
        ingredients_save = None
        resolver = self._current_crafting_interaction.get_resolver() if self._current_crafting_interaction else None
        if resolver:
            ingredients_save = self.recipe.use_ingredients.ingredients_save
            if ingredients_save.tests.run_tests(resolver):
                should_save_ingredients = random.random() < ingredients_save.save_chance.get_chance(resolver)
        if self.recipe.use_ingredients and self.recipe.use_ingredients.ingredients_save and should_save_ingredients and self._reserved_ingredients:
            self.refund_payment()
            if ingredients_save.notification:
                recipe_token = self.recipe.get_display_name()
                ingredients_token = LocalizationHelperTuning.get_bulleted_list((None,), (LocalizationHelperTuning.get_object_name(ingredient) for ingredient in self._reserved_ingredients))
                notification = ingredients_save.notification(self.crafter, resolver=resolver)
                notification.show_dialog(additional_tokens=(recipe_token, ingredients_token))
            if ingredients_save.balloon:
                balloon_requests = ingredients_save.balloon(self._current_crafting_interaction)
                if balloon_requests:
                    chosen_balloon = random.choice(balloon_requests)
                    if chosen_balloon is not None:
                        chosen_balloon.distribute()
            self._reserved_ingredients.clear()
            return
        for ingredient in self._reserved_ingredients:
            ingredient.destroy(source=self, cause='Consuming ingredients required to start crafting')
        self._reserved_ingredients.clear()

    def refund_payment(self):
        self._cost = None
        self._paying_sim = None
        if not self.crafter.is_being_destroyed:
            for ingredient in self._reserved_ingredients:
                inventory = ingredient.get_inventory()
                if inventory is not None and not inventory.try_move_hidden_object_to_inventory(ingredient, count=ingredient.stack_count()):
                    break

    def change_crafter(self, crafter):
        if self.crafter is crafter:
            return
        if self.crafter is not None:
            self.remove_order(self.crafter)
        self.crafter = crafter
        if (self.crafter_sim_id, self.recipe) not in self.orders:
            self.add_order(self.crafter_sim_id, self.recipe)

    def add_order(self, sim_id, recipe):
        self.orders.append((sim_id, recipe))
        self.multiple_order_process = True

    def remove_order(self, sim):
        if self.phase is None or self.phase.point_of_no_return:
            return
        if len(self.orders) == 1:
            if self.phase is not None:
                affordance = self.phase.super_affordance
                crafter = self.crafter
                if crafter is None:
                    logger.warn('Crafter with sim id:{} is uninstantiated when order is being removed in phase {} for recipe {}.  This may be valid, investigate why sim is uninstantiated', self._crafter_sim_id, self.phase, self.recipe, owner='nbaker', trigger_breakpoint=True)
                else:
                    for interaction in crafter.si_state:
                        if isinstance(interaction, affordance):
                            interaction.cancel(FinishingType.CRAFTING, cancel_reason_msg='CraftingOrderRemoved')
            return
        for (idx, order) in enumerate(self.orders):
            if order[0] == sim.id:
                del self.orders[idx]
                break
        logger.warn("Attempting to remove an order that isn't being tracked.")

    @property
    def current_ico(self):
        if self._current_ico_ref is not None:
            return self._current_ico_ref()

    @current_ico.setter
    def current_ico(self, value):
        if self._current_ico_ref is not None:
            old_ico = self._current_ico_ref()
            if old_ico is not None and not old_ico.crafting_component.is_final_product:
                self._current_ico_ref().remove_component(objects.components.types.CRAFTING_COMPONENT)
        self._previous_ico_ref = self._current_ico_ref
        self._current_ico_ref = None
        if value is not None:
            self._current_ico_ref = value.ref()
            self.add_crafting_component_to_object(value)

    @property
    def previous_ico(self):
        if self._previous_ico_ref is not None:
            return self._previous_ico_ref()

    @previous_ico.setter
    def previous_ico(self, value):
        if value is None:
            self._previous_ico_ref = None
        else:
            self._previous_ico_ref = value.ref()

    @property
    def crafter(self):
        if self._crafter_sim_id is None:
            return
        return services.object_manager().get(self._crafter_sim_id)

    @crafter.setter
    def crafter(self, value):
        if value is None:
            self._crafter_sim_id = None
        else:
            self._crafter_sim_id = value.sim_id

    @property
    def crafter_sim_id(self):
        return self._crafter_sim_id

    @property
    def owning_household(self):
        if self.crafter is None:
            return
        return self.crafter.household

    @property
    def id(self):
        pass

    def get_crafter_sim_info(self):
        if self._crafter_sim_id is None:
            return
        return services.sim_info_manager().get(self._crafter_sim_id)

    def get_crafted_by_text(self, is_from_gallery=False):
        if self.show_crafted_by_text and self.recipe.crafted_by_text:
            sim_info = self.get_crafter_sim_info()
            if sim_info is not None and not is_from_gallery:
                return self.recipe.crafted_by_text(sim_info)
            elif self._crafter_info_data is not None:
                return self.recipe.crafted_by_text(self._crafter_info_data)

    def remove_crafted_by_text(self):
        self.show_crafted_by_text = False

    def add_crafting_component_to_object(self, obj):
        obj.add_dynamic_component(objects.components.types.CRAFTING_COMPONENT)
        obj.set_crafting_process(self, is_final_product=self.current_phase_produces_final_product)

    @property
    def cancel_phase(self):
        if self.phase is None:
            return
        return self.phase.cancel_phase

    @property
    def previous_phase(self):
        return self._previous_phase

    @property
    def phase(self):
        if self._phase is not None:
            return self._phase
        elif self._previous_phase is not None:
            return self._previous_phase

    @phase.setter
    def phase(self, new_phase):
        logger.info('Set to new phase {}', new_phase)
        old_phase = self.phase
        if old_phase != new_phase:
            self._previous_phase = old_phase
            self._phase = new_phase
            if not old_phase.next_phases:
                self._previous_phase = None
            self.get_tracker(CraftingTuning.TURN_STATISTIC).set_value(CraftingTuning.TURN_STATISTIC, 0)

    @property
    def next_phases(self):
        if self.phase is not None:
            return self.phase.next_phases
        return self.recipe.first_phases

    @property
    def phase_index(self):
        return self.recipe.get_visible_phase_index(self.phase)

    @property
    def is_complete(self):
        return self.phase is None and self._previous_phase is None

    @property
    def is_last_phase(self):
        return self.phase is not None and not self.next_phases

    @property
    def is_single_phase_process(self):
        return self.recipe.is_single_phase_recipe

    @property
    def current_phase_produces_final_product(self):
        if self.phase is not None and self.phase.object_info_is_final_product:
            return True
        return False

    def get_phase_by_name(self, phase_name):
        if phase_name in self.recipe.phases:
            return self.recipe.phases[phase_name]

    def pop_order(self):
        (sim_id, recipe) = self.orders.pop(0)
        sim_info = services.sim_info_manager().get(sim_id)
        return (sim_info.get_sim_instance(), recipe)

    def get_order_or_recipe(self):
        if self.orders:
            (_, recipe) = self.orders[0]
            return recipe
        return self.recipe

    def setup_crafted_object(self, crafted_object, *, use_base_recipe=False, is_final_product=False, owning_household_id_override=None):
        crafted_object.add_dynamic_component(objects.components.types.CRAFTING_COMPONENT)
        crafted_object.set_crafting_process(self, use_base_recipe=use_base_recipe, is_final_product=is_final_product)
        owning_household_id = None
        if owning_household_id_override is None:
            crafter_roles = self.crafter.active_roles() if self.crafter is not None else ()
            if self.recipe.use_active_household_as_owner or any(role_state.active_household_crafting_override for role_state in crafter_roles):
                active_household_id = services.active_household_id()
                owning_household_id = active_household_id
            elif any(role_state.lot_owner_crafting_override for role_state in crafter_roles):
                owning_household = services.owning_household_of_active_lot()
                if owning_household is not None:
                    owning_household_id = owning_household.id
                    owning_household = self.owning_household
                    if owning_household is not None:
                        owning_household_id = owning_household.id
            else:
                owning_household = self.owning_household
                if owning_household is not None:
                    owning_household_id = owning_household.id
        else:
            owning_household_id = owning_household_id_override
        if owning_household_id is not None:
            crafted_object.set_household_owner_id(owning_household_id)
        self.recipe.setup_crafted_object(crafted_object, self.crafter, is_final_product)

    def apply_quality(self, obj):
        quality_stat = CraftingTuning.QUALITY_STATISTIC
        tracker = obj.get_tracker(quality_stat)
        total_quality_modifier = 0
        logger_quality_adjustment = {}
        stat_type = self.recipe.quality_control_statistic
        stat_instance = self.crafter.get_stat_instance(stat_type) or stat_type
        effective_skill_level = None
        if stat_instance is not None:
            effective_skill_level = self.crafter.get_effective_skill_level(stat_instance) if stat_instance.is_skill else stat_instance.get_user_value()
            quality_adjustment = self.recipe.get_final_product_quality_adjustment(effective_skill_level)
            logger_quality_adjustment['skill'] = str(quality_adjustment)
            total_quality_modifier += quality_adjustment
        if self._ingredient_quality_bonus:
            total_quality_modifier += self._ingredient_quality_bonus
            logger_quality_adjustment['ingredient'] = str(self._ingredient_quality_bonus)
            ingredient_state = IngredientTuning.get_ingredient_quality_state(self._ingredient_quality_bonus)
            if ingredient_state:
                obj.set_state(ingredient_state.state, ingredient_state)
        process_tracker = self.get_tracker(quality_stat)
        if process_tracker is not None:
            quality_statistic_instance = process_tracker.get_statistic(quality_stat)
            if quality_statistic_instance is not None:
                quality_value = quality_statistic_instance.get_value()
                logger_quality_adjustment['base'] = str(quality_value)
                shifted_quality = quality_value - quality_statistic_instance.min_value
                shifted_quality *= self._interaction_quality_multiplier
                quality_value = shifted_quality + quality_statistic_instance.min_value
                logger_quality_adjustment['multiplied'] = str(quality_value)
                total_quality_modifier += quality_value
        logger_quality_adjustment['final'] = str(total_quality_modifier)
        tracker.add_value(quality_stat, total_quality_modifier)
        crafting_handlers.log_quality(self, self.crafter.id, logger_quality_adjustment)
        obj.append_tags(self.recipe.apply_tags)
        self.make_masterwork_if_necessary(obj, effective_skill_level)

    def make_masterwork_if_necessary(self, obj, effective_skill_level):
        masterwork_data = self.recipe.masterworks_data
        if masterwork_data is None:
            return
        if self._current_crafting_interaction is None:
            logger.warn('Crafting interaction is None for recipe {} and object {}', self.recipe, obj, owner='camilogarcia')
            return
        resolver = self._current_crafting_interaction.get_resolver(target=obj)
        if not masterwork_data.base_test.run_tests(resolver):
            logger.debug('Masterwork failed base test', owner='nbaker')
            return
        final_chance = masterwork_data.base_chance
        logger.debug('Base masterwork chance: {}', final_chance, owner='nbaker')
        if effective_skill_level is not None:
            skill_delta = effective_skill_level - self.recipe.required_skill_level
            if skill_delta > 0:
                final_chance = final_chance + skill_delta*masterwork_data.skill_adjustment
                logger.debug('Masterwork skill modifier {}, new chance: {}', skill_delta*masterwork_data.skill_adjustment, final_chance, owner='nbaker')
        for multiplier_test in masterwork_data.multiplier_tests:
            if multiplier_test.tests.run_tests(resolver):
                final_chance *= multiplier_test.multiplier
                logger.debug('Masterwork modifier multiplier {}, new chance: {}', multiplier_test, final_chance, owner='nbaker')
        if random.random() > final_chance:
            logger.debug('Masterwork failed', owner='nbaker')
            return
        logger.debug('Masterwork succeeded', owner='nbaker')
        obj.set_state(CraftingTuning.MASTERWORK_STATE, CraftingTuning.MASTERWORK_STATE_VALUE)

    def apply_simoleon_value(self, obj, single_serving=False):
        if obj is self.original_target:
            return
        value_modifiers = self.recipe.simoleon_value_modifiers
        modifier = 1
        for (state_value, value_mods) in value_modifiers.items():
            if state_value.state is None:
                pass
            elif obj.has_state(state_value.state):
                actual_state_value = obj.get_state(state_value.state)
                if state_value == actual_state_value:
                    modifier *= value_mods.random_float()
        if obj.get_state(CraftingTuning.MASTERWORK_STATE) == CraftingTuning.MASTERWORK_STATE_VALUE:
            value_multiplier = self.recipe.masterworks_data.simoleon_value_multiplier
            modifier *= value_multiplier.random_float()
        if obj.has_state(CraftingTuning.MASTERWORK_STATE) and self.crafter is not None:
            simoleon_value_skill_curve = self.recipe.simoleon_value_skill_curve
            if simoleon_value_skill_curve is not None:
                modifier *= simoleon_value_skill_curve.get_multiplier(SingleSimResolver(self.crafter), self.crafter)
        if obj.get_state(CraftingTuning.COPY_STATE_VALUE.state) == CraftingTuning.COPY_STATE_VALUE:
            modifier *= CraftingTuning.COPY_VALUE_MULTIPLIER
        retail_price = self.recipe.retail_price
        if self.recipe.base_recipe is not None:
            retail_price = self.recipe.base_recipe.retail_price
        self.crafted_value = int(retail_price*modifier)
        obj.base_value = self.crafted_value

    def apply_quality_and_value(self, obj):
        self.apply_quality(obj)
        self.apply_simoleon_value(obj)

    def add_interaction_quality_multiplier(self, multiplier):
        self._interaction_quality_multiplier *= multiplier

    @property
    def crafting_quality(self):
        stat = self.get_stat_instance(CraftingTuning.QUALITY_STATISTIC)
        if stat is not None:
            return stat.get_value()
        return 0

    def apply_state_effects(self, interaction):
        resolver = interaction.get_resolver()
        for (state_value, effect_actions) in CraftingTuning.STATE_EFFECT_MAP.items():
            for obj in interaction.get_participants(ParticipantType.Object):
                if obj.has_state(state_value.state) and obj.get_state(state_value.state) is state_value:
                    loot = LootOperationList(resolver, (effect_actions,))
                    loot.apply_operations()

    def increment_phase(self, interaction=None):
        if interaction is not None:
            self.apply_state_effects(interaction)
        if self.phase is not None:
            if self.should_repeat_phase:
                return True
            self.phase = None
            if self.linked_process is not None:
                self.linked_process.phase = None
        return self.phase is not None

    @property
    def should_repeat_phase(self):
        if self.phase.loop_by_orders and len(self.orders) > 0:
            return True
        return False

    def get_turns_in_current_phase(self):
        if self.phase is None:
            return 0
        if self.phase.turn_based:
            num_turns = self.phase.num_turns
            if shorten_all_phases:
                num_turns = min(CraftingTuning.MAX_TURNS_FOR_AUTOSMOKE, num_turns)
            return num_turns
        elif self.phase.progress_based:
            return CraftingTuning.PROGRESS_VIRTUAL_TURNS
        return 0

    def get_progress(self):
        if self.phase is None:
            return 0
        if self.phase.turn_based:
            stat_type = CraftingTuning.TURN_STATISTIC
            scale = None
        elif self.phase.progress_based:
            stat_type = CraftingTuning.PROGRESS_STATISTIC
            scale = CraftingTuning.PROGRESS_VIRTUAL_TURNS
        else:
            return 0
        tracker = None
        ico_progress = 0
        if self.current_ico is not None:
            tracker = self.current_ico.get_tracker(stat_type)
        if tracker.has_statistic(stat_type):
            ico_progress = tracker.get_int_value(stat_type, scale=scale)
        tracker = self.get_tracker(stat_type)
        return max(ico_progress, tracker.get_int_value(stat_type, scale=scale))

    @property
    def should_go_to_next_phase_on_mixer_completion(self):
        current_turn = self.get_progress()
        total_turns = self.get_turns_in_current_phase()
        return current_turn >= total_turns

    def _create_aop_and_context_for_first_phase(self, start_crafting_si, crafting_target, **kwargs):
        sim = self.crafter
        if start_crafting_si.continuation_id and start_crafting_si.sim is sim:
            create_context_fn = functools.partial(start_crafting_si.context.clone_for_continuation, start_crafting_si)
        else:
            create_context_fn = functools.partial(InteractionContext, sim, group_id=start_crafting_si.group_id, insert_strategy=QueueInsertStrategy.LAST)
        context = create_context_fn(source=start_crafting_si.source, priority=start_crafting_si.priority)
        preferred_objects = set(start_crafting_si.preferred_objects)
        if sim in preferred_objects:
            preferred_objects.remove(sim)
        if self.original_target is not None and self.original_target is not sim:
            preferred_objects.add(self.original_target)
        pick = start_crafting_si.context.pick
        if pick is not None and pick.target is not None and pick.target is not sim:
            preferred_objects.add(pick.target)
        elif sim.posture_state.body_target is not None:
            preferred_objects.add(sim.posture_state.body_target)
        context.add_preferred_objects(preferred_objects)
        liabilities = ((CRAFTING_QUALITY_LIABILITY, CraftingQualityLiability(self, created_by='FirstPhase')),)
        (phase, aop_context) = self._choose_phase_and_create_aop_and_context(self.next_phases, sim, context, crafting_target, start_crafting_si, liabilities=liabilities, **kwargs)
        self.phase = phase
        return aop_context

    def push_si_for_first_phase(self, start_crafting_si, crafting_target=None) -> EnqueueResult:
        target = crafting_target if crafting_target is not None else self.original_target
        (aop, context) = self._create_aop_and_context_for_first_phase(start_crafting_si, target)
        if aop:
            return aop.test_and_execute(context)
        else:
            return EnqueueResult.NONE

    def _create_aop_and_context_for_phases(self, phases, previous_phase_si, source=DEFAULT, liabilities=None):
        sim = previous_phase_si.sim
        context = previous_phase_si.context.clone_for_continuation(previous_phase_si, source=DEFAULT, bucket=InteractionBucketType.BASED_ON_SOURCE)
        target = previous_phase_si.target
        if context.carry_target != target:
            context.carry_target = None
        (phase, result) = self._choose_phase_and_create_aop_and_context(phases, sim, context, target, previous_phase_si, liabilities=liabilities)
        if result != (None, None):
            self.phase = phase
        return result

    def _log_crafting_autonomy_requests(self, required_request, full_request, ico_request, chosen_interaction_str=None):

        def log_request(request, chosen_interaction_str, request_type):
            if request is not None:
                gsi_handlers.autonomy_handlers.archive_autonomy_data(request.sim, chosen_interaction_str, request_type, request.gsi_data)
                request.gsi_data = None

        if gsi_handlers.autonomy_handlers.archiver.enabled:
            log_request(required_request, chosen_interaction_str, 'Crafting Required Objects: FullAutonomy')
            log_request(full_request, chosen_interaction_str, 'Crafting All Objects: FullAutonomy')
            log_request(ico_request, chosen_interaction_str, 'Crafting ICO Required: FullAutonomy')

    def _find_phase_affordances(self, phases, sim, context, default_target, display_errors=True, **kwargs):
        affordance_to_phase = {}
        affordance_list = []
        ico_affordance_list = []
        for phase in phases:
            affordance = phase.super_affordance
            affordance_to_phase[affordance] = phase
            if phase.target_ico:
                ico_affordance_list.append(affordance)
            else:
                affordance_list.append(affordance)
        if affordance_list or not ico_affordance_list:
            logger.error("Couldn't find any interactions to look for for phases: {}", phases)
            return ((), affordance_to_phase)
        if self.original_target is not None and self.original_target is not sim:
            context.add_preferred_object(self.original_target)

        def get_interaction_parameters(affordance, base_interaction_parameters):
            if affordance not in affordance_to_phase:
                return base_interaction_parameters
            interaction_parameters = base_interaction_parameters.copy()
            interaction_parameters['phase'] = affordance_to_phase[affordance]
            return interaction_parameters

        def run_request(autonomy_service, affordance_list, required_objects=None):
            request = self._create_autonomy_request(sim, context, autonomy.autonomy_modes.FullAutonomy, affordance_list=affordance_list, required_objects=required_objects, crafting_process=self, get_interaction_parameters=get_interaction_parameters)
            result = autonomy_service.score_all_interactions(request)
            request.invalidate_created_interactions()
            return (result, request)

        result = None
        ico_result = None
        autonomy_service = services.autonomy_service()
        if autonomy_service is None:
            return ((), affordance_to_phase)
        required_request = None
        full_request = None
        ico_request = None
        if affordance_list:
            required_objects = set()
            if self.original_target is not None and self.original_target is not sim and (self.original_target.is_in_sim_inventory(sim=sim) or self.original_target.is_connected(sim)):
                required_objects.add(self.original_target)
            if default_target is not None and default_target is not sim:
                required_objects.add(default_target)
                inventoryitem_component = default_target.inventoryitem_component
                if inventoryitem_component is not None:
                    inventory_owner = inventoryitem_component.inventory_owner
                    if inventory_owner is not None:
                        required_objects.add(inventory_owner)
            elif required_objects or sim.posture_state.body_target is not None:
                required_objects.add(sim.posture_state.body_target)
            if required_objects:
                (result, required_request) = run_request(autonomy_service, affordance_list, required_objects=required_objects)
            if not result:
                (result, full_request) = run_request(autonomy_service, affordance_list)
        if ico_affordance_list:
            (ico_result, ico_request) = run_request(autonomy_service, ico_affordance_list, required_objects={self.current_ico})
        if result:
            if ico_result:
                result = result + ico_result
        else:
            result = ico_result
        if display_errors:
            if affordance_list:
                logger.warn("{}: Couldn't find object to run one of these interactions on: {}", phases, affordance_list)
            if ico_affordance_list:
                logger.warn("{}: Couldn't find one of these interactions on {}: {}", phases, self.current_ico, ico_affordance_list)
        return (result, affordance_to_phase, (required_request, full_request, ico_request))

    def _choose_phase_and_create_aop_and_context(self, phases, sim, context, default_target, previous_phase_si, liabilities=None, **kwargs):
        (scored_interactions, affordance_to_phase, autonomy_requests) = self._find_phase_affordances(phases, sim, context, default_target, **kwargs)
        if not scored_interactions:
            return (None, (None, None))
        best_score = None
        for scored_interaction_data in scored_interactions:
            scored_interaction_data.interaction.invalidate()
            if not best_score is None:
                if scored_interaction_data.score > best_score:
                    target_interaction = scored_interaction_data.interaction
                    best_score = scored_interaction_data.score
            target_interaction = scored_interaction_data.interaction
            best_score = scored_interaction_data.score
        target_affordance = target_interaction.affordance.get_interaction_type()
        phase = affordance_to_phase[target_affordance]
        exit_behavior = ()
        if not getattr(target_affordance, 'handles_go_to_next_recipe_phase', False):

            def auto_increment_phase():
                if self.increment_phase(interaction=previous_phase_si) or phase.target_ico and target is not None:
                    target.on_crafting_process_finished()

            exit_behavior = (auto_increment_phase,)
        target_affordance = previous_phase_si.generate_continuation_affordance(target_affordance)
        if issubclass(target_affordance, CarryCancelInteraction):
            context.source = InteractionContext.SOURCE_CARRY_CANCEL_AOP
        target = self.current_ico if phase.target_ico and self.current_ico is not None else target_interaction.target
        if gsi_handlers.autonomy_handlers.archiver.enabled:
            chosen_interaction_str = 'Interaction {} on {}; id:{}, sim:{}'.format(target_affordance, target, target_interaction.id, sim)
            self._log_crafting_autonomy_requests(*autonomy_requests, chosen_interaction_str=chosen_interaction_str)
        aop = AffordanceObjectPair(target_affordance, target, target_affordance, None, crafting_process=self, phase=phase, exit_functions=exit_behavior, liabilities=liabilities, anim_overrides=phase.anim_overrides, **kwargs)
        return (phase, (aop, context))

    def _push_si_for_phases(self, phases, previous_phase_si, source=DEFAULT, liabilities=None) -> EnqueueResult:
        (aop, context) = self._create_aop_and_context_for_phases(phases, previous_phase_si, source=source, liabilities=liabilities)
        if aop is None or context is None:
            return TestResult(False, 'Could not find AOP for phase(s): {}', phases)
        result = aop.test_and_execute(context)
        return result

    def cancel_crafting(self, previous_phase_si):
        if self.cancel_phase is not None and not self._push_si_for_phases((self.cancel_phase,), previous_phase_si):
            return False
        return True

    def create_aop_and_context_for_current_phase(self, previous_phase_si):
        return self._create_aop_and_context_for_phases(self.next_phases, previous_phase_si)

    def push_si_for_current_phase(self, previous_phase_si, from_resume=False, next_phases=None) -> ExecuteResult:
        liabilities = None
        if from_resume:
            liabilities = ((CRAFTING_QUALITY_LIABILITY, CraftingQualityLiability(self, created_by='Resume')),)
        if next_phases is None:
            if from_resume or self.should_repeat_phase or not self.next_phases:
                phase = None
                if self.orders:
                    (_, recipe) = self.orders[0]
                    phase = recipe.get_multiple_order_crafting_phase()
                if phase is not None:
                    next_phases = [phase]
                else:
                    next_phases = [self.phase]
            else:
                next_phases = self.next_phases
        return self._push_si_for_phases(next_phases, previous_phase_si, liabilities=liabilities)

    def get_accumulated_turns_for_all_phases(self):
        total_turns = 0
        if self.recipe is None:
            return 1
        for phase in self.recipe.phases.values():
            if not phase.is_visible:
                pass
            elif phase.turn_based:
                num_turns = phase.num_turns
                if shorten_all_phases:
                    num_turns = min(CraftingTuning.MAX_TURNS_FOR_AUTOSMOKE, num_turns)
                total_turns += num_turns
            elif phase.progress_based:
                total_turns += CraftingTuning.PROGRESS_VIRTUAL_TURNS
            else:
                total_turns += 1
        return total_turns

    def send_process_update(self, running_interaction, increment_turn=True):
        sim = self.crafter
        if sim is not None:
            logger_crafting = {}
            if self.phase is None:
                op = distributor.ops.InteractionProgressUpdate(sim.sim_id, 1, 0, running_interaction.id)
                Distributor.instance().add_op(sim, op)
                return
            if not self.phase.is_visible:
                crafting_handlers.log_process(self, sim.id, running_interaction, logger_crafting)
                return
            if self.phase.progress_based:
                turns = self.get_turns_in_current_phase()
                if turns == 0:
                    return
                current_progress = self.get_progress()
                progress = current_progress/turns
                logger_crafting['turns'] = str(turns)
                logger_crafting['progress'] = str(current_progress)
                logger_crafting['phase_type'] = 'progress'
            else:
                if increment_turn:
                    self._current_turn += 1
                logger_crafting['turns'] = str(self._total_turns)
                logger_crafting['progress'] = str(self._current_turn)
                logger_crafting['phase_type'] = 'turn'
                progress = self._current_turn/self._total_turns
            crafting_handlers.log_process(self, sim.id, running_interaction, logger_crafting)
            op = distributor.ops.InteractionProgressUpdate(sim.sim_id, progress, 0, running_interaction.id)
            Distributor.instance().add_op(sim, op)

    def copy_for_serve_interaction(self, recipe):
        new_process = CraftingProcess(recipe=recipe)
        new_process.crafter = self.crafter
        new_process.inscription = self.inscription
        new_process._current_ico_ref = self._current_ico_ref
        new_process._previous_ico_ref = self._previous_ico_ref
        new_process._phase = self._phase
        new_process._previous_phase = self._previous_phase
        new_process._cost = self._cost
        new_process._paying_sim = self._paying_sim
        new_process.orders = self.orders
        new_process._current_turn = self._current_turn
        new_process.ready_to_serve = self.ready_to_serve
        new_process.multiple_order_process = self.multiple_order_process
        new_process._reserved_ingredients = self._reserved_ingredients
        return new_process

    def save(self, crafting_process_msg):
        if self.recipe is None:
            return
        if self.recipe.guid64 == 0:
            logger.error('Trying to save an object with a recipe ID of 0, this is invalid. The recipe is {}', self.recipe)
            return
        crafting_process_msg.recipe_id = self.recipe.guid64
        if not self.ready_to_serve:
            if self.phase is not None:
                crafting_process_msg.phase_id = self.phase.id
            if self._previous_phase is not None:
                crafting_process_msg.previous_phase_id = self._previous_phase.id
        if self.phase is not None:
            crafting_process_msg.current_ico = self.current_ico.id
        if self.current_ico is not None and self._crafter_sim_id is not None:
            crafting_process_msg.crafter_sim_id = self._crafter_sim_id
        if self._crafter_info_data is None:
            crafter_info_msg = SimInfoNameData.generate_sim_info_name_data_msg(self.crafter.sim_info, use_profanity_filter=True)
            crafting_process_msg.crafter_info = crafter_info_msg
        if self.crafter is not None and self.inscription is not None:
            crafting_process_msg.inscription = self.inscription
        if self.crafted_value is not None:
            crafting_process_msg.crafted_value = self.crafted_value
        statistic_component = self.get_component(objects.components.types.STATISTIC_COMPONENT)
        statistic_tracker = statistic_component.get_statistic_tracker()
        if statistic_tracker is not None:
            regular_statistics = statistic_tracker.save()
            crafting_process_msg.statistic_tracker.statistics.extend(regular_statistics)

    def load(self, crafting_process_message):
        recipe_manager = services.get_instance_manager(sims4.resources.Types.RECIPE)
        self.recipe = recipe_manager.get(crafting_process_message.recipe_id)
        if self.recipe is None:
            return
        for phase in self.recipe.phases.values():
            if phase.id == crafting_process_message.phase_id:
                self.phase = phase
            elif phase.id == crafting_process_message.previous_phase_id:
                self._previous_phase = phase
        current_ico = services.object_manager().get(crafting_process_message.current_ico)
        if current_ico is None:
            current_ico = services.inventory_manager().get(crafting_process_message.current_ico)
        if current_ico is not None:
            self._current_ico_ref = current_ico.ref()
        if crafting_process_message.crafter_sim_id != 0:
            self._crafter_sim_id = crafting_process_message.crafter_sim_id
            self.add_order(self._crafter_sim_id, self.recipe)
        if crafting_process_message.HasField('crafter_info'):
            crafter_info = crafting_process_message.crafter_info
            self._crafter_info_data = SimInfoNameData(crafter_info.gender, crafter_info.first_name, crafter_info.last_name, crafter_info.full_name_key)
        if crafting_process_message.HasField('inscription'):
            self.inscription = crafting_process_message.inscription
        if crafting_process_message.HasField('crafted_value'):
            self.crafted_value = crafting_process_message.crafted_value
        statistic_component = self.get_component(objects.components.types.STATISTIC_COMPONENT)
        statistic_tracker = statistic_component.get_statistic_tracker()
        if statistic_tracker is not None:
            statistic_tracker.load(crafting_process_message.statistic_tracker.statistics)

class RecipeTestResult:
    __slots__ = ('_enabled', '_visible', '_errors', '_influence_by_active_mood')

    def __init__(self, enabled=True, visible=True, errors=None, influence_by_active_mood=False):
        self._enabled = enabled
        self._visible = visible
        if errors is None:
            self._errors = []
        else:
            self._errors = errors
        self._influence_by_active_mood = influence_by_active_mood

    def __repr__(self):
        visible_string = 'Visible' if self._visible else 'Invisible'
        return 'RecipeTestResult({}, {}, {} errors, Mood[{}])'.format(self._enabled, visible_string, len(self._errors), self._influence_by_active_mood)

    def __bool__(self):
        return self._enabled and self._visible

    @property
    def enabled(self):
        return self._enabled

    @property
    def visible(self):
        return self._visible

    @property
    def errors(self):
        return self._errors

    @property
    def influence_by_active_mood(self):
        return self._influence_by_active_mood
