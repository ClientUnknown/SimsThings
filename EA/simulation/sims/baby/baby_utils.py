from build_buy import find_objects_in_household_inventory, remove_object_from_household_inventory, object_exists_in_household_inventoryfrom objects import HiddenReasonFlagfrom objects.object_enums import ResetReasonfrom objects.system import create_objectfrom sims.baby.baby_tuning import BabyTuningimport servicesimport sims4.loglogger = sims4.log.Logger('Baby')
def assign_bassinet_for_baby(sim_info):
    object_manager = services.object_manager()
    for bassinet in object_manager.get_objects_of_type_gen(*BabyTuning.BABY_BASSINET_DEFINITION_MAP.values()):
        if not bassinet.transient:
            set_baby_sim_info_with_switch_id(bassinet, sim_info)
            bassinet.destroy(source=sim_info, cause='Assigned bassinet for baby.')
            return True
    return False

def assign_to_bassinet(sim_info):
    if object_exists_in_household_inventory(sim_info.id, sim_info.household_id):
        return
    bassinet = services.object_manager().get(sim_info.sim_id)
    if bassinet is None:
        if assign_bassinet_for_baby(sim_info):
            return
        create_and_place_baby(sim_info)

def create_and_place_baby(sim_info, position=None, routing_surface=None, **kwargs):
    bassinet = create_object(BabyTuning.get_default_definition(sim_info), obj_id=sim_info.sim_id)
    bassinet.set_sim_info(sim_info, **kwargs)
    bassinet.place_in_good_location(position=position, routing_surface=routing_surface)
    sim_info.suppress_aging()

def remove_stale_babies(household):
    if household is services.active_household():
        for obj_id in find_objects_in_household_inventory(tuple(definition.id for definition in BabyTuning.BABY_BASSINET_DEFINITION_MAP), household.id):
            sim_info = services.sim_info_manager().get(obj_id)
            if not sim_info.household is not household:
                if not sim_info.is_baby:
                    remove_object_from_household_inventory(obj_id, household)
            remove_object_from_household_inventory(obj_id, household)

def replace_bassinet(sim_info, bassinet=None, safe_destroy=False):
    bassinet = bassinet if bassinet is not None else services.object_manager().get(sim_info.sim_id)
    if bassinet is not None:
        empty_bassinet = create_object(BabyTuning.get_corresponding_definition(bassinet.definition))
        empty_bassinet.location = bassinet.location
        if safe_destroy:
            bassinet.make_transient()
        else:
            bassinet.reset(ResetReason.RESET_EXPECTED, None, 'Replacing Bassinet with child')
            bassinet.destroy(source=sim_info, cause='Replaced bassinet with empty version')
        return empty_bassinet

def run_baby_spawn_behavior(sim_info):
    sim_info.set_zone_on_spawn()
    if sim_info.is_baby:
        assign_to_bassinet(sim_info)
    else:
        replace_bassinet(sim_info)
    return True

def set_baby_sim_info_with_switch_id(bassinet, sim_info, **kwargs):
    if bassinet.id != sim_info.sim_id:
        new_bassinet = None
        try:
            bassinet_definition = BabyTuning.get_corresponding_definition(bassinet.definition)
            new_bassinet = create_object(bassinet_definition, obj_id=sim_info.sim_id)
            new_bassinet.set_sim_info(sim_info, **kwargs)
            new_bassinet.location = bassinet.location
        except:
            logger.exception('{} fail to set sim_info {}', bassinet, sim_info)
            if new_bassinet is not None:
                new_bassinet.destroy(source=sim_info, cause='Failed to set sim_info on bassinet')
        finally:
            sim_info.suppress_aging()
            bassinet.hide(HiddenReasonFlag.REPLACEMENT)
        return new_bassinet
