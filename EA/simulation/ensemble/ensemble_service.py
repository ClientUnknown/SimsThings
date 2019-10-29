from _collections import defaultdictfrom caches import cachedfrom distributor.rollback import ProtocolBufferRollbackfrom ensemble.ensemble import Ensemblefrom sims4.callback_utils import CallableListfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePackSafeReferencefrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4.resourceslogger = sims4.log.Logger('Ensembles')
class EnsembleService(Service):
    DEFAULT_ENSEMBLE_TYPE = TunablePackSafeReference(description='\n        A reference to the default ensemble type to use when adding traveling\n        Sims to an ensemble together.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE))

    def __init__(self):
        self._ensembles = defaultdict(list)
        self._ensemble_service_data = None

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_ENSEMBLE_SERVICE

    def create_ensemble(self, new_ensemble_type, potential_sims):
        sims = [sim for sim in potential_sims if new_ensemble_type.can_add_sim_to_ensemble(sim)]
        if len(sims) <= 1:
            return
        ensemble_sims = list(sims)
        if new_ensemble_type.visible:
            new_ensemble_priority = Ensemble.get_ensemble_priority(new_ensemble_type)
            for sim in tuple(ensemble_sims):
                visible_ensemble = self.get_visible_ensemble_for_sim(sim)
                if visible_ensemble is None:
                    pass
                else:
                    visible_ensemble_type = type(visible_ensemble)
                    if visible_ensemble_type is new_ensemble_type:
                        pass
                    else:
                        priority = Ensemble.get_ensemble_priority(visible_ensemble_type)
                        if priority < new_ensemble_priority:
                            self.remove_sim_from_ensemble(visible_ensemble_type, sim)
                        else:
                            ensemble_sims.remove(sim)
        if len(ensemble_sims) <= 1:
            return
        chosen_sims = ensemble_sims
        if new_ensemble_type.max_limit is not None and len(ensemble_sims) > new_ensemble_type.max_limit:
            selectable_sims = [sim for sim in ensemble_sims if sim.is_selectable]
            sims_needed = new_ensemble_type.max_limit - len(selectable_sims)
            if sims_needed < 0:
                chosen_sims = selectable_sims[:new_ensemble_type.max_limit]
            else:
                chosen_sims = selectable_sims
                other_sims = [sim for sim in ensemble_sims if sims not in chosen_sims]
                chosen_sims.extend(other_sims[:sims_needed])
        ensembles_to_merge = []
        for ensemble in self._ensembles[new_ensemble_type]:
            if any(ensemble.is_sim_in_ensemble(sim) for sim in chosen_sims):
                ensembles_to_merge.append(ensemble)
        if len(ensembles_to_merge) > 1:
            logger.error("Trying to merge multiple ensembles.  Design says that this shouldn't be happening so something is probably tuned wrong.")
        if ensembles_to_merge:
            final_ensemble = ensembles_to_merge.pop()
            for ensemble in ensembles_to_merge:
                if new_ensemble_type.max_limit is not None and len(final_ensemble) + len(ensemble) > new_ensemble_type.max_limit:
                    logger.error('Trying to merge two ensembles {} and {} that causes the ensemble size to go over the maximum limit.', final_ensemble, ensemble)
                    for sim in ensemble:
                        if sim in chosen_sims:
                            chosen_sims.remove(sim)
                else:
                    ensemble_sims = list(ensemble)
                    ensemble.end_ensemble()
                    self._ensembles[new_ensemble_type].remove(ensemble)
                    for sim in ensemble_sims:
                        final_ensemble.add_sim_to_ensemble(sim)
            for sim in chosen_sims:
                if len(final_ensemble) >= final_ensemble.max_limit:
                    break
                final_ensemble.add_sim_to_ensemble(sim)
        else:
            final_ensemble = new_ensemble_type()
            self._ensembles[new_ensemble_type].append(final_ensemble)
            final_ensemble.start_ensemble()
            for sim in chosen_sims:
                final_ensemble.add_sim_to_ensemble(sim)

    def remove_sim_from_ensemble(self, ensemble_type, sim):
        for ensemble in tuple(self._ensembles[ensemble_type]):
            if ensemble.is_sim_in_ensemble(sim):
                ensemble.remove_sim_from_ensemble(sim)
                if len(ensemble) <= 1:
                    ensemble.end_ensemble()
                    self._ensembles[ensemble_type].remove(ensemble)
                break

    def destroy_sims_ensemble(self, ensemble_type, sim):
        for ensemble in tuple(self._ensembles[ensemble_type]):
            if ensemble.is_sim_in_ensemble(sim):
                ensemble.end_ensemble()
                self._ensembles[ensemble_type].remove(ensemble)
                break

    def get_all_ensembles(self):
        return [ensemble for ensembles in self._ensembles.values() for ensemble in ensembles]

    def get_visible_ensemble_for_sim(self, sim):
        for ensembles in self._ensembles.values():
            for ensemble in ensembles:
                if ensemble.visible and ensemble.is_sim_in_ensemble(sim):
                    return ensemble

    def get_ensemble_for_sim(self, ensemble_type, sim):
        for ensemble in self._ensembles[ensemble_type]:
            if ensemble.is_sim_in_ensemble(sim):
                return ensemble

    def get_all_ensembles_for_sim(self, sim):
        ensembles_to_return = []
        for ensembles in self._ensembles.values():
            for ensemble in ensembles:
                if ensemble.is_sim_in_ensemble(sim):
                    ensembles_to_return.append(ensemble)
        return ensembles_to_return

    @cached
    def get_most_important_ensemble_for_sim(self, sim):
        best_priority = None
        best_ensemble = None
        for (ensemble_type, ensembles) in self._ensembles.items():
            for ensemble in ensembles:
                if ensemble.is_sim_in_ensemble(sim):
                    priority = Ensemble.get_ensemble_priority(ensemble_type)
                    if not best_priority is None:
                        if priority > best_priority:
                            best_priority = priority
                            best_ensemble = ensemble
                            break
                    best_priority = priority
                    best_ensemble = ensemble
                    break
        return best_ensemble

    def get_ensemble_multiplier(self, sim, target):
        ensemble = self.get_most_important_ensemble_for_sim(sim)
        if ensemble is None:
            return 1
        if target is None:
            target = sim
        return ensemble.get_ensemble_multiplier(target)

    def create_travel_ensemble_if_neccessary(self, traveled_sim_infos):
        sim_instances = []
        for sim_info in traveled_sim_infos:
            if not sim_info.is_human:
                pass
            else:
                sim = sim_info.get_sim_instance()
                if sim is None:
                    pass
                else:
                    sim_instances.append(sim)
        if not any([sim for sim in sim_instances if self.get_all_ensembles_for_sim(sim)]):
            self.create_ensemble(EnsembleService.DEFAULT_ENSEMBLE_TYPE, sim_instances)

    def load(self, zone_data=None):
        if zone_data.gameplay_zone_data.HasField('ensemble_service_data'):
            self._ensemble_service_data = zone_data.gameplay_zone_data.ensemble_service_data

    def _load_persisted_data(self):
        if self._ensemble_service_data is None:
            return
        ensemble_datas = self._ensemble_service_data.ensemble_datas
        self._ensemble_service_data = None
        if services.current_zone().time_has_passed_in_world_since_zone_save():
            return
        instance_manager = services.get_instance_manager(Types.ENSEMBLE)
        object_manager = services.object_manager()
        for ensemble_data in ensemble_datas:
            ensemble_type = instance_manager.get(ensemble_data.ensemble_type_id)
            if ensemble_type is None:
                pass
            else:
                sims = set()
                for sim_id in ensemble_data.sim_ids:
                    sim = object_manager.get(sim_id)
                    if sim is not None:
                        sims.add(sim)
                if not sims:
                    pass
                else:
                    self.create_ensemble(ensemble_type, sims)

    def save(self, object_list=None, zone_data=None, open_street_data=None, store_travel_group_placed_objects=False, save_slot_data=None):
        if zone_data is None:
            return
        for ensemble in self.get_all_ensembles():
            with ProtocolBufferRollback(zone_data.gameplay_zone_data.ensemble_service_data.ensemble_datas) as ensemble_data:
                ensemble_data.ensemble_type_id = ensemble.guid64
                ensemble_data.sim_ids.extend(sim.id for sim in ensemble)

    def on_all_sims_spawned_during_zone_spin_up(self):
        self._load_persisted_data()
        for sim in services.sim_info_manager().instanced_sims_gen():
            sim.create_auto_ensembles()

    def get_ensemble_sims_for_rally(self, sim):
        best_priority = None
        best_ensemble = None
        for (ensemble_type, ensembles) in self._ensembles.items():
            for ensemble in ensembles:
                if not ensemble.rally:
                    pass
                elif not ensemble.is_sim_in_ensemble(sim):
                    pass
                else:
                    priority = Ensemble.get_ensemble_priority(ensemble_type)
                    if not best_priority is None:
                        if priority > best_priority:
                            best_priority = priority
                            best_ensemble = ensemble
                            break
                    best_priority = priority
                    best_ensemble = ensemble
                    break
        if best_ensemble:
            return set(best_ensemble)
        return set()
