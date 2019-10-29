from weakref import WeakKeyDictionaryimport randomfrom animation.animation_utils import flush_all_animationsfrom cas.cas import get_caspart_bodytypefrom element_utils import build_critical_sectionfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableGlobalTestSetfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.liability import Liabilityfrom sims.outfits import outfit_utilsfrom sims.outfits.outfit_enums import OutfitCategory, OutfitFilterFlag, SpecialOutfitIndex, OutfitChangeReason, CLOTHING_BODY_TYPES, REGULAR_OUTFIT_CATEGORIESfrom sims.outfits.outfit_generator import TunableOutfitGeneratorSnippetfrom sims.outfits.outfit_utils import get_maximum_outfits_for_categoryfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, OptionalTunable, TunableEnumEntry, HasTunableFactory, TunableTuple, Tunable, TunableListfrom singletons import DEFAULTimport servicesimport sims4.loglogger = sims4.log.Logger('Outfits', default_owner='rfleig')SPECIAL_OUTFIT_KEY = (OutfitCategory.SPECIAL, 0)
class OutfitChangeBase(HasTunableSingletonFactory, AutoFactoryInit):

    def __bool__(self):
        return True

    def has_entry_change(self, interaction, **kwargs):
        raise NotImplementedError

    def has_exit_change(self, interaction, **kwargs):
        raise NotImplementedError

    def get_on_entry_change(self, interaction, **kwargs):
        raise NotImplementedError

    def get_on_exit_change(self, interaction, **kwargs):
        raise NotImplementedError

    def get_on_entry_outfit(self, interaction, **kwargs):
        raise NotImplementedError

    def get_on_exit_outfit(self, interaction, **kwargs):
        raise NotImplementedError

