from event_testing.resolver import SingleObjectResolverfrom interactions.interaction_finisher import FinishingTypefrom objects.components.object_relationship_component import ObjectRelationshipComponentfrom objects.object_creation import ObjectCreationfrom objects.placement.placement_helper import _PlacementStrategyLocationfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, Tunable, TunableEnumEntry, OptionalTunablefrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonMultiInteractionCompletedSituationStatefrom situations.situation_types import SituationCreationUIOptionimport servicesimport sims4import tagTARGET_OBJECT_TOKEN = 'target_object'CREATED_OBJECT_TOKEN = 'created_object'logger = sims4.log.Logger('CreateAndUseObjectSituation', default_owner='rrodgers')
class _CreateAndUseObjectSituationInitialState(CommonMultiInteractionCompletedSituationState):

    def _on_interactions_completed(self):
        self._change_state(self.owner.final_state())

    def timer_expired(self):
        self.owner._self_destruct()

class _CreateAndUseObjectSituationFinalState(CommonMultiInteractionCompletedSituationState):

    def _on_interactions_completed(self):
        self.owner._self_destruct()

    def timer_expired(self):
        self.owner._self_destruct()

class CreateAndUseObjectSituation(SituationComplexCommon):

    class _ObjectCreationTuning(ObjectCreation):
        pass

    INSTANCE_TUNABLES = {'situation_sims': TunableList(description='\n            The jobs and roles of situation sims in this situation.\n            ', tunable=TunableSituationJobAndRoleState()), 'associated_interaction_tag': OptionalTunable(description='\n            If tuned, this interaction will cancel all interactions with the\n            tuned tag on its situation sims when it ends. \n            ', tunable=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID)), 'initial_state': _CreateAndUseObjectSituationInitialState.TunableFactory(description='\n            The initial state of the CreateAndUseObjectSituation. Moves on to the next\n            state after a set of interactions are completed or will end the situation\n            if the timer expires.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'final_state': _CreateAndUseObjectSituationFinalState.TunableFactory(description='\n            The second and final state of the CreateAndUseObjectSituation. Will end the\n            situation if all tuned interactions are completed or if the timer expires.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'object_creation': _ObjectCreationTuning.TunableFactory(description="\n            An object to create for the duration of this situation. To place\n            this object relative to the target object of the situation, tune\n            the 'initial_location' of the placement to be from the Object \n            participant. \n            "), 'grant_relationship_with_target_object': Tunable(description='\n            If tuned, the target object of this situation will be given an\n            object relationship with each situation sim. BEWARE: Do not use this\n            option if the target object has a pre-existing relationship with any\n            of the situation sims. This scenario requires additional support.\n            ', tunable_type=bool, default=True), 'grant_relationship_with_created_object': Tunable(description='\n            If tuned, the created object of this situation will be given an\n            object relationship with each situation sim.\n            ', tunable_type=bool, default=True)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is None:
            target_object_id = self._seed.extra_kwargs.get('default_target_id', None)
            self._created_object = None
        else:
            target_object_id = reader.read_uint64(TARGET_OBJECT_TOKEN, None)
            created_object_id = self._load_object(reader, CREATED_OBJECT_TOKEN, claim=True)
            self._created_object = services.object_manager().get(created_object_id)
        if target_object_id:
            self._target_object = services.object_manager().get(target_object_id)
        else:
            self._target_object = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _CreateAndUseObjectSituationInitialState, factory=cls.initial_state), SituationStateData(2, _CreateAndUseObjectSituationFinalState, factory=cls.final_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(situation_sim.job, situation_sim.role_state) for situation_sim in cls.situation_sims]

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        if self._target_object is None:
            self._self_destruct()
        resolver = SingleObjectResolver(self._target_object)
        self.object_creation.initialize_helper(resolver)
        self._created_object = self.object_creation.create_object(resolver)
        self._claim_object(self._created_object.id)
        super().start_situation()
        self._change_state(self.initial_state())

    def get_target_object(self):
        return self._target_object

    def get_created_object(self):
        return self._created_object

    def _cancel_tagged_interactions_for_sim(self, sim):
        if self.associated_interaction_tag is None:
            return
        sim_interactions = sim.get_all_running_and_queued_interactions()
        for interaction in sim_interactions:
            if self.associated_interaction_tag in interaction.get_category_tags():
                interaction.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Canceled due to situation {} shutting down'.format(self))

    def on_remove(self):
        super().on_remove()
        if self._created_object:
            if self._created_object.interaction_refs:
                self._created_object.transient = True
            else:
                self._created_object.destroy(source=self, cause='Object destroyed since situation is ending')
            self._created_object = None
        for sim in self._situation_sims:
            self._cancel_tagged_interactions_for_sim(sim)

    def _on_set_sim_job(self, sim, job):
        super()._on_set_sim_job(sim, job)
        if self._target_object and self.grant_relationship_with_target_object and self._target_object:
            ObjectRelationshipComponent.setup_relationship(sim, self._target_object)
        if self._created_object and self.grant_relationship_with_created_object:
            ObjectRelationshipComponent.setup_relationship(sim, self._created_object)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self._cancel_tagged_interactions_for_sim(sim)
        if self._created_object and self.grant_relationship_with_created_object:
            self._created_object.objectrelationship_component.remove_relationship(sim.id)
        if self._target_object is not None and self.grant_relationship_with_target_object:
            self._target_object.objectrelationship_component.remove_relationship(sim.id)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._target_object is not None:
            writer.write_uint64(TARGET_OBJECT_TOKEN, self._target_object.id)
        if self._created_object is not None:
            writer.write_uint64(CREATED_OBJECT_TOKEN, self._created_object.id)
lock_instance_tunables(CreateAndUseObjectSituation._ObjectCreationTuning, location=_PlacementStrategyLocation.TunableFactory())lock_instance_tunables(CreateAndUseObjectSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)