from animation.animation_utils import flush_all_animationsfrom carry.carry_elements import enter_carry_while_holdingfrom element_utils import build_critical_sectionfrom filters.sim_template import TunableSimTemplatefrom filters.tunable import TunableSimFilterfrom interactions import ParticipantType, ParticipantTypeActorTargetSim, ParticipantTypeSingleSim, ParticipantTypeSinglefrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects import VisibilityStatefrom objects.object_creation import ObjectCreationMixinfrom objects.slots import RuntimeSlotfrom sims.genealogy_tracker import genealogy_caching, FamilyRelationshipIndexfrom sims.pregnancy.pregnancy_tracker import PregnancyTrackerfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_spawner import SimSpawner, SimCreatorfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import TunableList, OptionalTunable, Tunable, TunableEnumEntry, TunableVariant, TunableFactory, TunableReference, HasTunableSingletonFactory, AutoFactoryInitfrom singletons import EMPTY_SET, DEFAULTfrom tag import Tagfrom venues.venue_constants import NPCSummoningPurposefrom world.spawn_actions import TunableSpawnActionVariantimport element_utilsimport id_generatorimport interactionsimport servicesimport sims.ghostimport sims4.logimport sims4.mathimport sims4.telemetryimport telemetry_helperlogger = sims4.log.Logger('Creation')TELEMETRY_GROUP_OBJECT = 'OBJC'TELEMETRY_HOOK_OBJECT_CREATE_BSCEXTRA = 'CRBE'TELEMETRY_FIELD_OBJECT_INTERACTION = 'intr'TELEMETRY_FIELD_OBJECT_DEFINITION = 'objc'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_OBJECT)
class ObjectCreationElement(XevtTriggeredElement, ObjectCreationMixin):
    FACTORY_TUNABLES = {'cancel_on_destroy': Tunable(description='\n            If checked, the interaction will be canceled if object is destroyed\n            due to placement failure or if destroy on placement failure is\n            unchecked and the fallback fails.\n            ', tunable_type=bool, default=True), 'transient': Tunable(description='\n            If checked, the created object will be destroyed when the interaction ends.\n            ', tunable_type=bool, default=False), 'set_to_invisible': Tunable(description='\n            If checked, the created object will be set to invisible when the \n            interaction ends.\n            ', tunable_type=bool, default=False)}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(interaction, *args, sequence=sequence, **kwargs)
        self._definition_cache = None
        self._placement_failed = False
        self.initialize_helper(interaction.get_resolver())

    @property
    def definition(self):
        if self._definition_cache is None:
            self._definition_cache = super().definition
        return self._definition_cache

    @property
    def placement_failed(self):
        return self._placement_failed

    def create_object_in_sequence(self):
        self._place_object(self._object_helper.object)
        if self._placement_failed:
            if self.cancel_on_destroy:
                self.interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='Cannot place object')
                return False
            return True
        if not self.transient:
            self._object_helper.claim()
        if self.set_to_invisible:
            self._object_helper.object.visibility = VisibilityState(False)
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_OBJECT_CREATE_BSCEXTRA) as hook:
            hook.write_enum(TELEMETRY_FIELD_OBJECT_INTERACTION, self.interaction.guid64)
            hook.write_guid(TELEMETRY_FIELD_OBJECT_DEFINITION, self.definition.id)
        return True

    def _setup_created_object(self, created_object):
        self.interaction.object_create_helper = self._object_helper
        super()._setup_created_object(created_object)

    def _place_object(self, created_object):
        place_object = super()._place_object(created_object)
        if not place_object:
            self._placement_failed = True
        return place_object

    def _build_outer_elements(self, sequence):

        def set_carry_target(_):
            self.interaction.track = DEFAULT
            self.interaction.map_create_target(self.interaction.created_target)

        def enter_carry(timeline):
            result = yield from element_utils.run_child(timeline, enter_carry_while_holding(self.interaction, obj=self.interaction.created_target, carry_track_override=self.location.carry_track_override, owning_affordance=None, sequence=build_critical_section(sequence, flush_all_animations)))
            return result

        location_type = getattr(self.location, 'location', None)
        if location_type == self.CARRY:
            return self._object_helper.create(set_carry_target, enter_carry)
        else:
            return self._object_helper.create(sequence)

    def _do_behavior(self):
        self.create_object_in_sequence()

