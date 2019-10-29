from interactions import ParticipantTypefrom interactions.liability import Liabilityimport servicesimport sims4.logfrom sims4.tuning.tunable import TunableEnumEntry, TunableList, AutoFactoryInit, HasTunableFactory, TunableReferenceimport weakreflogger = sims4.log.Logger('TemporaryStateChangeLiability', default_owner='brgibson')
class TemporaryStateChangeLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'TemporaryStateChangeLiability'

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, target=None, temp_state_values=None):
        states_in_tuning = set()
        for temp_state_value_tuning in temp_state_values:
            if temp_state_value_tuning.state in states_in_tuning:
                logger.error('Multiple temp state values listed for state {} inside source: {}', temp_state_value_tuning.state, source)
            else:
                states_in_tuning.add(temp_state_value_tuning.state)

    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The participant that should get the temporary state values.\n            ', tunable_type=ParticipantType, default=ParticipantType.Invalid, invalid_enums=(ParticipantType.Invalid,)), 'temp_state_values': TunableList(description='\n            The temporary state values that will be added to the target \n            for as long as the liability exists\n            ', tunable=TunableReference(description='\n                A temporary state value on the target\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue')), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = interaction
        self._has_first_run_occurred = False
        self._have_temp_state_values_been_applied = False
        self._target_participant_ref = None
        self._original_state_values = []

    def on_add(self, interaction):
        self._interaction = interaction

    def on_run(self):
        if self._has_first_run_occurred:
            return
        self._has_first_run_occurred = True
        target_participant = self._interaction.get_participant(self.target)
        if target_participant is None:
            logger.error('Could not obtain {} target when running interaction {}', self.target, self._interaction)
            return
        if target_participant.state_component is None:
            logger.error('{} target does not have a state component when running interaction {}', self.target, self._interaction)
            return
        self._target_participant_ref = weakref.ref(target_participant)
        for temp_state_value_tuning in self.temp_state_values:
            self._try_apply_state_value_to_target(temp_state_value_tuning)

    def should_transfer(self, continuation):
        return self._has_first_run_occurred and not self._have_temp_state_values_been_applied

    def release(self):
        if self._have_temp_state_values_been_applied:
            target_participant = self._get_target()
            if target_participant is not None:
                for original_state_value in self._original_state_values:
                    target_participant.set_state(original_state_value.state, original_state_value)
        super().release()

    def _try_apply_state_value_to_target(self, temp_state_value_tuning):
        target_participant = self._get_target()
        if target_participant is None:
            return
        if not target_participant.has_state(temp_state_value_tuning.state):
            logger.error('{} does not have state {} when running interaction {}', self.target, temp_state_value_tuning.state, self._interaction)
            return
        if not target_participant.does_state_reset_on_load(temp_state_value_tuning.state):
            logger.error("reset_on_load_if_time_passes is set to False for {} target's state {} when running interaction {}", self.target, temp_state_value_tuning.state, self._interaction)
            return
        original_state_value = target_participant.get_state(temp_state_value_tuning.state)
        if original_state_value is None:
            logger.error('{} state {} is None when running interaction {}', self.target, temp_state_value_tuning.state, self._interaction)
            return
        self._original_state_values.append(original_state_value)
        target_participant.set_state(temp_state_value_tuning.state, temp_state_value_tuning)
        self._have_temp_state_values_been_applied = True

    def _get_target(self):
        if self._target_participant_ref is not None:
            return self._target_participant_ref()
