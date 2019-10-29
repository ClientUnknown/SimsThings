from element_utils import build_elementfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.base.super_interaction import SuperInteractionfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom interactions.utils.interaction_liabilities import CancelInteractionsOnExitLiability, CANCEL_INTERACTION_ON_EXIT_LIABILITYfrom interactions.utils.loot import LootOperationList, LootActionsfrom interactions.utils.tunable import SaveLockLiabilityfrom objects.slots import SlotTypefrom objects.system import create_objectfrom sims.baby.baby_tuning import BabyTuningfrom sims.baby.baby_utils import assign_bassinet_for_baby, create_and_place_baby, set_baby_sim_info_with_switch_idfrom sims.pregnancy.pregnancy_tuning import PregnancyTuningfrom sims.sim_info_types import Agefrom sims.sim_spawner import SimSpawnerfrom sims4.tuning.tunable import TunableReference, TunableEnumEntry, TunableList, TunablePackSafeReference, TunableTuple, OptionalTunablefrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_element import UiDialogElementfrom ui.ui_dialog_rename import RenameDialogElementfrom vfx import PlayEffectfrom world.travel_tuning import TravelSimLiability, TRAVEL_SIM_LIABILITYimport element_utilsimport interactionsimport servicesimport sims4logger = sims4.log.Logger('Pregnancy', default_owner='epanero')
class NameOffspringSuperInteractionMixin:

    def _get_name_dialog(self):
        raise NotImplementedError

    def _do_renames_gen(self, timeline, all_offspring, additional_tokens=()):
        offspring_index = 0
        while offspring_index < len(all_offspring):
            offspring_data = all_offspring[offspring_index]
            dialog = self._get_name_dialog()
            rename_element = RenameDialogElement(dialog, offspring_data, additional_tokens=additional_tokens)
            result = yield from element_utils.run_child(timeline, rename_element)
            if not result:
                self.cancel(FinishingType.DIALOG, cancel_reason_msg='Time out or missing first/last name')
                return False
            offspring_index += 1
        return True

