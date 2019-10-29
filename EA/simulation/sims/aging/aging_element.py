from clock import interval_in_real_secondsfrom element_utils import build_element, build_critical_section_with_finallyfrom elements import SleepElementfrom interactions import ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.work_lock_liability import WorkLockLiabilityfrom objects import VisibilityState, ALL_HIDDEN_REASONSfrom objects.system import create_objectfrom sims.aging.aging_tuning import AgingTuningfrom sims.baby.baby_tuning import BabyTuningfrom sims.sim_spawner import SimSpawnerfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableEnumEntry, TunableVariantfrom singletons import DEFAULTimport servicesimport sims4.loglogger = sims4.log.Logger('Aging')
class AgeUp(HasTunableFactory):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._previous_skills = None
        self._previous_trait_guid = None
        self._life_skill_trait_ids = None

    def __call__(self):
        self._previous_skills = {}
        for skill in self._sim_info.all_skills():
            if skill.age_up_skill_transition_data is not None:
                self._previous_skills[skill] = skill.get_user_value()
        if self._sim_info.is_toddler:
            for trait in self._sim_info.trait_tracker.personality_traits:
                self._previous_trait_guid = trait.guid64
                break
        self._life_skill_trait_ids = self._sim_info.advance_age()

    def can_execute(self):
        return True

    def is_baby_age_up(self):
        return self._sim_info.is_baby

    def show_age_up_dialog(self, ran_age_change=False):
        if self._sim_info.is_npc:
            return
        if not ran_age_change:
            return
        age_transition_data = self._sim_info.get_age_transition_data(self._sim_info.age)
        age_transition_data.show_age_transition_dialog(self._sim_info, previous_skills=self._previous_skills, previous_trait_guid=self._previous_trait_guid, from_age_up=True, life_skill_trait_ids=self._life_skill_trait_ids)

class AgeUpBaby(AgeUp):

    def __init__(self, *args, callback, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback

    def __call__(self, *args, **kwargs):
        self._callback(*args, **kwargs)

class AgeDown(HasTunableFactory):

    def __init__(self, sim_info):
        self._sim_info = sim_info

    def __call__(self):
        self._sim_info.reverse_age()

    def can_execute(self):
        return self._sim_info.can_reverse_age()

    def is_baby_age_up(self):
        return False

    def show_age_up_dialog(self, ran_age_change=False):
        pass

class ChangeAgeElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The Sim to age up or age down.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'action': TunableVariant(description='\n            The age action to perform.\n            ', age_up=AgeUp.TunableFactory(), age_down=AgeDown.TunableFactory(), default='age_up')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ran_age_change = False
        self._action = None

    @staticmethod
    def spawn_for_age_up(sim_info, position, spawn_action=None, sim_location=None):
        sim_info.advance_age()
        if spawn_action is None:
            spawn_action = lambda _: None

        def _pre_add(obj):
            obj.opacity = 1
            obj.visibility = VisibilityState(False)

        SimSpawner.spawn_sim(sim_info, position, spawn_action=spawn_action, sim_location=sim_location, pre_add_fn=_pre_add)
        target_sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        return target_sim

    def _get_sim_info(self):
        sim_or_bassinet = self.interaction.get_participant(self.participant)
        if sim_or_bassinet is None:
            return
        return sim_or_bassinet.sim_info

    def _build_baby_age_up_sequence(self, sim_info, sequence, is_external=False):
        bassinet = self.interaction.get_participant(self.participant)
        new_bassinet = middle_bassinet = None

        def _do_spawn_gen(timeline):
            nonlocal middle_bassinet, new_bassinet
            self.interaction.add_exit_function(_on_interaction_exit)
            self.interaction.remove_liability('ReservationLiability')
            if is_external:
                middle_bassinet = self.interaction.target
                target_sim = bassinet
            else:
                for handler in bassinet.get_reservation_handlers():
                    if handler.sim is self.interaction.sim:
                        bassinet.remove_reservation_handler(handler)
                middle_bassinet = bassinet.replace_for_age_up(interaction=self.interaction)
                yield timeline.run_child(SleepElement(interval_in_real_seconds(1)))
                target_sim = self.spawn_for_age_up(sim_info, bassinet.position, sim_location=bassinet.location)
                self.interaction.context.create_target_override = target_sim
                yield from target_sim._startup_sim_gen(timeline)
                master_controller = services.get_master_controller()
                master_controller.add_global_lock(target_sim)
                self.interaction.add_exit_function(lambda *_, **__: master_controller.remove_global_lock(target_sim))
                self.interaction.add_liability(WorkLockLiability.LIABILITY_TOKEN, WorkLockLiability(sim=target_sim))

            def _add_bassinet(obj):
                obj.location = middle_bassinet.location
                obj.opacity = 0

            new_bassinet = create_object(BabyTuning.get_corresponding_definition(middle_bassinet.definition), init=_add_bassinet)

            def _on_age_up_event(*_, **__):
                new_bassinet.opacity = 1
                middle_bassinet.remove_from_client()

            self._action = AgeUpBaby(sim_info, callback=_on_age_up_event)

        def _on_interaction_exit():
            if middle_bassinet is None:
                return
            middle_bassinet.make_transient()

        return build_element((_do_spawn_gen, sequence))

    def _build_outer_elements(self, sequence):
        sim_info = self._get_sim_info()
        if sim_info is None:
            return
        self._action = self.action(sim_info)
        if not self._action.can_execute():
            return
        is_baby_age_up = self.interaction.interaction_parameters.get('is_baby_age_up', False)
        if is_baby_age_up or self._action.is_baby_age_up():
            sequence = self._build_baby_age_up_sequence(sim_info, sequence, is_external=is_baby_age_up)
        lock_handle = None

        def _lock_save_for_aging(_):
            nonlocal lock_handle
            if is_baby_age_up or not sim_info.is_npc:

                class _AgeUpSaveLockHandle:

                    def get_lock_save_reason(self):
                        return AgingTuning.AGING_SAVE_LOCK_TOOLTIP(sim_info)

                lock_handle = _AgeUpSaveLockHandle()
                services.get_persistence_service().lock_save(lock_handle)

        def _unlock_save_for_aging(_):
            if lock_handle is not None:
                services.get_persistence_service().unlock_save(lock_handle)

        sequence = build_critical_section_with_finally(_lock_save_for_aging, sequence, _unlock_save_for_aging)
        return sequence

    def _do_behavior(self):
        sim_info = self._get_sim_info()
        if sim_info is None:
            return False
        if not self.ran_age_change:
            self._action()
            self.ran_age_change = True
        self._action.show_age_up_dialog(ran_age_change=self.ran_age_change)
