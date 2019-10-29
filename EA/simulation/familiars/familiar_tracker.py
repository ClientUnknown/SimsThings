import id_generatorfrom buffs.tunable import TunablePackSafeBuffReference, TunableBuffReferencefrom distributor.rollback import ProtocolBufferRollbackfrom familiars.familiar_enums import FamiliarTypefrom interactions.interaction_finisher import FinishingTypefrom protocolbuffers import SimObjectAttributes_pb2import servicesimport sims4.resourcesfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import SingleSimResolverfrom interactions.context import InteractionContext, InteractionSource, QueueInsertStrategyfrom interactions.priority import Priorityfrom interactions.utils.tunable_icon import TunableIconAllPacksfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED, ALL_HIDDEN_REASONSfrom objects.placement.placement_helper import _PlacementStrategyLocationfrom objects.system import create_objectfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.sim_info_types import Gender, Age, SpeciesExtendedfrom sims.sim_spawner import SimSpawnerfrom sims.sim_spawner_enums import SimNameTypefrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.log import Loggerfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, OptionalTunable, TunableReference, TunablePackSafeReferencefrom sims4.utils import classpropertyfrom ui.ui_dialog_notification import UiDialogNotificationfrom venues.venue_constants import NPCSummoningPurposefrom world import regionlogger = Logger('Familiars', default_owner='jjacobson')
class FamiliarInfo:

    def __init__(self, uid, familiar_type, name, pet_familiar_id):
        self._uid = uid
        self._familiar_type = familiar_type
        self._name = name
        self._pet_familiar_id = pet_familiar_id

    @property
    def uid(self):
        return self._uid

    @property
    def familiar_type(self):
        return self._familiar_type

    @property
    def icon_info(self):
        return IconInfoData(icon_resource=FamiliarTracker.FAMILIAR_DATA[self._familiar_type].icon)

    @property
    def pet_familiar_id(self):
        return self._pet_familiar_id

    @property
    def name(self):
        if self._pet_familiar_id is None:
            return LocalizationHelperTuning.get_raw_text(self._name)
        pet_familiar = services.sim_info_manager().get(self._pet_familiar_id)
        if pet_familiar is None:
            logger.error("Attempting to get the name of a pet familiar that doesn't exist.")
            return
        return LocalizationHelperTuning.get_sim_name(pet_familiar)

    @name.setter
    def name(self, new_name):
        if self._pet_familiar_id is None:
            self._name = new_name
        else:
            logger.error('Attempting to set the familiar Name of a Pet based Familiar.')

    @property
    def raw_name(self):
        if self._pet_familiar_id is None:
            return self._name
        pet_familiar = services.sim_info_manager().get(self._pet_familiar_id)
        if pet_familiar is None:
            logger.error("Attempting to get the name of a pet familiar that doesn't exist.")
            return
        return pet_familiar.full_name

    def save_familiar_info(self, familiar_data):
        familiar_data.familiar_uid = self.uid
        familiar_data.familiar_type = int(self._familiar_type)
        if self._name is not None:
            familiar_data.familiar_name = self._name
        if self._pet_familiar_id is not None:
            familiar_data.pet_familiar_id = self._pet_familiar_id

