from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantType, ParticipantTypeSinglefrom sims.outfits.outfit_enums import BodyType, OutfitCategoryfrom sims.outfits.outfit_utils import get_maximum_outfits_for_categoryfrom sims4.tuning.tunable import TunableEnumEntry, HasTunableSingletonFactory, AutoFactoryInit, TunableTuple, Tunable, OptionalTunable, TunableVariant, TunableEnumSetfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport sims4.loglogger = sims4.log.Logger('OutfitTests', default_owner='rmccord')
class OutfitBodyTypeTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The Sim we want to test the body type outfit for.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'outfit_override': OptionalTunable(description="\n            If enabled, specify a particular outfit to check the body types of.\n            Otherwise we check the subject's current outfit.\n            ", tunable=TunableTuple(description='\n                The outfit we want to check the body types of.\n                ', outfit_category=TunableEnumEntry(description='\n                    The outfit category.\n                    ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY), index=Tunable(description='\n                    The outfit index.\n                    ', tunable_type=int, default=0))), 'body_types': TunableWhiteBlackList(description='\n            The allowed and disallowed body types required to pass this test.\n            All CAS parts of the subject will be used to determine success or\n            failure.\n            ', tunable=TunableEnumEntry(description='\n                The body type we want the CAS part to support or not support.\n                ', tunable_type=BodyType, default=BodyType.FULL_BODY, invalid_enums=BodyType.NONE))}

    def get_expected_args(self):
        return {'subjects': self.subject}

    @cached_test
    def __call__(self, subjects, *args, **kwargs):
        for subject in subjects:
            if subject is None or not subject.is_sim:
                return TestResult(False, 'OutfitBodyTypeTest cannot test {}.', subject, tooltip=self.tooltip)
            outfit_category_and_index = subject.get_current_outfit() if self.outfit_override is None else (self.outfit_override.outfit_category, self.outfit_override.index)
            if not subject.has_outfit(outfit_category_and_index):
                return TestResult(False, 'OutfitBodyTypeTest cannot test {} since they do not have the requested outfit {}.', subject, outfit_category_and_index, tooltip=self.tooltip)
            outfit = subject.get_outfit(*outfit_category_and_index)
            if not self.body_types.test_collection(outfit.body_types):
                return TestResult(False, 'OutfitBodyTypeTest subject {} failed list of body types for outfit {}.', subject, outfit_category_and_index, tooltip=self.tooltip)
        return TestResult.TRUE

class OutfitTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    OUTFIT_CURRENT = 0
    OUTFIT_PREVIOUS = 1
    TEST_CAN_ADD = 0
    TEST_CANNOT_ADD = 1

    class _OutfitCategoryFromEnum(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'outfit_category': TunableEnumEntry(description='\n                The outfit category for which we must be able to add an outfit.\n                ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY)}

        def get_expected_args(self):
            return {}

        def get_outfit_category(self, **kwargs):
            return self.outfit_category

    class _OutfitCategoryFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The participant whose current outfit will determine the\n                resulting outfit category.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor)}

        def get_expected_args(self):
            return {'outfit_category_targets': self.participant}

        def get_outfit_category(self, outfit_category_targets=(), **kwargs):
            outfit_category_target = next(iter(outfit_category_targets), None)
            if outfit_category_target is not None:
                outfit = outfit_category_target.get_current_outfit()
                return outfit[0]

    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant against which to run this outfit test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'outfit': TunableVariant(description='\n            The outfit to use for the blacklist/whitelist tests.\n            ', locked_args={'current_outfit': OUTFIT_CURRENT, 'previous_outfits': OUTFIT_PREVIOUS}, default='current_outfit'), 'blacklist_outfits': TunableEnumSet(description="\n            If the specified participant's outfit matches any of these\n            categories, the test will fail.\n            ", enum_type=OutfitCategory), 'whitelist_outfits': TunableEnumSet(description="\n            If set, then the participant's outfit must match any of these\n            entries, or the test will fail.\n            ", enum_type=OutfitCategory), 'outfit_addition_test': OptionalTunable(description='\n            If enabled, then the test will verify whether or not the specified\n            participant can add an outfit to a specific category.\n            ', tunable=TunableTuple(description='\n                Tunables controlling the nature of this test.\n                ', outfit_category=TunableVariant(description='\n                    Define the outfit category for which we need to test addition.\n                    ', from_enum=_OutfitCategoryFromEnum.TunableFactory(), from_participant=_OutfitCategoryFromParticipant.TunableFactory(), default='from_enum'), test_type=TunableVariant(description='\n                    The condition to test for.\n                    ', locked_args={'can_add': TEST_CAN_ADD, 'cannot_add': TEST_CANNOT_ADD}, default='can_add')))}

    def get_expected_args(self):
        expected_args = {'test_targets': self.participant}
        if self.outfit_addition_test is not None:
            expected_args.update(self.outfit_addition_test.outfit_category.get_expected_args())
        return expected_args

    @cached_test
    def __call__(self, test_targets=(), **kwargs):
        for target in test_targets:
            if self.outfit == self.OUTFIT_CURRENT:
                outfit = target.get_current_outfit()
            elif self.outfit == self.OUTFIT_PREVIOUS:
                outfit = target.get_previous_outfit()
            if any(outfit[0] == blacklist_category for blacklist_category in self.blacklist_outfits):
                return TestResult(False, '{} is wearing a blacklisted outfit category', target, tooltip=self.tooltip)
            if self.whitelist_outfits and not any(outfit[0] == whitelist_category for whitelist_category in self.whitelist_outfits):
                return TestResult(False, '{} is not wearing any whitelisted outfit category', target, tooltip=self.tooltip)
            outfit_addition_test = self.outfit_addition_test
            if outfit_addition_test is not None:
                outfit_category = outfit_addition_test.outfit_category.get_outfit_category(**kwargs)
                outfits = target.get_outfits()
                outfits_in_category = outfits.get_outfits_in_category(outfit_category)
                if outfit_addition_test.test_type == self.TEST_CAN_ADD:
                    if outfits_in_category is not None and len(outfits_in_category) >= get_maximum_outfits_for_category(outfit_category):
                        return TestResult(False, '{} cannot add a new {} outfit, but is required to be able to', target, outfit_category, tooltip=self.tooltip)
                else:
                    if not outfits_in_category is None:
                        if len(outfits_in_category) < get_maximum_outfits_for_category(outfit_category):
                            return TestResult(False, '{} can add a new {} outfit, but is required not to not be able to', target, outfit_category, tooltip=self.tooltip)
                    return TestResult(False, '{} can add a new {} outfit, but is required not to not be able to', target, outfit_category, tooltip=self.tooltip)
        return TestResult.TRUE