class DeliverBabySuperInteraction(SuperInteraction, NameOffspringSuperInteractionMixin):
    INSTANCE_TUNABLES = {'inherited_loots': OptionalTunable(description='\n             If enabled, these loots will be applied to the baby if the parents\n             passed the test.\n             ', tunable=TunableList(description='\n                 List of loot given to the child based on the tests on the parents.\n                 ', tunable=TunableTuple(description='\n                     Tuple of tests on parents to loots given to children.\n                     ', birther_test=TunableTestSet(description='\n                        Test to run on the sim giving birth. \n                        '), non_birther_test=TunableTestSet(description='\n                        Test to run on the sim not giving birth. \n                        '), child_loot=TunableList(description='\n                        A list of loots to apply when both parents pass their tests.\n                        Actor = birther sim\n                        Target = baby\n                        ', tunable=LootActions.TunableReference(pack_safe=True)))))}

    def _get_name_dialog(self):
        data = PregnancyTuning.get_pregnancy_data(self.sim)
        return data.dialog(self.sim, resolver=SingleSimResolver(self.sim))

    def _build_outcome_sequence(self, *args, **kwargs):
        sequence = super()._build_outcome_sequence(*args, **kwargs)
        pregnancy_tracker = self.sim.sim_info.pregnancy_tracker
        return element_utils.must_run(element_utils.build_critical_section_with_finally(self._name_and_create_babies_gen, sequence, lambda _: pregnancy_tracker.clear_pregnancy()))

    def _name_and_create_babies_gen(self, timeline):
        pregnancy_tracker = self.sim.sim_info.pregnancy_tracker
        if not pregnancy_tracker.is_pregnant:
            return False
        pregnancy_tracker.create_offspring_data()
        if not self.sim.is_npc:
            result = yield from self._do_renames_gen(timeline, list(pregnancy_tracker.get_offspring_data_gen()))
            if not result:
                return result
        else:
            pregnancy_tracker.assign_random_first_names_to_offspring_data()
        result = yield from self._complete_pregnancy_gen(timeline, pregnancy_tracker)
        return result

    def _reset_actor_in_asms(self, target, actor_name):
        animation_context = self.animation_context
        if animation_context is not None:
            for asm in animation_context.get_asms_gen():
                asm.set_actor(actor_name, None)
                asm.set_actor(actor_name, target)

    def _create_new_bassinet_with_baby(self, pregnancy_tracker, offspring_data, empty_bassinet):
        sim_info = pregnancy_tracker.create_sim_info(offspring_data)
        new_bassinet = set_baby_sim_info_with_switch_id(empty_bassinet, sim_info)
        return new_bassinet

    def _create_additional_babies(self, pregnancy_tracker, extra_baby_list, position=None, routing_surface=None, create_bassinet=True):
        created_sim_infos = []
        for offspring_data in extra_baby_list:
            sim_info = pregnancy_tracker.create_sim_info(offspring_data)
            created_sim_infos.append(sim_info)
            if assign_bassinet_for_baby(sim_info) or create_bassinet:
                create_and_place_baby(sim_info, position=position, routing_surface=routing_surface)
        return created_sim_infos

    def _create_non_baby_offspring(self, pregnancy_tracker, offspring_data_list, target):
        created_sim_infos = []
        for offspring_data in offspring_data_list:
            sim_info = pregnancy_tracker.create_sim_info(offspring_data)
            created_sim_infos.append(sim_info)
            SimSpawner.spawn_sim(sim_info, target.position, sim_location=target.location)
        return tuple(created_sim_infos)

    def _handle_show_baby_in_bassinet(self, animation_context, bassinet):
        if animation_context is not None:

            def on_show_baby(_):
                bassinet.enable_baby_state()

            bassinet.empty_baby_state()
            self.store_event_handler(on_show_baby, handler_id=100)

    def _handle_hide_pregnant_sims_belly(self, animation_context, pregnancy_tracker):
        if animation_context is not None:

            def on_hide_belly(_):
                pregnancy_tracker.clear_pregnancy_visuals()

            self.store_event_handler(on_hide_belly, handler_id=101)

    def _complete_pregnancy_gen(self, timeline, pregnancy_tracker):
        offspring_data_list = list(pregnancy_tracker.get_offspring_data_gen())
        pregnant_sim = pregnancy_tracker._sim_info
        is_bassinet_birth = pregnant_sim.get_birth_age() == Age.BABY
        if is_bassinet_birth:
            new_target = self._create_new_bassinet_with_baby(pregnancy_tracker, offspring_data_list[0], self.target)
            self._reset_actor_in_asms(new_target, 'bassinet')
            self.target.transient = True
            self.set_target(new_target)
            self._handle_show_baby_in_bassinet(self.animation_context, new_target)
            sim_infos = self._create_additional_babies(pregnancy_tracker, offspring_data_list[1:])
            sim_infos.append(new_target.sim_info)
        else:
            sim_infos = self._create_non_baby_offspring(pregnancy_tracker, offspring_data_list, self.sim)
        self._handle_hide_pregnant_sims_belly(self.animation_context, pregnancy_tracker)
        if pregnant_sim.is_npc or self.inherited_loots:
            self._apply_inherited_loots(sim_infos, pregnancy_tracker)
        pregnancy_tracker.complete_pregnancy()
        return True

    def _apply_inherited_loots(self, sim_infos, pregnancy_tracker):
        inherited_loots = self.inherited_loots
        if not inherited_loots:
            return
        (birther, non_birther) = pregnancy_tracker.get_parents()
        for inherited_loot in inherited_loots:
            if birther and not inherited_loot.birther_test.run_tests(SingleSimResolver(birther)):
                pass
            elif non_birther and not inherited_loot.non_birther_test.run_tests(SingleSimResolver(non_birther)):
                pass
            else:
                for sim_info in sim_infos:
                    resolver = DoubleSimResolver(self.sim.sim_info, sim_info)
                    for individual_loot in inherited_loot.child_loot:
                        individual_loot.apply_to_resolver(resolver)

