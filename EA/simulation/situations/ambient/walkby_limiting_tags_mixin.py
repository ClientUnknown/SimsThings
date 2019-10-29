from tag import Tagimport servicesimport sims4.tuning.tunable
class WalkbyLimitingTagsMixin:
    INSTANCE_TUNABLES = {'can_start_walkby_limiting_tags': sims4.tuning.tunable.TunableSet(description="\n            Don't start a situation of this type if another situation is\n            already running that has any of these tags in its tags field.\n            \n            For instance, if you only want one Streaker at a time you would\n            create a new tag SITUATION_STREAKER. Then set that in both this\n            field and in the tags field of situation_streaker.\n            ", tunable=sims4.tuning.tunable.TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=['situation']))}

    @classmethod
    def _can_start_walkby(cls, lot_id:int):
        return not services.get_zone_situation_manager().is_situation_with_tags_running(cls.can_start_walkby_limiting_tags)
