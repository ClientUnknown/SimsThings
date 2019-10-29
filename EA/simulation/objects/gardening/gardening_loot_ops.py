import placementimport servicesimport sims4.logfrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import VisibilityStatefrom objects.system import create_objectfrom sims4.random import weighted_random_itemfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReferencefrom tunable_multiplier import TunableMultiplierlogger = sims4.log.Logger('GardeningLootOps', default_owner='jdimailig')
class CreatePlantAtLocationLootOperation(BaseLootOperation):
    FACTORY_TUNABLES = {'fruits_to_sprout_from': TunableList(description='\n            A list of weighted fruit definitions we want to create a plant from.\n            ', tunable=TunableTuple(description='\n                The fruit to spawn a plant.\n                ', fruit=TunableReference(manager=services.get_instance_manager(Types.OBJECT), pack_safe=True), weight=TunableMultiplier.TunableFactory()), minlength=1), 'states_to_set_on_plant': TunableList(description='\n            The states to set on the created plant.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True), unique_entries=True)}

    def __init__(self, *args, fruits_to_sprout_from, states_to_set_on_plant, **kwargs):
        super().__init__(*args, **kwargs)
        self._fruits_to_sprout_from = fruits_to_sprout_from
        self._states_to_set_on_plant = states_to_set_on_plant

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not self._fruits_to_sprout_from:
            return
        weighted_fruit_definitions = list((weighted_fruit.weight.get_multiplier(resolver), weighted_fruit.fruit) for weighted_fruit in self._fruits_to_sprout_from)
        fruit_to_germinate = sims4.random.pop_weighted(weighted_fruit_definitions)
        parent_slot = None
        if not subject.is_terrain:
            runtime_slots = tuple(subject.get_runtime_slots_gen())
            fruit_to_try = fruit_to_germinate
            fruit_to_germinate = None
            while fruit_to_germinate is None:
                for slot in runtime_slots:
                    if not slot.empty:
                        pass
                    elif slot.is_valid_for_placement(definition=fruit_to_try):
                        fruit_to_germinate = fruit_to_try
                        parent_slot = slot
                        break
                if fruit_to_germinate is not None:
                    break
                if not weighted_fruit_definitions:
                    break
                fruit_to_try = sims4.random.pop_weighted(weighted_fruit_definitions)

        def post_add(obj):
            obj.transient = True
            obj.visibility = VisibilityState(visibility=False, inherits=False, enable_drop_shadow=False)

        created_fruit = create_object(fruit_to_germinate, post_add=post_add)
        if created_fruit is None:
            logger.error(f'Error occurred creating {fruit_to_germinate} in {self}')
            return
        if created_fruit.gardening_component is None:
            logger.error(f'{created_fruit} is a fruit with no fruit gardening component tuned in {self}')
            return
        if parent_slot is None:
            starting_location = placement.create_starting_location(position=subject.position, routing_surface=subject.routing_surface)
            fgl_context = placement.create_fgl_context_for_object(starting_location, created_fruit, ignored_object_ids=(created_fruit.id,))
            (position, orientation) = placement.find_good_location(fgl_context)
            if position is None or orientation is None:
                logger.warn(f'Could not find good location for {created_fruit} using starting location {starting_location}')
                return
            created_fruit.move_to(translation=position, orientation=orientation, routing_surface=subject.routing_surface)
        else:
            parent_slot.add_child(created_fruit)
        created_plant = created_fruit.gardening_component.germinate()
        if not created_plant:
            logger.error(f'Failed to germinate {created_fruit}')
            return
        for state_to_set in self._states_to_set_on_plant:
            created_plant.set_state(state_to_set.state, state_to_set)
        if created_plant.gardening_component is None:
            logger.error(f'{created_plant} was germinated but had no gardening component!')
            return
        if resolver.interaction:
            resolver.interaction.context.create_target_override = created_plant
