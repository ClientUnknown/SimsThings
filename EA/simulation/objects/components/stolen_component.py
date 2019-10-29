from protocolbuffers import SimObjectAttributes_pb2from build_buy import ObjectOriginLocationfrom interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects.components import Component, types, componentmethodfrom objects.hovertip import TooltipFieldsComplete, HovertipStylefrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntryimport build_buyimport objects.components.typesimport servicesimport sims4.loglogger = sims4.log.Logger('StolenComponent', default_owner='jwilkinson')
class StolenComponent(Component, AutoFactoryInit, HasTunableFactory, allow_dynamic=True, component_name=types.STOLEN_COMPONENT, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.StolenComponent):
    STOLEN_FROM_HOUSEHOLD = TunableLocalizedStringFactory(description='\n        How the Stolen From text should appear for households.\n        e.g. "Stolen From Household: {0.String} " = Stolen From Household: Goth\n        ')
    STOLEN_FROM_LOT = TunableLocalizedStringFactory(description='\n        How the Stolen From text should appear for non-Household lots.\n        e.g. "Stolen From: {0.String}" = Stolen From: The Blue Velvet\n        ')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stolen_from_text = None
        self._stolen_from_career_guid = None
        self.stolen_from_household_id = None

    def get_company_name_from_career_guid(self):
        career = services.get_instance_manager(sims4.resources.Types.CAREER).get(self._stolen_from_career_guid)
        if career is not None:
            company_names = getattr(career.career_location, 'company_names', None)
            if not company_names:
                return
            else:
                return company_names[0]

    @componentmethod
    def set_stolen_from_data(self, stolen_from_text=None, stolen_from_career_guid=None):
        self.reset_stolen_data()
        if stolen_from_text is not None:
            self._stolen_from_text = stolen_from_text
        elif stolen_from_career_guid is not None:
            self._stolen_from_career_guid = stolen_from_career_guid
        else:
            stolen_from_household_id = self.owner.household_owner_id
            if not stolen_from_household_id:
                stolen_from_household_id = services.current_zone().lot.owner_household_id
            household = services.household_manager().get(stolen_from_household_id)
            if household is not None:
                self._stolen_from_text = household.name
                self.stolen_from_household_id = stolen_from_household_id
            else:
                lot_name = services.get_zone(self.owner.zone_id).lot.get_lot_name()
                if lot_name is not None:
                    self._stolen_from_text = lot_name
        self.update_hovertip()

    def update_hovertip(self):
        stolen_from_data = self._stolen_from_text if self._stolen_from_text is not None else self.get_company_name_from_career_guid()
        if stolen_from_data is not None:
            if self.stolen_from_household_id is not None:
                stolen_text = self.STOLEN_FROM_HOUSEHOLD(stolen_from_data)
            else:
                stolen_text = self.STOLEN_FROM_LOT(stolen_from_data)
            self.owner.hover_tip = HovertipStyle.HOVER_TIP_DEFAULT
            self.owner.update_tooltip_field(TooltipFieldsComplete.stolen_from_text, stolen_text, should_update=True)

    def reset_stolen_data(self):
        self.remove_stolen_data_from_hovertip()
        self._stolen_from_text = None
        self._stolen_from_career_guid = None
        self.stolen_from_household_id = None

    def remove_stolen_data_from_hovertip(self):
        self.owner.update_tooltip_field(TooltipFieldsComplete.stolen_from_text, None, should_update=True)

    def on_client_connect(self, client):
        self.update_hovertip()

    def save(self, persistence_master_message):
        persistable_data = SimObjectAttributes_pb2.PersistenceMaster.PersistableData()
        persistable_data.type = SimObjectAttributes_pb2.PersistenceMaster.PersistableData.StolenComponent
        stolen_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableStolenComponent.persistable_data]
        if self._stolen_from_text is not None:
            stolen_data.stolen_from_text = self._stolen_from_text
        if self.stolen_from_household_id is not None:
            stolen_data.stolen_from_household_id = self.stolen_from_household_id
        if self._stolen_from_career_guid is not None:
            stolen_data.stolen_from_career_guid = self._stolen_from_career_guid
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistence_master_message):
        stolen_data = persistence_master_message.Extensions[SimObjectAttributes_pb2.PersistableStolenComponent.persistable_data]
        if stolen_data.HasField('stolen_from_text'):
            self._stolen_from_text = stolen_data.stolen_from_text
        if stolen_data.HasField('stolen_from_household_id'):
            self.stolen_from_household_id = stolen_data.stolen_from_household_id
        if stolen_data.HasField('stolen_from_career_guid'):
            self._stolen_from_career_guid = stolen_data.stolen_from_career_guid
        self.update_hovertip()

class ReturnStolenObject(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            Element that returns a stolen object to the household that previously owned it.\n            \n            If this household exists, the object will be placed in the household inventory.\n            If this household does not exist, the object will be deleted.\n            If the object was stolen from a venue, it will be deleted.\n            ', 'participant': TunableEnumEntry(description='\n            The participant of the interaction that will be returned.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def _do_behavior(self):
        obj = self.interaction.get_participant(self.participant)
        if obj is None:
            return
        sim = self.interaction.sim
        if sim is None:
            return
        stolen_component = obj.get_component(objects.components.types.STOLEN_COMPONENT)
        if stolen_component is None:
            logger.error("Interaction: {} is attempting to use the ReturnStolenObject basic extra on an object that doesn't have the stolen component.", self.interaction)
            return
        obj.remove_from_client(fade_duration=obj.FADE_DURATION)
        stolen_from_household_id = stolen_component.stolen_from_household_id
        household = services.household_manager().get(stolen_from_household_id)
        if household is not None:
            obj.set_household_owner_id(household.id)

            def on_reservation_change(*_, **__):
                if not obj.in_use:
                    obj.unregister_on_use_list_changed(on_reservation_change)
                    object_location_type = ObjectOriginLocation.SIM_INVENTORY if obj.is_in_sim_inventory else ObjectOriginLocation.ON_LOT
                    if not build_buy.move_object_to_household_inventory(obj, object_location_type=object_location_type):
                        obj.schedule_destroy_asap()

            if obj.in_use:
                obj.register_on_use_list_changed(on_reservation_change)
            elif not build_buy.move_object_to_household_inventory(obj):
                obj.schedule_destroy_asap()
        else:
            obj.make_transient()

class MarkObjectAsStolen(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': "\n            Element that adds the StolenComponent to the object, as well as\n            data from where it was stolen.\n            If it was stolen from a household, the Household ID will be stored,\n            so that the object can be returned to that household's inventory\n            if the player chooses to do so. See the ReturnStolenObject basic\n            extra for that functionality.\n            ", 'participant': TunableEnumEntry(description='\n            The participant of the interaction that will be marked as stolen.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    @staticmethod
    def mark_object_as_stolen(obj, stolen_from_text=None, stolen_from_career_guid=None):
        obj.add_dynamic_component(types.STOLEN_COMPONENT)
        obj.set_stolen_from_data(stolen_from_text=stolen_from_text, stolen_from_career_guid=stolen_from_career_guid)

    def _do_behavior(self):
        obj = self.interaction.get_participant(self.participant)
        if obj is None:
            return
        self.mark_object_as_stolen(obj)
