from protocolbuffers import SimObjectAttributes_pb2from careers.career_event_zone_director import CareerEventZoneDirectorfrom careers.career_event_zone_requirement import RequiredCareerEventZoneTunableVariantfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions.utils.loot import LootActionsfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.protocol_buffer_utils import has_fieldfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, OptionalTunable, TunableReference, TunableTuple, TunableRange, TunableListfrom tunable_multiplier import TunableMultiplierfrom venues.venue_service import ZoneDirectorRequestTypeimport enumimport servicesimport sims4logger = sims4.log.Logger('Careers', default_owner='tingyul')
class MedalPayout(TunableTuple):

    def __init__(self, *args, **kwargs):
        super().__init__(work_performance=TunableMultiplier.TunableFactory(description='\n                Multiplier on the base full day work performance (tunable at\n                CareerLevel -> Performance Metrics -> Base Performance).\n                '), money=TunableMultiplier.TunableFactory(description='\n                Multiplier on full day pay, determined by hourly wage (tunable\n                at Career Level -> Simoleons Per Hour), multiplied by work day\n                length (tunable at Career Level -> Work Scheduler), modified by\n                any additional multipliers (e.g. tuning on Career Level ->\n                Simolean Trait Bonus, Career Track -> Overmax, etc.).\n                '), text=TunableLocalizedStringFactory(description='\n                Text shown at end of event notification/dialog if the Sim\n                finishes at this medal.\n                \n                0 param - Sim in the career\n                '), additional_loots=TunableList(description='\n                Any additional loot needed on this medal payout. Currently, this\n                is used to award additional drama nodes/dialogs on this level.\n                ', tunable=LootActions.TunableReference(description='\n                    The loot action applied.\n                    ', pack_safe=True)), **kwargs)

class CareerEventState(enum.Int, export=False):
    CREATED = 0
    REQUESTED = 1
    RUNNING = 2
    STOPPED = 3

