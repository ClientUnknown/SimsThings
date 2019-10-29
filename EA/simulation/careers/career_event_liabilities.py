from interactions import ParticipantTypefrom interactions.liability import Liabilityfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReference, HasTunableSingletonFactory, TunableVariant, OptionalTunable, TunableTuple, TunableMapping, TunableEnumEntryimport servicesimport sims4.resourcesfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.bouncer.bouncer_types import BouncerRequestPriority, RequestSpawningOptionlogger = sims4.log.Logger('CareerEventLiability', default_owner='tingyul')
class CareerEventTravelType(HasTunableSingletonFactory, AutoFactoryInit):

    def apply(self, career, resolver):
        raise NotImplementedError

class CareerEventTravelStartTopEvent(CareerEventTravelType):

    def apply(self, career, resolver):
        career.career_event_manager.start_top_career_event()

class _CareerEventTravelSubEvent(CareerEventTravelType):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        start_situation = value.start_situation
        if start_situation is not None:
            valid_job_types = start_situation.situation.get_tuned_jobs()
            for situation_job_type in start_situation.job_assignments.values():
                if situation_job_type not in valid_job_types:
                    logger.error('{} is an assigned job in {} but {} does not have that job', situation_job_type, instance_class, start_situation.situation)

    FACTORY_TUNABLES = {'start_situation': OptionalTunable(description='\n            If enabled, then a specific situation is to be started once the\n            travel request has finished. Participants of the requesting\n            interaction can fulfill specific jobs within that situation.\n            ', tunable=TunableTuple(description='\n                The situation data necessary to create a situation once the\n                travel request has ended.\n                ', situation=TunableReference(description='\n                    The situation to start.\n                    ', manager=services.situation_manager()), job_assignments=TunableMapping(description='\n                    The assignments for participants in this interaction.\n                    ', key_type=TunableEnumEntry(description='\n                        The participant that is to take on the specified job.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Actor), value_type=TunableReference(description='\n                        The situation job that is to be assigned to the\n                        specified participant.\n                        ', manager=services.situation_job_manager())))), 'verify_tunable_callback': _verify_tunable_callback}

    def apply(self, career, resolver):
        start_situation = self.start_situation
        if start_situation is not None:

            def start_situation_fn(zone_id):
                guest_list = SituationGuestList(invite_only=True)
                for (participant_type, situation_job_type) in start_situation.job_assignments.items():
                    for participant in resolver.get_participants(participant_type):
                        guest_list.add_guest_info(SituationGuestInfo(participant.sim_id, situation_job_type, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
                situation_manager = services.get_zone_situation_manager()
                return situation_manager.create_situation(start_situation.situation, guest_list=guest_list, zone_id=zone_id, spawn_sims_during_zone_spin_up=True, user_facing=False, travel_request_kwargs={'is_career_event': True})

        else:
            start_situation_fn = None
        career.career_event_manager.start_top_career_event(start_situation_fn=start_situation_fn)

class CareerEventTravelRequestSubEvent(_CareerEventTravelSubEvent):
    FACTORY_TUNABLES = {'career_event': TunableReference(description='\n            Career sub event to travel to and start upon arriving.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_EVENT))}

    def apply(self, career, resolver):
        career.career_event_manager.request_career_event(self.career_event)
        return super().apply(career, resolver)

class CareerEventTravelUnrequestSubEvent(_CareerEventTravelSubEvent):

    def apply(self, career, resolver):
        career.career_event_manager.unrequest_career_event()
        return super().apply(career, resolver)

class CareerEventTravelCrimeScene(_CareerEventTravelSubEvent):

    def apply(self, career, resolver):
        if not hasattr(career, 'get_crime_scene_career_event'):
            logger.error('Trying to use crime scene travel type without a career that has crime scenes')
            return
        career_event = career.get_crime_scene_career_event()
        career.career_event_manager.request_career_event(career_event)
        return super().apply(career, resolver)

class CareerEventTravelLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'CareerEventTravelLiability'
    FACTORY_TUNABLES = {'travel_type': TunableVariant(description='\n            Which type of career event travel to do.\n            ', start_work=CareerEventTravelStartTopEvent.TunableFactory(), start_sub_event=CareerEventTravelRequestSubEvent.TunableFactory(), end_sub_event=CareerEventTravelUnrequestSubEvent.TunableFactory(), crime_scene=CareerEventTravelCrimeScene.TunableFactory(), default='start_sub_event')}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction

    def should_transfer(self, continuation):
        return False

    def release(self):
        if self._interaction is None or not self._interaction.allow_outcomes:
            return
        career = self._interaction.sim.sim_info.career_tracker.career_currently_within_hours
        if career is None:
            logger.error("Sim {} is currently not at work -- can't start career event travel liability", self._interaction.sim)
            return
        if career.career_event_manager is None:
            logger.error("Sim {} is currently not part of a career event -- can't start career event travel liability", self._interaction.sim)
            return
        self.travel_type.apply(career, self._interaction.get_resolver())
