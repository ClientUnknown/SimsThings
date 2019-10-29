from protocolbuffers import SimObjectAttributes_pb2 as protocolsimport operatorimport randomfrom event_testing import test_eventsfrom objects.components import componentmethod_with_fallback, typesfrom objects.components.state import TunableStateValueReferencefrom objects.components.types import GARDENING_COMPONENTfrom objects.gardening.gardening_component import _GardeningComponentfrom objects.gardening.gardening_tuning import GardeningTuningfrom objects.hovertip import TooltipFieldsfrom objects.slots import SlotTypefrom objects.system import create_objectfrom placement import FGLSearchFlagsDefault, FGLSearchFlag, create_starting_location, FindGoodLocationContext, find_good_locationfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableReference, TunableMapping, TunableList, TunableTuple, TunableRangeimport objects.components.typesimport servicesimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Gardening', default_owner='camilogarcia')
class GardeningFruitComponent(_GardeningComponent, component_name=objects.components.types.GARDENING_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.GardeningComponent):
    FACTORY_TUNABLES = {'plant': TunableReference(description='\n            The plant that this fruit will grow into if planted or if it\n            spontaneously germinates.\n            ', manager=services.definition_manager()), 'splicing_recipies': TunableMapping(description='\n            The set of splicing recipes for this fruit. If a plant grown from\n            this fruit is spliced with one of these other fruits, the given type\n            of fruit will be also be spawned.\n            ', key_type=TunableReference(manager=services.definition_manager()), value_type=TunableReference(manager=services.definition_manager())), 'spawn_slot': SlotType.TunableReference(), 'spawn_state_mapping': TunableMapping(description='\n            Mapping of states from the spawner object into the possible states\n            that the spawned object may have.\n            ', key_type=TunableStateValueReference(), value_type=TunableList(description='\n                List of possible child states for a parent state.\n                ', tunable=TunableTuple(description='\n                    Pair of weight and possible state that the spawned object\n                    may have.\n                    ', weight=TunableRange(description='\n                        Weight that object will have on the probability\n                        calculation of which object to spawn.\n                        ', tunable_type=int, default=1, minimum=0), child_state=TunableStateValueReference()))), 'fruit_name': TunableLocalizedString(description='\n            Fruit name that will be used on the spliced plant description.\n            ', allow_catalog_name=True), 'season_harvest_times': TunableLocalizedString(description='\n            The text to display for the harvestable time to grow when seasons\n            are available.\n            '), 'season_harvest_times_fallback': TunableLocalizedString(description='\n            The text to display for the harvestable time to grow when seasons\n            are uninstalled.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._germination_handle = None

    def on_add(self, *args, **kwargs):
        self.start_germination_timer()
        return super().on_add(*args, **kwargs)

    def on_remove(self, *_, **__):
        self.stop_germination_timer()

    def scale_modifiers_gen(self):
        yield self.owner.get_stat_value(GardeningTuning.SCALE_COMMODITY)

    def on_state_changed(self, state, old_value, new_value, from_init):
        self.update_hovertip()

    def on_added_to_inventory(self):
        for (on_state_value, to_state_value) in GardeningTuning.PICKUP_STATE_MAPPING.items():
            if self.owner.has_state(on_state_value):
                self.owner.set_state(to_state_value)

    @componentmethod_with_fallback(lambda : None)
    def get_notebook_information(self, reference_notebook_entry, notebook_sub_entries):
        notebook_entry = reference_notebook_entry(self.owner.definition.id)
        return (notebook_entry,)

    def start_germination_timer(self):
        if self._germination_handle is not None:
            return
        germinate_stat = self.owner.commodity_tracker.add_statistic(GardeningTuning.SPONTANEOUS_GERMINATION_COMMODITY)
        value = random.uniform(germinate_stat.initial_value - GardeningTuning.SPONTANEOUS_GERMINATION_COMMODITY_VARIANCE, germinate_stat.initial_value)
        germinate_stat.set_value(value)
        threshold = sims4.math.Threshold(germinate_stat.convergence_value, operator.le)
        self._germination_handle = self.owner.commodity_tracker.create_and_add_listener(germinate_stat.stat_type, threshold, self.germinate)

    def stop_germination_timer(self):
        if self._germination_handle is None:
            return
        self.owner.commodity_tracker.remove_listener(self._germination_handle)
        self._germination_handle = None

    def _on_failure_to_germinate(self):
        self.owner.fade_in()
        dialog = GardeningTuning.GERMINATE_FAILURE_NOTIFICATION(self.owner)
        dialog.show_dialog(additional_tokens=(self.owner,))

    def germinate(self, *_, **__):
        self.stop_germination_timer()
        result = None
        try:
            result = self._germinate()
        except:
            self.start_germination_timer()
            raise
        if result == False:
            self.start_germination_timer()
            self._on_failure_to_germinate()
        if result is None:
            self.stop_germination_timer()
        return result

    def _germinate(self):
        plant = None
        try:
            plant = create_object(self.plant)
            location = self._find_germinate_location(plant)
            if location is None:
                plant.destroy(source=self.owner, cause='Failed to germinate: No location found')
                plant = None
                return False
            if self.owner.parent_slot is not None:
                self.owner.parent_slot.add_child(plant)
            else:
                plant.location = location
            gardening_component = plant.get_component(types.GARDENING_COMPONENT)
            gardening_component.add_fruit(self.owner, sprouted_from=True)
            created_object_quality = self.owner.get_state(GardeningTuning.QUALITY_STATE_VALUE)
            current_household = services.owning_household_of_active_lot()
            if current_household is not None:
                plant.set_household_owner_id(current_household.id)
                services.get_event_manager().process_events_for_household(test_events.TestEvent.ItemCrafted, current_household, crafted_object=plant, skill=None, quality=created_object_quality, masterwork=None)
            if self.owner.in_use:
                self.owner.transient = True
            else:
                self.owner.destroy(source=self.owner, cause='Successfully germinated.')
        except:
            logger.exception('Failed to germinate.')
            if plant is not None:
                plant.destroy(source=self.owner, cause='Failed to germinate.')
                plant = None
                return False

    def _find_germinate_location(self, plant):
        if self.owner.parent_slot is not None:
            result = self.owner.parent_slot.is_valid_for_placement(definition=self.plant, objects_to_ignore=(self.owner,))
            if not result:
                return
            location = self.owner.location
        else:
            search_flags = FGLSearchFlagsDefault | FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS | FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS | FGLSearchFlag.SHOULD_TEST_BUILDBUY
            starting_location = create_starting_location(location=self.owner.location)
            context = FindGoodLocationContext(starting_location, ignored_object_ids=(self.owner.id,), object_id=plant.id, object_def_state_index=plant.state_index, object_footprints=(plant.get_footprint(),), search_flags=search_flags)
            (translation, orientation) = find_good_location(context)
            if translation is None or orientation is None:
                return
            location = sims4.math.Location(sims4.math.Transform(translation, orientation), self.owner.routing_surface)
        return location

    @property
    def is_on_tree(self):
        if self.owner.parent_slot is not None and self.spawn_slot in self.owner.parent_slot.slot_types:
            return True
        return False

    def _ui_metadata_gen(self):
        yield from super()._ui_metadata_gen()
        season_service = services.season_service()
        if season_service is not None:
            season_text = GardeningTuning.get_seasonality_text_from_plant(self.plant)
            if season_text:
                yield (TooltipFields.season_text.name, season_text)
