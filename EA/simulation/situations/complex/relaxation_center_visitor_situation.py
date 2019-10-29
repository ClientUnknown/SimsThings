import randomfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims4.tuning.tunable import OptionalTunable, TunableSimMinute, Tunable, TunableTuplefrom situations.ambient.anchored_open_streets_autonomy_situation import AnchoredAutonomySituationStateMixin, GroupAnchoredAutonomySituationCommonfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, CommonSituationState, SituationStateDatafrom situations.situation_job import SituationJobimport filtersimport servicesimport sims4.tuninglogger = sims4.log.Logger('Relaxation Center Situations', default_owner='rfleig')DO_STUFF_TIMEOUT = 'do_stuff'ARRIVING_TIMEOUT = 'arriving'DEPARTING_TIMEOUT = 'departing'CUSTOM_SAVE_OUTFIT = 'wearing_situation_outfit'
class _ArrivingState(CommonInteractionCompletedSituationState, AnchoredAutonomySituationStateMixin):
    FACTORY_TUNABLES = {'arrival_timeout': OptionalTunable(description="\n            Optional tunable for how long to wait before progressing to the\n            Do Stuff state. This is basically here for if you don't care\n            if they do the arriving behavior all of the time.\n            ", tunable=TunableSimMinute(description='\n                The length of time before moving onto the Do Stuff state.\n                ', default=60))}

    def __init__(self, arrival_timeout, **kwargs):
        super().__init__(**kwargs)
        self._arrival_timeout = arrival_timeout
        self._arrived_sims = []

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._arrival_timeout is not None:
            self._create_or_load_alarm(ARRIVING_TIMEOUT, self._arrival_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._arrived_sims.clear()
        self.owner._change_state(self.owner.do_stuff_situation_state())

    def _additional_tests(self, sim_info, event, resolver):
        if not self.owner.sim_of_interest(sim_info):
            return False
        if not resolver.interaction.is_finishing_naturally:
            return False
        else:
            self._arrived_sims.append(sim_info)
            if not self.owner.all_sims_of_interest_arrived(self._arrived_sims):
                return False
        return True

    def timer_expired(self):
        self.owner._change_state(self.owner.do_stuff_situation_state())

    def should_anchor_new_arrival(self):
        return True

class _DoStuffState(CommonSituationState, AnchoredAutonomySituationStateMixin):
    FACTORY_TUNABLES = {'do_stuff_timeout': OptionalTunable(description='\n            Optional tunable for when to end the Do Stuff state. \n\n            If this is enabled then the Do Stuff state will eventually time\n            out and either end the situation or have the Sim go into the \n            Change Clothes state.\n            \n            If this is disabled the situation will just stay in the Do Stuff\n            state forever.\n            ', tunable=TunableTuple(description='\n            \n                ', min_time=TunableSimMinute(description='\n                    The length of time to wait before advancing to the\n                    Change Clothes state.\n                    ', default=60), max_time=TunableSimMinute(description='\n                    The maximum time a visitor will spend on the relaxation\n                    venue as a guest.\n                    ', default=60))), 'change_outfit_before_leave': Tunable(description='\n            If True then the Sim will advance to the Change Clothes state.\n            If False then the Sim will just end the situation at the end of the\n            Do Stuff state.\n            ', tunable_type=bool, default=True)}

    def __init__(self, do_stuff_timeout, change_outfit_before_leave, **kwargs):
        super().__init__(**kwargs)
        self._do_stuff_timeout = do_stuff_timeout
        self._change_outfit_before_leave = change_outfit_before_leave

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._do_stuff_timeout is not None:
            duration = random.uniform(self._do_stuff_timeout.min_time, self._do_stuff_timeout.max_time)
            self._create_or_load_alarm(DO_STUFF_TIMEOUT, duration, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        if self._change_outfit_before_leave:
            self.owner._change_state(self.owner.change_clothes_leave_situation_state())
        else:
            self.owner._self_destruct()

class _ChangeClothesLeave(CommonInteractionCompletedSituationState, AnchoredAutonomySituationStateMixin):
    FACTORY_TUNABLES = {'departing_timeout': OptionalTunable(description='\n            Optional tunable for how long to wait before progressing past the\n            change clothes state. This is basically here so that if the Sim \n            takes a long time to change clothes they will just give up and\n            leave the lot.\n            ', tunable=TunableSimMinute(description='\n                The length of time before moving onto the Do Stuff state.\n                ', default=60))}

    def __init__(self, departing_timeout, **kwargs):
        super().__init__(**kwargs)
        self._departing_timeout = departing_timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._departing_timeout is not None:
            self._create_or_load_alarm(DEPARTING_TIMEOUT, self._departing_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def _additional_tests(self, sim_info, event, resolver):
        if not self.owner.sim_of_interest(sim_info):
            return False
        elif not resolver.interaction.is_finishing_naturally:
            return False
        return True

    def timer_expired(self):
        self.owner._self_destruct()

class RelaxationCenterVisitorSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_default_job': SituationJob.TunableReference(description='\n            The default job that a visitor will be in during the situation.\n            '), 'arriving_situation_state': _ArrivingState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Massage \n            Therapist.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_arriving_situation_state'), 'do_stuff_situation_state': _DoStuffState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            everything except for arrive and leave.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_do_stuff_situation_state'), 'change_clothes_leave_situation_state': _ChangeClothesLeave.TunableFactory(description='\n            The state that is used to get the Sim to change clothes before \n            ending the situation and ending up in the leave lot situation.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_change_clothes_leave_situation_state')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visitor = None
        reader = self._seed.custom_init_params_reader
        self.apply_situation_outfit = False
        if reader is not None:
            self.apply_situation_outfit = reader.read_bool(CUSTOM_SAVE_OUTFIT, False)

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _ArrivingState, factory=cls.arriving_situation_state), SituationStateData(2, _DoStuffState, factory=cls.do_stuff_situation_state), SituationStateData(3, _ChangeClothesLeave, factory=cls.change_clothes_leave_situation_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.arriving_situation_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        return cls.situation_default_job

    def start_situation(self):
        super().start_situation()
        self._change_state(self.arriving_situation_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._visitor = sim
        if self.apply_situation_outfit:
            self.set_job_uniform(sim, job_type, (OutfitCategory.SITUATION, 0))
            sim.sim_info.try_set_current_outfit((OutfitCategory.SITUATION, 0))

    def _save_custom_situation(self, writer):
        if self._visitor is not None:
            writer.write_bool(CUSTOM_SAVE_OUTFIT, self._visitor.get_current_outfit()[0] == OutfitCategory.SITUATION)

    def sim_of_interest(self, sim_info):
        if self._visitor is not None and self._visitor.sim_info is sim_info:
            return True
        return False

    def all_sims_of_interest_arrived(self, arrived_sims):
        return True

class AnchoredRelaxationCenterVisitorSituation(GroupAnchoredAutonomySituationCommon):
    INSTANCE_TUNABLES = {'situation_default_job': SituationJob.TunableReference(description='\n            The default job that a visitor will be in during the situation.\n            '), 'arriving_situation_state': _ArrivingState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Massage \n            Therapist.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_arriving_situation_state'), 'do_stuff_situation_state': _DoStuffState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            everything except for arrive and leave.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_do_stuff_situation_state'), 'change_clothes_leave_situation_state': _ChangeClothesLeave.TunableFactory(description='\n            The state that is used to get the Sim to change clothes before \n            ending the situation and ending up in the leave lot situation.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_change_clothes_leave_situation_state')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _ArrivingState, factory=cls.arriving_situation_state), SituationStateData(2, _DoStuffState, factory=cls.do_stuff_situation_state), SituationStateData(3, _ChangeClothesLeave, factory=cls.change_clothes_leave_situation_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.arriving_situation_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        object_manager = services.object_manager()
        for _ in object_manager.get_objects_with_tag_gen(cls.object_anchor_tag):
            return True
        return False

    @classmethod
    def default_job(cls):
        return cls.situation_default_job

    def start_situation(self):
        super().start_situation()
        self._anchor_position = self.get_new_anchor_position(self.object_anchor_tag)
        self._change_state(self.arriving_situation_state())

    def sim_of_interest(self, sim_info):
        for sim in self._situation_sims:
            if sim.sim_info is sim_info:
                return True
        return False

    def all_sims_of_interest_arrived(self, arrived_sims):
        for sim in self._situation_sims:
            if sim.sim_info not in arrived_sims:
                return False
        return True
