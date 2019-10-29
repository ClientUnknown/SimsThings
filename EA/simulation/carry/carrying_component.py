from animation.posture_manifest import Handfrom carry.holstering_tuning import TunableHolsteringBehaviorVariantfrom carry.put_down_strategy import PutDownStrategyOverridefrom objects.components import Component, types, componentmethodfrom sims.sim_info_types import Agefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableVariant, TunableMapping, TunableReference, TunableEnumEntry, TunableTuplefrom singletons import DEFAULTimport servicesimport sims4.resources
class CarryingComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.CARRYING_COMPONENT):

    class _CarryLocomotionBipedal(HasTunableFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'handedness_trait_map': TunableMapping(description="\n                Associate the Sim's handedness to specific traits.\n                ", key_type=TunableEnumEntry(description="\n                    The Sim's handedness.\n                    ", tunable_type=Hand, default=Hand.RIGHT), value_type=TunableReference(description='\n                    The trait associated with this specific handedness.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)))}

        def __init__(self, sim, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._sim = sim
            self._handedness = None

        def get_allowed_hands_type(self, allowed_hands_data):
            return allowed_hands_data.biped_allowed_hands

        def get_preferred_hand(self):
            if self._handedness is None:
                for (handedness, handedness_trait) in self.handedness_trait_map.items():
                    if self._sim.has_trait(handedness_trait):
                        self._handedness = handedness
                        break
                self.set_preferred_hand(Hand.RIGHT if self._sim.sim_id % 4 else Hand.LEFT)
            return self._handedness

        def set_preferred_hand(self, hand):
            if self._handedness is not None:
                handedness_trait = self.handedness_trait_map.get(self._handedness)
                if handedness_trait is not None:
                    self._sim.remove_trait(handedness_trait)
            handedness_trait = self.handedness_trait_map.get(hand)
            if handedness_trait is not None:
                self._sim.add_trait(handedness_trait)
            self._handedness = hand

    class _CarryLocomotionQuadrupedal(HasTunableFactory, AutoFactoryInit):

        def __init__(self, sim, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._sim = sim

        def get_allowed_hands_type(self, allowed_hands_data):
            return allowed_hands_data.quadruped_allowed_hands

        def get_preferred_hand(self):
            return Hand.RIGHT

        def set_preferred_hand(self, hand):
            pass

    FACTORY_TUNABLES = {'carry_locomotion': TunableVariant(description='\n            Define how this Sim locomotes, and by that how this Sim holds\n            things.\n            ', bipedal=_CarryLocomotionBipedal.TunableFactory(), quadrupedal=_CarryLocomotionQuadrupedal.TunableFactory(), default='bipedal'), 'default_put_down_strategy': TunableReference(description='\n            If the object specifies no species-specific put down tuning,\n            fallback to this strategy.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STRATEGY)), 'put_down_strategy_multipliers': TunableMapping(description="\n            Define some global multiplier that affect a Sim's behavior when\n            putting down objects. For instance, toddlers might be generally\n            discouraged from putting objects in slots, and Wild toddlers might\n            be generally encouraged to put objects on the floor.\n            ", key_type=TunableReference(description='\n                If the Sim has this trait, these multipliers are applied.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=PutDownStrategyOverride.TunableFactory()), 'holstering_behavior': TunableTuple(description='\n            Define the holstering behavior for this Sim.\n            ', default_behavior=TunableHolsteringBehaviorVariant(description='\n                Define the default holstering behavior for this Sim.\n                '), age_specific_behavior=TunableMapping(description='\n                Define age-specific holstering behavior for this Sim. For\n                example, toddlers always holster objects while routing (visual\n                choice).\n                ', key_type=TunableEnumEntry(description='\n                    The age for which this behavior applies.\n                    ', tunable_type=Age, default=Age.ADULT), value_type=TunableHolsteringBehaviorVariant()))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._carry_locomotion_data = self.carry_locomotion(self.owner)

    def on_add(self, *args, **kwargs):
        self.get_preferred_hand()

    @componentmethod
    def get_default_put_down_strategy(self):
        return self.default_put_down_strategy

    @componentmethod
    def is_allowed_to_holster(self):
        holstering_behavior = self.holstering_behavior.age_specific_behavior.get(self.owner.age, self.holstering_behavior.default_behavior)
        return holstering_behavior.is_holstering_allowed()

    @componentmethod
    def is_required_to_holster_while_routing(self, carry_object):
        holstering_behavior = self.holstering_behavior.age_specific_behavior.get(self.owner.age, self.holstering_behavior.default_behavior)
        return holstering_behavior.is_required_to_holster_while_routing(carry_object)

    @componentmethod
    def is_required_to_holster_for_transition(self, source, destination):
        holstering_behavior = self.holstering_behavior.age_specific_behavior.get(self.owner.age, self.holstering_behavior.default_behavior)
        return holstering_behavior.is_required_to_holster_for_transition(source, destination)

    @componentmethod
    def get_allowed_hands_type(self, allowed_hands_data):
        return self._carry_locomotion_data.get_allowed_hands_type(allowed_hands_data)

    @componentmethod
    def get_preferred_hand(self):
        return self._carry_locomotion_data.get_preferred_hand()

    @componentmethod
    def set_preferred_hand(self, hand):
        self._carry_locomotion_data.set_preferred_hand(hand)

    def _get_put_down_override(self, override_name):
        result = 1
        for (trait, override) in self.put_down_strategy_multipliers.items():
            if not self.owner.has_trait(trait):
                pass
            else:
                cost_override = getattr(override, override_name, DEFAULT)
                if cost_override is DEFAULT:
                    pass
                else:
                    if cost_override is None:
                        return
                    result *= cost_override
        return result

    @componentmethod
    def get_put_down_object_inventory_cost_override(self):
        return self._get_put_down_override('object_inventory_cost_override')

    @componentmethod
    def get_put_down_slot_cost_override(self):
        return self._get_put_down_override('slot_cost_override')
