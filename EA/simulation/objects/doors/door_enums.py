import enum
class VenueFrontdoorRequirement(enum.Int):
    NEVER = 0
    ALWAYS = 1
    OWNED_OR_RENTED = 2
