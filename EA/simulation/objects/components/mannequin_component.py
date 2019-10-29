from _collections import defaultdictfrom _weakrefset import WeakSetfrom protocolbuffers import SimObjectAttributes_pb2from buffs.appearance_modifier.appearance_modifier import AppearanceModifierfrom objects.components import Component, componentmethodfrom objects.components.state import TunableStateValueReferencefrom objects.components.types import MANNEQUIN_COMPONENTfrom sims.outfits.outfit_enums import OutfitCategory, BodyTypeFlag, REGULAR_OUTFIT_CATEGORIESfrom sims.outfits.outfit_utils import get_maximum_outfits_for_categoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Gender, Agefrom sims4.resources import get_protobuff_for_keyfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableEnumEntry, TunableSkinTone, HasTunableSingletonFactory, TunableResourceKey, TunableVariant, OptionalTunable, TunableRange, TunableMapping, TunableTuplefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport distributor.fieldsimport distributor.opsimport enumimport servicesimport sims4.resources
class _MannequinGroupData:

    def __init__(self):
        self._mannequins = WeakSet()
        self._mannequin_data = None

    def __iter__(self):
        return iter(self._mannequins)

    def add_mannequin(self, mannequin):
        self._mannequins.add(mannequin)

    def get_mannequin_data(self):
        return self._mannequin_data

    def set_mannequin_data(self, mannequin_data):
        self._mannequin_data = mannequin_data

    def reconcile_mannequin_data(self):
        for mannequin_component in self._mannequins:
            mannequin_component.reconcile_mannequin_data()

class MannequinGroupSharingMode(enum.Int, export=False):
    ACCEPT_MERGED = 0
    ACCEPT_YOURS = 1
    ACCEPT_THEIRS = 2
with sims4.reload.protected(globals()):
    _mannequin_group_sharing_mode = MannequinGroupSharingMode.ACCEPT_MERGED
    _mannequin_group_sharing_warning_enabled = True
def get_mannequin_group_data(mannequin_group, mannequin_data):
    current_zone = services.current_zone()
    if not hasattr(current_zone, 'mannequin_group_data'):
        setattr(current_zone, 'mannequin_group_data', defaultdict(_MannequinGroupData))
    key = (mannequin_group, mannequin_data.age, mannequin_data.gender)
    return current_zone.mannequin_group_data[key]

def set_mannequin_group_data_reference(mannequin_group, mannequin_data):
    mannequin_group_data = get_mannequin_group_data(mannequin_group, mannequin_data)
    mannequin_group_data.set_mannequin_data(mannequin_data)

def get_mannequin_group_sharing_mode():
    return _mannequin_group_sharing_mode

def set_mannequin_group_sharing_mode(mannequin_group_sharing_mode:MannequinGroupSharingMode):
    global _mannequin_group_sharing_mode
    _mannequin_group_sharing_mode = mannequin_group_sharing_mode

def show_mannequin_group_sharing_warning_notification():
    global _mannequin_group_sharing_warning_enabled
    if _mannequin_group_sharing_warning_enabled:
        _mannequin_group_sharing_warning_enabled = False
        if MannequinComponent.MANNEQUIN_GROUP_SHARING_WARNING_NOTIFICATION is not None:
            notification = MannequinComponent.MANNEQUIN_GROUP_SHARING_WARNING_NOTIFICATION(services.active_sim_info())
            notification.show_dialog()

def enable_mannequin_group_sharing_warning_notification():
    global _mannequin_group_sharing_warning_enabled
    _mannequin_group_sharing_warning_enabled = True

class MannequinComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=MANNEQUIN_COMPONENT, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.MannequinComponent):
    MANNEQUIN_GROUP_SHARING_WARNING_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        A notification to show explaining how outfit merging will clobber\n        outfits on the mannequin being placed into the world.\n        ', pack_safe=True)

    class _MannequinGroup(DynamicEnum):
        INVALID = 0

    class _MannequinTemplateExplicit(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'age': TunableEnumEntry(description='\n                The default age of this object when placed from Build/Buy.\n                ', tunable_type=Age, default=Age.ADULT), 'gender': TunableEnumEntry(description='\n                The default gender of this object when placed from\n                Build/Buy.\n                ', tunable_type=Gender, default=Gender.MALE), 'skin_tone': TunableSkinTone(description='\n                The default skin tone of this object when placed from Build/Buy.\n                ')}

        def create_sim_info_data(self, sim_id):
            return SimInfoBaseWrapper(sim_id=sim_id, age=self.age, gender=self.gender, species=self.species, skin_tone=self.skin_tone)

    class _MannequinTemplateResource(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'resource_key': TunableResourceKey(description='\n                The SimInfo file to use.\n                ', default=None, resource_types=(sims4.resources.Types.SIMINFO,)), 'outfit': OptionalTunable(description='\n                If enabled, the mannequin will default to the specified outfit.\n                ', tunable=TunableTuple(description='\n                    The outfit to switch the mannequin into.\n                    ', outfit_category=TunableEnumEntry(description='\n                        The outfit category.\n                        ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY), outfit_index=TunableRange(description='\n                        The outfit index.\n                        ', tunable_type=int, minimum=0, maximum=4, default=0)))}

        def create_sim_info_data(self, sim_id):
            sim_info_data = SimInfoBaseWrapper(sim_id=sim_id)
            sim_info_data.load_from_resource(self.resource_key)
            if self.outfit is not None:
                outfit_to_set = (self.outfit.outfit_category, self.outfit.outfit_index)
                if sim_info_data.has_outfit(outfit_to_set):
                    sim_info_data.set_current_outfit(outfit_to_set)
                    sim_info_data.set_previous_outfit(outfit_to_set, force=True)
            return sim_info_data

    FACTORY_TUNABLES = {'template': TunableVariant(description='\n            Define how the initial SimInfo data for this mannequin is created.\n            ', explicit=_MannequinTemplateExplicit.TunableFactory(), resource=_MannequinTemplateResource.TunableFactory(), default='resource'), 'cap_modifier': TunableRange(description='\n            This mannequin will be worth this many Sims when computing the cap\n            limit for NPCs in the world. While mannequins are not simulating\n            entities, they might have rendering costs that are equivalent to\n            those of Sims. We therefore need to limit how many of them are in\n            the world.\n            \n            Please consult Client Systems or CAS before changing this to a lower\n            number, as it might negatively impact performance, especially on\n            Minspec.\n            ', tunable_type=float, default=0.5, minimum=0, needs_tuning=False), 'outfit_sharing': OptionalTunable(description='\n            If enabled, all mannequins sharing the same group, age, and gender\n            will share outfits. Objects placed from the Gallery or the household\n            inventory will add any unique outfits to the master list, but will\n            lose any outfit beyond the maximum per category.\n            ', tunable=TunableEnumEntry(description='\n                The enum that controls how mannequins share outfits.\n                ', tunable_type=_MannequinGroup, default=_MannequinGroup.INVALID)), 'outfit_states': TunableMapping(description='\n            A mapping of outfit category to states. When the mannequin is\n            wearing the specified outfit category, it will transition into the\n            specified state.\n            ', key_type=TunableEnumEntry(description='\n                The outfit category that will trigger the associated state\n                change.\n                ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY), value_type=TunableStateValueReference(description='\n                The state of the object when the mannequin is wearing the\n                associated outfit category.\n                ')), 'outfit_modifiers': TunableMapping(description='\n            A mapping of modifiers to apply to the mannequin while in the\n            specified state.\n            ', key_type=TunableStateValueReference(description='\n                The state that triggers these outfit modifiers.\n                '), value_type=AppearanceModifier.TunableFactory(description='\n                An appearance modifier to apply while this state is active.\n                ')), 'state_trigger_grubby': TunableStateValueReference(description='\n            The state that triggers the mannequin being grubby. Any other state\n            on this track will set the mannequin as not grubby.\n            ', allow_none=True), 'state_trigger_singed': TunableStateValueReference(description='\n            The state that triggers the mannequin being singed. Any other state\n            on this track will set the mannequin as not singed.\n            ', allow_none=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim_info_data = None
        self._pose = None
        self._is_grubby = False
        self._is_singed = False

    @property
    def mannequin_id(self):
        return self.owner.id

    @distributor.fields.ComponentField(op=distributor.ops.ChangeSimOutfit)
    def mannequin_outfit(self):
        return self._sim_info_data.get_current_outfit()

    _resend_mannequin_outfit = mannequin_outfit.get_resend()

    @distributor.fields.ComponentField(op=distributor.ops.SetMannequinPose)
    def mannequin_pose(self):
        return self._pose

    @mannequin_pose.setter
    def mannequin_pose(self, value):
        self._pose = value

    @distributor.fields.ComponentField(op=distributor.ops.PreloadSimOutfit)
    def mannequin_outfit_preload_list(self):
        return self._sim_info_data.preload_outfit_list

    _resend_mannequin_outfit_preload_list = mannequin_outfit_preload_list.get_resend()

    @distributor.fields.ComponentField(op=distributor.ops.SetMannequinData, priority=distributor.fields.Field.Priority.HIGH)
    def sim_info_data(self):
        appearance_override_sim_info = self._sim_info_data.appearance_tracker.appearance_override_sim_info
        if appearance_override_sim_info is not None:
            return appearance_override_sim_info
        return self._sim_info_data

    _resend_sim_info_data = sim_info_data.get_resend()

    @distributor.fields.ComponentField(op=distributor.ops.SetGrubby)
    def mannequin_is_grubby(self):
        return self._is_grubby

    @mannequin_is_grubby.setter
    def mannequin_is_grubby(self, value):
        self._is_grubby = value

    @distributor.fields.ComponentField(op=distributor.ops.SetSinged)
    def mannequin_is_singed(self):
        return self._is_singed

    @mannequin_is_singed.setter
    def mannequin_is_singed(self, value):
        self._is_singed = value

    @componentmethod
    def get_current_outfit(self):
        return self._sim_info_data.get_current_outfit()

    @componentmethod
    def get_previous_outfit(self):
        return self._sim_info_data.get_previous_outfit()

    @componentmethod
    def get_outfits(self):
        return self._sim_info_data.get_outfits()

    @componentmethod
    def set_current_outfit(self, outfit):
        return self._sim_info_data.set_current_outfit(outfit)

    def _on_outfit_change(self, *_, **__):
        self._resend_mannequin_outfit()
        self._update_outfit_state()

    def _on_outfit_generated(self, outfit_category, outfit_index):
        self._sim_info_data.set_outfit_flags(outfit_category, outfit_index, BodyTypeFlag.CLOTHING_ALL)
        mannequin_group_data = get_mannequin_group_data(self.outfit_sharing, self._sim_info_data)
        mannequin_group_data.set_mannequin_data(self._sim_info_data)
        mannequin_group_data.reconcile_mannequin_data()

    def _on_preload_outfits_changed(self):
        self._resend_mannequin_outfit_preload_list()

    def _update_outfit_state(self):
        if self.owner.id:
            outfit_category = self.get_current_outfit()[0]
            outfit_state = self.outfit_states.get(outfit_category)
            if outfit_state is not None:
                self.owner.set_state(outfit_state.state, outfit_state)

    def on_add(self, *_, **__):
        sim_spawner_service = services.sim_spawner_service()
        sim_spawner_service.add_npc_cap_modifier(self.cap_modifier)
        zone = services.current_zone()
        if zone.is_zone_loading or not self.owner.is_downloaded:
            self.reconcile_mannequin_data(is_add=True)
        self._update_outfit_state()

    def on_remove(self, *_, **__):
        sim_spawner_service = services.sim_spawner_service()
        sim_spawner_service.add_npc_cap_modifier(-self.cap_modifier)
        if self._sim_info_data is not None:
            self._sim_info_data.on_outfit_changed.remove(self._on_outfit_change)
            self._sim_info_data.on_outfit_generated.remove(self._on_outfit_generated)
            self._sim_info_data.on_preload_outfits_changed.remove(self._on_preload_outfits_changed)

    def on_state_changed(self, state, old_value, new_value, from_init):
        old_appearance_modifier = self.outfit_modifiers.get(old_value)
        if old_appearance_modifier is not None:
            self._sim_info_data.appearance_tracker.remove_appearance_modifiers(state, source=self)
        new_appearance_modifier = self.outfit_modifiers.get(new_value)
        if new_appearance_modifier is not None:
            self._sim_info_data.appearance_tracker.add_appearance_modifiers(new_appearance_modifier.appearance_modifiers, state, new_appearance_modifier.priority, new_appearance_modifier.apply_to_all_outfits, source=self)
        if state is self.state_trigger_singed.state:
            if new_value is self.state_trigger_singed:
                self.mannequin_is_singed = True
            else:
                self.mannequin_is_singed = False
        if state is self.state_trigger_grubby.state:
            if new_value is self.state_trigger_grubby:
                self.mannequin_is_grubby = True
            else:
                self.mannequin_is_grubby = False
        self._resend_sim_info_data()
        self._resend_mannequin_outfit()

    def pre_add(self, manager, obj_id):
        self._sim_info_data = self.template.create_sim_info_data(obj_id)
        self._sim_info_data.on_outfit_changed.append(self._on_outfit_change)
        self._sim_info_data.on_outfit_generated.append(self._on_outfit_generated)
        self._sim_info_data.on_preload_outfits_changed.append(self._on_preload_outfits_changed)
        if self.outfit_sharing is not None:
            mannequin_group_data = get_mannequin_group_data(self.outfit_sharing, self._sim_info_data)
            mannequin_group_data.add_mannequin(self)

    def populate_sim_info_data_proto(self, sim_info_data_msg):
        sim_info_data_msg.mannequin_id = self.mannequin_id
        self._sim_info_data.save_sim_info(sim_info_data_msg)
        if self._pose is not None:
            sim_info_data_msg.animation_pose.asm = get_protobuff_for_key(self._pose.asm)
            sim_info_data_msg.animation_pose.state_name = self._pose.state_name

    def save(self, persistence_master_message):
        persistable_data = SimObjectAttributes_pb2.PersistenceMaster.PersistableData()
        persistable_data.type = SimObjectAttributes_pb2.PersistenceMaster.PersistableData.MannequinComponent
        mannequin_component_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableMannequinComponent.persistable_data]
        if self._sim_info_data is not None:
            self.populate_sim_info_data_proto(mannequin_component_data.sim_info_data)
        persistence_master_message.data.extend((persistable_data,))

    def load(self, persistable_data):
        sim_info_data_proto = None
        persistence_service = services.get_persistence_service()
        if persistence_service is not None:
            sim_info_data_proto = persistence_service.get_mannequin_proto_buff(self.mannequin_id)
            if sim_info_data_proto is not None and self.outfit_sharing is not None:
                set_mannequin_group_data_reference(self.outfit_sharing, self._sim_info_data)
        if sim_info_data_proto is None:
            mannequin_component_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableMannequinComponent.persistable_data]
            if mannequin_component_data.HasField('sim_info_data'):
                sim_info_data_proto = mannequin_component_data.sim_info_data
        if sim_info_data_proto is not None:
            self._sim_info_data.load_sim_info(sim_info_data_proto)
            persistence_service.del_mannequin_proto_buff(self.mannequin_id)
        zone = services.current_zone()
        if not zone.is_zone_loading:
            self.reconcile_mannequin_data(is_add=True, is_loaded=True)

    def on_finalize_load(self):
        self.reconcile_mannequin_data()

    def _replace_outfits(self, sim_info_data):
        current_outfit = self.get_current_outfit()
        default_outfit = (OutfitCategory.BATHING, 0)
        for (outfit_category, outfit_list) in sim_info_data.get_all_outfits():
            if outfit_category not in REGULAR_OUTFIT_CATEGORIES:
                pass
            else:
                self._sim_info_data.remove_outfits_in_category(outfit_category)
                for (outfit_index, outfit_data) in enumerate(outfit_list):
                    source_outfit = (outfit_category, outfit_index)
                    destination_outfit = self._sim_info_data.add_outfit(outfit_category, outfit_data)
                    self._sim_info_data.generate_merged_outfit(sim_info_data, destination_outfit, default_outfit, source_outfit, preserve_outfit_flags=True)
        if self._sim_info_data.has_outfit(current_outfit):
            self._sim_info_data.set_current_outfit(current_outfit)
        else:
            self._sim_info_data.set_current_outfit(default_outfit)

    def _resend_mannequin_data(self):
        self._resend_sim_info_data()
        self._resend_mannequin_outfit()

    def reconcile_mannequin_data(self, *args, **kwargs):
        self.reconcile_mannequin_data_internal(*args, **kwargs)
        enable_mannequin_group_sharing_warning_notification()
        self._resend_mannequin_data()

    def reconcile_mannequin_data_internal(self, is_add=False, is_loaded=False):
        if self.outfit_sharing is None:
            return
        mannequin_group_sharing_mode = get_mannequin_group_sharing_mode()
        mannequin_group_data = get_mannequin_group_data(self.outfit_sharing, self._sim_info_data)
        if is_loaded:
            if mannequin_group_sharing_mode == MannequinGroupSharingMode.ACCEPT_THEIRS:
                mannequin_group_data.set_mannequin_data(self._sim_info_data)
                for mannequin in mannequin_group_data:
                    if mannequin is not self:
                        mannequin._replace_outfits(self._sim_info_data)
                        mannequin._resend_mannequin_data()
                return
            if mannequin_group_sharing_mode == MannequinGroupSharingMode.ACCEPT_YOURS:
                self._replace_outfits(mannequin_group_data.get_mannequin_data())
                return
        mannequin_data = mannequin_group_data.get_mannequin_data()
        if mannequin_data is None:
            mannequin_group_data.set_mannequin_data(self._sim_info_data)
            if is_add:
                mannequin_group_data.reconcile_mannequin_data()
                return
        else:
            if is_add:
                if mannequin_group_sharing_mode == MannequinGroupSharingMode.ACCEPT_MERGED:
                    for (outfit_category, outfit_list) in self._sim_info_data.get_all_outfits():
                        if outfit_category not in REGULAR_OUTFIT_CATEGORIES:
                            pass
                        else:
                            for (outfit_index, outfit_data) in enumerate(outfit_list):
                                if mannequin_data.is_generated_outfit_duplicate_in_category(self._sim_info_data, (outfit_category, outfit_index)):
                                    pass
                                else:
                                    outfits_in_category = mannequin_data.get_outfits_in_category(outfit_category)
                                    if outfits_in_category is not None and len(outfits_in_category) >= get_maximum_outfits_for_category(outfit_category):
                                        show_mannequin_group_sharing_warning_notification()
                                    else:
                                        mannequin_data.generate_merged_outfit(self._sim_info_data, mannequin_data.add_outfit(outfit_category, outfit_data), mannequin_data.get_current_outfit(), (outfit_category, outfit_index), preserve_outfit_flags=True)
                mannequin_group_data.reconcile_mannequin_data()
                return
            if self.owner.id:
                for outfit_category in REGULAR_OUTFIT_CATEGORIES:
                    self._sim_info_data.generate_merged_outfits_for_category(mannequin_data, outfit_category, preserve_outfit_flags=True)
