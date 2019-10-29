from _collections import defaultdictfrom collections import namedtupleimport operatorimport randomimport weakreffrom protocolbuffers import Outfits_pb2from animation import get_throwaway_animation_contextfrom animation.animation_utils import create_run_animation, flush_all_animationsfrom animation.arb import Arbfrom animation.asm import create_asmfrom element_utils import build_critical_sectionfrom event_testing.resolver import SingleSimResolverfrom gsi_handlers import outfit_change_handlersfrom objects import ALL_HIDDEN_REASONSfrom sims.outfits.outfit_enums import OutfitCategory, NON_RANDOMIZABLE_OUTFIT_CATEGORIES, OutfitChangeReason, OutfitFilterFlagfrom sims.outfits.outfit_tuning import OutfitTuningfrom singletons import DEFAULTimport element_utilsimport servicesimport sims4.loglogger = sims4.log.Logger('Outfits', default_owner='epanero')OutfitPriority = namedtuple('OutfitPriority', ('change_reason', 'priority', 'interaction_ref'))
class OutfitTrackerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_outfit_priorities = []
        self._randomize_daily = defaultdict(lambda : True)
        self._last_randomize = defaultdict(lambda : None)
        self._daily_defaults = {}
        self._outfit_dirty = set()

    def add_default_outfit_priority(self, interaction, outfit_change_reason, priority):
        interaction_ref = weakref.ref(interaction) if interaction is not None else None
        outfit_priority = OutfitPriority(outfit_change_reason, priority, interaction_ref)
        self._default_outfit_priorities.append(outfit_priority)
        return id(outfit_priority)

    def add_outfit(self, outfit_category:OutfitCategory, outfit_data):
        (outfit_category, outfit_index) = self._base.add_outfit(outfit_category, outfit_data)
        return (OutfitCategory(outfit_category), outfit_index)

    def can_switch_to_outfit(self, outfit_category_and_index) -> bool:
        if outfit_category_and_index is None:
            return False
        if self.outfit_is_dirty(outfit_category_and_index[0]):
            return True
        elif self._current_outfit == outfit_category_and_index:
            return False
        return True

    def _get_random_daily_outfit(self, outfit_category):
        current_time = services.time_service().sim_now
        existing_default = outfit_category in self._daily_defaults
        last_randomize_time = self._last_randomize[outfit_category]
        if existing_default and (current_time.absolute_days() - last_randomize_time.absolute_days() >= 1 or current_time.day() != last_randomize_time.day()):
            index = 0
            number_of_outfits = self.get_number_of_outfits_in_category(outfit_category)
            if number_of_outfits > 1:
                if existing_default:
                    index = random.randrange(number_of_outfits - 1)
                    exclusion = self._daily_defaults[outfit_category]
                    if index >= exclusion:
                        index += 1
                else:
                    index = random.randrange(number_of_outfits)
            self._daily_defaults[outfit_category] = index
            self._last_randomize[outfit_category] = current_time
        return (outfit_category, self._daily_defaults[outfit_category])

    def generate_unpopulated_outfits(self, outfit_categories):
        for outfit_category in outfit_categories:
            if not self.has_outfit((outfit_category, 0)):
                self.generate_outfit(outfit_category=outfit_category)

    def get_all_outfit_entries(self):
        for outfit_category in OutfitCategory:
            if outfit_category == OutfitCategory.CURRENT_OUTFIT:
                pass
            else:
                for outfit_index in range(self.get_number_of_outfits_in_category(outfit_category)):
                    yield (outfit_category, outfit_index)

    def get_all_outfits(self):
        for outfit_category in OutfitCategory:
            if outfit_category == OutfitCategory.CURRENT_OUTFIT:
                pass
            else:
                yield (outfit_category, self.get_outfits_in_category(outfit_category))

    def get_change_outfit_element(self, outfit_category_and_index, do_spin=True, interaction=None):

        def change_outfit(timeline):
            arb = Arb()
            self.try_set_current_outfit(outfit_category_and_index, do_spin=do_spin, arb=arb, interaction=interaction)
            if not arb.empty:
                clothing_element = create_run_animation(arb)
                yield from element_utils.run_child(timeline, clothing_element)

        return change_outfit

    def get_change_outfit_element_and_archive_change_reason(self, outfit_category_and_index, do_spin=True, interaction=None, change_reason=None):
        if outfit_change_handlers.archiver.enabled:
            outfit_change_handlers.log_outfit_change(self.get_sim_info(), outfit_category_and_index, change_reason)
        return self.get_change_outfit_element(outfit_category_and_index, do_spin, interaction)

    def get_default_outfit(self, interaction=None, resolver=None):
        default_outfit = OutfitPriority(None, 0, None)
        if self._default_outfit_priorities:
            default_outfit = max(self._default_outfit_priorities, key=operator.attrgetter('priority'))
        if interaction is not None or resolver is not None:
            return self.get_outfit_for_clothing_change(interaction, default_outfit.change_reason, resolver=resolver)
        if default_outfit.interaction_ref() is not None:
            return self.get_outfit_for_clothing_change(default_outfit.interaction_ref(), default_outfit.change_reason)
        return self._current_outfit

    def get_next_outfit_for_category(self, outfit_category):
        return (outfit_category, self.get_number_of_outfits_in_category(outfit_category))

    def get_number_of_outfits_in_category(self, outfit_category):
        return len(self.get_outfits_in_category(outfit_category))

    def get_outfit(self, outfit_category:OutfitCategory, outfit_index:int):
        if not self.has_outfit((outfit_category, outfit_index)):
            self.generate_outfit(outfit_category, outfit_index)
        try:
            return self._base.get_outfit(outfit_category, outfit_index)
        except RuntimeError as exception:
            raise exception

    def get_outfit_change(self, interaction, change_reason, resolver=None, **kwargs):
        if change_reason is not None:
            outfit_category_and_index = self.get_outfit_for_clothing_change(interaction, change_reason, resolver=resolver)
            return build_critical_section(self.get_change_outfit_element_and_archive_change_reason(outfit_category_and_index, interaction=interaction, change_reason=change_reason, **kwargs), flush_all_animations)

    def get_outfit_for_clothing_change(self, interaction, reason, resolver=None):
        for trait in self.get_traits():
            reason = trait.get_outfit_change_reason(reason)
        if reason == OutfitChangeReason.Invalid:
            return self._current_outfit
        if reason == OutfitChangeReason.DefaultOutfit:
            return self.get_default_outfit(interaction=interaction, resolver=resolver)
        if reason == OutfitChangeReason.PreviousClothing:
            return self._previous_outfit
        if reason == OutfitChangeReason.RandomOutfit:
            return self.get_random_outfit()
        if reason == OutfitChangeReason.CurrentOutfit:
            return self._current_outfit
        elif reason == OutfitChangeReason.ExitBedNPC:
            if self.is_npc:
                return self._previous_outfit
            return
        return
        resolver_to_use = resolver or interaction.get_resolver()
        outfit_change = None
        if reason in OutfitTuning.OUTFIT_CHANGE_REASONS:
            test_group_and_outfit_list = OutfitTuning.OUTFIT_CHANGE_REASONS[reason]
            for test_group_and_outfit in test_group_and_outfit_list:
                outfit_category = test_group_and_outfit.outfit_category
                if outfit_category == OutfitCategory.BATHING and not self.has_outfit_category(OutfitCategory.BATHING):
                    self.generate_outfit(OutfitCategory.BATHING, filter_flag=OutfitFilterFlag.NONE)
                if outfit_category != OutfitCategory.CURRENT_OUTFIT and not self.has_outfit_category(outfit_category):
                    pass
                else:
                    if test_group_and_outfit.tests:
                        if test_group_and_outfit.tests.run_tests(resolver_to_use):
                            if test_group_and_outfit.outfit_category == OutfitCategory.CURRENT_OUTFIT or test_group_and_outfit.outfit_category == self._current_outfit[0]:
                                outfit_change = self._current_outfit
                            elif self._randomize_daily[outfit_category]:
                                outfit_change = self._get_random_daily_outfit(outfit_category)
                            else:
                                outfit_change = (outfit_category, 0)
                            break
                    if test_group_and_outfit.outfit_category == OutfitCategory.CURRENT_OUTFIT or test_group_and_outfit.outfit_category == self._current_outfit[0]:
                        outfit_change = self._current_outfit
                    elif self._randomize_daily[outfit_category]:
                        outfit_change = self._get_random_daily_outfit(outfit_category)
                    else:
                        outfit_change = (outfit_category, 0)
                    break
        if outfit_change is None:
            outfit_change = (OutfitCategory.EVERYDAY, 0)
        outfit_change = self._run_weather_fixup(reason, outfit_change, resolver_to_use)
        outfit_change = self._run_career_fixup(outfit_change, interaction)
        return outfit_change

    def _run_weather_fixup(self, reason, outfit_change, resolver):
        weather_service = services.weather_service()
        if weather_service is None:
            return outfit_change
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return outfit_change
        weather_outfit_change = weather_service.get_weather_outfit_change(resolver, reason=reason)
        if weather_outfit_change is None:
            return outfit_change
        if not sim.is_outside:
            return outfit_change
        elif reason in weather_service.WEATHER_OUFTIT_CHANGE_REASONS_TO_IGNORE:
            return outfit_change
        return weather_outfit_change

    def _run_career_fixup(self, outfit_change, interaction):
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return outfit_change
        if not self._career_tracker.has_part_time_career_outfit():
            return outfit_change
        if outfit_change[0] != OutfitCategory.CAREER or interaction is None or hasattr(interaction, 'career_uid') and interaction.career_uid == None:
            return outfit_change
        elif interaction.career_uid is not None:
            self.remove_outfits_in_category(OutfitCategory.CAREER)
            career = self._career_tracker.get_career_by_uid(interaction.career_uid)
            career.generate_outfit()
            career_outfit_change = (OutfitCategory.CAREER, 0)
            return career_outfit_change
        return outfit_change

    def get_outfits_in_category(self, outfit_category:OutfitCategory):
        return self._base.get_outfits_in_category(outfit_category)

    def get_random_outfit(self, outfit_categories=()):
        valid_outfits = []
        for (outfit_category, outfit_index) in self.get_all_outfit_entries():
            if outfit_categories and outfit_category not in outfit_categories:
                pass
            elif outfit_category == OutfitCategory.CURRENT_OUTFIT:
                pass
            elif outfit_category in NON_RANDOMIZABLE_OUTFIT_CATEGORIES:
                pass
            else:
                valid_outfits.append((outfit_category, outfit_index))
        if valid_outfits:
            return random.choice(valid_outfits)
        return (self.occult_tracker.get_fallback_outfit_category(self.current_occult_types), 0)

    def get_sim_info(self):
        return self

    def has_outfit(self, outfit):
        return self._base.has_outfit(outfit[0], outfit[1])

    def has_outfit_category(self, outfit_category):
        return self.has_outfit((outfit_category, 0))

    def has_cas_part(self, cas_part):
        try:
            return cas_part in self._base.get_outfit(*self._current_outfit).part_ids
        except RuntimeError as exception:
            logger.exception('Exception encountered trying to get the current outfit: ', exc=exception, level=sims4.log.LEVEL_ERROR)
            return False

    def is_wearing_outfit(self, category_and_index):
        if self.outfit_is_dirty(category_and_index[0]):
            return False
        return self._current_outfit == category_and_index

    def load_outfits(self, outfit_msg):
        self._base.outfits = outfit_msg.SerializeToString()

    def remove_default_outfit_priority(self, outfit_priority_id):
        for (index, value) in enumerate(self._default_outfit_priorities):
            if id(value) == outfit_priority_id:
                self._default_outfit_priorities.pop(index)
                break

    def remove_outfit(self, outfit_category:OutfitCategory, outfit_index:int=DEFAULT):
        outfit_index = self.get_number_of_outfits_in_category(outfit_category) - 1 if outfit_index is DEFAULT else outfit_index
        return self._base.remove_outfit(outfit_category, outfit_index)

    def remove_outfits_in_category(self, outfit_category:OutfitCategory):
        while self.has_outfit((outfit_category, 0)):
            self.remove_outfit(outfit_category, 0)

    def remove_all_but_one_outfit_in_category(self, outfit_category:OutfitCategory):
        while self.has_outfit((outfit_category, 1)):
            self.remove_outfit(outfit_category, 1)

    def clear_outfits_to_minimum(self):
        for (outfit_category, _) in self.get_all_outfits():
            if outfit_category is OutfitCategory.EVERYDAY:
                self.remove_all_but_one_outfit_in_category(outfit_category)
            else:
                self.remove_outfits_in_category(outfit_category)

    def save_outfits(self):
        outfits_msg = Outfits_pb2.OutfitList()
        outfits_msg.ParseFromString(self._base.outfits)
        return outfits_msg

    def set_outfit_flags(self, outfit_category:OutfitCategory, outfit_index:int, outfit_flags:int):
        outfit_flags_low = int(outfit_flags & 18446744073709551615)
        outfit_flags_high = int(outfit_flags >> 64 & 18446744073709551615)
        return self._base.set_outfit_flags(outfit_category, outfit_index, outfit_flags_low, outfit_flags_high)

    def _apply_on_outfit_changed_loot(self):
        is_sim = getattr(self, 'is_sim', False)
        if is_sim:
            resolver = SingleSimResolver(self)
            for loot_action in OutfitTuning.LOOT_ON_OUTFIT_CHANGE:
                loot_action.apply_to_resolver(resolver)

    def try_set_current_outfit(self, outfit_category_and_index, do_spin=False, arb=None, interaction=None):
        sim = self.get_sim_instance()
        if sim is None:
            do_spin = False
        if arb is None:
            logger.error('Must pass in a valid ARB for the clothing spin.')
            do_spin = False
        if self.can_switch_to_outfit(outfit_category_and_index):
            if do_spin:
                did_change = False

                def set_ending(*_, **__):
                    nonlocal did_change
                    if not did_change:
                        laundry_service = services.get_laundry_service()
                        if laundry_service is not None:
                            laundry_service.on_spin_outfit_change(sim, outfit_category_and_index, interaction)
                        if self.set_current_outfit(outfit_category_and_index):
                            self._apply_on_outfit_changed_loot()
                        did_change = True

                arb.register_event_handler(set_ending, handler_id=100)
                if sim is not None:
                    animation_element_tuning = OutfitTuning.OUTFIT_CHANGE_ANIMATION
                    clothing_context = get_throwaway_animation_context()
                    clothing_change_asm = create_asm(animation_element_tuning.asm_key, context=clothing_context)
                    clothing_change_asm.update_locked_params(sim.get_transition_asm_params())
                    result = sim.posture.setup_asm_interaction(clothing_change_asm, sim, None, animation_element_tuning.actor_name, None)
                    sim.set_trait_asm_parameters(clothing_change_asm, animation_element_tuning.actor_name)
                    if not result:
                        logger.error('Could not setup asm for Clothing Change. {}', result)
                    clothing_change_asm.request(animation_element_tuning.begin_states[0], arb)
            elif self.set_current_outfit(outfit_category_and_index):
                self._apply_on_outfit_changed_loot()

    def set_outfit_dirty(self, outfit_category):
        self._outfit_dirty.add(outfit_category)

    def clear_outfit_dirty(self, outfit_category):
        self._outfit_dirty.discard(outfit_category)

    def outfit_is_dirty(self, outfit_category):
        if outfit_category in self._outfit_dirty:
            return True
        return False
