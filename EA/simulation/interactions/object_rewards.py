from collections import Counterimport randomfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom objects.components import typesfrom objects.components.state import TunableStateValueReferencefrom sims4.localization import LocalizationHelperTuningfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import TunableRange, TunableTuple, TunableList, TunableVariant, HasTunableSingletonFactory, Tunable, OptionalTunable, TunableEnumEntry, AutoFactoryInitfrom tunable_multiplier import TestedSumfrom tunable_utils.create_object import ObjectCreator, RecipeCreatorfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport build_buyimport servicesimport sims4.loglogger = sims4.log.Logger('ObjectRewards', default_owner='rmccord')
class ObjectRewardsTuning(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'quantity': TunableRange(description='\n            Quantity of objects to create when loot action gets triggered.\n            The result of this loot will do a quantity number of random checks\n            to see which reward objects it will give.\n            e.g. quantity 2 will do 2 random checks using the weights tuned \n            to see which items it will give each time.\n            ', tunable_type=int, default=10, minimum=0, maximum=None), 'tested_bonus_quantity': TestedSum.TunableFactory(description='\n            A sum based multiplier for a bonus quantity of items to give.\n            ', locked_args={'base_value': 0}), 'reward_objects': TunableList(description='\n            List of pair of object reference-weight for the random calculation\n            e.g. Pair1[3,obj1] Pair2[7,obj2] means obj1 has a 30% chance of \n            being picked and obj2 has 70% chance of being picked\n            ', tunable=TunableTuple(reward=TunableList(description='\n                    List of objects to reward.  When the random check picks \n                    this value from the weight calculation it will give all\n                    the items tuned on this list.\n                    ', tunable=TunableVariant(specify_definition=ObjectCreator.TunableFactory(description='\n                            Object reference of the type of game object needed.\n                            ', get_definition=(True,)), specify_recipe=RecipeCreator.TunableFactory(description='\n                            Recipe to be created.\n                            '), default='specify_definition'), minlength=1), weight=TunableRange(description='\n                    Weight that object will have on the probability calculation \n                    of which objects will be created.\n                    ', tunable_type=int, default=1, minimum=0), states_on_reward_object=TunableList(description='\n                    List of states to set on the object reward after it has \n                    been created.\n                    ', tunable=TunableStateValueReference()), quantity=OptionalTunable(description='\n                    If this group of reward objects is chosen, this is the\n                    number of rewards (chosen randomly) to give from this list.\n                    If this is set to "One of Each" then the player will get one\n                    of everything in the list.\n                    ', disabled_name='one_of_each', enabled_name='specific_amount', tunable=TunableRange(description='\n                        The number of random objects to give from this list.\n                        This does mean the same object could be given multiple\n                        times. This can also be tuned to a value higher than the\n                        number of objects in the list.\n                        ', tunable_type=int, minimum=1, default=1))), minlength=1)}

