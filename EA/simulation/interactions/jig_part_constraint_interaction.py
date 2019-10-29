from interactions.base.interaction import Interactionfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import Transform, Nowherefrom sims4.tuning.tunable import Tunable, TunableSet, TunableEnumWithFilterfrom sims4.utils import flexmethodfrom tag import Tagimport servicesimport sims4logger = sims4.log.Logger('JigPartConstraintInteraction', default_owner='cjiang')
class JigPartConstraintInteraction(SuperInteraction):

    def __init__(self, *args, jig_object=None, jig_part_index=0, **kwargs):
        super().__init__(*args, **kwargs)
        self._jig_object = jig_object
        self._jig_part_index = jig_part_index

    @flexmethod
    def _constraint_gen(cls, inst, sim, *args, **kwargs):
        yield from super()._constraint_gen(sim, *args, **kwargs)
        if inst is not None and inst._jig_object is not None:
            jig = inst._jig_object
            parts = jig.parts
            part_index = inst._jig_part_index
            if parts is None:
                logger.error("{} doesn't have part tuned", jig)
                yield Nowhere('Exception while trying to get routing slot on the jig part.')
                return
            if part_index >= len(parts):
                logger.error('{} only have {} parts, out of index {}', jig, len(parts), part_index)
                yield Nowhere('Exception while trying to get routing slot on the jig part.')
                return
            part = parts[part_index]
            yield Transform(part.transform, routing_surface=jig.routing_surface)

class SynchMixerInteraction(MixerInteraction):
    INSTANCE_TUNABLES = {'virtual_actor_name': Tunable(description='\n            The name of the virtual actor sims will be put in.\n            ', tunable_type=str, default='x')}

    def get_asm(self, *args, **kwargs):
        asm = super().get_asm(*args, **kwargs)
        asm.remove_virtual_actors_by_name(self.virtual_actor_name)
        for sim in self.get_sims():
            if self.sim is not sim:
                asm.add_virtual_actor(self.virtual_actor_name, sim)
        return asm

    def _get_required_sims(self, *args, **kwargs):
        sims = super()._get_required_sims(*args, **kwargs)
        sims.update(self.get_sims())
        return sims

    def get_sims(self):
        raise NotImplementedError

class SynchInSituationMixerInteraction(SynchMixerInteraction):
    INSTANCE_TUNABLES = {'situation_tags': TunableSet(description='\n            Tags for arbitrary groupings of situation types.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['situation'], default=Tag.INVALID, pack_safe=True))}

    def get_sims(self):
        sim_list = []
        situation_manager = services.get_zone_situation_manager()
        situation_list = situation_manager.get_situations_by_tags(self.situation_tags)
        for situation in situation_list:
            if situation.is_sim_in_situation(self.sim):
                sim_list.extend(situation.all_sims_in_situation_gen())
        return sim_list
