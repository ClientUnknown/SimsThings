from _weakrefset import WeakSetimport randomfrom event_testing.register_test_event_mixin import RegisterTestEventMixinfrom event_testing.resolver import SingleSimResolver, DoubleObjectResolverfrom event_testing.test_events import TestEventfrom laundry.laundry_tuning import LaundryTuningfrom objects.system import create_objectfrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyimport primitivesimport servicesimport sims4.loglogger = sims4.log.Logger('Laundry', default_owner='mkartika')
class LaundryService(RegisterTestEventMixin, Service):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._laundry_hero_objects = WeakSet()
        self._hampers = WeakSet()
        self._affected_household = None
        self._hero_object_exist_before_bb = False

    @classproperty
    def required_packs(cls):
        return (Pack.SP13,)

    @property
    def hero_object_exist(self):
        if self._laundry_hero_objects:
            return True
        return False

    @property
    def laundry_hero_objects(self):
        return self._laundry_hero_objects

    @property
    def hampers(self):
        return self._hampers

    @property
    def affected_household(self):
        return self._affected_household

    def _get_affected_household(self):
        household = services.active_household()
        if household is None:
            return
        elif household.home_zone_id != services.current_zone_id():
            return
        return household

    def _find_hamper_and_laundry_objects(self):
        object_manager = services.object_manager()
        self._laundry_hero_objects = WeakSet(object_manager.get_objects_with_tags_gen(*LaundryTuning.LAUNDRY_HERO_OBJECT_TAGS))
        if self._affected_household is None:
            return
        self._hampers = WeakSet(object_manager.get_objects_with_tags_gen(*LaundryTuning.HAMPER_OBJECT_TAGS))

    def _find_closest_hamper(self, sim, hampers):
        estimate_distance = primitives.routing_utils.estimate_distance_helper
        if not hampers:
            return
        return min(hampers, key=lambda h: estimate_distance(sim, h))

    def _add_clothing_pile_to_hamper(self, sim):
        if not self._hampers:
            return False
        full_hamper_state = LaundryTuning.PUT_CLOTHING_PILE_ON_HAMPER.full_hamper_state
        available_hampers = set(obj for obj in self._hampers if not obj.state_value_active(full_hamper_state))
        if not available_hampers:
            return False
        sim_resolver = SingleSimResolver(sim.sim_info)
        if not LaundryTuning.PUT_CLOTHING_PILE_ON_HAMPER.tests.run_tests(sim_resolver):
            return False
        if random.random() > LaundryTuning.PUT_CLOTHING_PILE_ON_HAMPER.chance:
            return True
        obj_def = LaundryTuning.PUT_CLOTHING_PILE_ON_HAMPER.clothing_pile.definition
        if obj_def is None:
            logger.error('Failed to create clothing pile on hamper for {} because the pile definition is None.', sim)
            return False
        obj = None
        try:
            obj = create_object(obj_def)
        except:
            logger.error('Failed to create clothing pile {} on hamper for {}.', obj_def, sim)
            if obj is not None:
                obj.destroy(source=self, cause='Transferred to hamper.')
            return False
        finally:
            for initial_state in LaundryTuning.PUT_CLOTHING_PILE_ON_HAMPER.clothing_pile.initial_states:
                if initial_state.tests.run_tests(sim_resolver):
                    state_val = initial_state.state
                    if obj.has_state(state_val.state):
                        obj.set_state(state_val.state, state_val)
            closest_hamper = self._find_closest_hamper(sim, available_hampers)
            resolver = DoubleObjectResolver(obj, closest_hamper)
            for loot_action in LaundryTuning.PUT_CLOTHING_PILE_ON_HAMPER.loots_to_apply:
                loot_action.apply_to_resolver(resolver)
            obj.destroy(source=self, cause='Transferred to hamper.')
        return True

    def _generate_clothing_pile(self, interaction):
        loot = LaundryTuning.GENERATE_CLOTHING_PILE.loot_to_apply
        if loot is not None:
            if interaction is None:
                logger.error('Trying to generate clothing pile from None interaction.')
                return
            loot.apply_to_resolver(interaction.get_resolver())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete:
            self._update_last_unload_laundry_time()
            self._update_finished_laundry_condition(resolver)

    def _update_last_unload_laundry_time(self):
        if self._affected_household is None:
            return
        self._affected_household.laundry_tracker.update_last_unload_laundry_time()

    def _update_finished_laundry_condition(self, resolver):
        if self._affected_household is None:
            return
        self._affected_household.laundry_tracker.update_finished_laundry_condition(resolver)

    def on_spin_outfit_change(self, sim, outfit_category_and_index, interaction):
        if self._affected_household is None or not self.hero_object_exist:
            return
        if sim.sim_info.is_pet:
            return
        if sim.household is not self._affected_household:
            return
        no_pile_tag = LaundryTuning.GENERATE_CLOTHING_PILE.no_pile_interaction_tag
        if no_pile_tag in interaction.get_category_tags():
            return
        current_outfit = sim.sim_info.get_current_outfit()[0]
        target_outfit = outfit_category_and_index[0]
        no_pile_outfits = LaundryTuning.GENERATE_CLOTHING_PILE.no_pile_outfit_category
        naked_outfits = LaundryTuning.GENERATE_CLOTHING_PILE.naked_outfit_category
        if current_outfit not in no_pile_outfits and (target_outfit not in no_pile_outfits and (sim.on_home_lot and current_outfit not in naked_outfits)) and not self._add_clothing_pile_to_hamper(sim):
            self._generate_clothing_pile(interaction)
        if target_outfit not in naked_outfits:
            self._affected_household.laundry_tracker.apply_laundry_effect(sim)

    def on_service_enabled(self):
        self._affected_household.laundry_tracker.update_last_unload_laundry_time()

    def on_service_disabled(self):
        self._affected_household.laundry_tracker.reset()

    def on_build_buy_enter(self):
        self._hero_object_exist_before_bb = self.hero_object_exist

    def on_build_buy_exit(self):
        self._find_hamper_and_laundry_objects()
        if self._affected_household is not None and self._hero_object_exist_before_bb != self.hero_object_exist:
            if self.hero_object_exist:
                self.on_service_enabled()
            else:
                self.on_service_disabled()

    def on_loading_screen_animation_finished(self):
        self._affected_household = self._get_affected_household()
        self._find_hamper_and_laundry_objects()

    def on_zone_load(self):
        interaction_tag = LaundryTuning.PUT_AWAY_FINISHED_LAUNDRY.interaction_tag
        self._register_test_event(TestEvent.InteractionComplete, interaction_tag)

    def on_zone_unload(self):
        self._unregister_for_all_test_events()
