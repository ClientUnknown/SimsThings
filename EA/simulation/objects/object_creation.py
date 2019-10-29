import build_buyimport fishing.fishing_dataimport functoolsimport objects.components.typesimport randomimport servicesimport simsimport sims4.logimport sims4.resourcesfrom collections import namedtuplefrom crafting.crafting_grab_serving_mixin import GrabServingMixinfrom event_testing.resolver import InteractionResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSingle, ParticipantTypeSingleSim, ParticipantTypeActorTargetSim, ParticipantTypeObjectfrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom objects.components.state import TunableStateValueReference, StateComponentfrom objects.components.stolen_component import MarkObjectAsStolenfrom objects.components.stored_object_info_tuning import StoredObjectTypefrom objects.components.types import STORED_SIM_INFO_COMPONENT, STORED_OBJECT_INFO_COMPONENTfrom objects.helpers.create_object_helper import CreateObjectHelperfrom objects.hovertip import TooltipFieldsCompletefrom objects.placement.placement_helper import _PlacementStrategyLocation, _PlacementStrategySlotfrom postures import PostureTrackGroup, PostureTrackfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableList, TunableTuple, TunableEnumEntry, TunableVariant, OptionalTunable, Tunable, TunableSet, TunableRange, TunableFactoryfrom singletons import DEFAULTfrom tag import Tag, TunableTagsfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog_notification import UiDialogNotificationlogger = sims4.log.Logger('Creation')ObjectCreationParams = namedtuple('ObjectCreationParams', ('definition', 'setup_params'))
class CreationDataBase:

    def get_definition(self, resolver):
        raise NotImplementedError

    def get_creation_params(self, resolver):
        return ObjectCreationParams(self.get_definition(resolver), {})

    def setup_created_object(self, resolver, created_object, **setup_params):
        pass

    def get_source_object(self, resolver):
        pass

class _ObjectDefinition(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'definition': TunableReference(description='\n            The definition of the object that is created.\n            ', manager=services.definition_manager(), pack_safe=True)}

    def get_definition(self, resolver):
        return self.definition