class SimCreationElement(XevtTriggeredElement):

    class _ActiveHouseholdFactory(TunableFactory):

        @staticmethod
        def factory(_):
            return services.active_household()

        FACTORY_TYPE = factory

    class _ParticipantHouseholdFactory(TunableFactory):

        @staticmethod
        def factory(interaction, participant):
            sim = interaction.get_participant(participant)
            if sim is None:
                logger.error('_ParticipantHouseholdFactory: {} does not have participant {}', interaction, participant, owner='jjacobson')
                return
            return sim.household

        FACTORY_TYPE = factory

        def __init__(self, *args, **kwargs):
            super().__init__(participant=TunableEnumEntry(description='\n                    The participant that will have their household used to put the\n                    sim into.\n                    ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), **kwargs)

    class _NoHousheoldFactory(TunableFactory):

        @staticmethod
        def factory(_):
            pass

        FACTORY_TYPE = factory

    class _HiddenHouseholdFactory(TunableFactory):

        @staticmethod
        def factory(_):
            household = services.household_manager().create_household(services.get_first_client().account)
            household.set_to_hidden(family_funds=0)
            return household

        FACTORY_TYPE = factory

    class _BaseSimInfoSource(HasTunableSingletonFactory, AutoFactoryInit):

        def get_sim_infos_and_positions(self, resolver):
            raise NotImplementedError('Attempting to use the _BaseSimInfoSource base class, use sub-classes instead.')

        def _try_add_sim_info_to_household(self, sim_info, resolver, household, skip_household_check=False):
            if household is not None and (skip_household_check or household is not sim_info.household):
                if not household.can_add_sim_info(sim_info):
                    logger.warn('create_sim_from_sim_info element on the interaction: {} could not add a new sim to the tuned household.', resolver.interaction)
                    return False
                if sim_info.household is not household:
                    sim_info.household.remove_sim_info(sim_info)
                household.add_sim_info_to_household(sim_info)
            return True

        def do_pre_spawn_behavior(self, sim_info, resolver, household):
            self._try_add_sim_info_to_household(sim_info, resolver, household)

        def do_post_spawn_behavior(self, sim_info, resolver, client_manager):
            client = client_manager.get_client_by_household_id(sim_info.household_id)
            if client is not None:
                client.add_selectable_sim_info(sim_info)

    class _TargetedObjectResurrection(_BaseSimInfoSource):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The participant of the interaction against whom any relationship\n                and genealogy tunables are applied.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'sim_info_subject': TunableEnumEntry(description='\n                The subject from which the Sim Info used to create the new Sim\n                should be fetched.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object), 'resurrect': Tunable(description='\n                If checked, all Ghost traits are removed from the created Sim\n                and its death type is cleared.\n                \n                If unchecked, this is a simple spawn operation.\n                ', tunable_type=bool, default=True)}

        def get_sim_infos_and_positions(self, resolver, household):
            use_fgl = True
            stored_sim_info_object = resolver.get_participant(self.sim_info_subject)
            if stored_sim_info_object is None:
                return ()
            sim_info = stored_sim_info_object.get_stored_sim_info()
            if sim_info is None:
                return ()
            return ((sim_info, stored_sim_info_object.position, None, use_fgl),)

        def do_pre_spawn_behavior(self, sim_info, resolver, household):
            super().do_pre_spawn_behavior(sim_info, resolver, household)
            if self.resurrect:
                sims.ghost.Ghost.remove_ghost_from_sim(sim_info)

    class _MassObjectResurrection(_BaseSimInfoSource):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The participant of the interaction that will have sims resurrected\n                around their position.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'radius': TunableDistanceSquared(description='\n                The distance around a participant that will resurrect all of the\n                dead sim objects.\n                ', default=1), 'tag': TunableEnumEntry(description='\n                Tag the delineates an object that we want to resurrect sims\n                from.\n                ', tunable_type=Tag, default=Tag.INVALID)}

        def get_sim_infos_and_positions(self, resolver, household):
            use_fgl = True
            sim_infos_and_positions = []
            participant = resolver.get_participant(self.participant)
            position = participant.position
            for obj in services.object_manager().get_objects_with_tag_gen(self.tag):
                obj_position = obj.position
                distance_from_pos = obj_position - position
                if distance_from_pos.magnitude_squared() > self.radius:
                    pass
                else:
                    sim_info = obj.get_stored_sim_info()
                    if sim_info is None:
                        pass
                    else:
                        sim_infos_and_positions.append((sim_info, obj_position, None, use_fgl))
            return tuple(sim_infos_and_positions)

        def do_pre_spawn_behavior(self, sim_info, resolver, household):
            super().do_pre_spawn_behavior(sim_info, resolver, household)
            sims.ghost.Ghost.remove_ghost_from_sim(sim_info)

    class _SlotSpawningSimInfoSource(_BaseSimInfoSource):

        class _SlotByName(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'slot_name': Tunable(description='\n                    The exact name of a slot on the parent object.\n                    ', tunable_type=str, default='_ctnm_')}

            def get_slot_type_and_hash(self):
                return (None, sims4.hash_util.hash32(self.slot_name))

        class _SlotByType(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'slot_type': TunableReference(description='\n                    A particular slot type in which the should spawn.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))}

            def get_slot_type_and_hash(self):
                return (self.slot_type, None)

        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The participant that is a sim that will be cloned\n                Note: MUST be a sim. Use create object - clone object for non-sim objects.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'sim_spawn_slot': TunableVariant(description="\n                The slot on the parent object where the sim should spawn. This\n                may be either the exact name of a bone on the parent object or a\n                slot type, in which case the first empty slot of the specified type\n                will be used. If None is chosen, then the sim will at or near\n                the interaction target's location.\n                ", by_name=_SlotByName.TunableFactory(), by_type=_SlotByType.TunableFactory()), 'spawn_location_participant': TunableEnumEntry(description='\n                The participant used for finding where to spawn the Sim.  Typically you want to leave this as object.\n                \n                Special cases include:\n                - For self-interactions, Object will resolve to None.  This can be set to Actor if you want to spawn\n                near the Sim running the interaction.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

        def __init__(self, sim_spawn_slot=None, **kwargs):
            super().__init__(sim_spawn_slot=sim_spawn_slot, **kwargs)
            self._slot_type = None
            self._bone_name_hash = None
            if sim_spawn_slot is not None:
                (self._slot_type, self._bone_name_hash) = sim_spawn_slot.get_slot_type_and_hash()

        def _get_position_and_location(self, spawning_object, resolver):
            (position, location) = (None, None)
            if self._slot_type is not None:
                for runtime_slot in spawning_object.get_runtime_slots_gen(slot_types={self._slot_type}, bone_name_hash=self._bone_name_hash):
                    location = runtime_slot.location
            elif self._bone_name_hash is not None:
                runtime_slot = RuntimeSlot(spawning_object, self._bone_name_hash, EMPTY_SET)
                if runtime_slot is not None:
                    location = runtime_slot.location
            else:
                location = spawning_object.location
            if location is not None:
                location = sims4.math.Location(location.world_transform, spawning_object.routing_surface, slot_hash=location.slot_hash)
                position = location.transform.translation
            return (position, location)

        def _get_spawning_object(self, resolver):
            spawning_object = resolver.get_participant(self.spawn_location_participant)
            if spawning_object.is_sim:
                spawning_object = spawning_object.get_sim_instance()
            return spawning_object

    class _CloneSimInfoSource(_SlotSpawningSimInfoSource):
        FACTORY_TUNABLES = {'force_fgl': Tunable(description="\n                Normally, FGL will only be invoked if no spawning position is found.  Use this tunable to force\n                FGL to run. e.g. Cloning spell uses caster Sim's position as a spawning position.  In that case,\n                we still want to force FGL so the clone spawns near that Sim rather than directly on top of the Sim. \n                ", tunable_type=bool, default=False)}

        def _ensure_parental_lineage_exists(self, source_sim_info, clone_sim_info):
            with genealogy_caching():
                if any(source_sim_info.genealogy.get_parent_sim_ids_gen()):
                    return
                mom_id = id_generator.generate_object_id()
                source_sim_info.genealogy.set_family_relation(FamilyRelationshipIndex.MOTHER, mom_id)
                clone_sim_info.genealogy.set_family_relation(FamilyRelationshipIndex.MOTHER, mom_id)
                sim_info_manager = services.sim_info_manager()
                for child_sim_id in source_sim_info.genealogy.get_children_sim_ids_gen():
                    child_sim_info = sim_info_manager.get(child_sim_id)
                    if child_sim_info is not None:
                        grandparent_relation = FamilyRelationshipIndex.MOTHERS_MOM if source_sim_info.is_female else FamilyRelationshipIndex.FATHERS_MOM
                        child_sim_info.genealogy.set_family_relation(grandparent_relation, mom_id)

        def _create_clone_sim_info(self, source_sim_info, resolver, household):
            sim_creator = SimCreator(gender=source_sim_info.gender, age=source_sim_info.age, first_name=SimSpawner.get_random_first_name(source_sim_info.gender, source_sim_info.species), last_name=source_sim_info._base.last_name, traits=source_sim_info.trait_tracker.equipped_traits)
            (sim_info_list, _) = SimSpawner.create_sim_infos((sim_creator,), household=household, account=source_sim_info.account, generate_deterministic_sim=True, creation_source='cloning', skip_adding_to_household=True)
            clone_sim_info = sim_info_list[0]
            source_sim_proto = source_sim_info.save_sim(for_cloning=True)
            clone_sim_id = clone_sim_info.sim_id
            clone_first_name = clone_sim_info._base.first_name
            clone_last_name = clone_sim_info._base.last_name
            clone_breed_name = clone_sim_info._base.breed_name
            clone_first_name_key = clone_sim_info._base.first_name_key
            clone_last_name_key = clone_sim_info._base.last_name_key
            clone_full_name_key = clone_sim_info._base.full_name_key
            clone_breed_name_key = clone_sim_info._base.breed_name_key
            clone_sim_info.load_sim_info(source_sim_proto, is_clone=True, default_lod=SimInfoLODLevel.FULL)
            clone_sim_info.sim_id = clone_sim_id
            clone_sim_info._base.first_name = clone_first_name
            clone_sim_info._base.last_name = clone_last_name
            clone_sim_info._base.breed_name = clone_breed_name
            clone_sim_info._base.first_name_key = clone_first_name_key
            clone_sim_info._base.last_name_key = clone_last_name_key
            clone_sim_info._base.full_name_key = clone_full_name_key
            clone_sim_info._base.breed_name_key = clone_breed_name_key
            clone_sim_info._household_id = household.id
            if not self._try_add_sim_info_to_household(clone_sim_info, resolver, household, skip_household_check=True):
                return
            source_trait_tracker = source_sim_info.trait_tracker
            clone_trait_tracker = clone_sim_info.trait_tracker
            for trait in clone_trait_tracker.personality_traits:
                if not source_trait_tracker.has_trait(trait):
                    clone_sim_info.remove_trait(trait)
            for trait in clone_trait_tracker.gender_option_traits:
                if not source_trait_tracker.has_trait(trait):
                    clone_sim_info.remove_trait(trait)
            correct_aspiration_trait = clone_sim_info.primary_aspiration.primary_trait
            for trait in tuple(clone_trait_tracker.aspiration_traits):
                if trait is not correct_aspiration_trait:
                    clone_sim_info.remove_trait(trait)
            source_sim_info.relationship_tracker.create_relationship(clone_sim_info.sim_id)
            source_sim_info.relationship_tracker.add_relationship_score(clone_sim_info.sim_id, 1)
            self._ensure_parental_lineage_exists(source_sim_info, clone_sim_info)
            services.sim_info_manager().set_default_genealogy(sim_infos=(clone_sim_info,))
            clone_sim_info.set_default_data()
            clone_sim_info.save_sim()
            household.save_data()
            if not household.is_active_household:
                clone_sim_info.request_lod(SimInfoLODLevel.BASE)
            clone_sim_info.resend_physical_attributes()
            clone_sim_info.relationship_tracker.clean_and_send_remaining_relationship_info()
            return clone_sim_info

        def do_pre_spawn_behavior(self, sim_info, resolver, household):
            pass

        def get_sim_infos_and_positions(self, resolver, household):
            use_fgl = False
            sim_info = resolver.get_participant(self.participant)
            clone_sim_info = self._create_clone_sim_info(sim_info, resolver, household)
            if clone_sim_info is None:
                return ()
            (position, location) = (None, None)
            spawning_object = self._get_spawning_object(resolver)
            if spawning_object is not None:
                (position, location) = self._get_position_and_location(spawning_object, resolver)
                use_fgl = self.force_fgl or position is None
            return ((clone_sim_info, position, location, use_fgl),)

        def do_post_spawn_behavior(self, sim_info, resolver, client_manager):
            super().do_post_spawn_behavior(sim_info, resolver, client_manager)
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=True)

    class _SimFilterSimInfoSource(_SlotSpawningSimInfoSource):
        FACTORY_TUNABLES = {'filter': TunableSimFilter.TunableReference(description='\n                Sim filter that is used to create or find a Sim that matches\n                this filter request.\n                ')}

        def get_sim_filter_gsi_name(self):
            return str(self)

        def get_sim_infos_and_positions(self, resolver, household):
            use_fgl = True
            sim_info = resolver.get_participant(self.participant)
            filter_result = services.sim_filter_service().submit_matching_filter(sim_filter=self.filter, requesting_sim_info=sim_info, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
            if not filter_result:
                return ()
            (position, location) = (None, None)
            spawning_object = self._get_spawning_object(resolver)
            if spawning_object is not None:
                (position, location) = self._get_position_and_location(spawning_object, resolver)
                use_fgl = position is None
            return ((filter_result[0].sim_info, position, location, use_fgl),)

    class _SimTemplateSimInfoSource(_SlotSpawningSimInfoSource):
        FACTORY_TUNABLES = {'template': TunableSimTemplate.TunableReference(description='\n                The template to use.\n                ')}

        def get_sim_infos_and_positions(self, resolver, household):
            sim_creator = self.template.sim_creator
            (sim_info_list, _) = SimSpawner.create_sim_infos((sim_creator,), household=household)
            self.template.add_template_data_to_sim(sim_info_list[0], sim_creator=sim_creator)
            (position, location) = (None, None)
            spawning_object = self._get_spawning_object(resolver)
            if spawning_object is not None:
                (position, location) = self._get_position_and_location(spawning_object, resolver)
                use_fgl = position is None
            return ((sim_info_list[0], position, location, use_fgl),)

    class _GenalogySetAsChild(HasTunableSingletonFactory):

        def __call__(self, actor_sim_info, created_sim_info):
            created_sim_info.last_name = SimSpawner.get_last_name(actor_sim_info.last_name, created_sim_info.gender, created_sim_info.species)
            parent_a = actor_sim_info
            parent_b = services.sim_info_manager().get(parent_a.spouse_sim_id)
            created_sim_info.relationship_tracker.destroy_all_relationships()
            for relation in FamilyRelationshipIndex:
                relation_id = created_sim_info.get_relation(relation)
                relation_info = services.sim_info_manager().get(relation_id)
                if relation_info is not None:
                    created_sim_info.genealogy.remove_family_link(relation)
                    family_relation = relation_info.genealogy.get_family_relationship_bit(created_sim_info.sim_id)
                    relation_info.genealogy.clear_family_relation(family_relation)
                    relation_info.relationship_tracker.destroy_relationship(created_sim_info.sim_id)
                created_sim_info.genealogy.clear_family_relation(relation)
            PregnancyTracker.initialize_sim_info(created_sim_info, parent_a, parent_b)

    FACTORY_TUNABLES = {'sim_info_source': TunableVariant(description='\n            The source of the sim_info and position data for the sims to be\n            created.\n            ', targeted=_TargetedObjectResurrection.TunableFactory(), mass_object=_MassObjectResurrection.TunableFactory(), clone_a_sim=_CloneSimInfoSource.TunableFactory(), sim_filter=_SimFilterSimInfoSource.TunableFactory(), sim_template=_SimTemplateSimInfoSource.TunableFactory(), default='targeted'), 'household_option': TunableVariant(description='\n            The household that the created sim should be put into.\n            ', active_household=_ActiveHouseholdFactory(), participant_household=_ParticipantHouseholdFactory(), no_household=_NoHousheoldFactory(), hidden_household=_HiddenHouseholdFactory(), default='participant_household'), 'spawn_action': TunableSpawnActionVariant(description='\n            Define the methods to show the Sim after spawning on the lot. This\n            defaults to fading the Sim in, but can be a specific interaction or\n            an animation.\n            '), 'relationship_bits_to_add': TunableList(description='\n            A list of relationship bits to add between the source sim\n            and the created sim.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT))), 'set_summoning_purpose': OptionalTunable(description="\n            If enabled this will trigger the summon NPC situation depending\n            on the summoning purpose type set.  This should be tuned when\n            we create Sims and don't add them into the active household.\n            ", tunable=TunableEnumEntry(description='\n                The purpose that is used to summon the sim to the lot.  \n                Defined in venue tuning.\n                ', tunable_type=NPCSummoningPurpose, default=NPCSummoningPurpose.DEFAULT)), 'set_genealogy': TunableVariant(description='\n            Genealogy option to set on the created Sim.   \n            Example: Setting a child of a family.\n            ', set_as_child=_GenalogySetAsChild.TunableFactory(), locked_args={'no_action': None}, default='no_action')}

    def _apply_relationship_bits(self, actor_sim_info, created_sim_info):
        for rel_bit in self.relationship_bits_to_add:
            actor_sim_info.relationship_tracker.add_relationship_bit(created_sim_info.sim_id, rel_bit, force_add=True)

    def _do_behavior(self):
        resolver = self.interaction.get_resolver()
        target_participant = resolver.get_participant(self.sim_info_source.participant)
        household = self.household_option(self.interaction)
        client_manager = services.client_manager()
        for (sim_info, position, location, use_fgl) in self.sim_info_source.get_sim_infos_and_positions(resolver, household):
            if target_participant is not None:
                self._apply_relationship_bits(target_participant, sim_info)
            self.sim_info_source.do_pre_spawn_behavior(sim_info, resolver, household)
            SimSpawner.spawn_sim(sim_info, position, spawn_action=self.spawn_action, sim_location=location, use_fgl=use_fgl)
            if self.set_summoning_purpose is not None:
                services.current_zone().venue_service.venue.summon_npcs((sim_info,), self.set_summoning_purpose)
            if self.set_genealogy is not None and target_participant is not None:
                self.set_genealogy(target_participant, sim_info)
            self.sim_info_source.do_post_spawn_behavior(sim_info, resolver, client_manager)
        return True