class HaveBabyAtHospitalInteraction(DeliverBabySuperInteraction):
    INSTANCE_TUNABLES = {'partner_affordance': TunableReference(description='\n             When the Pregnant Sim leaves the lot to give birth, this is the affordance \n             that will get pushed on the other Sim involved with the pregnancy if\n             there is one and the Sim is on lot.\n             ', manager=services.affordance_manager()), 'off_lot_birth_dialog': UiDialogOkCancel.TunableFactory(description='\n            This dialog informs the player that the babies are on the home lot\n            and they can follow the birthing Sim to their home lot. We always\n            display this, even if the birthing Sim is not the last selectable\n            one on the lot.\n            ')}

    def _pre_perform(self, *args, **kwargs):
        self.add_liability(interactions.rabbit_hole.RABBIT_HOLE_LIABILTIY, interactions.rabbit_hole.RabbitHoleLiability(self))
        return super()._pre_perform(*args, **kwargs)

    def _complete_pregnancy_gen(self, timeline, pregnancy_tracker):
        is_off_lot_birth = False
        baby_sim_infos = []
        for offspring_data in pregnancy_tracker.get_offspring_data_gen():
            sim_info = pregnancy_tracker.create_sim_info(offspring_data)
            current_zone = services.current_zone()
            if current_zone.id == sim_info.zone_id:
                services.daycare_service().exclude_sim_from_daycare(sim_info)
                if not assign_bassinet_for_baby(sim_info):
                    create_and_place_baby(sim_info)
            else:
                is_off_lot_birth = True
            baby_sim_infos.append(sim_info)
        offspring_count = pregnancy_tracker.offspring_count
        pregnancy_tracker.complete_pregnancy()
        self._apply_inherited_loots(baby_sim_infos, pregnancy_tracker)
        if is_off_lot_birth:
            travel_liability = TravelSimLiability(self, self.sim.sim_info, self.sim.sim_info.household.home_zone_id, expecting_dialog_response=True)
            self.add_liability(TRAVEL_SIM_LIABILITY, travel_liability)

            def on_travel_dialog_response(dialog):
                if dialog.accepted:
                    if self.outcome is not None:
                        loot = LootOperationList(self.get_resolver(), self.outcome.get_loot_list())
                        loot.apply_operations()
                    save_lock_liability = self.get_liability(SaveLockLiability.LIABILITY_TOKEN)
                    if save_lock_liability is not None:
                        save_lock_liability.release()
                    travel_liability.travel_dialog_response(dialog)

            travel_dialog_element = UiDialogElement(self.sim, self.get_resolver(), dialog=self.off_lot_birth_dialog, on_response=on_travel_dialog_response, additional_tokens=(offspring_count,))
            result = yield from element_utils.run_child(timeline, travel_dialog_element)
            return result
        return True

    def prepare_gen(self, timeline, *args, **kwargs):
        result = yield from super().prepare_gen(timeline, *args, **kwargs)
        if result != InteractionQueuePreparationStatus.FAILURE:
            self._push_spouse_to_hospital()
        return result

    def _push_spouse_to_hospital(self):
        pregnancy_tracker = self.sim.sim_info.pregnancy_tracker
        sim_info = None
        (parent_a, parent_b) = pregnancy_tracker.get_parents()
        if parent_b is not None:
            if parent_a.sim_id == self.sim.sim_id:
                sim_info = parent_b
            else:
                sim_info = parent_a
        if parent_a is not None and sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        if sim.queue.has_duplicate_super_affordance(self.partner_affordance, sim, None):
            return
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High)
        result = sim.push_super_affordance(self.partner_affordance, sim, context)
        if result:
            interaction = result.interaction
            interaction.add_liability(interactions.rabbit_hole.RABBIT_HOLE_LIABILTIY, interactions.rabbit_hole.RabbitHoleLiability(interaction))
            liability = CancelInteractionsOnExitLiability()
            self.add_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY, liability)
            liability.add_cancel_entry(parent_b, interaction)
        return result