class _ObjectDefinitionTested(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'fallback_definition': TunableReference(description='\n            Should no test pass, use this definition.\n            ', manager=services.definition_manager(), allow_none=True), 'definitions': TunableList(description='\n            A list of potential object definitions to use.\n            ', tunable=TunableTuple(weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this definition relative to other\n                    definitions in this list.\n                    '), definition=TunableReference(description='\n                    The definition of the object to be created.\n                    ', manager=services.definition_manager(), pack_safe=True)))}

    def get_definition(self, resolver):
        definition = weighted_random_item([(pair.weight.get_multiplier(resolver), pair.definition) for pair in self.definitions])
        if definition is not None:
            return definition
        return self.fallback_definition

class _RecipeDefinition(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'show_crafted_by_text': Tunable(description='\n            Show crafted by text on the tooltip of item created by this recipe. \n            ', tunable_type=bool, default=True)}

    @TunableFactory.factory_option
    def recipe_factory_tuning(pack_safe=False):
        return {'recipe': TunableReference(description='\n                The recipe to use to create the object.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), pack_safe=pack_safe)}

    def get_definition(self, resolver):
        return self.recipe.final_product.definition

    def setup_created_object(self, resolver, created_object, **__):
        from crafting.crafting_process import CraftingProcess
        crafter = resolver.get_participant(ParticipantType.Actor)
        crafting_process = CraftingProcess(crafter=crafter, recipe=self.recipe)
        if not self.show_crafted_by_text:
            crafting_process.remove_crafted_by_text()
        crafting_process.setup_crafted_object(created_object, is_final_product=True)

class _RandomWeightedRecipe(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'weighted_recipes': TunableList(description='\n            A list of weighted list of recipes that can be available for recipe creation.\n            ', tunable=TunableTuple(description='\n                The weighted recipe.\n                ', recipe=_RecipeDefinition.TunableFactory(recipe_factory_tuning={'pack_safe': True}), weight=TunableMultiplier.TunableFactory()), minlength=1)}

    def get_definition(self, resolver):
        logger.error('\n            get_definition is being called in _RandomWeightedRecipe, this should not be a standard behavior\n            when creating an object.  get_creation_params is the expected way to get the definition\n            ', owner='jdimailig')
        return self.get_creation_params(resolver).definition

    def get_creation_params(self, resolver):
        weighted_recipe_creation_data = list((weighted_recipe.weight.get_multiplier(resolver), weighted_recipe.recipe) for weighted_recipe in self.weighted_recipes)
        chosen_creation_data = weighted_random_item(weighted_recipe_creation_data)
        return ObjectCreationParams(chosen_creation_data.get_definition(resolver), {'chosen_creation_data': chosen_creation_data})

    def setup_created_object(self, resolver, created_object, chosen_creation_data=DEFAULT):
        if chosen_creation_data is DEFAULT:
            logger.error('chosen_creation_data not passed in!')
            return
        chosen_creation_data.setup_created_object(resolver, created_object)

class _CloneObject(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):

    class _ParticipantObject(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                Used to clone a participant object.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object)}

        def get_object(self, resolver):
            return resolver.get_participant(self.participant)

    class _SlottedObject(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'slotted_to_participant': TunableTuple(description='\n                Used to clone an object slotted to a participant.\n                ', parent_object_participant=TunableEnumEntry(description='\n                    The participant object which will contain the specified\n                    slot where the object to be cloned is slotted.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Object), parent_slot_type=TunableReference(description='\n                    A particular slot type where the cloned object can be found.  The\n                    first slot of this type found on the source_object will be used.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)))}

        def get_object(self, resolver):
            parent_object = resolver.get_participant(self.slotted_to_participant.parent_object_participant)
            if parent_object is not None:
                for runtime_slot in parent_object.get_runtime_slots_gen(slot_types={self.slotted_to_participant.parent_slot_type}, bone_name_hash=None):
                    if runtime_slot.empty:
                        pass
                    else:
                        return runtime_slot.children[0]

    FACTORY_TUNABLES = {'source_object': TunableVariant(description='\n            Where the object to be cloned can be found.\n            ', is_participant=_ParticipantObject.TunableFactory(), slotted_to_participant=_SlottedObject.TunableFactory(), default='slotted_to_participant'), 'definition_override': OptionalTunable(description='\n            Override to specify a different definition than that of the object\n            being cloned.\n            ', tunable=TunableReference(description='\n                The definition of the object that is created.\n                ', manager=services.definition_manager()))}

    def get_definition(self, resolver):
        if self.definition_override is not None:
            return self.definition_override
        else:
            source_object = self.get_source_object(resolver)
            if source_object is not None:
                return source_object.definition

    def get_source_object(self, resolver):
        return self.source_object.get_object(resolver)

class _CreatePhotoObject(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Used to create photo of a participant object.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def get_definition(self, resolver):
        object_to_shoot = resolver.get_participant(self.participant)
        if hasattr(object_to_shoot, 'get_photo_definition'):
            photo_definition = object_to_shoot.get_photo_definition()
            if photo_definition is not None:
                return photo_definition
        logger.error('{} create object basic extra tries to create a photo of {}, but none of the component provides get_photo_definition function', resolver, object_to_shoot, owner='cjiang')

    def setup_created_object(self, resolver, created_object, **__):
        crafter = resolver.get_participant(ParticipantType.Actor)
        created_object.add_dynamic_component(STORED_SIM_INFO_COMPONENT, sim_id=crafter.id)

class _FishingDataFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Participant on which we will get the fishing data information \n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object)}

    def get_fish_definition(self, resolver):
        target = resolver.get_participant(self.participant)
        if target is None:
            logger.error('{} create object tried to create an object using fishing data, but the participant {} is None.', resolver, self.participant, owner='mkartika')
            return
        fishing_location_component = target.fishing_location_component
        if fishing_location_component is None:
            logger.error('{} create object tried to create an object using fishing data on {}, but has no tuned Fishing Location Component.', resolver, target, owner='mkartika')
            return
        fishing_data = fishing_location_component.fishing_data
        if fishing_data is None:
            logger.error('{} create object tried to create an object using fishing data on {}, but has no tuned Fishing Data.', resolver, target, owner='shouse')
            return
        else:
            fish = fishing_data.choose_fish(resolver, require_bait=False)
            if fish is None:
                logger.error('{} create object tried to create an object using fishing data on {}, but caught no fish.', resolver, target, owner='mkartika')
                return
        return fish

class _FishingDataFromReference(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'fishing_data': fishing.fishing_data.TunableFishingDataReference(description='\n            Fishing data reference.\n            ')}

    def get_fish_definition(self, resolver):
        fishing_data = self.fishing_data
        if fishing_data is None:
            logger.error('{} create object tried to create an object without fishing data, so caught no fish.', resolver, owner='shouse')
            return
        else:
            fish = self.fishing_data.choose_fish(resolver, require_bait=False)
            if fish is None:
                logger.error('{} create object tried to create an object using fishing data {}, but caught no fish.', resolver, self.fishing_data, owner='mkartika')
                return
        return fish

class TunableFishingDataTargetVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, participant=_FishingDataFromParticipant.TunableFactory(), reference=_FishingDataFromReference.TunableFactory(), default='participant', **kwargs)

class _CreateObjectFromFishingData(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'source': TunableFishingDataTargetVariant(description='\n            Source on which we will get the fishing data information \n            ')}

    def get_definition(self, resolver):
        return self.source.get_fish_definition(resolver)

class _CreateObjectFromStoredObjectInfo(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'stored_object_info_participant': TunableEnumEntry(description='\n            The Sim participant of this interaction which contains the stored\n            object info that is used to create this object.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'stored_object_type': TunableEnumEntry(description='\n            The type of object being stored. This will be used to retrieve the\n            stored object from the Stored Object Info Component of the target.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID, invalid_enums=(StoredObjectType.INVALID,))}

    def get_definition(self, resolver):
        source_object = resolver.get_participant(self.stored_object_info_participant)
        if source_object is None:
            logger.error('{} create object basic extra tried to create an obj using stored object info, but the participant is None.', resolver, owner='jwilkinson')
            return
        stored_obj_info_component = source_object.get_component(STORED_OBJECT_INFO_COMPONENT)
        if stored_obj_info_component is None:
            logger.error("{} create object basic extra tried to create an obj using stored object info, but the participant doesn't have a stored object info component.", resolver, owner='jwilkinson')
            return
        definition_id = stored_obj_info_component.get_stored_object_info_definition_id(self.stored_object_type)
        definition = services.definition_manager().get(definition_id)
        return definition

    def setup_created_object(self, resolver, created_object, **__):
        source_object = resolver.get_participant(self.stored_object_info_participant)
        stored_obj_info_component = source_object.get_component(STORED_OBJECT_INFO_COMPONENT)
        if stored_obj_info_component is None:
            logger.error("{} create object basic extra tried to setup a created obj using stored object info, but the participant doesn't have a stored object info component.", resolver, owner='jwilkinson')
            return
        custom_name = stored_obj_info_component.get_stored_object_info_custom_name(self.stored_object_type)
        if custom_name is not None:
            created_object.set_custom_name(custom_name)
        states = stored_obj_info_component.get_stored_object_info_states(self.stored_object_type)
        if states:
            state_manager = services.get_instance_manager(sims4.resources.Types.OBJECT_STATE)
            for (state_guid, state_value_guid) in states:
                state = state_manager.get(state_guid)
                if state is None:
                    pass
                else:
                    state_value = state_manager.get(state_value_guid)
                    if state_value is None:
                        pass
                    else:
                        created_object.set_state(state, state_value, immediate=True)

class _RandomFromTags(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'filter_tags': TunableTags(description='\n            Define tags to try and create the object. Picks randomly from\n            objects with these tags.\n            ', minlength=1)}

    def get_definition(self, resolver):
        definition_manager = services.definition_manager()
        filtered_defs = list(definition_manager.get_definitions_for_tags_gen(self.filter_tags))
        if len(filtered_defs) > 0:
            return random.choice(filtered_defs)
        logger.error('{} create object basic extra tries to find object definitions tagged as {} , but no object definitions were found.', resolver, self.filter_tags, owner='jgiordano')

class _CraftableServing(CreationDataBase, GrabServingMixin, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'serving_source': TunableEnumEntry(description='\n            The source of the \n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_definition(self, resolver):
        recipe = self._get_recipe(resolver)
        if recipe is None:
            return
        return recipe.final_product_definition

    def _get_recipe(self, resolver):
        target = resolver.get_participant(self.serving_source)
        if target is None or not target.has_component(objects.components.types.CRAFTING_COMPONENT):
            logger.error('{} does not have a crafting component!', target)
            return
        recipe = target.get_recipe()
        if self.use_linked_recipe_mapping:
            interaction = resolver.interaction
            if interaction is not None:
                return recipe.get_linked_recipe(interaction.get_interaction_type())
        return recipe.get_base_recipe()

    def setup_created_object(self, resolver, created_object, **__):
        target = resolver.get_participant(self.serving_source)
        self._setup_crafted_object(self._get_recipe(resolver), target, created_object)

class TunableObjectCreationDataVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, definition=_ObjectDefinition.TunableFactory(), definition_tested=_ObjectDefinitionTested.TunableFactory(), recipe=_RecipeDefinition.TunableFactory(), random_recipe=_RandomWeightedRecipe.TunableFactory(), serving=_CraftableServing.TunableFactory(), clone_object=_CloneObject.TunableFactory(), create_photo_object=_CreatePhotoObject.TunableFactory(), random_by_tags=_RandomFromTags.TunableFactory(), from_stored_object_info=_CreateObjectFromStoredObjectInfo.TunableFactory(), from_fishing_data=_CreateObjectFromFishingData.TunableFactory(), default='definition', **kwargs)

class ObjectCreationMixin:
    INVENTORY = 'inventory'
    CARRY = 'carry'
    INSTANCE_TUNABLES = FACTORY_TUNABLES = {'creation_data': TunableObjectCreationDataVariant(description='\n            Define the object to create.\n            '), 'initial_states': TunableList(description='\n            A list of states to apply to the object as soon as it is created.\n            ', tunable=TunableTuple(description='\n                The state to apply and optional tests to decide if the state\n                should apply.\n                ', state=TunableStateValueReference(), tests=OptionalTunable(description='\n                    If enabled, the state will only get set on the created\n                    object if the tests pass. Note: These tests can not be\n                    performed on the newly created object.\n                    ', tunable=TunableTestSet()))), 'destroy_on_placement_failure': Tunable(description="\n            If checked, the created object will be destroyed on placement failure.\n            If unchecked, the created object will be placed into an appropriate\n            inventory on placement failure if possible.  If THAT fails, object\n            will be destroyed.\n            By default it goes into location target's inventory, you can use \n            fallback_location_target_override to make the created object go to\n            another participant's inventory.\n            ", tunable_type=bool, default=False), 'owner_sim': TunableEnumEntry(description='\n            The participant Sim whose household should own the object. Leave this\n            as Invalid to not assign ownership.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantType.Invalid), 'location': TunableVariant(description='\n            Where the object should be created.\n            ', default='position', position=_PlacementStrategyLocation.TunableFactory(), slot=_PlacementStrategySlot.TunableFactory(), inventory=TunableTuple(description='\n                An inventory based off of the chosen Participant Type.\n                ', locked_args={'location': INVENTORY}, location_target=TunableEnumEntry(description='\n                    "The owner of the inventory the object will be created in."\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor), mark_object_as_stolen_from_career=Tunable(description='\n                    Marks the object as stolen from a career by the tuned location_target participant.\n                    This should only be checked if this basic extra is on a CareerSuperInteraction.\n                    ', tunable_type=bool, default=False), place_in_hidden_inventory=Tunable(description='\n                    If True, the object is placed in the hidden inventory rather than the user-facing inventory.\n                    ', tunable_type=bool, default=False)), carry=TunableTuple(description='\n                Carry the object. Note: This expects an animation in the\n                interaction to trigger the carry.\n                ', locked_args={'location': CARRY}, carry_track_override=OptionalTunable(description='\n                    If enabled, specify which carry track the Sim must use to carry the\n                    created object.\n                    ', tunable=TunableEnumEntry(description='\n                        Which hand to carry the object in.\n                        ', tunable_type=PostureTrackGroup, default=PostureTrack.RIGHT)))), 'reserve_object': OptionalTunable(description='\n            If this is enabled, the created object will be reserved for use by\n            the set Sim.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)), 'fallback_location_target_override': OptionalTunable(description="\n            This will be ignored if destroy_on_placement_failure is checked. If this is enabled, we override fallback\n            location target.\n            Currently this is used when location target is different with the target whose inventory we want this\n            created object to go into. For example we want to create an object near another object but we want this\n            object to go to actor's inventory when placement fails.\n            ", tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor)), 'notification_inventory': OptionalTunable(description='\n            The notification to show when created object is placed in an inventory.\n            ', tunable=TunableTuple(participant_inventory=UiDialogNotification.TunableFactory(description="\n                    The notification to show when created object is placed in a participant's (such as sim's) inventory.\n                    "), household_inventory=UiDialogNotification.TunableFactory(description='\n                    The notification to show when created object is placed in a household inventory.\n                    '))), 'temporary_tags': OptionalTunable(description='\n            If enabled, these Tags are added to the created object and DO NOT\n            persist.\n            ', tunable=TunableSet(description='\n                A set of temporary tags that are added to the created object.\n                These tags DO NOT persist.\n                ', tunable=TunableEnumEntry(description='\n                    A tag that is added to the created object. This tag DOES\n                    NOT persist.\n                    ', tunable_type=Tag, default=Tag.INVALID), minlength=1))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resolver = None
        self._object_helper = None
        self._assigned_ownership = set()
        self._definition = None
        self._setup_params = None

    def initialize_helper(self, resolver, post_add=None):
        self._assigned_ownership.clear()
        self.resolver = resolver
        reserved_sim = None
        if self.reserve_object is not None:
            reserved_sim_info = self.resolver.get_participant(self.reserve_object)
            reserved_sim = reserved_sim_info.get_sim_instance()
        interaction = None
        if isinstance(self.resolver, InteractionResolver):
            interaction = self.resolver.interaction
        (self._definition, self._setup_params) = self.creation_data.get_creation_params(resolver)
        self._object_helper = CreateObjectHelper(reserved_sim, self._definition, interaction, object_to_clone=self.creation_data.get_source_object(self.resolver), init=self._setup_created_object, post_add=post_add)

    @property
    def definition(self):
        return self.creation_data.get_definition(self.resolver)

    def create_object(self, resolver):
        self.initialize_helper(resolver, post_add=self._place_object)
        created_object = self._object_helper.create_object()
        self._object_helper = None
        return created_object

    def _setup_created_object(self, created_object):
        self.creation_data.setup_created_object(self.resolver, created_object, **self._setup_params)
        if self.owner_sim != ParticipantType.Invalid:
            owner_sim = self.resolver.get_participant(self.owner_sim)
            if owner_sim is not None and owner_sim.is_sim:
                created_object.set_household_owner_id(owner_sim.household.id)
                self._assigned_ownership.add(created_object.id)
        for initial_state in self.initial_states:
            if created_object.state_component is None:
                created_object.add_component(StateComponent(created_object))
            if not initial_state.tests is None:
                pass
            if created_object.has_state(initial_state.state.state):
                created_object.set_state(initial_state.state.state, initial_state.state)
        if self.temporary_tags is not None:
            created_object.append_tags(self.temporary_tags)
        if created_object.has_component(objects.components.types.CRAFTING_COMPONENT):
            created_object.crafting_component.update_simoleon_tooltip()
            created_object.crafting_component.update_quality_tooltip()
            created_object.update_tooltip_field(TooltipFieldsComplete.simoleon_value, created_object.current_value)
        created_object.update_object_tooltip()

    def _get_ignored_object_ids(self):
        pass

    def _place_object_no_fallback(self, created_object):
        if hasattr(self.location, 'try_place_object'):
            ignored_object_ids = self._get_ignored_object_ids()
            return self.location.try_place_object(created_object, self.resolver, ignored_object_ids=ignored_object_ids)
        elif self.location.location == self.CARRY:
            return True
        return False

    def _get_fallback_location_target(self, created_object):
        if self.fallback_location_target_override is not None:
            target_override = self.resolver.get_participant(self.fallback_location_target_override)
            if target_override is not None:
                return target_override
            logger.error('Fallback location target override for participant {} and created object {} is none.\n                                Invalid participant?', self.fallback_location_target_override, created_object)
        if hasattr(self.location, '_get_reference_objects_gen'):
            for obj in self.location._get_reference_objects_gen(created_object, self.resolver):
                return obj
        return self.resolver.get_participant(self.location.location_target)

    def _place_object(self, created_object):
        self._setup_created_object(created_object)
        if self._place_object_no_fallback(created_object):
            return True
        if not self.destroy_on_placement_failure:
            participant = self._get_fallback_location_target(created_object)
            if isinstance(participant, sims.sim_info.SimInfo):
                participant = participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            location_type = getattr(self.location, 'location', None)
            if participant.is_sim and location_type == self.INVENTORY and self.location.mark_object_as_stolen_from_career:
                interaction = self.resolver.interaction
                if interaction is None:
                    logger.error('Mark Object As Stolen From Career is checked on CreateObject loot {}. \n                                    This should only be check on basic extra in a CareerSuperInteraction.', self)
                    return False
                career_uid = interaction.interaction_parameters.get('career_uid')
                if career_uid is not None:
                    career = interaction.sim.career_tracker.get_career_by_uid(career_uid)
                    if career is not None:
                        name_data = career.get_career_location().get_persistable_company_name_data()
                        text = None
                        guid = None
                        if isinstance(name_data, str):
                            text = name_data
                        else:
                            guid = name_data
                        MarkObjectAsStolen.mark_object_as_stolen(created_object, stolen_from_text=text, stolen_from_career_guid=guid)
                else:
                    logger.error('Interaction {} is tuned with a CreateObject basic extra that has mark_object_as_stolen_from_career as True,\n                                    but is not a CareerSuperInteraction. This is not supported.', interaction)
            if created_object.inventoryitem_component is not None:
                if created_object.id not in self._assigned_ownership:
                    if participant.is_sim:
                        participant_household_id = participant.household.id
                    else:
                        participant_household_id = participant.get_household_owner_id()
                    created_object.set_household_owner_id(participant_household_id)
                    self._assigned_ownership.add(created_object.id)
                if participant.inventory_component.player_try_add_object(created_object, hidden=location_type == self.INVENTORY and self.location.place_in_hidden_inventory):
                    if self.notification_inventory:
                        notification = self.notification_inventory.participant_inventory(participant, self.resolver)
                        notification.show_dialog()
                    return True
            sim = self.resolver.get_participant(ParticipantType.Actor)
            if not (participant.inventory_component is not None and sim is None or sim.is_sim):
                owning_household = services.owning_household_of_active_lot()
                if owning_household is not None:
                    for sim_info in owning_household.sim_info_gen():
                        if sim_info.is_instanced():
                            sim = sim_info.get_sim_instance()
                            break
            if not sim.is_npc:
                try:
                    created_object.set_household_owner_id(sim.household.id)
                    if build_buy.move_object_to_household_inventory(created_object):
                        if self.notification_inventory:
                            notification = self.notification_inventory.household_inventory(sim, self.resolver)
                            notification.show_dialog()
                        return True
                    logger.error('Creation: Failed to place object {} in household inventory.', created_object, owner='rmccord')
                except KeyError:
                    pass
        return False

class ObjectCreation(ObjectCreationMixin, HasTunableSingletonFactory, AutoFactoryInit):
    pass

class ObjectCreationOp(ObjectCreationMixin, BaseLootOperation):
    FACTORY_TUNABLES = {'quantity': TunableRange(description='\n            The number of objects that will be created.\n            ', tunable_type=int, default=1, minimum=1, maximum=10)}

    def __init__(self, *, creation_data, initial_states, destroy_on_placement_failure, owner_sim, location, reserve_object, temporary_tags, quantity, notification_inventory, fallback_location_target_override, **kwargs):
        super().__init__(**kwargs)
        self.creation_data = creation_data
        self.initial_states = initial_states
        self.destroy_on_placement_failure = destroy_on_placement_failure
        self.owner_sim = owner_sim
        self.location = location
        self.reserve_object = reserve_object
        self.temporary_tags = temporary_tags
        self.quantity = quantity
        self.notification_inventory = notification_inventory
        self.fallback_location_target_override = fallback_location_target_override

    def _apply_to_subject_and_target(self, subject, target, resolver):
        for _ in range(self.quantity):
            self.create_object(resolver)
