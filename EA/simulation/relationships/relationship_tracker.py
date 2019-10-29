from event_testing.results import TestResultfrom interactions.base.picker_interaction import PickerSuperInteractionfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import Tunablefrom sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom ui.ui_dialog_picker import ObjectPickerRowimport cachesimport servicesimport sims4.loglogger = sims4.log.Logger('Relationship', default_owner='jjacobson')relationship_setup_logger = sims4.log.Logger('DefaultRelSetup', default_owner='manus')
class RelationshipTracker(SimInfoTracker):

    def __init__(self, sim_info):
        super().__init__()
        self._sim_info = sim_info
        self.spouse_sim_id = None

    def __iter__(self):
        return services.relationship_service().get_all_sim_relationships(self._sim_info.sim_id).__iter__()

    def __len__(self):
        return len(services.relationship_service().get_all_sim_relationships(self._sim_info.sim_id))

    def create_relationship(self, target_sim_id:int):
        services.relationship_service().create_relationship(self._sim_info.sim_id, target_sim_id)

    def destroy_relationship(self, target_sim_id:int, notify_client=True):
        services.relationship_service().destroy_relationship(self._sim_info.sim_id, target_sim_id, notify_client=notify_client)

    def destroy_all_relationships(self):
        services.relationship_service().destroy_all_relationships(self._sim_info.sim_id)

    def load(self, relationship_save_data):
        if relationship_save_data:
            for rel_save in relationship_save_data:
                services.relationship_service().load_legacy_data(self._sim_info.sim_id, rel_save)

    def send_relationship_info(self, target_sim_id=None):
        services.relationship_service().send_relationship_info(self._sim_info.sim_id, target_sim_id=target_sim_id)

    def clean_and_send_remaining_relationship_info(self):
        services.relationship_service().clean_and_send_remaining_relationship_info(self._sim_info.sim_id)

    def add_create_relationship_listener(self, callback):
        services.relationship_service().add_create_relationship_listener(self._sim_info.sim_id, callback)

    def remove_create_relationship_listener(self, callback):
        services.relationship_service().remove_create_relationship_listener(self._sim_info.sim_id, callback)

    @caches.cached
    def get_relationship_score(self, target_sim_id:int, track=DEFAULT):
        return services.relationship_service().get_relationship_score(self._sim_info.sim_id, target_sim_id, track=track)

    def add_relationship_score(self, target_sim_id:int, increment, track=DEFAULT, threshold=None):
        services.relationship_service().add_relationship_score(self._sim_info.sim_id, target_sim_id, increment, track=track, threshold=threshold)

    def set_relationship_score(self, target_sim_id:int, value, track=DEFAULT, threshold=None):
        services.relationship_service().set_relationship_score(self._sim_info.sim_id, target_sim_id, value, track=track, threshold=threshold)

    def enable_player_sim_track_decay(self, to_enable=True):
        logger.debug('Enabling ({}) decay for player sim: {}'.format(to_enable, self._sim_info))
        services.relationship_service().enable_player_sim_track_decay(self._sim_info.sim_id, to_enable=to_enable)

    def get_relationship_prevailing_short_term_context_track(self, target_sim_id:int):
        return services.relationship_service().get_relationship_prevailing_short_term_context_track(self._sim_info.sim_id, target_sim_id)

    def get_default_short_term_context_bit(self):
        track = RelationshipGlobalTuning.DEFAULT_SHORT_TERM_CONTEXT_TRACK
        return track.get_bit_at_relationship_value(track.initial_value)

    def get_relationship_track(self, target_sim_id:int, track=DEFAULT, add=False):
        return services.relationship_service().get_relationship_track(self._sim_info.sim_id, target_sim_id, track=track, add=add)

    def relationship_tracks_gen(self, target_sim_id:int):
        yield from services.relationship_service().relationship_tracks_gen(self._sim_info.sim_id, target_sim_id)

    def add_relationship_multipliers(self, handle, relationship_multipliers):
        services.relationship_service().add_relationship_multipliers(self._sim_info.sim_id, handle, relationship_multipliers)

    def remove_relationship_multipliers(self, handle):
        services.relationship_service().remove_relationship_multipliers(self._sim_info.sim_id, handle)

    def on_added_to_social_group(self, target_sim_id:int):
        services.relationship_service().on_added_to_social_group(self._sim_info.sim_id, target_sim_id)

    def on_removed_from_social_group(self, target_sim_id:int):
        services.relationship_service().on_removed_from_social_group(self._sim_info.sim_id, target_sim_id)

    def set_default_tracks(self, target_sim, update_romance=True, family_member=False, default_track_overrides=None, bits_only=False):
        services.relationship_service().set_default_tracks(self._sim_info.sim_id, target_sim.sim_id, update_romance=update_romance, family_member=family_member, default_track_overrides=default_track_overrides, bits_only=bits_only)

    def add_relationship_bit(self, target_sim_id:int, bit_to_add, force_add=False, from_load=False, send_rel_change_event=True, allow_readdition=True):
        services.relationship_service().add_relationship_bit(self._sim_info.sim_id, target_sim_id, bit_to_add=bit_to_add, force_add=force_add, from_load=from_load, send_rel_change_event=send_rel_change_event, allow_readdition=allow_readdition)

    def remove_relationship_bit(self, target_sim_id:int, bit, send_rel_change_event=True):
        services.relationship_service().remove_relationship_bit(self._sim_info.sim_id, target_sim_id, bit, send_rel_change_event=send_rel_change_event)

    def remove_relationship_bit_by_collection_id(self, target_sim_id:int, collection_id, notify_client=True, send_rel_change_event=True):
        services.relationship_service().remove_relationship_bit_by_collection_id(self._sim_info.sim_id, target_sim_id, collection_id, notify_client=notify_client, send_rel_change_event=send_rel_change_event)

    def remove_exclusive_relationship_bit(self, bit):
        services.relationship_service().remove_exclusive_relationship_bit(self._sim_info.sim_id, bit)

    def get_all_bits(self, target_sim_id:int=None):
        return services.relationship_service().get_all_bits(self._sim_info.sim_id, target_sim_id=target_sim_id)

    def get_relationship_depth(self, target_sim_id:int):
        return services.relationship_service().get_relationship_depth(self._sim_info.sim_id, target_sim_id)

    def has_bit(self, target_sim_id:int, bit):
        return services.relationship_service().has_bit(self._sim_info.sim_id, target_sim_id, bit)

    def get_highest_priority_track_bit(self, target_sim_id):
        return services.relationship_service().get_highest_priority_track_bit(self._sim_info.sim_id, target_sim_id)

    def get_highest_priority_bit(self, target_sim_id):
        return services.relationship_service().get_highest_priority_bit(self._sim_info.sim_id, target_sim_id)

    def update_bits_on_age_up(self, current_age):
        services.relationship_service().update_bits_on_age_up(self._sim_info.sim_id, current_age)

    def target_sim_gen(self):
        yield from services.relationship_service().target_sim_gen(self._sim_info.sim_id)

    def get_target_sim_infos(self):
        return services.relationship_service().get_target_sim_infos(self._sim_info.sim_id)

    def has_relationship(self, target_sim_id):
        return services.relationship_service().has_relationship(self._sim_info.sim_id, target_sim_id)

    def add_relationship_appropriateness_buffs(self, target_sim_id:int):
        services.relationship_service().add_relationship_appropriateness_buffs(self._sim_info.sim_id, target_sim_id)

    def get_depth_sorted_rel_bit_list(self, target_sim_id):
        return services.relationship_service().get_depth_sorted_rel_bit_list(self._sim_info.sim_id, target_sim_id)

    def get_knowledge(self, target_sim_id:int, initialize=False):
        return services.relationship_service().get_knowledge(self._sim_info.sim_id, target_sim_id, initialize=initialize)

    def add_known_trait(self, trait, target_sim_id:int, notify_client=True):
        services.relationship_service().add_known_trait(trait, self._sim_info.sim_id, target_sim_id, notify_client=notify_client)

    def add_knows_career(self, target_sim_id:int, notify_client=True):
        services.relationship_service().add_knows_career(self._sim_info.sim_id, target_sim_id, notify_client=notify_client)

    def remove_knows_career(self, target_sim_id:int, notify_client=True):
        services.relationship_service().remove_knows_career(self._sim_info.sim_id, target_sim_id, notify_client=notify_client)

    def print_relationship_info(self, target_sim_id:int, _connection):
        services.relationship_service().print_relationship_info(self._sim_info.sim_id, target_sim_id, _connection)

    def relationship_decay_metrics(self, target_sim_id):
        return services.relationship_service().relationship_decay_metrics(self._sim_info.sim_id, target_sim_id)

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.MINIMUM

    def on_lod_update(self, old_lod, new_lod):
        services.relationship_service().on_lod_update(self._sim_info.sim_id, old_lod, new_lod)

class RelbitPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'is_add': Tunable(description='\n                If this interaction is trying to add a relbit to the\n                sim->target or to remove a relbit from the sim->target.', tunable_type=bool, default=True)}

    @flexmethod
    def _test(cls, inst, target, context, **kwargs):
        if target is context.sim:
            return TestResult(False, 'Cannot run rel picker as a self interaction.')
        inst_or_cls = inst if inst is not None else cls
        return super(PickerSuperInteraction, inst_or_cls)._test(target, context, **kwargs)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.target)
        return True

    @classmethod
    def _bit_selection_gen(cls, target, context):
        bit_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)
        rel_tracker = context.sim.sim_info.relationship_tracker
        target_sim_id = target.sim_id
        if cls.is_add:
            for bit in bit_manager.types.values():
                if bit.is_collection or not rel_tracker.has_bit(target_sim_id, bit):
                    yield bit
        else:
            for bit in rel_tracker.get_all_bits(target_sim_id=target_sim_id):
                yield bit

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        for bit in cls._bit_selection_gen(target, context):
            if bit.display_name:
                display_name = bit.display_name(context.sim, target)
                row = ObjectPickerRow(name=display_name, icon=bit.icon, row_description=bit.bit_description(context.sim, target), tag=bit)
                yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        bit = choice_tag
        rel_tracker = self.sim.sim_info.relationship_tracker
        target_sim_id = self.target.sim_id
        if bit is not None:
            if self.is_add:
                rel_tracker.add_relationship_bit(target_sim_id, bit, force_add=True)
            else:
                rel_tracker.remove_relationship_bit(target_sim_id, bit)
