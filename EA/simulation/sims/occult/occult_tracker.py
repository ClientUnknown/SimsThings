import randomfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom algos import count_bitsfrom bucks.bucks_enums import BucksTypefrom cas.cas import generate_occult_siminfofrom distributor.rollback import ProtocolBufferRollbackfrom routing import SurfaceTypefrom sims.occult.occult_enums import OccultTypefrom sims.occult.occult_tuning import OccultTuningfrom sims.outfits.outfit_enums import REGULAR_OUTFIT_CATEGORIES, HIDDEN_OUTFIT_CATEGORIES, BodyTypeFlag, OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Agefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, TunableReference, Tunable, TunablePackSafeReference, TunableSet, OptionalTunablefrom sims4.tuning.tunable_base import ExportModesfrom traits.traits import Traitimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Occult Tracker', default_owner='trevor')
class OccultTracker:
    OCCULT_DATA = TunableMapping(description="\n        A mapping of occult types to data that affect a Sim's behavior.\n        ", key_type=TunableEnumEntry(description='\n            The occult type that this entry applies to.\n            ', tunable_type=OccultType, default=OccultType.HUMAN), value_type=TunableTuple(description='\n            Occult data specific to this occult type.\n            ', fallback_outfit_category=TunableEnumEntry(description='\n                The outfit category to default to when the sim changes occult forms\n                and is unable to stay in the same outfit.\n                ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY), occult_trait=Trait.TunableReference(description='\n                The trait that all Sims that have this occult are equipped with.\n                ', pack_safe=True), current_occult_trait=OptionalTunable(description='\n                If enabled then this occult will have an alternate form controlled by a trait.\n                ', tunable=Trait.TunableReference(description='\n                    That trait that all Sims currently in this occult are equipped\n                    with.\n                    ', pack_safe=True)), part_occult_trait=Trait.TunableReference(description='\n                If not None, this allows the tuning of a trait to identify \n                a Sim that is partly this occult.\n                The trait that identifies a Sim that is partly occult. For any\n                part occult trait, we will apply genetics that are half occult\n                and half non-occult.\n                ', allow_none=True, pack_safe=True), additional_occult_traits=TunableSet(description="\n                A list of traits that will also be applied to a Sim of this\n                occult type. These will only be applied if this Sim is the full\n                occult type and not just a partial occult. It also doesn't\n                matter if they are in their current occult form or not. These\n                traits will be applied regardless.\n                ", tunable=Trait.TunableReference(pack_safe=True)), add_current_occult_trait_to_babies=Tunable(description='\n                If True, babies will automatically be given the tuned Current\n                Occult Trait when the tuned Occult Trait is added to them. This\n                is currently only meant for aliens.\n                ', tunable_type=bool, default=True), generate_new_human_form_on_add=Tunable(description='\n                If True, humans being given this occult for the first time will\n                have a new human form generated for them (i.e. Aliens need a new\n                human form when they change to an alien). If false, their\n                human/base form will remain the same (i.e. Vampires should\n                remain similar in appearance).\n                ', tunable_type=bool, default=True), primary_buck_type=TunableEnumEntry(description='\n                The primary buck type for this occult. For example, this is \n                "Powers" for vampires.\n                ', tunable_type=BucksType, default=BucksType.INVALID, pack_safe=True), secondary_buck_type=TunableEnumEntry(description='\n                The secondary buck type for this occult. For example, this is \n                "Weaknesses" for vampires.\n                ', tunable_type=BucksType, default=BucksType.INVALID, pack_safe=True), experience_statistic=TunableReference(description='\n                    A reference to a ranked statistic to be used for tracking\n                    the experience and level/ranking up.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',), pack_safe=True, allow_none=True), cas_add_occult_tooltip=TunableLocalizedString(description='\n                This is the tooltip shown on the cas add occult button\n                ', allow_none=True), cas_alternative_form_add_tooltip=TunableLocalizedString(description='\n                This is the tooltip shown on the cas add alternaive form button\n                ', allow_none=True), cas_alternative_form_delete_tooltip=TunableLocalizedString(description='\n                This is the tooltip shown on the cas delete alternaive form button\n                ', allow_none=True), cas_alternative_form_delete_confirmation=TunableLocalizedString(description='\n                This is the text shown in the dialog when deleting the alternative form\n                ', allow_none=True), cas_alternative_form_sim_name_tooltip=TunableLocalizedString(description='\n                This is the tooltip shown on the cas sim skewer alternative form icon\n                ', allow_none=True), cas_alternative_form_copy_tooltip=TunableLocalizedString(description="\n                This is the tooltip shown on the cas copy to alternative form\n                button. If this is None, it is assumed the player shouldn't be\n                able to copy from their base form into their alternative form.\n                ", allow_none=True), cas_base_form_copy_tooltip=TunableLocalizedString(description="\n                This is the tooltip shown on the cas copy to base form button.\n                If this is None, it is assumed the player shouldn't be able to\n                copy from their alternative form into their base form.\n                ", allow_none=True), cas_base_form_link_tooltip=TunableLocalizedString(description='\n                The tooltip shown in CAS when the base form is selected.\n                ', allow_none=True), cas_alternative_form_link_tooltip=TunableLocalizedString(description='\n                The tooltip shown in CAS when the alternative form is selected.\n                ', allow_none=True), cas_alternative_form_copy_options_heading=TunableLocalizedString(description='\n                This is the header text shown on the cas copy to alternative form options panel\n                ', allow_none=True), cas_disabled_while_in_alternative_form_tooltip=TunableLocalizedString(description='\n                This is the tooltip shown on any cas panels that are disabled\n                when editing the occult alternative form\n                ', allow_none=True), cas_molecule_disabled_while_in_alternative_form_tooltip=TunableLocalizedString(description="\n                This is the tooltip shown on the molecule when it's disabled due\n                to the current Sim being in their alternate occult form.\n                ", allow_none=True), cas_default_to_alternative_form=Tunable(description='\n                If checked, this occult type will default to their alternative\n                form when first added to CAS. If left unchecked, the Sim will\n                default to their base form like usual.\n                ', tunable_type=bool, default=False), cas_can_delete_alternative_form=Tunable(description="\n                If checked, the Sim's alternative form can be deleted in CAS. If\n                unchecked, the alternative form can't be deleted. If the Occult \n                doesn't have an alternative form, this is ignored.\n                ", tunable_type=bool, default=False), cas_invalid_age_warning_title=TunableLocalizedString(description='\n                The title for the dialog when an occult Sim attempts to enter an \n                invalid age (i.e. aging a Vampire down to child).\n                ', allow_none=True), cas_invalid_age_warning_body=TunableLocalizedString(description='\n                The body text for the dialog when an occult Sim attempts to enter an \n                invalid age (i.e. aging a Vampire down to child).\n                ', allow_none=True), min_age_for_occult_ui=TunableEnumEntry(description='\n                The minimum age a sim can be in order for occult-specific UI to \n                be used.\n                ', tunable_type=Age, default=Age.BABY), export_class_name='OccultTrackerItem'), export_modes=ExportModes.All, tuple_name='OccultDataTuple')
    VAMPIRE_DAYWALKER_PERK = TunableTuple(description='\n        Perks for daywalker vampire Sim.\n        ', trait=TunablePackSafeReference(description='\n            Trait for vampire.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), perk=TunablePackSafeReference(description='\n            Buck type for the daywalker vampire.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)))

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._sim_info_map = dict()
        self._pending_occult_type = None
        self._occult_form_available = True

    def __repr__(self):
        return '<OccultTracker: {} ({}) @{}>'.format(str(self._sim_info), self._sim_info.occult_types, self._sim_info.current_occult_types)

    @classmethod
    def get_fallback_outfit_category(cls, occult_type):
        if occult_type == OccultType.HUMAN:
            return OutfitCategory.EVERYDAY
        return cls.OCCULT_DATA[occult_type].fallback_outfit_category

    @property
    def sim_info(self):
        return self._sim_info

    @property
    def is_occult_form_available(self):
        return self._occult_form_available

    def add_occult_type(self, occult_type):
        if not self.has_occult_type(occult_type):
            self._sim_info.occult_types |= occult_type
            self._update_occult_traits()

    def add_occult_for_premade_sim(self, occult_sim_info, occult_type):
        if self._sim_info_map:
            logger.error('Trying to add occult data for premade sim, {}, but the sim already has occult sim infos in the sim info map of their occult tracker. Data might be lost here!', self._sim_info)
            self._sim_info_map.clear()
        current_form_sim_info = self._create_new_sim_info_base_wrapper(self._sim_info)
        self._add_sim_info_to_map(current_form_sim_info)
        occult_sim_info._base.current_occult_types = occult_type
        self._sim_info.occult_types |= occult_type
        self._add_sim_info_to_map(occult_sim_info)
        self._update_occult_traits()

    def remove_occult_type(self, occult_type):
        if occult_type == self._sim_info.current_occult_types:
            self.switch_to_occult_type(OccultType.HUMAN)
        if self.has_occult_type(occult_type):
            self._sim_info.occult_types &= ~occult_type
            self._update_occult_traits()
            self._sim_info._base.remove_invalid_face_parts()
            self._sim_info.resend_physical_attributes()
            self._sim_info.resend_current_outfit()
        if occult_type in self._sim_info_map:
            del self._sim_info_map[occult_type]

    def switch_to_occult_type(self, occult_type):
        if occult_type not in self._sim_info_map:
            self.add_occult_type(occult_type)
            self._generate_sim_info(occult_type)
        if self._sim_info.current_occult_types != occult_type:
            self._switch_to_occult_type_internal(occult_type)
            self._update_occult_traits()

    def set_pending_occult_type(self, occult_type):
        self._pending_occult_type = occult_type

    def _switch_to_occult_type_internal(self, occult_type):
        current_outfit = self._sim_info.get_current_outfit()
        current_sim_info = self._sim_info_map[self._sim_info.current_occult_types]
        current_sim_info.load_outfits(self._sim_info.save_outfits())
        self._sim_info.current_occult_types = occult_type
        occult_sim_info = self._sim_info_map[occult_type]
        self._copy_shared_attributes(occult_sim_info, self._sim_info, occult_type)
        SimInfoBaseWrapper.copy_physical_attributes(self._sim_info._base, occult_sim_info)
        self._sim_info.load_outfits(occult_sim_info.save_outfits())
        if self._sim_info.has_outfit(current_outfit):
            self._sim_info.set_current_outfit(current_outfit)
        else:
            (outfit_category, outfit_index) = current_outfit
            if outfit_category != OutfitCategory.BATHING:
                if not self._sim_info.has_outfit((outfit_category, outfit_index)):
                    outfit_category = self.get_fallback_outfit_category(occult_type)
                    outfit_index = 0
                self._sim_info.set_current_outfit((outfit_category, outfit_index))
        self._sim_info.appearance_tracker.evaluate_appearance_modifiers()
        sim_instance = self._sim_info.get_sim_instance()
        if sim_instance is not None:
            sim_instance.on_outfit_changed(self._sim_info, self._sim_info.get_current_outfit())
        self._sim_info.resend_physical_attributes()
        self._sim_info.resend_current_outfit()
        self._sim_info.force_resend_suntan_data()

    def has_occult_type(self, occult_type):
        if self._sim_info.occult_types & occult_type:
            return True
        return False

    def get_occult_sim_info(self, occult_type):
        return self._sim_info_map.get(occult_type)

    def _create_new_sim_info_base_wrapper(self, original_sim_info):
        sim_info = SimInfoBaseWrapper(gender=original_sim_info.gender, age=original_sim_info.age, species=original_sim_info.species, first_name=original_sim_info.first_name, last_name=original_sim_info.last_name, breed_name=original_sim_info.breed_name, full_name_key=original_sim_info.full_name_key, breed_name_key=original_sim_info.breed_name_key)
        SimInfoBaseWrapper.copy_physical_attributes(sim_info._base, original_sim_info)
        return sim_info

    def _add_sim_info_to_map(self, sim_info):
        occult_type = sim_info._base.current_occult_types
        if occult_type in self._sim_info_map.keys():
            logger.error("Adding a sim info to the occult tracker's sim info map that already exists. Sim: {}, Duplicate Occult Type: {}", self._sim_info, occult_type)
        self._sim_info_map[occult_type] = sim_info

    def _generate_sim_info(self, occult_type, generate_new=True):
        if self._sim_info_map or occult_type != OccultType.HUMAN:
            generate_new_human_form = self.OCCULT_DATA[occult_type].generate_new_human_form_on_add
            self._generate_sim_info(OccultType.HUMAN, generate_new=generate_new_human_form)
        sim_info = self._create_new_sim_info_base_wrapper(self._sim_info)
        if generate_new:
            self._copy_trait_ids(sim_info, self._sim_info)
            generate_occult_siminfo(sim_info._base, sim_info._base, occult_type)
            for outfit_category in REGULAR_OUTFIT_CATEGORIES:
                sim_info.generate_outfit(outfit_category=outfit_category)
            self._copy_shared_attributes(sim_info, self._sim_info, occult_type)
        sim_info._base.current_occult_types = occult_type
        self._add_sim_info_to_map(sim_info)
        return sim_info

    def has_any_occult_or_part_occult_trait(self):
        for trait_data in self.OCCULT_DATA.values():
            if self.sim_info.has_trait(trait_data.occult_trait):
                return True
            if trait_data.part_occult_trait is not None and self.sim_info.has_trait(trait_data.part_occult_trait):
                return True
        return False

    @staticmethod
    def _copy_trait_ids(sim_info_a, sim_info_b):
        if any(trait.is_gender_option_trait for trait in sim_info_b.trait_tracker):
            sim_info_a._base.base_trait_ids = sim_info_b.trait_ids

    def _copy_shared_attributes(self, sim_info_a, sim_info_b, occult_type):
        sim_info_a.physique = sim_info_b.physique
        OccultTracker._copy_trait_ids(sim_info_a, sim_info_b)
        fallback_outfit_category = self.get_fallback_outfit_category(occult_type)
        for outfit_category in HIDDEN_OUTFIT_CATEGORIES:
            sim_info_a.generate_merged_outfits_for_category(sim_info_b, outfit_category, outfit_flags=BodyTypeFlag.CLOTHING_ALL, fallback_outfit_category=fallback_outfit_category)

    def _update_occult_traits(self):
        for (occult_type, trait_data) in self.OCCULT_DATA.items():
            if self.has_occult_type(occult_type):
                self._sim_info.add_trait(trait_data.occult_trait)
                for additional_trait in trait_data.additional_occult_traits:
                    self._sim_info.add_trait(additional_trait)
                if self._sim_info.current_occult_types == occult_type:
                    if trait_data.current_occult_trait is not None:
                        self._sim_info.add_trait(trait_data.current_occult_trait)
                        self._sim_info.remove_trait(trait_data.current_occult_trait)
                else:
                    self._sim_info.remove_trait(trait_data.current_occult_trait)
                    self._sim_info.remove_trait(trait_data.current_occult_trait)
                    self._sim_info.remove_trait(trait_data.occult_trait)
                    for additional_trait in trait_data.additional_occult_traits:
                        self._sim_info.remove_trait(additional_trait)
            else:
                self._sim_info.remove_trait(trait_data.current_occult_trait)
                self._sim_info.remove_trait(trait_data.occult_trait)
                for additional_trait in trait_data.additional_occult_traits:
                    self._sim_info.remove_trait(additional_trait)
        if not self._sim_info.occult_types:
            self._sim_info.add_trait(OccultTuning.NO_OCCULT_TRAIT)
        else:
            self._sim_info.remove_trait(OccultTuning.NO_OCCULT_TRAIT)

    def apply_occult_age(self, age):
        if not self._sim_info_map:
            return SimInfoBaseWrapper.apply_age(self.sim_info, age)
        for (occult_type, sim_info) in self._sim_info_map.items():
            if occult_type == self._sim_info.current_occult_types:
                SimInfoBaseWrapper.apply_age(self.sim_info, age)
                SimInfoBaseWrapper.apply_age(sim_info, age)
                SimInfoBaseWrapper.copy_physical_attributes(sim_info, self.sim_info)
            else:
                SimInfoBaseWrapper.apply_age(sim_info, age)

    def validate_appropriate_occult(self, sim, occult_form_before_reset):
        if self._sim_info.current_occult_types == OccultType.HUMAN and self.has_occult_type(OccultType.MERMAID):
            if sim.routing_surface.type == SurfaceType.SURFACETYPE_POOL and occult_form_before_reset == OccultType.MERMAID:
                self.switch_to_occult_type(OccultType.MERMAID)
        elif self._sim_info.current_occult_types == OccultType.MERMAID and self.has_occult_type(OccultType.HUMAN) and sim.routing_surface.type != SurfaceType.SURFACETYPE_POOL:
            self.switch_to_occult_type(OccultType.HUMAN)

    def apply_occult_genetics(self, parent_a, parent_b, seed, **kwargs):
        r = random.Random()
        r.seed(seed)
        if r.random() < 0.5:
            occult_tracker_a = parent_a.occult_tracker
            occult_tracker_b = parent_b.occult_tracker
        else:
            occult_tracker_a = parent_b.occult_tracker
            occult_tracker_b = parent_a.occult_tracker
        parent_a_normal = occult_tracker_a.get_occult_sim_info(OccultType.HUMAN) or occult_tracker_a.sim_info
        parent_b_normal = occult_tracker_b.get_occult_sim_info(OccultType.HUMAN) or occult_tracker_b.sim_info
        normal_sim_info = self.get_occult_sim_info(OccultType.HUMAN) or self._sim_info
        SimInfoBaseWrapper.apply_genetics(normal_sim_info, parent_a_normal, parent_b_normal, seed=seed, **kwargs)
        for (occult_type, trait_data) in self.OCCULT_DATA.items():
            if self.has_occult_type(occult_type):
                parent_info_a = occult_tracker_a.get_occult_sim_info(occult_type) or occult_tracker_a.sim_info
                parent_info_b = occult_tracker_b.get_occult_sim_info(occult_type) or occult_tracker_b.sim_info
                offspring_info = self.get_occult_sim_info(occult_type) or self._generate_sim_info(occult_type)
                if occult_type == self._sim_info.current_occult_types:
                    SimInfoBaseWrapper.apply_genetics(self._sim_info, parent_info_a, parent_info_b, seed=seed, **kwargs)
                    SimInfoBaseWrapper.copy_physical_attributes(offspring_info, self._sim_info)
                else:
                    SimInfoBaseWrapper.apply_genetics(offspring_info, parent_info_a, parent_info_b, seed=seed, **kwargs)
            if trait_data.part_occult_trait is not None and self._sim_info.has_trait(trait_data.part_occult_trait):
                if occult_tracker_a.has_occult_type(occult_type):
                    parent_info_a = occult_tracker_a.get_occult_sim_info(occult_type) or parent_a_normal
                    parent_info_b = parent_b_normal
                else:
                    parent_info_a = parent_a_normal
                    parent_info_b = occult_tracker_b.get_occult_sim_info(occult_type) or parent_b_normal
                SimInfoBaseWrapper.apply_genetics(normal_sim_info, parent_info_a, parent_info_b, seed=seed, **kwargs)
        if not self._sim_info.current_occult_types:
            SimInfoBaseWrapper.copy_physical_attributes(normal_sim_info, self._sim_info)

    def on_all_traits_loaded(self):
        if self._sim_info_map:
            self._update_occult_traits()
            self._switch_to_occult_type_internal(self._sim_info.current_occult_types)
        else:
            self._sim_info.add_trait(OccultTuning.NO_OCCULT_TRAIT)
        for (occult_type, sim_info) in self._sim_info_map.items():
            if occult_type != self._sim_info.current_occult_types:
                sim_info.update_gender_for_traits(gender_override=self._sim_info.gender, trait_ids_override=self._sim_info.trait_ids)
        self._sim_info.update_gender_for_traits()

    def post_load(self):
        if self._pending_occult_type:
            self.switch_to_occult_type(self._pending_occult_type)
            self._pending_occult_type = None

    def get_current_occult_types(self):
        return self._sim_info.current_occult_types

    def get_anim_overrides(self):
        return {'hasOccultForm': self._occult_form_available}

    def on_sim_ready_to_simulate(self, sim):
        for (occult_type, trait_data) in self.OCCULT_DATA.items():
            if self.has_occult_type(occult_type):
                exp_stat = trait_data.experience_statistic
                stat = self._sim_info.commodity_tracker.get_statistic(exp_stat)
                if stat is not None:
                    stat.on_sim_ready_to_simulate()
        self.validate_appropriate_occult(sim, None)

    def save(self):
        data = protocols.PersistableOccultTracker()
        data.occult_types = self._sim_info.occult_types
        data.current_occult_types = self._sim_info.current_occult_types
        data.occult_form_available = self._occult_form_available
        if self._pending_occult_type is not None:
            data.pending_occult_type = self._pending_occult_type
        for (occult_type, sim_info) in self._sim_info_map.items():
            with ProtocolBufferRollback(data.occult_sim_infos) as sim_info_data:
                self._copy_shared_attributes(sim_info, self._sim_info, occult_type)
                sim_info_data.occult_type = occult_type
                sim_info_data.outfits = sim_info.save_outfits()
                SimInfoBaseWrapper.copy_physical_attributes(sim_info_data, sim_info)
        return data

    def load(self, data):
        self._sim_info.occult_types = data.occult_types or OccultType.HUMAN
        self._sim_info.current_occult_types = data.current_occult_types or OccultType.HUMAN
        self._pending_occult_type = data.pending_occult_type
        self._occult_form_available = data.occult_form_available
        occult_data_map = {}
        for sim_info_data in data.occult_sim_infos:
            occult_data_map[sim_info_data.occult_type] = sim_info_data
        for occult_type in OccultType:
            if occult_type != OccultType.HUMAN and occult_type not in self.OCCULT_DATA:
                self._sim_info.occult_types &= ~occult_type
                if self._sim_info.current_occult_types == occult_type:
                    self._sim_info.current_occult_types = OccultType.HUMAN
                if self._pending_occult_type == occult_type:
                    self._pending_occult_type = None
            elif occult_type in occult_data_map:
                sim_info_data = occult_data_map[occult_type]
                sim_info = self._generate_sim_info(sim_info_data.occult_type, generate_new=False)
                if occult_type == self._sim_info.current_occult_types:
                    SimInfoBaseWrapper.copy_physical_attributes(sim_info_data, self._sim_info._base)
                else:
                    sim_info.load_outfits(sim_info_data.outfits)
                    SimInfoBaseWrapper.copy_physical_attributes(sim_info._base, sim_info_data)
            elif occult_type != OccultType.HUMAN and self.has_occult_type(occult_type) and occult_type == self._sim_info.current_occult_types:
                self._generate_sim_info(occult_type, generate_new=False)