class CareerEvent(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.CAREER_EVENT)):
    INSTANCE_TUNABLES = {'required_zone': RequiredCareerEventZoneTunableVariant(description='\n            The required zone for this career event (e.g. the hospital lot for\n            a doctor career event). The Sim involved in this event will\n            automatically travel to this zone at the beginning of the work\n            shift. The Sim will in general be prohibited from leaving this zone\n            without work -- the lone exception is the Sim is allowed to travel\n            for a career sub-event (e.g. a detective Sim running a career event\n            requiring the police station lot is allowed to initiate the sub-\n            event of investigating the crime scene at a commercial lot).\n            '), 'zone_director': OptionalTunable(description='\n            An optional zone director to apply to the zone the career event\n            takes place.\n            ', tunable=CareerEventZoneDirector.TunableReference()), 'scorable_situation': OptionalTunable(description='\n            A situation which the player must complete. Work performance for\n            the Sim will depend on how much the Sim accomplishes. This should\n            be enabled for main events and disabled for sub events. Example:\n            \n            Detective Career. The career event that starts at the beginning of\n            the work shift, going to the police station, will have a scorable\n            situation. The sub event to go to the crime scene will not, as the\n            career event will not be scored against it.\n            ', tunable=TunableTuple(situation=TunableReference(description='\n                    Situation which the Sim in the career event will be scored by.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), allow_none=True, class_restrictions=('CareerEventSituation',)), medal_payout_tin=MedalPayout(description='\n                    Work performance and money payout if scorable situation\n                    ends with a tin medal.\n                    '), medal_payout_bronze=MedalPayout(description='\n                    Work performance and money payout if scorable situation\n                    ends with a bronze medal.\n                    '), medal_payout_silver=MedalPayout(description='\n                    Work performance and money payout if scorable situation\n                    ends with a silver medal.\n                    '), medal_payout_gold=MedalPayout(description='\n                    Work performance and money payout if scorable situation\n                    ends with a gold medal.\n                    ')), enabled_by_default=True, disabled_value=None, disabled_name='sub_event', enabled_name='main_event'), 'tests': TunableTestSet(description='\n            Tests for if this career event is available to the Sim\n            ParticipantType.Actor.\n            '), 'loot_on_request': LootActions.TunableReference(description='\n            Loot applied when the career event is requested to start. Happens\n            before traveling.\n            \n            Example 1: A detective is at home and goes to work. This loot\n            applies while the detective is still on the home lot, right before\n            the travel to the police station happens.\n            \n            Example 2: A detective at the police station travels to a crime\n            scene. This loot for the crime scene sub event applies while the\n            detective is still at the police station, right before the travel.\n            ', allow_none=True), 'loot_on_start': LootActions.TunableReference(description='\n            Loot applied when the career event starts. Happens after travel.\n            \n            Example 1: A detective is at home and goes to work. This loot \n            applies at the police station, right after traveling.\n            \n            Example 2: A detective at the police station travels to a crime\n            scene. This loot for the crime scene sub event applies at the\n            crime scene lot, right after traveling.\n            ', allow_none=True), 'loots_on_end': TunableList(description='\n            Loots applied when the career event ends.\n            ', tunable=LootActions.TunableReference(description='\n                A loot applied when the career event ends.\n                ', allow_none=True, pack_safe=True)), 'cooldown': TunableRange(description='\n            How many work days before this career event will be offered again.\n            ', tunable_type=int, minimum=0, default=0)}

    def __init__(self, career):
        self._career = career
        self._required_zone_id = None
        self._event_situation_id = 0
        self._state = CareerEventState.CREATED

    @property
    def sim_info(self):
        return self._career.sim_info

    @property
    def career(self):
        return self._career

    def on_career_event_requested(self):
        self._advance_state(CareerEventState.REQUESTED)
        self._required_zone_id = self.required_zone.get_required_zone_id(self.sim_info)
        if self.loot_on_request is not None:
            resolver = SingleSimResolver(self._career.sim_info)
            self.loot_on_request.apply_to_resolver(resolver)

    def on_career_event_start(self):
        self._advance_state(CareerEventState.RUNNING)
        if self.loot_on_start is not None:
            resolver = SingleSimResolver(self._career.sim_info)
            self.loot_on_start.apply_to_resolver(resolver)

    def on_career_event_stop(self):
        self._advance_state(CareerEventState.STOPPED)
        resolver = SingleSimResolver(self._career.sim_info)
        for loot in self.loots_on_end:
            if loot is not None:
                loot.apply_to_resolver(resolver)
        curr_zone = services.venue_service().get_zone_director()
        if curr_zone and self.zone_director and self.zone_director.guid64 == curr_zone.guid64:
            curr_zone.on_career_event_stop()

    def request_zone_director(self):
        if self.zone_director is not None:
            zone_director = self.zone_director(career_event=self)
            venue_service = services.venue_service()
            if venue_service.has_zone_director:
                venue_service.change_zone_director(zone_director, True)
            else:
                preserve_state = self._state >= CareerEventState.RUNNING
                venue_service.request_zone_director(zone_director, ZoneDirectorRequestType.CAREER_EVENT, preserve_state=preserve_state)

    def get_event_situation_id(self):
        return self._event_situation_id

    def set_event_situation_id(self, event_situation_id):
        self._event_situation_id = event_situation_id

    def get_required_zone_id(self):
        return self._required_zone_id

    def _advance_state(self, state):
        logger.assert_log(state > self._state, 'Going backwards when trying to advance state. Old: {}, New: {}', self._state, state)
        self._state = state

    def start_from_zone_spin_up(self):
        if self._state == CareerEventState.REQUESTED:
            self.on_career_event_start()

    def get_career_event_data_proto(self):
        proto = SimObjectAttributes_pb2.CareerEventData()
        proto.career_event_id = self.guid64
        proto.event_situation_id = self._event_situation_id
        if self._required_zone_id is not None:
            proto.required_zone_id = self._required_zone_id
        proto.state = self._state
        return proto

    def load_from_career_event_data_proto(self, proto):
        self._event_situation_id = proto.event_situation_id
        if has_field(proto, 'required_zone_id'):
            self._required_zone_id = proto.required_zone_id
        self._state = CareerEventState(proto.state)