CLEANUP_INTERACTION_CALLBACK_LIABILITY = 'CleanupInteractionCallbackLiability'
class CleanupInteractionCallbackLiability(Liability):

    def __init__(self, *args, cleanup_interaction_callback, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleanup_interaction_callback = cleanup_interaction_callback

    def release(self):
        self.cleanup_interaction_callback()

    def should_transfer(self):
        return False

class DeliverBabyOnSurgeryTableInteraction(DeliverBabySuperInteraction):
    INSTANCE_TUNABLES = {'bassinet_to_use': TunableReference(description='\n            Bassinet with Baby object definition id.\n            ', manager=services.definition_manager()), 'bassinet_slot_type': SlotType.TunableReference(description='\n            SlotType used to place the bassinet when it is created.\n            '), 'surgery_table_participant_type': TunableEnumEntry(description='\n            A reference to the ParticipantType that the surgery table will be\n            in this interaction.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), '_loot_per_baby': TunableList(description='\n            Loot that will be applied when a baby is born to a non NPC Sim. \n            Actor will be the mom and TargetSim will be the sim_info of the baby.\n            This will work for multiple babies as each loot will be applied to \n            each baby sim info.\n            \n            None of these loots will be applied to a baby born to an NPC Sim.\n            ', tunable=LootActions.TunableReference(pack_safe=True)), 'destroy_baby_in_bassinet_vfx': PlayEffect.TunableFactory(description='\n            The VFX to play when the baby is being destroyed during an NPC \n            birth sequence.\n            '), 'after_delivery_interaction': TunablePackSafeReference(description='\n            The interaction to push on the Sim after delivering a baby at the\n            hospital.\n            ', manager=services.affordance_manager(), allow_none=True)}
    FADE_BASSINET_EVENT_TAG = 201
    DESTROY_BASSINET_EVENT_TAG = 202

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_exit_function(self._destroy_sim_info_if_neccesary)
        self._bassinet = None
        self._baby_object = None

    def _pre_perform(self, *args, **kwargs):
        bassinet_def = BabyTuning.get_corresponding_definition(self.bassinet_to_use)
        self._bassinet = create_object(bassinet_def)
        surgery_table = self.get_participant(self.surgery_table_participant_type)
        if surgery_table is None:
            logger.error('No surgery table found for {}', self, owner='tastle')
            return False
        surgery_table.part_owner.slot_object(self.bassinet_slot_type, self._bassinet)
        return True

    def _build_outcome_sequence(self):
        sequence = super()._build_outcome_sequence()
        return build_element((self._handle_npc_bassinet_fade_and_effect, sequence))

    def _handle_npc_bassinet_fade_and_effect(self, timeline):
        if self.sim.is_npc:

            def _fade_bassinet(_):
                if self._baby_object is not None:
                    self._baby_object.fade_out()
                    effect = self.destroy_baby_in_bassinet_vfx(self._baby_object)
                    effect.start_one_shot()

            self.store_event_handler(_fade_bassinet, handler_id=self.FADE_BASSINET_EVENT_TAG)

    def _destroy_sim_info_if_neccesary(self):
        if self.sim.is_npc and self._baby_object is not None:
            baby_sim_info = self._baby_object.sim_info
            if self._parent_is_playable(baby_sim_info):
                baby_sim_info.inject_into_inactive_zone(baby_sim_info.household.home_zone_id)
            else:
                baby_sim_info.remove_permanently(household=baby_sim_info.household)

    def _parent_is_playable(self, sim_info):
        for parent_info in sim_info.genealogy.get_parent_sim_infos_gen():
            if parent_info is not None and parent_info.is_player_sim:
                return True
        return False

    def _complete_pregnancy_gen(self, timeline, pregnancy_tracker):
        offspring_data_list = list(pregnancy_tracker.get_offspring_data_gen())
        new_baby = self._create_new_bassinet_with_baby(pregnancy_tracker, offspring_data_list[0], self._bassinet)
        self._bassinet.destroy()
        self._bassinet = None
        self._reset_actor_in_asms(new_baby, 'bassinet')
        self.interaction_parameters['created_target_id'] = new_baby.id
        self._baby_object = new_baby
        sim_infos = []
        if self.sim.is_npc and self._parent_is_playable(new_baby.sim_info):
            sim_infos = self._create_additional_babies(pregnancy_tracker, offspring_data_list[1:], position=new_baby.position, routing_surface=new_baby.routing_surface, create_bassinet=not self.sim.is_npc)
        sim_infos.append(new_baby.sim_info)
        if not self.sim.is_npc:
            self._apply_per_baby_loot(sim_infos)
            self._apply_inherited_loots(sim_infos, pregnancy_tracker)
            self._push_post_delivery_interaction(sim_infos)
        pregnancy_tracker.complete_pregnancy()
        return True

    def _push_post_delivery_interaction(self, sim_infos):
        if self._baby_object is not None and self.after_delivery_interaction is not None:

            def _destroy_all_bassinets():
                for sim_info in sim_infos:
                    bassinet_object = services.object_manager().get(sim_info.sim_id)
                    if bassinet_object is not None:
                        bassinet_object.make_transient()

            liabilities = ((CLEANUP_INTERACTION_CALLBACK_LIABILITY, CleanupInteractionCallbackLiability(cleanup_interaction_callback=_destroy_all_bassinets)),)
            context = self.context.clone_for_continuation(self)
            self.sim.push_super_affordance(self.after_delivery_interaction, self._baby_object, context, liabilities=liabilities)

    def _apply_per_baby_loot(self, sim_infos):
        for sim_info in sim_infos:
            resolver = DoubleSimResolver(self.sim.sim_info, sim_info)
            for loot in self._loot_per_baby:
                loot.apply_to_resolver(resolver)