class TunableOutfitChange(TunableVariant):

    class _OutfitChangeNone(OutfitChangeBase):

        def __bool__(self):
            return False

        def has_entry_change(self, interaction, **kwargs):
            return False

        def has_exit_change(self, interaction, **kwargs):
            return False

        def get_on_entry_change(self, interaction, **kwargs):
            pass

        def get_on_exit_change(self, interaction, **kwargs):
            pass

        def get_on_entry_outfit(self, interaction, **kwargs):
            pass

        def get_on_exit_outfit(self, interaction, **kwargs):
            pass

    class _OutfitChangeForReason(OutfitChangeBase):
        FACTORY_TUNABLES = {'on_entry': OptionalTunable(description='\n                When enabled, define the change reason to apply on posture\n                entry.\n                ', tunable=TunableEnumEntry(tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid)), 'on_exit': OptionalTunable(description='\n                When enabled, define the change reason to apply on posture\n                exit.\n                ', tunable=TunableEnumEntry(tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid))}

        def _get_outfit_resolver_and_sim_info(self, interaction, sim_info=DEFAULT):
            if sim_info is DEFAULT:
                return (None, interaction.sim.sim_info)
            return (SingleSimResolver(sim_info), sim_info)

        def has_entry_change(self, interaction, **kwargs):
            return self.on_entry is not None

        def has_exit_change(self, interaction, **kwargs):
            return self.on_exit is not None

        def get_on_entry_change(self, interaction, sim_info=DEFAULT, **kwargs):
            (resolver, sim_info) = self._get_outfit_resolver_and_sim_info(interaction, sim_info=sim_info)
            return sim_info.get_outfit_change(interaction, self.on_entry, resolver=resolver, **kwargs)

        def get_on_exit_change(self, interaction, sim_info=DEFAULT, **kwargs):
            (resolver, sim_info) = self._get_outfit_resolver_and_sim_info(interaction, sim_info=sim_info)
            return sim_info.get_outfit_change(interaction, self.on_exit, resolver=resolver, **kwargs)

        def get_on_entry_outfit(self, interaction, sim_info=DEFAULT):
            if self.on_entry is not None:
                (resolver, sim_info) = self._get_outfit_resolver_and_sim_info(interaction, sim_info=sim_info)
                return sim_info.get_outfit_for_clothing_change(interaction, self.on_entry, resolver=resolver)

        def get_on_exit_outfit(self, interaction, sim_info=DEFAULT):
            if self.on_exit is not None:
                (resolver, sim_info) = self._get_outfit_resolver_and_sim_info(interaction, sim_info=sim_info)
                return sim_info.get_outfit_for_clothing_change(interaction, self.on_exit, resolver=resolver)

    class _OutfitChangeForTags(OutfitChangeBase):

        @staticmethod
        def _verify_tunable_callback(instance_class, tunable_name, source, value, **kwargs):
            if value.on_entry and value.on_entry.auto_undo_on_exit and value.on_exit is not None:
                logger.error('{} has tuned both on_entry.auto_undo_on_exit and on_exit in a For Tags outfit change. These two things conflict.', instance_class, owner='rfleig')

        class OutfitTypeSpecial(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'special_outfit_index': TunableEnumEntry(description='\n                    The Special outfit index to use when creating the outfit using\n                    the provided flags. There are multiple Special outfits that \n                    are indexed by the entries in the SpecialOutfitIndex enum.\n                    \n                    GPE NOTE:\n                    If you want to add a new index you will need to add a value\n                    to SpecialOutfitIndex as well as change the values in \n                    outfit_tuning.py and OutfitTypes.h to allow for more special\n                    outfits.\n                    ', tunable_type=SpecialOutfitIndex, default=SpecialOutfitIndex.DEFAULT)}

            def get_outfit(self, *args):
                return (OutfitCategory.SPECIAL, self.special_outfit_index)

            def __call__(self, sim_info, outfit_generator):
                if self.special_outfit_index > 0:
                    for i in range(0, self.special_outfit_index):
                        if not sim_info.has_outfit((OutfitCategory.SPECIAL, i)):
                            sim_info.generate_outfit(OutfitCategory.SPECIAL, i)
                outfit_generator(sim_info, OutfitCategory.SPECIAL, outfit_index=self.special_outfit_index)
                return (OutfitCategory.SPECIAL, self.special_outfit_index)

        class OutfitTypeCurrent(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'restrict_to_regular': Tunable(description='\n                    If checked, the Sim will switch out of any non-regular\n                    outfits (and into Everyday) before applying the\n                    modification.\n                    \n                    If this is unchecked, the Sim will modify whatever outfit\n                    they are wearing, including, for example, career outfits.\n                    The modification is permanent.\n                    ', tunable_type=bool, default=True)}

            def get_outfit(self, sim_info, *args):
                if sim_info is not DEFAULT:
                    (outfit_category, outfit_index) = sim_info.get_current_outfit()
                else:
                    outfit_category = OutfitCategory.SPECIAL
                    outfit_index = SpecialOutfitIndex.DEFAULT
                if outfit_category not in REGULAR_OUTFIT_CATEGORIES:
                    outfit_category = OutfitCategory.EVERYDAY
                    outfit_index = 0
                return (outfit_category, outfit_index)

            def __call__(self, sim_info, outfit_generator):
                (outfit_category, outfit_index) = self.get_outfit(sim_info)
                outfit_generator(sim_info, outfit_category, outfit_index=outfit_index)
                return (outfit_category, outfit_index)

        class OutfitTypeCategory(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'outfit_category': TunableEnumEntry(description='\n                    Outfit Category\n                    ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY, invalid_enums=(OutfitCategory.CURRENT_OUTFIT,))}

            def get_outfit(self, *args):
                return (self.outfit_category, 0)

            def __call__(self, sim_info, outfit_generator):
                outfit_generator(sim_info, self.outfit_category)
                return (self.outfit_category, 0)

        FACTORY_TUNABLES = {'on_entry': OptionalTunable(description='\n                The tuning for how to handle the outfit change on entry of\n                the new context.\n                ', tunable=TunableTuple(description='\n                    Contains the tags used to tune the outfit and also\n                    a preference for whether or not to automatically switch out\n                    of the tags outfit when on exit.\n                    ', outfit_to_modify=TunableVariant(description='\n                        The outfit we want to generate over.\n                        ', current=OutfitTypeCurrent.TunableFactory(), outfit_category=OutfitTypeCategory.TunableFactory(), special=OutfitTypeSpecial.TunableFactory(), default='special'), generator=TunableOutfitGeneratorSnippet(), do_spin=Tunable(description='\n                        If checked, the Sim will animate and perform a clothing\n                        change spin. If unchecked, the Sim will change outfits\n                        without animating.\n                        ', tunable_type=bool, default=True), auto_undo_on_exit=Tunable(description="\n                        If True then the Sim will switch out of the entry tag\n                        outfit on exit. \n                        If False then the Sim will stay in the tag outfit.\n                        \n                        NOTE: This tuning conflicts with the On Exit tuning. If\n                        this is set to true and On Exit is enabled then an \n                        error should occur on load because you can't both switch\n                        out of the tag outfit and switch into a different tag\n                        outfit.\n                        ", tunable_type=bool, default=True)), enabled_by_default=True), 'on_exit': OptionalTunable(description='\n                The clothing change that happens on exit of the current context.\n                ', tunable=TunableList(description='\n                    A list of (tests, clothing change) tuples. The first entry\n                    that passes all of its tests will be used while the other\n                    entries after that one will be ignored. So the order of the \n                    list is essentially priority.\n                    ', tunable=TunableTuple(description='\n                        A tuple of clothing changes and tests for whether they\n                        should happen or not.\n                        ', outfit_to_modify=TunableVariant(description='\n                            The outfit we want to generate over.\n                            ', current=OutfitTypeCurrent.TunableFactory(), outfit_category=OutfitTypeCategory.TunableFactory(), special=OutfitTypeSpecial.TunableFactory(), default='special'), generator=TunableOutfitGeneratorSnippet(), tests=TunableGlobalTestSet(description='\n                            Tests to run when deciding which clothing change\n                            entry to use. All of the tests must pass in order \n                            for the item to pass.\n                            ')))), 'verify_tunable_callback': _verify_tunable_callback}

        def has_entry_change(self, interaction, **kwargs):
            return self.on_entry is not None

        def has_exit_change(self, interaction, **kwargs):
            return self.on_exit is not None

        def get_on_entry_change(self, interaction, sim_info=DEFAULT, do_spin=True, **kwargs):
            if not self.on_entry:
                return
            sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
            do_spin &= self.on_entry.do_spin
            for trait in sim_info.get_traits():
                outfit_change_reason = trait.get_outfit_change_reason(None)
                if outfit_change_reason is not None:
                    return sim_info.get_outfit_change(interaction, outfit_change_reason, do_spin=do_spin, **kwargs)
            (category, index) = self.on_entry.outfit_to_modify(sim_info, self.on_entry.generator)
            return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason((category, index), do_spin=do_spin, interaction=interaction, change_reason=interaction, **kwargs), flush_all_animations)

        def get_on_exit_change(self, interaction, sim_info=DEFAULT, **kwargs):
            sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
            if self.on_exit or self.on_entry is not None and self.on_entry.auto_undo_on_exit:
                return sim_info.get_outfit_change(interaction, OutfitChangeReason.CurrentOutfit, **kwargs)
            if self.on_exit:
                choice = self.choose_on_exit_clothing_change(sim_info)
                if choice is None:
                    return
                else:
                    (category, index) = choice.outfit_to_modify(sim_info, choice.generator)
                    return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason((category, index), interaction=interaction, change_reason=interaction, **kwargs), flush_all_animations)

        def choose_on_exit_clothing_change(self, sim_info):
            resolver = SingleSimResolver(sim_info)
            for outfit_change in self.on_exit:
                result = outfit_change.tests.run_tests(resolver)
                if result:
                    return outfit_change

        def get_on_entry_outfit(self, interaction, sim_info=DEFAULT):
            if self.on_entry is not None:
                return self.on_entry.outfit_to_modify.get_outfit(sim_info)

        def get_on_exit_outfit(self, interaction, sim_info=DEFAULT):
            if sim_info is DEFAULT:
                sim_info = interaction.sim.sim_info
                resolver = None
            else:
                resolver = SingleSimResolver(sim_info)
            if self.on_exit or self.on_entry is not None and self.on_entry.auto_undo_on_exit:
                return sim_info.get_outfit_for_clothing_change(interaction, OutfitChangeReason.CurrentOutfit, resolver=resolver)
            if self.on_exit:
                choice = self.choose_on_exit_clothing_change(sim_info)
                if choice is None:
                    return
                else:
                    return choice.outfit_to_modify(sim_info, choice.generator)

    class _OutfitChangeFromPickedItemId(OutfitChangeBase):

        class _OnEntry(HasTunableSingletonFactory):

            @property
            def is_entry_change(self):
                return True

            @property
            def is_exit_change(self):
                return False

        class _OnExit(HasTunableSingletonFactory):

            @property
            def is_entry_change(self):
                return False

            @property
            def is_exit_change(self):
                return True

        FACTORY_TUNABLES = {'timing': TunableVariant(description='\n                Define when this outfit change happens.\n                ', on_entry=_OnEntry.TunableFactory(), on_exit=_OnExit.TunableFactory(), default='on_entry')}

        def _get_outfit(self, interaction):
            outfits = interaction.get_participants(ParticipantType.PickedItemId)
            if not outfits:
                return
            outfit = next(iter(outfits))
            return outfit

        def _get_outfit_change(self, interaction, sim_info=DEFAULT, **kwargs):
            outfit = self._get_outfit(interaction)
            if outfit is not None:
                sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
                return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason(outfit, interaction=interaction, change_reason=interaction, **kwargs), flush_all_animations)

        def has_entry_change(self, interaction, **kwargs):
            return self.timing.is_entry_change

        def has_exit_change(self, interaction, **kwargs):
            return self.timing.is_exit_change

        def get_on_entry_change(self, *args, **kwargs):
            if self.timing.is_entry_change:
                return self._get_outfit_change(*args, **kwargs)

        def get_on_exit_change(self, *args, **kwargs):
            if self.timing.is_exit_change:
                return self._get_outfit_change(*args, **kwargs)

        def get_on_entry_outfit(self, interaction, sim_info=DEFAULT):
            if self.timing.is_entry_change:
                return self._get_outfit(interaction)

        def get_on_exit_outfit(self, interaction, sim_info=DEFAULT):
            if self.timing.is_exit_change:
                return self._get_outfit(interaction)

    class _OutfitChangeWithState(OutfitChangeBase):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._outfit_change_map = WeakKeyDictionary()

        def has_entry_change(self, interaction, **kwargs):
            return self.get_on_entry_outfit(interaction, **kwargs) is not None

        def has_exit_change(self, interaction, **kwargs):
            return self.get_on_exit_outfit(interaction, **kwargs) is not None

        def _get_outfit_change_internal(self, interaction, sim_info):
            sim_map = self._outfit_change_map.get(interaction)
            if sim_map is None:
                sim_map = WeakKeyDictionary()
                self._outfit_change_map[interaction] = sim_map
            change = sim_map.get(sim_info)
            if change is None:
                change = self._create_outfit_change_internal(interaction, sim_info)
                sim_map[sim_info] = change
            return change

        def _create_outfit_change_internal(self, interaction, sim_info):
            raise NotImplementedError

        def get_on_entry_change(self, interaction, sim_info=DEFAULT, **kwargs):
            sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
            for trait in sim_info.get_traits():
                outfit_change_reason = trait.get_outfit_change_reason(None)
                if outfit_change_reason is not None:
                    return sim_info.get_outfit_change(interaction, outfit_change_reason, **kwargs)
            outfit_change = self._get_outfit_change_internal(interaction, sim_info)
            if outfit_change is not None:
                return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason(outfit_change.entry_outfit, interaction=interaction, change_reason=interaction, **kwargs), flush_all_animations)

        def get_on_exit_change(self, interaction, sim_info=DEFAULT, **kwargs):
            sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
            outfit_change = self._get_outfit_change_internal(interaction, sim_info)
            if outfit_change is not None:
                return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason(outfit_change.exit_outfit, interaction=interaction, change_reason=interaction, **kwargs), flush_all_animations)

        def get_on_entry_outfit(self, interaction, sim_info=DEFAULT):
            sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
            outfit_change = self._get_outfit_change_internal(interaction, sim_info)
            if outfit_change is not None:
                return outfit_change.entry_outfit

        def get_on_exit_outfit(self, interaction, sim_info=DEFAULT):
            sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
            outfit_change = self._get_outfit_change_internal(interaction, sim_info)
            if outfit_change is not None:
                return outfit_change.exit_outfit

    class _OutfitChangeFromZone(_OutfitChangeWithState):
        FACTORY_TUNABLES = {'auto_undo_on_exit': Tunable(description='\n                If checked, the Sim will use the previous outfit as the\n                on_exit outfit for this outfit change.\n                \n                Has no effect for outfit changes that do not perform an on_exit\n                change, such as on_route outfit changes.\n                ', tunable_type=bool, default=True)}

        def _create_outfit_change_internal(self, interaction, sim_info):
            current_outfit = sim_info.get_current_outfit()
            self.entry_outfit = None
            self.exit_outfit = current_outfit if self.auto_undo_on_exit else None
            if sim_info.is_wearing_outfit(SPECIAL_OUTFIT_KEY):
                return self
            zone_director = services.venue_service().get_zone_director()
            if zone_director is None:
                return self
            (zone_outfit, outfit_key) = zone_director.get_zone_outfit(sim_info)
            if zone_outfit is None:
                return self
            if sim_info.is_wearing_outfit(outfit_key) and outfit_utils.is_sim_info_wearing_all_outfit_parts(sim_info, zone_outfit, outfit_key):
                return self
            sim_info.generate_merged_outfit(zone_outfit, SPECIAL_OUTFIT_KEY, sim_info.get_current_outfit(), outfit_key)
            self.entry_outfit = SPECIAL_OUTFIT_KEY
            return self

    class _OutfitChangeFromParticipant(_OutfitChangeWithState):

        class _OutfitChangeTemporary(HasTunableFactory, AutoFactoryInit):

            def __init__(self, sim_info, outfit_source, *args, **kwargs):
                super().__init__(*args, **kwargs)
                outfits = outfit_source.get_outfits()
                source_outfit = outfit_source.get_current_outfit()
                sim_info.generate_merged_outfit(outfits.get_sim_info(), SPECIAL_OUTFIT_KEY, sim_info.get_current_outfit(), source_outfit)
                self.entry_outfit = SPECIAL_OUTFIT_KEY
                self.exit_outfit = sim_info.get_current_outfit()

        class _OutfitChangeAddition(HasTunableFactory, AutoFactoryInit):

            def __init__(self, sim_info, outfit_source, *args, **kwargs):
                super().__init__(*args, **kwargs)
                source_outfit = outfit_source.get_current_outfit()
                source_category = source_outfit[0]
                source_outfits = outfit_source.get_outfits()
                target_outfits = sim_info.get_outfits()
                outfits_in_category = target_outfits.get_outfits_in_category(source_category)
                outfits_in_category = len(outfits_in_category) if outfits_in_category is not None else 0
                current_outfit = sim_info.get_current_outfit()
                if outfits_in_category >= get_maximum_outfits_for_category(source_category):
                    available_outfits = [(source_category, index) for index in range(1, outfits_in_category) if (source_category, index) != current_outfit]
                    destination_outfit = random.choice(available_outfits)
                else:
                    destination_outfit = target_outfits.get_next_outfit_for_category(source_category)
                sim_info.generate_merged_outfit(source_outfits.get_sim_info(), destination_outfit, current_outfit, source_outfit)
                self.entry_outfit = destination_outfit
                self.exit_outfit = None

        FACTORY_TUNABLES = {'outfit_participant': TunableEnumEntry(description='\n                The Sim or object whose current outfit is going to be\n                temporarily applied to the Sim being affected by this change.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'outfit_change_behavior': TunableVariant(description='\n                Define how this outfit is to be applied to the Sim.\n                ', temporary=_OutfitChangeTemporary.TunableFactory(), addition=_OutfitChangeAddition.TunableFactory(), default='temporary')}

        def _create_outfit_change_internal(self, interaction, sim_info):
            outfit_participant = interaction.get_participant(self.outfit_participant)
            if outfit_participant is None:
                return
            return self.outfit_change_behavior(sim_info, outfit_participant)

    class _OutfitChangeForNew(_OutfitChangeWithState):

        class _OutfitChangeGeneration(HasTunableFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'outfit_category': TunableEnumEntry(description="\n                    The outfit category for which we're creating a new outfit.\n                    ", tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY)}

            def __init__(self, interaction, sim_info, *args, **kwargs):
                super().__init__(*args, **kwargs)
                outfits = sim_info.get_outfits()
                current_outfit = sim_info.get_current_outfit()
                outfits_in_category = outfits.get_outfits_in_category(self.outfit_category)
                outfits_in_category = len(outfits_in_category) if outfits_in_category is not None else 0
                if outfits_in_category >= get_maximum_outfits_for_category(self.outfit_category):
                    available_outfits = [(self.outfit_category, index) for index in range(1, outfits_in_category) if (self.outfit_category, index) != current_outfit]
                    (_, outfit_index) = random.choice(available_outfits)
                else:
                    (_, outfit_index) = outfits.get_next_outfit_for_category(self.outfit_category)
                sim_info.generate_outfit(outfit_category=self.outfit_category, outfit_index=outfit_index, filter_flag=OutfitFilterFlag.NONE)
                self.entry_outfit = (self.outfit_category, outfit_index)
                self.exit_outfit = None

        FACTORY_TUNABLES = {'outfit_change_behavior': _OutfitChangeGeneration.TunableFactory()}

        def _create_outfit_change_internal(self, interaction, sim_info):
            return self.outfit_change_behavior(interaction, sim_info)

    def __init__(self, allow_outfit_change=True, **kwargs):
        options = {'no_change': TunableOutfitChange._OutfitChangeNone.TunableFactory()}
        if allow_outfit_change:
            options['for_reason'] = TunableOutfitChange._OutfitChangeForReason.TunableFactory()
            options['for_tags'] = TunableOutfitChange._OutfitChangeForTags.TunableFactory()
            options['for_new'] = TunableOutfitChange._OutfitChangeForNew.TunableFactory()
            options['from_participant'] = TunableOutfitChange._OutfitChangeFromParticipant.TunableFactory()
            options['from_zone'] = TunableOutfitChange._OutfitChangeFromZone.TunableFactory()
            options['from_picker'] = TunableOutfitChange._OutfitChangeFromPickedItemId.TunableFactory()
        kwargs.update(options)
        super().__init__(default='no_change', **kwargs)

class InteractionOnRouteOutfitChange(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(no_change=TunableOutfitChange._OutfitChangeNone.TunableFactory(), for_reason=TunableOutfitChange._OutfitChangeForReason.TunableFactory(on_entry=TunableEnumEntry(description='\n                    Define the change reason to apply on\n                    entry.\n                    ', tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid), locked_args={'on_exit': None}), from_zone=TunableOutfitChange._OutfitChangeFromZone.TunableFactory(locked_args={'auto_undo_on_exit': False}), default='no_change', **kwargs)

class ChangeOutfitLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'ChangeOutfitLiability'
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant of this interaction that is going to have\n            the specified affordance pushed upon them.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'outfit_change': TunableOutfitChange(description='\n            The outfit change we want to perform if the interaction does not\n            finish naturally.\n            ')}

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = interaction

    def on_add(self, interaction):
        self._interaction = interaction

    def release(self):
        sim = self._interaction.get_participant(self.subject)
        outfit = self.outfit_change.get_on_entry_outfit(self._interaction, sim_info=sim.sim_info)
        if outfit is None:
            outfit = self.outfit_change.get_on_exit_outfit(self._interaction, sim_info=sim.sim_info)
        if outfit is not None:
            sim.sim_info.set_current_outfit(outfit)
        super().release()