class ObjectRewardsOperation(BaseLootOperation):
    FACTORY_TUNABLES = {'object_rewards': ObjectRewardsTuning.TunableFactory(description='\n            Object rewards when running the loot.  Rewards objects will be created\n            and sent to the tuned inventory.\n            '), 'notification': OptionalTunable(description='\n            If enabled, a notification will be displayed when this object reward\n            is granted to a Sim.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification to display when this object reward is granted\n                to the Sim. There is one additional token provided: a string\n                representing a bulleted list of all individual rewards granted.\n                ')), 'force_family_inventory': Tunable(description='\n            If Enabled, the rewards object(s) will be put in the family \n            inventory no matter what.  If not enabled, the object will try to\n            be added to the sim inventory, if that is not possible it will be\n            added to the family inventory as an automatic fallback.', tunable_type=bool, default=False), 'place_in_mailbox': Tunable(description='\n            If Enabled, the rewards object(s) will be put in the mailbox if\n            the active lot is the sims home lot', tunable_type=bool, default=False), 'make_sim_owner': Tunable(description='\n            If enabled, the actor of the loot will be set as the owner of the\n            object\n            ', tunable_type=bool, default=False), 'store_sim_info_on_reward': OptionalTunable(description="\n            If enabled, a sim info will be stored on the reward object. This \n            is mostly used for the cow plant life essence, which will store the\n            sim info of the sim from which the life essence was drained.\n            \n            Ex: For cow plant's milk life essence, we want to transfer the dead\n            sim's sim info from the cow plant to the created essence drink.\n            ", tunable=TunableTuple(description='\n            \n                ', participant=TunableEnumEntry(description='\n                    The participant of this interaction which has a \n                    StoredSimInfoComponent. The stored sim info will be transferred\n                    to the created rewards and will then be removed from the source.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Object), transfer_from_stored_sim_info=Tunable(description='\n                    If checked then the sim info that will be stored on the \n                    reward is going to be transfered from the participants\n                    StoredSimInfoComponent. The stored sim info will be transferred\n                    to the created rewards and will then be removed from the source.\n                    \n                    If not checked then the participant sim info will be \n                    stored directly onto the object, instead of transfered.\n                    ', tunable_type=bool, default=True)))}

    def __init__(self, object_rewards, notification, force_family_inventory, place_in_mailbox, make_sim_owner, store_sim_info_on_reward, subject=None, **kwargs):
        super().__init__(subject=subject, **kwargs)
        self._object_rewards = object_rewards
        self._notification = notification
        self._force_family_inventory = force_family_inventory
        self._make_sim_owner = make_sim_owner
        self._store_sim_info_on_reward = store_sim_info_on_reward
        self._place_in_mailbox = place_in_mailbox

    def _create_object_rewards(self, obj_weight_states_tuple, obj_counter, resolver, subject=None, placement_override_func=None):
        (obj_result, obj_states, quantity) = weighted_random_item(obj_weight_states_tuple)
        object_rewards = []
        if quantity is None:
            object_rewards = obj_result
        else:
            object_rewards.extend(random.choice(obj_result) for _ in range(quantity))
        for obj_reward in object_rewards:
            created_obj = obj_reward(init=None, post_add=lambda *args: self._place_object(*args, resolver=resolver, subject=subject, placement_override_func=placement_override_func))
            obj_counter[created_obj.definition] += 1
            if created_obj is not None and obj_states:
                for obj_state in obj_states:
                    created_obj.set_state(obj_state.state, obj_state)

    def apply_with_placement_override(self, subject, resolver, placement_override_func):
        self._apply_to_subject_and_target(subject, None, resolver, placement_override_func=placement_override_func)

    def _apply_to_subject_and_target(self, subject, target, resolver, placement_override_func=None):
        if subject.is_npc:
            return
        obj_counter = Counter()
        quantity = self._object_rewards.quantity
        quantity += self._object_rewards.tested_bonus_quantity.get_modified_value(resolver)
        for _ in range(int(quantity)):
            weight_pairs = [(data.weight, (data.reward, data.states_on_reward_object, data.quantity)) for data in self._object_rewards.reward_objects]
            self._create_object_rewards(weight_pairs, obj_counter, resolver, subject=subject, placement_override_func=placement_override_func)
        if obj_counter and self._notification is not None:
            obj_names = [LocalizationHelperTuning.get_object_count(count, obj) for (obj, count) in obj_counter.items()]
            dialog = self._notification(subject, resolver=resolver)
            dialog.show_dialog(additional_tokens=(LocalizationHelperTuning.get_bulleted_list((None,), obj_names),))
        return True

    def _place_object(self, created_object, resolver=None, subject=None, placement_override_func=None):
        subject_to_apply = subject if subject is not None else resolver.get_participant(ParticipantType.Actor)
        created_object.update_ownership(subject_to_apply, make_sim_owner=self._make_sim_owner)
        if self._store_sim_info_on_reward is not None:
            stored_sim_source = resolver.get_participant(self._store_sim_info_on_reward.participant)
            if self._store_sim_info_on_reward.transfer_from_stored_sim_info:
                sim_id = stored_sim_source.get_stored_sim_id()
            else:
                sim_id = stored_sim_source.id
            if sim_id is not None:
                created_object.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=sim_id)
                if self._store_sim_info_on_reward.transfer_from_stored_sim_info:
                    stored_sim_source.remove_component(types.STORED_SIM_INFO_COMPONENT)
                created_object.update_object_tooltip()
        if placement_override_func is not None:
            placement_override_func(subject_to_apply, created_object)
            return
        if self._place_in_mailbox:
            sim_household = subject_to_apply.household
            if sim_household is not None:
                zone = services.get_zone(sim_household.home_zone_id)
                if zone is not None:
                    lot_hidden_inventory = zone.lot.get_hidden_inventory()
                    if lot_hidden_inventory is not None and lot_hidden_inventory.player_try_add_object(created_object):
                        return
        if not self._force_family_inventory:
            instanced_sim = subject_to_apply.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if instanced_sim is not None and instanced_sim.inventory_component.can_add(created_object) and instanced_sim.inventory_component.player_try_add_object(created_object):
                return
        if not build_buy.move_object_to_household_inventory(created_object):
            logger.error('Failed to add object reward {} to household inventory.', created_object, owner='rmccord')
