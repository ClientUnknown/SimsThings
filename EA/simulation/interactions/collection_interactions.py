from build_buy import ObjectOriginLocationfrom interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.picker_interaction import ObjectPickerInteractionfrom interactions.base.picker_strategy import StatePickerEnumerationStrategyfrom objects.collection_manager import CollectionIdentifier, ObjectCollectionDatafrom objects.components.state import ObjectState, ObjectStateValuefrom objects.system import create_objectfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTimport build_buyimport servicesimport sims4logger = sims4.log.Logger('CollectionInteractions')
class CollectionInteractionData:
    COLLECTION_COMBINING_TUNING = TunableMapping(description='\n        Mapping of collectible id, to states that we allow for collectible\n        combining.\n        ', key_type=TunableEnumEntry(description='\n            ID of the collectible that can be combined.\n            ', tunable_type=CollectionIdentifier, default=CollectionIdentifier.Unindentified), value_type=TunableTuple(description='\n            Possible states that can be combined on a collectible.\n            Mapping of state values that can be combined to get a new state\n            ', states_to_combine=TunableList(description='\n                Any states tuned here will be transfered from the combine \n                collectibles to the resulting object.\n                For example: Frogs will transfer their color and pattern \n                states.\n                ', tunable=ObjectState.TunableReference(description='\n                    State that can be inherited by the new collectible.\n                    ')), combination_mapping=TunableList(description='\n                Mapping of possible father-mother states to which new\n                state can they generate on the newly created collectible.\n                e.g.  If collectible A has green color state, and collectible\n                B has blue color states the resulting state can be a Green \n                color state.  This means the outcome of the interaction will\n                look for a collectible that has this resulting state value.\n                ', tunable=TunableTuple(description='\n                    State combinations to create a new state on the \n                    result collectible.\n                    ', father_state=ObjectStateValue.TunableReference(), mother_state=ObjectStateValue.TunableReference(), resulting_state=ObjectStateValue.TunableReference()))))

class CollectionPickerInteraction(ObjectPickerInteraction):
    INSTANCE_TUNABLES = {'collection_type': TunableEnumEntry(description='\n            ID of collectible that can be selected.\n            ', tunable_type=CollectionIdentifier, default=CollectionIdentifier.Unindentified, tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        (interaction_col_id, _, _) = ObjectCollectionData.get_collection_info_by_definition(target.definition.id)
        inst._combine_data = CollectionInteractionData.COLLECTION_COMBINING_TUNING.get(interaction_col_id)
        inst._collectible_data = set(ObjectCollectionData.get_collection_data(interaction_col_id).object_list)
        for collectible in context.sim.inventory_component:
            if not collectible.id == target.id or collectible.stack_count() == 1:
                pass
            elif collectible.collectable_component:
                (collectible_id, _, _) = ObjectCollectionData.get_collection_info_by_definition(collectible.definition.id)
                if collectible_id == interaction_col_id:
                    yield collectible

    def on_choice_selected(self, choice_tag, **kwargs):
        mother = choice_tag
        if mother is None:
            return
        father = self.target
        transferable_states = {}
        for state in self._combine_data.states_to_combine:
            mother_state = mother.get_state(state)
            father_state = father.get_state(state)
            transferable_states[state] = [mother_state, father_state]
            for combine_data in self._combine_data.combination_mapping:
                if combine_data.father_state == father_state and combine_data.mother_state == mother_state:
                    transferable_states[state].append(combine_data.resulting_state)
        if not transferable_states:
            logger.error('CollectionPickerInteraction: {} and {} collectibles have no transferable states', mother, father, owner='camilogarcia')
            return
        states_to_transfer = []
        for states in transferable_states.values():
            states_to_transfer.append(sims4.random.random.choice(states))
        target_match = len(states_to_transfer)
        possible_outcomes = []
        for collectable in self._collectible_data:
            match = 0
            for target_states in collectable.collectable_item.cls._components.state._tuned_values.states:
                if target_states.default_value in states_to_transfer:
                    match += 1
            if match == target_match:
                possible_outcomes.append(collectable.collectable_item)
        if not possible_outcomes:
            logger.error('CollectionPickerInteraction: No possible result when combining  {} and {}', mother, father, owner='camilogarcia')
            return
        definition_to_create = sims4.random.random.choice(possible_outcomes)
        obj = create_object(definition_to_create)
        if obj is None:
            logger.error('CollectionPickerInteraction: Failed to create object when combining  {} and {}', mother, father, owner='camilogarcia')
            return
        obj.update_ownership(self.sim.sim_info)
        if not self.sim.inventory_component.player_try_add_object(obj):
            obj.set_household_owner_id(services.active_household_id())
            if not build_buy.move_object_to_household_inventory(obj, object_location_type=ObjectOriginLocation.SIM_INVENTORY):
                logger.error('CollectionPickerInteraction: Failed to add object {} to household inventory.', obj, owner='rmccord')
        self._push_continuation(obj)

    def __init__(self, *args, **kwargs):
        self._combine_data = None
        self._collectible_data = None
        choice_enumeration_strategy = StatePickerEnumerationStrategy()
        super().__init__(*args, choice_enumeration_strategy=choice_enumeration_strategy, **kwargs)

class AwardCollectiblesInteraction(ImmediateSuperInteraction):

    def _run_interaction_gen(self, timeline):
        self._give_objects_for_collection_type()
        return True

    def _object_definitions_gen(self):
        collection_type = self.interaction_parameters.get('collection_type')
        if collection_type is None:
            return
        collection_data = ObjectCollectionData.get_collection_data(collection_type)
        if collection_data is None:
            return
        yield from (i.collectable_item for i in collection_data.object_list)
        yield from (i.collectable_item for i in collection_data.bonus_object_list)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, collection_type=None, **interaction_parameters):
        if collection_type is None:
            return
        collection_data = ObjectCollectionData.get_collection_data(collection_type)
        return cls.display_name(collection_data.collection_name)

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        for collection_type in CollectionIdentifier.values:
            if CollectionIdentifier.Unindentified == collection_type:
                pass
            elif ObjectCollectionData.get_collection_data(collection_type) is None:
                pass
            else:
                yield AffordanceObjectPair(cls, target, cls, None, collection_type=collection_type, **kwargs)

    def _give_objects_for_collection_type(self, **kwargs):
        for obj_def in self._object_definitions_gen():
            obj = create_object(obj_def)
            if obj is None:
                logger.error('AwardCollectiblesInteraction: Failed to create object {}', obj_def, owner='jdimailig')
            else:
                obj.update_ownership(self.sim.sim_info)
                if not self.sim.inventory_component.player_try_add_object(obj):
                    obj.set_household_owner_id(services.active_household_id())
                    if not build_buy.move_object_to_household_inventory(obj, object_location_type=ObjectOriginLocation.SIM_INVENTORY):
                        logger.error('AwardCollectiblesInteraction: Failed to add object {} to household inventory.', obj, owner='jdimailig')
