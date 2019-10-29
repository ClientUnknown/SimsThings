from interactions.base.picker_interaction import ObjectPickerInteractionfrom interactions.base.picker_strategy import StatePickerEnumerationStrategyfrom interactions.base.super_interaction import SuperInteractionfrom objects.components import typesfrom objects.gardening.gardening_tuning import GardeningTuningfrom sims4.utils import flexmethodfrom singletons import DEFAULTimport event_testing
class GardeningSpliceInteraction(SuperInteraction):

    def _run_interaction_gen(self, timeline):
        result = yield from super()._run_interaction_gen(timeline)
        if result:
            gardening_component = self.target.get_component(types.GARDENING_COMPONENT)
            shoot = gardening_component.create_shoot()
            try:
                if shoot is not None and self.sim.inventory_component.player_try_add_object(shoot):
                    shoot.update_ownership(self.sim.sim_info)
                    shoot = None
                    return True
            finally:
                if shoot is not None:
                    shoot.destroy(source=self, cause='Failed to add shoot to player inventory.')
        return False

class GardeningGraftPickerInteraction(ObjectPickerInteraction):

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        gardening_component = target.get_component(types.GARDENING_COMPONENT)
        for shoot in context.sim.inventory_component:
            if gardening_component.can_splice_with(shoot):
                yield shoot

    def __init__(self, *args, **kwargs):
        choice_enumeration_strategy = StatePickerEnumerationStrategy()
        super().__init__(*args, choice_enumeration_strategy=choice_enumeration_strategy, **kwargs)

class GardeningGraftInteraction(SuperInteraction):

    @flexmethod
    def test(cls, inst, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst is not None and inst.carry_target is None:
            return event_testing.results.TestResult(False, 'Carry target of grafting shoot is None.')
        return super(__class__, inst_or_cls).test(context=context, **kwargs)

    def _run_interaction_gen(self, timeline):
        result = yield from super()._run_interaction_gen(timeline)
        if result:
            shoot = self.carry_target
            gardening_component = self.target.get_component(types.GARDENING_COMPONENT)
            gardening_component.add_fruit(shoot)
            self.target.set_state(GardeningTuning.SPLICED_STATE_VALUE.state, GardeningTuning.SPLICED_STATE_VALUE)
            shoot.transient = True
        return False
