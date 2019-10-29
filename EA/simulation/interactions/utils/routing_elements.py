from element_utils import build_critical_sectionfrom interactions import ParticipantTypeObjectfrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import ANYWHEREfrom interactions.utils.routing import get_route_element_for_path, PlanRoutefrom sims4.tuning.tunable import TunableEnumEntry, TunableList, TunableMapping, HasTunableFactory, AutoFactoryInitimport element_utilsimport elementsimport routingimport sims4.loglogger = sims4.log.Logger('Routing', default_owner='rmccord')
class RouteToLocationElement(elements.ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'route_constraints': TunableMapping(description='\n            A list of constraints and the participant they are relative to\n            that the Sim will route to fulfill when this element runs. \n            ', key_name='relative_participant', key_type=TunableEnumEntry(description='\n                The participant tuned here will have this constraint \n                applied to them.\n                ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), value_name='constraints', value_type=TunableList(description='\n                Constraints relative to the relative participant.\n                ', tunable=TunableGeometricConstraintVariant(description='\n                    A constraint that must be fulfilled in order to interact\n                    with this object.\n                    '), minlength=1), minlength=1)}

    def __init__(self, interaction, sequence=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence

    def behavior_element(self, timeline):
        total_constraint = ANYWHERE
        for (relative_participant, constraints) in self.route_constraints.items():
            relative_object = self.interaction.get_participant(relative_participant)
            if relative_object is None:
                pass
            else:
                for constraint in constraints:
                    relative_constraint = constraint.create_constraint(self.interaction.sim, relative_object, objects_to_ignore=[relative_object])
                    total_constraint = total_constraint.intersect(relative_constraint)
                    if not total_constraint.valid:
                        logger.error('Routing Element cannot resolve constraints for {}', self.interaction)
                        return False
        sim = self.interaction.sim
        goals = []
        handles = total_constraint.get_connectivity_handles(sim)
        for handle in handles:
            goals.extend(handle.get_goals())
        if not goals:
            return False
        route = routing.Route(sim.routing_location, goals, routing_context=sim.routing_context)
        plan_primitive = PlanRoute(route, sim, interaction=self.interaction)
        result = yield from element_utils.run_child(timeline, plan_primitive)
        if not result:
            return False
        if not (plan_primitive.path.nodes and plan_primitive.path.nodes.plan_success):
            return False
        route = get_route_element_for_path(sim, plan_primitive.path, interaction=self.interaction)
        result = yield from element_utils.run_child(timeline, build_critical_section(route))
        return result

    def _run(self, timeline):
        child_element = build_critical_section(self.sequence, self.behavior_element)
        return timeline.run_child(child_element)
