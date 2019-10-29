import randomfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom buffs.tunable import TunableBuffReferencefrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableReference, TunableList, TunableTuple, OptionalTunablefrom sims4.utils import classpropertyfrom ui.ui_dialog_notification import TunableUiDialogNotificationReferenceimport clubsimport servicesimport sims4.reloadwith sims4.reload.protected(globals()):
    _is_death_enabled = Truelogger = sims4.log.Logger('Death')DEATH_INTERACTION_MARKER_ATTRIBUTE = 'death_interaction'
def toggle_death(enabled=None):
    global _is_death_enabled
    if enabled is None:
        _is_death_enabled = not _is_death_enabled
    else:
        _is_death_enabled = enabled

def is_death_enabled():
    return _is_death_enabled

def get_death_interaction(sim):
    return getattr(sim, DEATH_INTERACTION_MARKER_ATTRIBUTE, None)

class DeathType(DynamicEnumLocked):
    NONE = 0

    @classmethod
    def get_random_death_type(cls):
        death_types = list(cls)[1:]
        return random.choice(death_types)

class DeathTracker(SimInfoTracker):
    DEATH_ZONE_ID = 0
    DEATH_TYPE_GHOST_TRAIT_MAP = TunableMapping(description='\n        The ghost trait to be applied to a Sim when they die with a given death\n        type.\n        ', key_type=TunableEnumEntry(description='\n            The death type to map to a ghost trait.\n            ', tunable_type=DeathType, default=DeathType.NONE), key_name='Death Type', value_type=TunableReference(description='\n            The ghost trait to apply to a Sim when they die from the specified\n            death type.\n            ', manager=services.trait_manager()), value_name='Ghost Trait')
    DEATH_BUFFS = TunableList(description='\n        A list of buffs to apply to Sims when another Sim dies. For example, use\n        this tuning to tune a "Death of a Good Friend" buff.\n        ', tunable=TunableTuple(test_set=TunableReference(description="\n                The test that must pass between the dying Sim (TargetSim) and\n                the Sim we're considering (Actor). If this test passes, no\n                further test is executed.\n                ", manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TestSetInstance',), pack_safe=True), buff=TunableBuffReference(description='\n                The buff to apply to the Sim.\n                ', pack_safe=True), notification=OptionalTunable(description='\n                If enabled, an off-lot death generates a notification for the\n                target Sim. This is limited to one per death instance.\n                ', tunable=TunableUiDialogNotificationReference(description='\n                    The notification to show.\n                    ', pack_safe=True))))
    IS_DYING_BUFF = TunableReference(description='\n        A reference to the buff a Sim is given when they are dying.\n        ', manager=services.buff_manager())
    DEATH_RELATIONSHIP_BIT_FIXUP_LOOT = TunableReference(description='\n        A reference to the loot to apply to a Sim upon death.\n        \n        This is where the relationship bit fixup loots will be tuned. This\n        used to be on the interactions themselves but if the interaction was\n        reset then the bits would stay as they were. If we add more relationship\n        bits we want to clean up on death, the references Loot is the place to \n        do it.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION))

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._death_type = None
        self._death_time = None

    @property
    def death_type(self):
        return self._death_type

    @property
    def death_time(self):
        return self._death_time

    @property
    def is_ghost(self):
        return self._sim_info.trait_tracker.has_any_trait(self.DEATH_TYPE_GHOST_TRAIT_MAP.values())

    def get_ghost_trait(self):
        return self.DEATH_TYPE_GHOST_TRAIT_MAP.get(self._death_type)

    def set_death_type(self, death_type, is_off_lot_death=False):
        is_npc = self._sim_info.is_npc
        household = self._sim_info.household
        self._sim_info.inject_into_inactive_zone(self.DEATH_ZONE_ID, start_away_actions=False, skip_instanced_check=True, skip_daycare=True)
        household.remove_sim_info(self._sim_info, destroy_if_empty_household=True)
        if is_off_lot_death:
            household.pending_urnstone_ids.append(self._sim_info.sim_id)
        self._sim_info.transfer_to_hidden_household()
        clubs.on_sim_killed_or_culled(self._sim_info)
        if death_type is None:
            return
        relationship_service = services.relationship_service()
        for target_sim_info in relationship_service.get_target_sim_infos(self._sim_info.sim_id):
            resolver = DoubleSimResolver(target_sim_info, self._sim_info)
            for death_data in self.DEATH_BUFFS:
                if not death_data.test_set(resolver):
                    pass
                else:
                    target_sim_info.add_buff_from_op(death_data.buff.buff_type, buff_reason=death_data.buff.buff_reason)
                    if is_npc and not target_sim_info.is_npc:
                        notification = death_data.notification(target_sim_info, resolver=resolver)
                        notification.show_dialog()
                    break
        ghost_trait = DeathTracker.DEATH_TYPE_GHOST_TRAIT_MAP.get(death_type)
        if ghost_trait is not None:
            self._sim_info.add_trait(ghost_trait)
        self._death_type = death_type
        self._death_time = services.time_service().sim_now.absolute_ticks()
        self._sim_info.reset_age_progress()
        self._sim_info.resend_death_type()
        self._handle_remove_rel_bits_on_death()
        services.get_event_manager().process_event(test_events.TestEvent.SimDeathTypeSet, sim_info=self._sim_info)

    def _handle_remove_rel_bits_on_death(self):
        resolver = SingleSimResolver(self._sim_info)
        if self.DEATH_RELATIONSHIP_BIT_FIXUP_LOOT is not None:
            for (loot, _) in self.DEATH_RELATIONSHIP_BIT_FIXUP_LOOT.get_loot_ops_gen():
                result = loot.test_resolver(resolver)
                if result:
                    loot.apply_to_resolver(resolver)

    def clear_death_type(self):
        self._death_type = None
        self._death_time = None
        self._sim_info.resend_death_type()

    def save(self):
        if self._death_type is not None:
            data = protocols.PersistableDeathTracker()
            data.death_type = self._death_type
            data.death_time = self._death_time
            return data

    def load(self, data):
        try:
            self._death_type = DeathType(data.death_type)
        except:
            self._death_type = DeathType.NONE
        self._death_time = data.death_time

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.MINIMUM
