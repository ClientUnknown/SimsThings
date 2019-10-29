import enum
class Priority(enum.Int):
    Low = 1
    High = 2
    Critical = 3

class PriorityExtended(Priority, export=False):
    SubLow = 0

def can_priority_displace(priority_new, priority_existing, allow_clobbering=False):
    if priority_new is None:
        return False
    if allow_clobbering:
        return priority_new >= priority_existing
    return priority_new > priority_existing

def can_displace(interaction_new, interaction_existing, allow_clobbering=False):
    if not can_priority_displace(interaction_new.priority, interaction_existing.priority, allow_clobbering=allow_clobbering):
        return False
    return not interaction_existing.is_cancel_aop
