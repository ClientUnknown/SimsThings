import randomfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import DoubleSimResolverfrom interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom interactions.utils.notification import NotificationElementfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import TunableVariant, TunableTuple, TunableList, TunableRange, OptionalTunable, TunableSet, TunableReferencefrom traits.traits import Traitimport interactions.utilsimport servicesimport sims4.resources
class KnowOtherSimTraitOp(BaseTargetedLootOperation):
    TRAIT_SPECIFIED = 0
    TRAIT_RANDOM = 1
    TRAIT_ALL = 2
    FACTORY_TUNABLES = {'traits': TunableVariant(description='\n            The traits that the subject may learn about the target.\n            ', specified=TunableTuple(description='\n                Specify individual traits that can be learned.\n                ', locked_args={'learned_type': TRAIT_SPECIFIED}, potential_traits=TunableList(description='\n                    A list of traits that the subject may learn about the target.\n                    ', tunable=Trait.TunableReference())), random=TunableTuple(description='\n                Specify a random number of traits to learn.\n                ', locked_args={'learned_type': TRAIT_RANDOM}, count=TunableRange(description='\n                    The number of potential traits the subject may learn about\n                    the target.\n                    ', tunable_type=int, default=1, minimum=1)), all=TunableTuple(description="\n                The subject Sim may learn all of the target's traits.\n                ", locked_args={'learned_type': TRAIT_ALL}), default='specified'), 'notification': OptionalTunable(description="\n            Specify a notification that will be displayed for every subject if\n            information is learned about each individual target_subject. This\n            should probably be used only if you can ensure that target_subject\n            does not return multiple participants. The first two additional\n            tokens are the Sim and target Sim, respectively. A third token\n            containing a string with a bulleted list of trait names will be a\n            String token in here. If you are learning multiple traits, you\n            should probably use it. If you're learning a single trait, you can\n            get away with writing specific text that does not use this token.\n            ", tunable=NotificationElement.TunableFactory(locked_args={'recipient_subject': None})), 'notification_no_more_traits': OptionalTunable(description='\n            Specify a notification that will be displayed when a Sim knows\n            all traits of another target Sim.\n            ', tunable=NotificationElement.TunableFactory(locked_args={'recipient_subject': None}))}

    def __init__(self, *args, traits, notification, notification_no_more_traits, **kwargs):
        super().__init__(*args, **kwargs)
        self.traits = traits
        self.notification = notification
        self.notification_no_more_traits = notification_no_more_traits

    @property
    def loot_type(self):
        return interactions.utils.LootType.RELATIONSHIP_BIT

    @staticmethod
    def _select_traits(knowledge, trait_tracker, random_count=None):
        traits = tuple(trait for trait in trait_tracker.personality_traits if trait not in knowledge.known_traits)
        if random_count is not None and traits:
            return random.sample(traits, min(random_count, len(traits)))
        return traits

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        trait_tracker = target.trait_tracker
        if self.traits.learned_type == self.TRAIT_SPECIFIED:
            traits = tuple(trait for trait in self.traits.potential_traits if trait_tracker.has_trait(trait) and trait not in knowledge.known_traits)
        elif self.traits.learned_type == self.TRAIT_ALL:
            traits = self._select_traits(knowledge, trait_tracker)
        elif self.traits.learned_type == self.TRAIT_RANDOM:
            traits = self._select_traits(knowledge, trait_tracker, random_count=self.traits.count)
            if traits or self.notification_no_more_traits is not None:
                interaction = resolver.interaction
                if interaction is not None:
                    self.notification_no_more_traits(interaction).show_notification(additional_tokens=(subject, target), recipients=(subject,), icon_override=IconInfoData(obj_instance=target))
        for trait in traits:
            knowledge.add_known_trait(trait)
        if traits:
            interaction = resolver.interaction
            if interaction is not None and self.notification is not None:
                trait_string = LocalizationHelperTuning.get_bulleted_list((None,), (trait.display_name(target) for trait in traits))
                self.notification(interaction).show_notification(additional_tokens=(subject, target, trait_string), recipients=(subject,), icon_override=IconInfoData(obj_instance=target))

class KnowOtherSimCareerOp(BaseTargetedLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.RELATIONSHIP_BIT

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None or knowledge.knows_career:
            return
        knowledge.add_knows_career(target.sim_id)
        career_tracker = target.career_tracker
        if career_tracker.has_custom_career:
            career_tracker.custom_career_data.show_custom_career_knowledge_notification(subject, DoubleSimResolver(subject, target))
            return
        for career in knowledge.get_known_careers():
            career.show_knowledge_notification(subject, DoubleSimResolver(subject, target))

class KnowOtherSimsStat(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'statistics': TunableSet(description='\n            A list of all the Statistics that the Sim can learn from\n            this loot op.\n            ', tunable=TunableReference(description='\n                A tunable reference to a statistic that might be learned\n                from this op.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True))}

    def __init__(self, *args, statistics=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._statistics = statistics

    @property
    def loot_type(self):
        return interactions.utils.LootType.RELATIONSHIP

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        target_tracker = target.commodity_tracker
        for stat in self._statistics:
            if target_tracker.has_statistic(stat):
                knowledge.add_known_stat(stat)
