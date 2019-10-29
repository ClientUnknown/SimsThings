from sims4.tuning.tunable import TunableReferenceimport servicesimport sims4.resources
class LineUtils:
    ROUTE_TO_WAITING_IN_LINE = TunableReference(description='\n        A reference to the interaction used for getting Sims to route closer\n        to the target before running the wait in line interaction.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
