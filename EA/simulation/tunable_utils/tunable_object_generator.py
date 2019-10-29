from interactions import ParticipantType
class _ObjectGeneratorFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):

    @TunableFactory.factory_option
    def participant_type_data(*, participant_type, participant_default):
        return {'participant': TunableEnumEntry(description='\n                The participant determining which objects are to be generated.\n                ', tunable_type=participant_type, default=participant_default)}

    def get_objects(self, resolver, *args, **kwargs):
        return resolver.get_participants(self.participant, *args, **kwargs)

class TunableObjectGeneratorVariant(TunableVariant):

    def __init__(self, *args, participant_type=ParticipantType, participant_default=ParticipantType.Actor, **kwargs):
        super().__init__(*args, from_participant=_ObjectGeneratorFromParticipant.TunableFactory(participant_type_data={'participant_type': participant_type, 'participant_default': participant_default}), from_gardening=_ObjectGeneratorFromGardening.TunableFactory(), from_stored_object_component=_ObjectGeneratorFromStoredObjectComponent.TunableFactory(), default='from_participant', **kwargs)
