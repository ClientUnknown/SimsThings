from caches import cachedfrom event_testing.resolver import DoubleObjectResolverfrom objects.object_creation import TunableObjectCreationDataVariantfrom tunable_utils.tested_list import TunableTestedListfrom vfx import PlayEffectimport servicesimport sims4.tuning.tunableimport tagimport traits.traits
class Ghost:
    URNSTONE_TAG_FILTER_PREFIXES = ('func',)
    URNSTONE_TAG = sims4.tuning.tunable.TunableEnumWithFilter(description='\n        The tag associated with urns and tombstone. They all need this tag if\n        they want to be considered for an NPC ghost to spawn.\n        ', tunable_type=tag.Tag, filter_prefixes=URNSTONE_TAG_FILTER_PREFIXES, default=tag.Tag.INVALID)
    URNSTONE_DEFINITION = TunableObjectCreationDataVariant(description='\n        When Sims die, create this urnstone. This applies to all types of death,\n        i.e. the Death interactions as well as the auto-generation of urnstones\n        for Sims that have died off-lot.\n        ')
    URNSTONE_RELEASE_VFX = TunableTestedList(description="\n        When a Ghost's spirit is released from the Urnstone, either via a player\n        interaction or by the Culling commodity expiring, play this VFX.\n        ", tunable_type=PlayEffect.TunableFactory())
    WALKBY_COOLDOWN = sims4.tuning.tunable.TunableSimMinute(description='\n        The amount of time the ghost must wait before performing another\n        walkby. The cooldown time starts when the ghost is uninstantiated.\n        ', default=48)

    @classmethod
    def _check_urnstone_validity(cls, urnstone, require_uninstantiated=True):
        stored_sim_info = urnstone.get_stored_sim_info()
        if stored_sim_info is None:
            return False
        if not require_uninstantiated:
            return True
        if stored_sim_info.is_instanced():
            return False
        elif cls._is_ghost_on_ambient_cooldown(stored_sim_info):
            return False
        return True

    @classmethod
    def _is_ghost_on_ambient_cooldown(cls, sim_info):
        saved_time = sim_info.time_sim_was_saved
        if saved_time is None:
            return True
        time_delta = services.time_service().sim_now - saved_time
        return time_delta.in_minutes() <= cls.WALKBY_COOLDOWN

    @classmethod
    def get_urnstones_gen(cls):
        yield from services.object_manager().get_objects_with_tag_gen(cls.URNSTONE_TAG)

    @classmethod
    @cached
    def get_valid_urnstones(cls, require_uninstantiated=True):
        return list(u for u in cls.get_urnstones_gen() if cls._check_urnstone_validity(u, require_uninstantiated=require_uninstantiated))

    @classmethod
    def get_urnstone_for_sim_id(cls, sim_id):
        for urnstone in cls.get_urnstones_gen():
            if urnstone.get_stored_sim_id() == sim_id:
                return urnstone

    @classmethod
    def remove_ghost_from_sim(cls, sim_info):
        sim_info.trait_tracker.remove_traits_of_type(traits.traits.TraitType.GHOST)
        sim_info.death_tracker.clear_death_type()
        sim = sim_info.get_sim_instance()
        if sim is not None:
            sim.routing_context.ghost_route = False
        sim_info.update_age_callbacks()

    @classmethod
    def make_ghost_if_needed(cls, sim_info):
        trait = sim_info.death_tracker.get_ghost_trait()
        if trait is not None:
            sim_info.add_trait(trait)

    @classmethod
    def enable_ghost_routing(cls, sim_info):
        sim = sim_info.get_sim_instance()
        if sim is not None:
            sim.routing_context.ghost_route = True

    @classmethod
    def play_release_ghost_vfx(cls, sim_info):
        urnstone = cls.get_urnstone_for_sim_id(sim_info.sim_id)
        if urnstone is None:
            return
        resolver = DoubleObjectResolver(sim_info, urnstone)
        for vfx in cls.URNSTONE_RELEASE_VFX(resolver=resolver):
            vfx = vfx(urnstone)
            vfx.start_one_shot()
            break
