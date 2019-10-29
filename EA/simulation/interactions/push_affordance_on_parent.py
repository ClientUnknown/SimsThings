import randomfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableReferenceimport services
class PushAffordanceOnRandomParent(XevtTriggeredElement):
    FACTORY_TUNABLES = {'affordance_to_push': TunableReference(description='\n            The affordance to push on a random parent of the Actor.\n            ', manager=services.affordance_manager(), class_restrictions='SuperInteraction', pack_safe=True)}

    def _do_behavior(self, *args, **kwargs):
        child_sim = self.interaction.sim
        child_sim_info = child_sim.sim_info
        household = child_sim_info.household
        parents = set()
        for sim_info in household:
            if sim_info is child_sim_info or not sim_info.is_teen_or_younger:
                if not sim_info.is_instanced():
                    pass
                else:
                    parents.add(sim_info)
        for parent_sim_info in child_sim_info.genealogy.get_parent_sim_infos_gen():
            if parent_sim_info.is_instanced():
                parents.add(parent_sim_info)
        if not parents:
            return
        random_parent = random.choice(list(parents)).get_sim_instance()
        context = InteractionContext(random_parent, InteractionContext.SOURCE_SCRIPT, Priority.High)
        random_parent.push_super_affordance(self.affordance_to_push, child_sim, context)
