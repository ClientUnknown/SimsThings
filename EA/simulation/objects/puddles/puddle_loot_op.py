from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom objects.puddles import PuddleSize, create_puddle, PuddleLiquidfrom sims4.tuning.tunable import TunableEnumEntry, TunableList, TunableTuple, TunableRange, TunableReference, Tunable, OptionalTunableimport servicesimport sims4.loglogger = sims4.log.Logger('Puddles')
class TunablePuddleFactory(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(none=TunableRange(int, 5, minimum=0, description='Relative chance of no puddle.'), small=TunableRange(int, 5, minimum=0, description='Relative chance of small puddle.'), medium=TunableRange(int, 0, minimum=0, description='Relative chance of medium puddle.'), large=TunableRange(int, 0, minimum=0, description='Relative chance of large puddle.'), liquid=TunableEnumEntry(description='\n                The liquid of the puddle that will be generated.\n                ', tunable_type=PuddleLiquid, default=PuddleLiquid.WATER), **kwargs)

class CreatePuddlesLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'description': '\n            This loot will create puddles based on a tuned set of chances.\n            ', 'trait_based_puddle_factory': OptionalTunable(description='\n            A particpant type may be set to choose a puddle factory\n            based on traits the participant has.\n                     \n            If disabled, the default puddle factory is used.\n            ', tunable=TunableTuple(subject=TunableEnumEntry(description='\n                     The participant type whose traits are checked to determine\n                     which Trait Puddle Factory to use.\n                     ', tunable_type=ParticipantType, default=ParticipantType.Actor), trait_puddle_factory=TunableList(description='\n                    Ordered list of puddle factories with associated trait.\n                    Will use the first factory whose trait is on the subject.\n                    ', tunable=TunableTuple(trait=TunableReference(manager=services.trait_manager()), puddle_factory=TunablePuddleFactory(description='\n                            The chance of creating a puddle of various sizes.\n                            '))))), 'default_puddle_factory': TunablePuddleFactory(description='\n            This set of chances will be used if the sim creating the puddle does\n            not match any of the traits in the trait_puddle_chances tuning list.\n            '), 'max_distance': Tunable(description='\n                Maximum distance from the source object a puddle can be spawned.\n                If no position is found within this distance no puddle will be \n                made.\n                ', tunable_type=float, default=2.5), 'locked_args': {'subject': None}}

    def __init__(self, trait_based_puddle_factory, default_puddle_factory, max_distance, **kwargs):
        super().__init__(**kwargs)
        self.trait_based_puddle_factory = trait_based_puddle_factory
        self.default_puddle_factory = default_puddle_factory
        self.max_distance = max_distance
        self._subject = None if self.trait_based_puddle_factory is None else self.trait_based_puddle_factory.subject

    def _apply_to_subject_and_target(self, subject, target, resolver):
        puddle_factory = self.default_puddle_factory
        if subject is not None:
            trait_tracker = subject.trait_tracker
            for item in self.trait_based_puddle_factory.trait_puddle_factory:
                if trait_tracker.has_trait(item.trait):
                    puddle_factory = item.puddle_factory
                    break
        puddle = self.create_puddle_from_factory(puddle_factory)
        if puddle is not None:
            target_obj = target.get_sim_instance() if target.is_sim else target
            puddle.place_puddle(target_obj, self.max_distance)

    def create_puddle_from_factory(self, puddle_factory):
        value = sims4.random.weighted_random_item([(puddle_factory.none, PuddleSize.NoPuddle), (puddle_factory.small, PuddleSize.SmallPuddle), (puddle_factory.medium, PuddleSize.MediumPuddle), (puddle_factory.large, PuddleSize.LargePuddle)])
        return create_puddle(value, puddle_factory.liquid)
