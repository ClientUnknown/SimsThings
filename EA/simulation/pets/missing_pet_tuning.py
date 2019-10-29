from interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableFactoryimport interactionsimport singletons
class MakePetMissing(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        if subject.is_pet and subject.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            missing_pet_tracker = subject.household.missing_pet_tracker
            missing_pet_tracker.run_away(subject)

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        if description is singletons.DEFAULT:
            description = 'The object the tags are applied to.'
        return BaseLootOperation.get_participant_tunable(*('subject',), description=description, default_participant=interactions.ParticipantType.Actor, **kwargs)

class PostMissingPetAlert(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        if subject.household.missing_pet_tracker.is_pet_missing(subject):
            missing_pet_tracker = subject.household.missing_pet_tracker
            missing_pet_tracker.post_alert()

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        if description is singletons.DEFAULT:
            description = 'The object the tags are applied to.'
        return BaseLootOperation.get_participant_tunable(*('subject',), description=description, default_participant=interactions.ParticipantType.Actor, **kwargs)
