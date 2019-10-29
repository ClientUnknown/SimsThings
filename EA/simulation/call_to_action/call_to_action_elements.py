from interactions import ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import HasTunableFactory, Tunable, TunableList, TunableReference, TunableEnumEntryimport servicesimport sims4.loglogger = sims4.log.Logger('call_to_action', default_owner='nabaker')SITUATIONSTATE_ENDED_CTA_TOKEN = 'situationstate_end_cta_ids'
class SituationStateCallToActionMixin(HasTunableFactory):
    FACTORY_TUNABLES = {'call_to_actions': TunableList(description='\n            List of call to actions that should be started at the beginning\n            of this state, and last until the state is deactivated (or until\n            a basic extra ends it "early").\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION)))}

    def __init__(self, *args, call_to_actions=[], **kwargs):
        super().__init__(*args, **kwargs)
        self._call_to_actions = call_to_actions
        self._ended_cta_ids = []

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if reader is not None:
            self._ended_cta_ids = list(reader.read_uint64s(SITUATIONSTATE_ENDED_CTA_TOKEN, ()))
        call_to_action_service = services.call_to_action_service()
        for call_to_action_fact in self._call_to_actions:
            if call_to_action_fact.guid64 not in self._ended_cta_ids:
                call_to_action_service.begin(call_to_action_fact, self)

    def on_cta_ended(self, value):
        self._ended_cta_ids.append(value)

    def on_deactivate(self):
        call_to_action_service = services.call_to_action_service()
        for call_to_action_fact in self._call_to_actions:
            call_to_action_service.end(call_to_action_fact)
        super().on_deactivate()

    def save_state(self, writer):
        super().save_state(writer)
        if self._ended_cta_ids is not None:
            writer.write_uint64s(SITUATIONSTATE_ENDED_CTA_TOKEN, self._ended_cta_ids)
OPENSTREETDIRECTOR_ENDED_CTA_TOKEN = 'openstreetdirector_ended_cta_ids'
class OpenStreetDirectorCallToActionMixin:
    INSTANCE_TUNABLES = {'_call_to_actions': TunableList(description='\n            List of call to actions that should be started at the beginning\n            of this Open Street Director, and last until it ends (or until\n            a basic extra ends it "early").\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ended_cta_ids = []

    def on_startup(self):
        super().on_startup()
        call_to_action_service = services.call_to_action_service()
        for call_to_action_fact in self._call_to_actions:
            if call_to_action_fact.guid64 not in self._ended_cta_ids:
                call_to_action_service.begin(call_to_action_fact, self)

    def _clean_up(self):
        call_to_action_service = services.call_to_action_service()
        for call_to_action_fact in self._call_to_actions:
            call_to_action_service.end(call_to_action_fact)
        super()._clean_up()

    def on_cta_ended(self, value):
        self._ended_cta_ids.append(value)

    def _load_custom_open_street_director(self, street_director_proto, reader):
        super()._load_custom_open_street_director(street_director_proto, reader)
        if reader is not None:
            self._ended_cta_ids = list(reader.read_uint64s(OPENSTREETDIRECTOR_ENDED_CTA_TOKEN, ()))

    def _save_custom_open_street_director(self, street_director_proto, writer):
        super()._save_custom_open_street_director(street_director_proto, writer)
        if self._ended_cta_ids is not None:
            writer.write_uint64s(OPENSTREETDIRECTOR_ENDED_CTA_TOKEN, self._ended_cta_ids)

class TurnOffCallToAction(XevtTriggeredElement):
    FACTORY_TUNABLES = {'_call_to_action': TunableReference(description='\n            Call to action that should be turned off.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION)), '_permanent': Tunable(description='\n            Whether the tuned call to action should be permanently turned off,\n            or only turned off for the remainder of the owning incident.\n            ', tunable_type=bool, default=False), '_participant': TunableEnumEntry(description='\n            The participant of this interaction that must be selectable to turn\n            off the call to action.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

    def _do_behavior(self):
        participant = self.interaction.get_participant(self._participant)
        if participant is not None and participant.sim_info.is_selectable:
            services.call_to_action_service().abort(self._call_to_action, self._permanent)
