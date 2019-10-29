import randomfrom event_testing.resolver import SingleObjectResolverfrom interactions.constraints import TunableCircle, Anywherefrom interactions.utils.satisfy_constraint_interaction import SitOrStandSuperInteractionfrom situations.service_npcs.modify_lot_items_tuning import TunableObjectModifyTestSetimport servicesimport sims4.loglogger = sims4.log.Logger('Route Near Object Interaction', default_owner='rfleig')
class RouteNearObjectInteraction(SitOrStandSuperInteraction):
    INSTANCE_TUNABLES = {'object_tests': TunableObjectModifyTestSet(description='\n            Tests to specify what objects to apply actions to.\n            Every test in at least one of the sublists must pass\n            for the action associated with this tuning to be run.\n            '), 'circle_constraint_around_chosen_object': TunableCircle(1.5, description='\n            Circle constraint around the object that is chosen.\n            ')}

    def __init__(self, aop, context, *args, **kwargs):
        constraint = self._build_constraint(context)
        super().__init__(aop, context, *args, constraint_to_satisfy=constraint, **kwargs)

    def _build_constraint(self, context):
        all_objects = list(services.object_manager().values())
        random.shuffle(all_objects)
        for obj in all_objects:
            if not obj.is_sim:
                if not obj.is_on_active_lot():
                    pass
                else:
                    resolver = SingleObjectResolver(obj)
                    if not self.object_tests.run_tests(resolver):
                        pass
                    else:
                        constraint = self.circle_constraint_around_chosen_object.create_constraint(context.sim, obj)
                        if constraint.valid:
                            return constraint
        logger.warn('No objects were found for this interaction to route the Sim near. Interaction = {}', type(self))
        return Anywhere()