class FamiliarTracker(SimInfoTracker):
    FAMILIAR_DATA = TunableMapping(description='\n        A mapping between the familiar type and data associated with that familiar type.\n        ', key_type=TunableEnumEntry(description='\n            The type of familiar associated with this data.\n            ', tunable_type=FamiliarType, default=FamiliarType.CAT), value_type=TunableTuple(description='\n            Data associated with a specific familiar type.\n            ', icon=TunableIconAllPacks(description='\n                The icon of the familiar within the picker.\n                '), familiar_type=OptionalTunable(description="\n                The type of familiar this is.\n                Object Familiars have a special object associated with them that is created whenever the Sim is created\n                and has an interaction pushed on the owning Sim to places the pet familiar in a routing formation with\n                the owning Sim.\n                \n                Pet Based Familiars are instead based on Pets and rely on the Pet's autonomy to drive most behavior\n                with the familiar. \n                ", tunable=TunableTuple(description='\n                    Data related to Object Based Familiars.\n                    ', familiar_object=TunablePackSafeReference(description='\n                        The definition of the familiar object that will be created.\n                        ', manager=services.definition_manager()), name_list=TunableEnumEntry(description="\n                        The name list associated with this familiar type.\n                        \n                        Since familiars don't have any specific gender associated with them we always just use Male\n                        names.\n                        ", tunable_type=SimNameType, default=SimNameType.DEFAULT), follow_affordance=TunablePackSafeReference(description='\n                        The specific affordance to follow a familiar.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), familiar_description=TunableLocalizedStringFactory(description='\n                        The description of this familiar as it appears in the familiar rename dialogs.\n                        '), familiar_token_object=TunableReference(description="\n                        The definition of the familiar token object that will be created and played into the user's\n                        inventory when the familiar is unbound.\n                        ", manager=services.definition_manager(), pack_safe=True)), enabled_by_default=True, disabled_name='pet_based_familiar', enabled_name='object_based_familiar')))
    FAMILIAR_PLACEMENT = _PlacementStrategyLocation.TunableFactory(description="\n        Method for placing the familiar's initial position based on the Sim.\n        ")
    FAMILIAR_ENSEMBLE = TunablePackSafeReference(description='\n        The ensemble to place pet familiars in with their master.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE))
    PET_FAMILIAR_BIT = TunablePackSafeReference(description='\n        The relationship bit to indicate that a pet is a familiar.\n        ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT))
    FAMILIAR_SUMMON_FAILURE_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A TNS that is displayed when the familiar fails to be summoned.\n        ')
    PET_FAMILIAR_SET_ACTIVE_AFFORDANCE = TunablePackSafeReference(description='\n        An interaction pushed on pet Sims when they are set to be the active familiar.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    PET_FAMILIAR_BUFF = TunableMapping(description='\n        A buff added to pet familiars based on age and species.\n        ', key_type=TunableEnumEntry(description='\n            The age that this buff will be applied to.\n            ', tunable_type=Age, default=Age.ADULT), value_type=TunableMapping(key_type=TunableEnumEntry(description='\n                The species that this buff will be applied to.\n                ', tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,)), value_type=TunableBuffReference(description='\n                The buff that will be given to the Familiar of this age/species pair.\n                ', pack_safe=True)))
    ACTIVE_FAMILIAR_BUFF = TunableBuffReference(description='\n        The buff that will be given to the Sim when they have an active familiar.\n        ', pack_safe=True)

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._active_familiar_id = None
        self._active_familiar_obj_id = None
        self._familiars = {}
        self._sim_buff_handle = None
        self._pet_buff_handle = None

    def __iter__(self):
        yield from self._familiars.values()

    @property
    def has_familiars(self):
        return len(self._familiars) > 0

    @property
    def active_familiar_id(self):
        return self._active_familiar_id

    @property
    def active_familiar_id_pet_id(self):
        if self._active_familiar_id is None:
            return
        return self._familiars[self._active_familiar_id].pet_familiar_id

    @property
    def active_familiar_type(self):
        if self._active_familiar_id is None:
            return
        return self._familiars[self._active_familiar_id].familiar_type

    def get_active_familiar(self):
        return services.object_manager().get(self._active_familiar_obj_id)

    def get_familiar_name(self, familiar_uid):
        if familiar_uid not in self._familiars:
            logger.error("Attempting to get name of familiar that does not exist within {}'s familiar tracker", self._owner)
            return
        return self._familiars[familiar_uid].name

    def get_familiar_icon(self, familiar_uid):
        if familiar_uid not in self._familiars:
            logger.error("Attempting to get icon of familiar that does not exist within {}'s familiar tracker", self._owner)
            return
        return IconInfoData(FamiliarTracker.FAMILIAR_DATA[self._familiars[familiar_uid].familiar_type].icon)

    def get_familiar_description(self, familiar_uid):
        if familiar_uid not in self._familiars:
            logger.error("Attempting to get description of familiar that does not exist within {}'s familiar tracker", self._owner)
            return
        familiar_type = FamiliarTracker.FAMILIAR_DATA[self._familiars[familiar_uid].familiar_type].familiar_type
        if familiar_type is None:
            logger.error('Attempting to get the description of a Pet familiar.  These familiars do not need descriptions for rename dialogs.')
            return
        return familiar_type.familiar_description

    def bind_familiar(self, familiar_type, pet_familiar=None):
        if pet_familiar is None:
            name = SimSpawner.get_random_first_name(Gender.MALE, sim_name_type_override=FamiliarTracker.FAMILIAR_DATA[familiar_type].familiar_type.name_list)
            pet_familiar_id = None
        else:
            name = None
            pet_familiar_id = pet_familiar.sim_id
            services.relationship_service().add_relationship_bit(self._owner.sim_id, pet_familiar.sim_id, FamiliarTracker.PET_FAMILIAR_BIT)
        familiar_uid = id_generator.generate_object_id()
        new_familiar = FamiliarInfo(familiar_uid, familiar_type, name, pet_familiar_id)
        self._familiars[new_familiar.uid] = new_familiar
        return new_familiar.uid

    def unbind_familiar(self, familiar_uid):
        if familiar_uid not in self._familiars:
            logger.error('Attemting to unbind familiar that is not in the familiar tracker.')
            return
        if self._active_familiar_id is not None and self._active_familiar_id == familiar_uid:
            self.dismiss_familiar()
        familiar_info = self._familiars[familiar_uid]
        pet_familiar_id = familiar_info.pet_familiar_id
        if pet_familiar_id is not None:
            services.relationship_service().remove_relationship_bit(self._owner.sim_id, pet_familiar_id, FamiliarTracker.PET_FAMILIAR_BIT)
        else:
            sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is not None:
                familiar_token = create_object(self.FAMILIAR_DATA[familiar_info.familiar_type].familiar_type.familiar_token_object)
                if familiar_token is not None:
                    familiar_token.set_household_owner_id(self._owner.household_id)
                    sim.inventory_component.system_add_object(familiar_token)
                else:
                    logger.error('Attempting to create familiar token on unbind, but failed to do so.')
            else:
                logger.error('Sim is not instanced when unbinding familiar.  The familiar token will not be generated.')
        del self._familiars[familiar_uid]

    def set_familiar_name(self, familiar_id, new_name):
        if familiar_id is None:
            if self._active_familiar_id:
                logger.error('Trying to set the name of a familiar with both no specified familiar nor no active familiar.')
                return
            familiar_id = self._active_familiar_id
        self._familiars[familiar_id].name = new_name

    def _on_familiar_summon_failure(self, error_message, familiar_object=None, exc=None, warn=False):
        if exc is not None:
            logger.exception(error_message, exc=exc)
        elif warn:
            logger.warn(error_message)
        else:
            logger.error(error_message)
        if familiar_object is not None:
            familiar_object.destroy()
        self._active_familiar_id = None
        self._active_familiar_obj_id = None
        resolver = SingleSimResolver(self._owner)
        dialog = self.FAMILIAR_SUMMON_FAILURE_NOTIFICATION(self._owner, resolver)
        dialog.show_dialog()

    def _on_familiar_follow_interaction_finished_prematurely(self, interaction):
        if interaction.is_finishing_naturally or interaction.has_been_reset:
            return
        self._active_familiar_id = None
        self._active_familiar_obj_id = None
        if self._sim_buff_handle is not None:
            self._owner.remove_buff(self._sim_buff_handle)
            self._sim_buff_handle = None

    def _create_and_establish_familiar_link(self):
        sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if sim is None:
            return
        familiar_type = self._familiars[self._active_familiar_id].familiar_type
        familiar_data = FamiliarTracker.FAMILIAR_DATA[familiar_type]
        if familiar_data.familiar_type is None:
            try:
                self._active_familiar_obj_id = self._familiars[self._active_familiar_id].pet_familiar_id
                pet_familiar_sim_info = services.sim_info_manager().get(self._active_familiar_obj_id)
                buff_info_to_add = self.PET_FAMILIAR_BUFF[pet_familiar_sim_info.age][pet_familiar_sim_info.extended_species]
                self._pet_buff_handle = pet_familiar_sim_info.add_buff(buff_info_to_add.buff_type, buff_reason=buff_info_to_add.buff_reason)
                pet_familiar = services.object_manager().get(self._active_familiar_obj_id)
                if services.current_zone().is_zone_running:
                    if pet_familiar is None:
                        services.current_zone().venue_service.venue.summon_npcs((pet_familiar_sim_info,), NPCSummoningPurpose.BRING_PLAYER_SIM_TO_LOT)
                    else:
                        context = InteractionContext(pet_familiar, InteractionContext.SOURCE_SCRIPT, Priority.Critical, insert_strategy=QueueInsertStrategy.NEXT)
                        pet_familiar.push_super_affordance(FamiliarTracker.PET_FAMILIAR_SET_ACTIVE_AFFORDANCE, None, context)
            except Exception as e:
                self._on_familiar_summon_failure('Exception encountered when trying to create familiar.  Deactivating familiar.', familiar_object=pet_familiar, exc=e)
            if self._sim_buff_handle is None:
                self._sim_buff_handle = self._owner.add_buff(self.ACTIVE_FAMILIAR_BUFF.buff_type, buff_reason=self.ACTIVE_FAMILIAR_BUFF.buff_reason)
            return
        familiar = services.object_manager().get(self._active_familiar_obj_id)
        if familiar is None:
            try:
                familiar_obj_def = familiar_data.familiar_type.familiar_object
                familiar = create_object(familiar_obj_def)
                if familiar is None:
                    self._on_familiar_summon_failure('Failure to create familiar object.  Deactivating familiar.')
                    return
                resolver = SingleSimResolver(self._owner)
                if not FamiliarTracker.FAMILIAR_PLACEMENT.try_place_object(familiar, resolver):
                    self._on_familiar_summon_failure('Failure to create familiar object.  Deactivating familiar.', familiar_object=familiar, warn=True)
                    return
                self._active_familiar_obj_id = familiar.id
            except Exception as e:
                self._on_familiar_summon_failure('Exception encountered when trying to create familiar.  Deactivating familiar.', familiar_object=familiar, exc=e)
                return
        context = InteractionContext(sim, InteractionSource.SCRIPT, Priority.Critical, insert_strategy=QueueInsertStrategy.NEXT)
        result = sim.push_super_affordance(familiar_data.familiar_type.follow_affordance, familiar, context)
        if not result:
            self._on_familiar_summon_failure('Failed to push familiar follow interaction.  Deactivating Familiar.', familiar_object=familiar)
            return
        result.interaction.register_on_finishing_callback(self._on_familiar_follow_interaction_finished_prematurely)
        if self._sim_buff_handle is None:
            self._sim_buff_handle = self._owner.add_buff(self.ACTIVE_FAMILIAR_BUFF.buff_type, buff_reason=self.ACTIVE_FAMILIAR_BUFF.buff_reason)

    def remove_active_pet_familiar_buff(self):
        if self._pet_buff_handle is None:
            return
        pet_sim_info = services.sim_info_manager().get(self._familiars[self._active_familiar_id].pet_familiar_id)
        if pet_sim_info is None:
            self._pet_buff_handle = None
            return
        pet_sim_info.remove_buff(self._pet_buff_handle)
        self._pet_buff_handle = None

    def set_active_familiar(self, familiar_uid):
        if familiar_uid not in self._familiars:
            logger.error("Attempting to set a familiar as active that isn't an actual familiar.")
            return
        if self._active_familiar_obj_id is not None:
            active_familiar_obj = services.object_manager().get(self._active_familiar_obj_id)
            if active_familiar_obj is not None and not active_familiar_obj.is_sim:
                active_familiar_obj.destroy()
            self.remove_active_pet_familiar_buff()
            self._active_familiar_obj_id = None
        self._active_familiar_id = familiar_uid
        self._create_and_establish_familiar_link()

    def dismiss_familiar(self):
        if self._active_familiar_id is None:
            return
        if self._sim_buff_handle is not None:
            self._owner.remove_buff(self._sim_buff_handle)
            self._sim_buff_handle = None
        self.remove_active_pet_familiar_buff()
        familiar = self.get_active_familiar()
        if familiar is None:
            if self._familiars[self._active_familiar_id].pet_familiar_id is None:
                logger.error("Attempting to dismiss a familiar that is active, but doesn't have a familiar object.")
            self._active_familiar_obj_id = None
            self._active_familiar_id = None
            return
        if not familiar.is_sim:
            owner_sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if owner_sim is None:
                familiar.destroy()
            else:
                follow_affordance = self.FAMILIAR_DATA[self._familiars[self._active_familiar_id].familiar_type].familiar_type.follow_affordance
                sim_interactions = owner_sim.get_all_running_and_queued_interactions()
                for interaction in sim_interactions:
                    if interaction.affordance is follow_affordance:
                        interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='User changed familiars.')
        self._active_familiar_obj_id = None
        self._active_familiar_id = None

    def on_sim_startup(self):
        if self._active_familiar_id is None:
            return
        if self._sim_buff_handle is None:
            self._sim_buff_handle = self._owner.add_buff(self.ACTIVE_FAMILIAR_BUFF.buff_type, buff_reason=self.ACTIVE_FAMILIAR_BUFF.buff_reason)
        self._create_and_establish_familiar_link()

    def on_sim_removed(self):
        if self._active_familiar_id is None:
            return
        if self._sim_buff_handle is not None:
            self._owner.remove_buff(self._sim_buff_handle)
            self._sim_buff_handle = None
        self.remove_active_pet_familiar_buff()
        active_familiar = self.get_active_familiar()
        if active_familiar is None or active_familiar.is_sim:
            return
        active_familiar.destroy()

    def on_household_member_removed(self):
        sim_info_manager = services.sim_info_manager()
        for familiar_data in tuple(self._familiars.values()):
            pet_familiar = sim_info_manager.get(familiar_data.pet_familiar_id)
            if pet_familiar is None:
                pass
            elif pet_familiar.household_id == self._owner.household_id:
                pass
            else:
                services.relationship_service().remove_relationship_bit(self._owner.sim_id, familiar_data.pet_familiar_id, FamiliarTracker.PET_FAMILIAR_BIT)
                if self._active_familiar_id == familiar_data.uid:
                    self.dismiss_familiar()
                del self._familiars[familiar_data.uid]
                return

    def save(self):
        data = SimObjectAttributes_pb2.PersistableFamiliarTracker()
        if self._active_familiar_id is not None:
            data.active_familiar_uid = self._active_familiar_id
        for familiar_info in self._familiars.values():
            with ProtocolBufferRollback(data.familiars) as entry:
                familiar_info.save_familiar_info(entry)
        return data

    def load(self, data):
        if data.HasField('active_familiar_uid'):
            self._active_familiar_id = data.active_familiar_uid
        sim_info_manager = services.sim_info_manager()
        for familiar_data in data.familiars:
            if familiar_data.HasField('familiar_name'):
                familiar_name = familiar_data.familiar_name
            else:
                familiar_name = None
            if familiar_data.HasField('pet_familiar_id'):
                pet_familiar_id = familiar_data.pet_familiar_id
            else:
                pet_familiar_id = None
            try:
                loaded_familiar = FamiliarInfo(familiar_data.familiar_uid, FamiliarType(familiar_data.familiar_type), familiar_name, pet_familiar_id=pet_familiar_id)
            except Exception as e:
                logger.exception('Exception encountered when trying to load familiar.  Skipping familiar.', exc=e)
                if pet_familiar_id is not None:
                    services.relationship_service().remove_relationship_bit(self._owner.sim_id, pet_familiar_id, FamiliarTracker.PET_FAMILIAR_BIT)
            self._familiars[familiar_data.familiar_uid] = loaded_familiar

    def on_all_sim_infos_loaded(self):
        sim_info_manager = services.sim_info_manager()
        for familiar_data in tuple(self._familiars.values()):
            pet_familiar_id = familiar_data.pet_familiar_id
            if pet_familiar_id is None:
                pass
            else:
                pet_familiar = sim_info_manager.get(pet_familiar_id)
                if pet_familiar is not None and pet_familiar.household_id == self._owner.household_id:
                    pass
                else:
                    self.unbind_familiar(familiar_data.uid)

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.ACTIVE

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.dismiss_familiar()
            self._clean_up()
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._owner.id)
            if sim_msg is not None:
                self.load(sim_msg.attributes.familiar_tracker)

    def _clean_up(self):
        self._active_familiar_obj_id = None
        self._active_familiar_id = None
        self._familiars.clear()
        self._familiars = None
