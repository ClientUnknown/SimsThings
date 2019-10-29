import randomfrom event_testing.tests import TunableTestSetfrom interactions.utils.has_display_text_mixin import HasDisplayTextMixinfrom interactions.utils.success_chance import SuccessChancefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableEnumEntry, TunableFactory, OptionalTunableimport interactionsimport interactions.utilsimport servicesimport singletonsimport tag
class BaseLootOperation(HasTunableSingletonFactory, HasDisplayTextMixin):
    FACTORY_TUNABLES = {'tests': TunableTestSet(description='\n            The test to decide whether the loot action can be applied.\n            '), 'chance': SuccessChance.TunableFactory(description='\n            Percent chance that the loot action will be considered. The\n            chance is evaluated just before running the tests.\n            ')}

    @staticmethod
    def get_participant_tunable(tunable_name, optional=False, description='', participant_type_enum=interactions.ParticipantType, default_participant=interactions.ParticipantType.Actor, invalid_participants=interactions.ParticipantType.Invalid):
        enum_tunable = TunableEnumEntry(description=description, tunable_type=participant_type_enum, default=default_participant, invalid_enums=invalid_participants)
        if optional:
            return {tunable_name: OptionalTunable(description=description, tunable=enum_tunable)}
        return {tunable_name: enum_tunable}

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        if description is singletons.DEFAULT:
            description = 'The sim(s) the operation is applied to.'
        return BaseLootOperation.get_participant_tunable(*('subject',), description=description, **kwargs)

    def __init__(self, *args, subject=interactions.ParticipantType.Actor, target_participant_type=None, advertise=False, tests=None, chance=SuccessChance.ONE, exclusive_to_owning_si=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._advertise = advertise
        self._subject = subject
        self._target_participant_type = target_participant_type
        self._tests = tests
        self._chance = chance

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.subject)

    @property
    def advertise(self):
        return self._advertise

    @property
    def tested(self):
        return self._tests is not None

    @property
    def stat(self):
        pass

    def get_stat(self, interaction):
        return self.stat

    @property
    def subject(self):
        return self._subject

    @property
    def target_participant_type(self):
        return self._target_participant_type

    @property
    def chance(self):
        return self._chance

    @property
    def loot_type(self):
        return interactions.utils.LootType.GENERIC

    def test_resolver(self, resolver, ignore_chance=False):
        if ignore_chance or self._chance.multipliers or random.random() > self._chance.get_chance(resolver):
            return False
        test_result = True
        if self._tests:
            test_result = self._tests.run_tests(resolver)
            if not test_result:
                return test_result
        if self._chance.multipliers:
            chance = self._chance.get_chance(resolver)
            if ignore_chance and not chance:
                return False
            elif random.random() > chance:
                return False
        return test_result

    def _get_display_text_tokens(self, resolver=None):
        if resolver is not None:
            subject = resolver.get_participant(self._subject)
            target = resolver.get_participant(self._target_participant_type)
            return (subject, target)
        return ()

    @staticmethod
    def resolve_participants(participant, resolver):
        if isinstance(participant, tag.Tag):
            return (obj for obj in services.object_manager().values() if obj.has_tag(participant))
        return resolver.get_participants(participant)

    def apply_to_resolver(self, resolver, skip_test=False):
        if skip_test or not self.test_resolver(resolver):
            return (False, None)
        if self.subject is not None:
            for recipient in self.resolve_participants(self.subject, resolver):
                if self.target_participant_type is not None:
                    for target_recipient in self.resolve_participants(self.target_participant_type, resolver):
                        self._apply_to_subject_and_target(recipient, target_recipient, resolver)
                else:
                    self._apply_to_subject_and_target(recipient, None, resolver)
        elif self.target_participant_type is not None:
            for target_recipient in self.resolve_participants(self.target_participant_type, resolver):
                self._apply_to_subject_and_target(None, target_recipient, resolver)
        else:
            self._apply_to_subject_and_target(None, None, resolver)
        return (True, self._on_apply_completed())

    def _apply_to_subject_and_target(self, subject, target, resolver):
        raise NotImplemented

    def _get_object_from_recipient(self, recipient):
        if recipient is None:
            return
        elif recipient.is_sim:
            return recipient.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        return recipient

    def _on_apply_completed(self):
        pass

    def apply_to_interaction_statistic_change_element(self, resolver):
        self.apply_to_resolver(resolver, skip_test=True)

class BaseTargetedLootOperation(BaseLootOperation):

    @TunableFactory.factory_option
    def target_participant_type_options(description=singletons.DEFAULT, default_participant=interactions.ParticipantType.Invalid, **kwargs):
        if description is singletons.DEFAULT:
            description = 'Participant(s) that subject will apply operations on.'
        return BaseLootOperation.get_participant_tunable(*('target_participant_type',), description=description, default_participant=default_participant, **kwargs)
