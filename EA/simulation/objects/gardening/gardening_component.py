from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom protocolbuffers import UI_pb2 as ui_protocolsfrom protocolbuffers.Localization_pb2 import LocalizedStringTokenfrom distributor.rollback import ProtocolBufferRollbackfrom objects.collection_manager import ObjectCollectionData, CollectionIdentifier, ObjectCollectionRarityfrom objects.components import Componentfrom objects.components.tooltip_component import TooltipProvidingComponentMixinfrom objects.gardening.gardening_spawner import FruitSpawnerDatafrom objects.gardening.gardening_tuning import GardeningTuningfrom sims.rebate_manager import RebateCategoryEnumfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, TunableTupleimport services
class _SplicedFruitData:

    def __init__(self, fruit_name_key):
        self._fruit_name_key = fruit_name_key

    def populate_localization_token(self, token):
        token.type = LocalizedStringToken.OBJECT
        token.catalog_name_key = self._fruit_name_key
        token.catalog_description_key = self._fruit_name_key

class _GardeningComponent(AutoFactoryInit, Component, HasTunableFactory, TooltipProvidingComponentMixin, persistence_key=protocols.PersistenceMaster.PersistableData.GardeningComponent):
    FACTORY_TUNABLES = {'_unidentified_overrides': OptionalTunable(description='\n            If enabled, the unidentified version of this object has a different\n            name and description.\n            ', tunable=TunableTuple(description='\n                Overrides for the unidentified version of this object.\n                ', unidentified_name=TunableLocalizedString(description='\n                    Name that will be used when unidentified.\n                    '), unidentified_description=TunableLocalizedString(description='\n                    Description that will be used when unidentified.\n                    ')))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ui_metadata_handles = []
        self.owner.add_statistic_component()
        self.hovertip_requested = False
        self._fruit_spawners = []
        self._exclusive_fruits = set()

    @property
    def is_shoot(self):
        return False

    def on_add(self, *_, **__):
        self.owner.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_GARDENING
        active_household = services.active_household()
        if active_household is not None and services.current_zone_id() == active_household.zone_id and self.owner.is_on_active_lot():
            if hasattr(self, 'fruit_name'):
                return
            rebate_manager = active_household.rebate_manager
            rebate_manager.add_rebate_for_object(self.owner.id, RebateCategoryEnum.GAMEPLAY_OBJECT)

    def register_rebate_tests(self, test_set):
        for tests in test_set:
            services.get_event_manager().register_tests(self, tests)

    def handle_event(self, sim_info, event_type, resolver, **kwargs):
        if resolver.event_kwargs.get('state_change_obj') is not self.owner:
            return
        active_household = services.active_household()
        if active_household is not None and services.current_zone_id() == active_household.zone_id:
            rebate_manager = active_household.rebate_manager
            rebate_manager.add_rebate_for_object(self.owner.id, RebateCategoryEnum.GAMEPLAY_OBJECT)

    def _ui_metadata_gen(self):
        if GardeningTuning.is_spliced(self.owner):
            fruit_names = self.get_root_stock_names()
            description = LocalizationHelperTuning.get_comma_separated_list(*fruit_names)
            plant_name = GardeningTuning.SPLICED_PLANT_NAME()
        else:
            unidentified_overrides = self._unidentified_overrides
            if unidentified_overrides is not None and GardeningTuning.is_unidentified(self.owner):
                description = unidentified_overrides.unidentified_description
                plant_name = unidentified_overrides.unidentified_name
            else:
                if self.is_shoot and self.root_stock is not None:
                    description = LocalizationHelperTuning.get_name_value_pair(GardeningTuning.SHOOT_DESCRIPTION_STRING, LocalizationHelperTuning.get_object_name(self.root_stock.main_spawner.definition))
                else:
                    description = LocalizationHelperTuning.get_object_description(self.owner.definition)
                plant_name = LocalizationHelperTuning.get_object_name(self.owner.definition)
        yield ('recipe_name', plant_name)
        yield ('recipe_description', description)
        subtext = self.owner.get_state_strings()
        if subtext is not None:
            yield ('subtext', subtext)

    def update_hovertip(self):
        if self.hovertip_requested:
            old_handles = list(self._ui_metadata_handles)
            try:
                self._ui_metadata_handles = []
                for (name, value) in self._ui_metadata_gen():
                    handle = self.owner.add_ui_metadata(name, value)
                    self._ui_metadata_handles.append(handle)
            finally:
                for handle in old_handles:
                    self.owner.remove_ui_metadata(handle)
                self.owner.update_ui_metadata()

    def on_client_connect(self, client):
        self.update_hovertip()

    def show_gardening_details(self):
        return not any(self.owner.state_value_active(state) for state in GardeningTuning.DISABLE_DETAILS_STATE_VALUES)

    def show_gardening_tooltip(self):
        return not any(self.owner.state_value_active(state) for state in GardeningTuning.DISABLE_TOOLTIP_STATE_VALUES)

    def on_hovertip_requested(self):
        if not self.hovertip_requested:
            self.hovertip_requested = True
            self.update_hovertip()
            return True
        return False

    @property
    def fruit_spawners(self):
        return tuple(self._fruit_spawners)

    @property
    def root_stock(self):
        if not self._fruit_spawners:
            return
        return self._fruit_spawners[0]

    def get_root_stock_names(self):
        fruit_names = []
        for spawner in self._fruit_spawners:
            if spawner.spawn_weight == 0:
                pass
            else:
                tree_fruit_name_key = spawner.main_spawner.cls._components.gardening._tuned_values.fruit_name.hash
                if tree_fruit_name_key not in fruit_names:
                    fruit_names.append(tree_fruit_name_key)
        localized_fruit_names = []
        for fruit_name in fruit_names:
            localized_fruit_names.append(LocalizationHelperTuning.get_object_name(_SplicedFruitData(fruit_name)))
        return localized_fruit_names

    @property
    def root_stock_gardening_tuning(self):
        if self.root_stock is None:
            return
        return self.root_stock.main_spawner.cls._components.gardening

    def _add_spawner(self, fruit_definition):
        if fruit_definition in GardeningTuning.EXCLUSIVE_FRUITS:
            if not self._exclusive_fruits:
                for other_spawner in self._fruit_spawners:
                    if other_spawner.main_spawner in GardeningTuning.EXCLUSIVE_FRUITS:
                        pass
                    else:
                        other_spawner.spawn_weight = 0
            self._exclusive_fruits.add(fruit_definition)
        spawn_weight = self._get_fruit_spawn_weight(fruit_definition)
        spawner_data = FruitSpawnerData(spawn_weight=spawn_weight)
        spawner_data.set_fruit(fruit_definition)
        self._fruit_spawners.append(spawner_data)
        self.owner.add_spawner_data(spawner_data)

    def _get_fruit_spawn_weight(self, fruit):
        if self._exclusive_fruits and fruit not in GardeningTuning.EXCLUSIVE_FRUITS:
            return 0
        plant_rarity = None
        fruit_rarity = None
        gardening_collection_data = ObjectCollectionData.get_collection_data(CollectionIdentifier.Gardening)
        for obj_data in gardening_collection_data.object_list:
            if obj_data.collectable_item is fruit.definition:
                fruit_rarity = obj_data.rarity
            if obj_data.collectable_item is self.root_stock.main_spawner:
                plant_rarity = obj_data.rarity
            if self.root_stock is not None and fruit_rarity and plant_rarity:
                break
        if fruit_rarity is None:
            fruit_rarity = ObjectCollectionRarity.COMMON
        else:
            fruit_rarity = ObjectCollectionData.COLLECTION_RARITY_MAPPING[fruit_rarity].rarity_value
        if self.root_stock is not None:
            if plant_rarity is None:
                plant_rarity = ObjectCollectionRarity.COMMON
            else:
                plant_rarity = ObjectCollectionData.COLLECTION_RARITY_MAPPING[plant_rarity].rarity_value
            if fruit_rarity < plant_rarity:
                spawn_rarity = plant_rarity
            else:
                spawn_rarity = fruit_rarity
        else:
            spawn_rarity = fruit_rarity
        spawn_weight = GardeningTuning.SPAWN_WEIGHTS[spawn_rarity]
        return spawn_weight

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.GardeningComponent
        gardening_component_data = persistable_data.Extensions[protocols.PersistableGardeningComponent.persistable_data]
        for fruit_data in self._fruit_spawners:
            with ProtocolBufferRollback(gardening_component_data.fruit_spawners) as fruit_spawners:
                fruit_spawners.definition_id = fruit_data.main_spawner.definition.id
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        definition_manager = services.definition_manager()
        gardening_component_data = persistable_data.Extensions[protocols.PersistableGardeningComponent.persistable_data]
        for fruit_spawner in gardening_component_data.fruit_spawners:
            definition = definition_manager.get(fruit_spawner.definition_id)
            if definition is None:
                pass
            else:
                self._add_spawner(definition)

    def populate_localization_token(self, token):
        token.type = LocalizedStringToken.OBJECT
        unidentified_overrides = self._unidentified_overrides
        if unidentified_overrides is not None and GardeningTuning.is_unidentified(self.owner):
            token.catalog_name_key = unidentified_overrides.unidentified_name.hash
            token.catalog_description_key = unidentified_overrides.unidentified_description.hash
        else:
            self.owner.definition.populate_localization_token(token)
