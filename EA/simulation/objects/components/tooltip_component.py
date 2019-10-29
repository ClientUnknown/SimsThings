from _collections import defaultdictfrom collections import namedtupleimport operatorfrom protocolbuffers import UI_pb2 as ui_protocolsfrom event_testing.resolver import SingleObjectResolverfrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom objects.components import Component, types, componentmethod_with_fallback, componentmethodfrom objects.hovertip import HovertipStyle, TooltipFields, TooltipFieldConcatenationType, TooltipFieldsCompletefrom sims4.localization import TunableLocalizedStringFactoryVariant, LocalizationHelperTuning, ConcatenationStylefrom sims4.math import Thresholdfrom sims4.resources import CompoundTypesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableList, TunableTuple, TunableEnumEntry, HasTunableFactory, TunableMapping, Tunable, TunableReference, TunableResourceKeyfrom situations.service_npcs.modify_lot_items_tuning import TunableObjectModifyTestSetimport cachesimport objects.componentsimport servicesimport sims4.resourceslogger = sims4.log.Logger('Tooltip Component', default_owner='shipark')
class TooltipConcatenateData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'concatenation_type': TunableEnumEntry(description='\n            Type of concatenation that will be used on the tuned field and \n            the component field. \n            Example:\n            We tune the text "Crafted by Sim", and we tune it to CONCATENATE\n            BEFORE result would be:\n            Crafted by Sim CONCATENATION_STYLE RecipeName \n            \n            If we tune it to be CONCATENATE AFTER result will be:\n            RecipeName CONCATENATION_STYLE Crafted by Sim  \n            ', tunable_type=TooltipFieldConcatenationType, default=TooltipFieldConcatenationType.CONCATENATE_BEFORE), 'concatenation_style': TunableEnumEntry(description='\n            Style of concatenation that ill be use between the two fields\n            on the tunable. \n            \n            Example:\n            Using COMMA_SEPARATION = "string1, string"\n            \n            Using NEW_LINE_SEPARATION = "string1 \n string" \n            \n            Using CONCATENATE_SEPARATION string1 and string will be concatenated\n            but the order will change depending on the language.\n            For example if we concatenated the tested state of a potion we will\n            want the string "Tested Reaper Potion" as a concatenated string, \n            but this will be different in other languanges as the following \n            example shows:\n            English e.g. {0.String} {1.String} {"Untested"} {"Reaper Potion"}\n            Spanish e.g. {1.String} {0.String} {"Pocion de muerte} {"sin probar"}\n            So whenever you select CONCATENATE_SEPARATION be aware that the \n            order will be given by the language itself.\n            ', tunable_type=ConcatenationStyle, default=ConcatenationStyle.NEW_LINE_SEPARATION)}

class TooltipText(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'text': TunableLocalizedStringFactoryVariant(description='\n            Text that will be displayed on the tuned tooltip_fields of the \n            tooltip.\n            '), 'text_tokens': OptionalTunable(description="\n            If enabled, localization tokens to be passed into 'text' can be\n            explicitly defined. For example, you could use a participant that is\n            not normally used, such as a owned sim. Or you could also\n            pass in statistic and commodity values. If disabled, the standard\n            tokens from the interaction will be used (such as Actor and\n            TargetSim).\n            Participants tuned here should only be relevant to objects.  If \n            you try to tune a participant which only exist when you run an \n            interaction (e.g. carry_target) tooltip wont show anything.\n            ", tunable=LocalizationTokens.TunableFactory()), 'override_component_information': OptionalTunable(description='\n            When override component fields is chosen, this tooltip field\n            tuning will have the highest priority over what data is displayed.\n            So if an object has some fields set by the crafting component or\n            name component, if this is set, this will trump that information.\n                        \n            When concatenate with component fields is set, you have the option\n            to combine the tooltip information given by the a component with\n            any string you decide to add.\n            \n            Example:\n            If we choose to override component fields on the recipe_name field\n            of a craftable we will override the recipe_name that gets set \n            by the crafting system.\n            \n            If we choose to concatenate we could have things like \n            recipe_name, my_new_text\n            ', disabled_name='override_component_fields', enabled_name='concatenate_with_component_fields', tunable=TooltipConcatenateData.TunableFactory())}

class TransferCustomTooltip(BaseTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error("The Transfer Custom Tooltip loot tuned on: '{}' has a subject participant of None value.", self)
            return
        subject_tooltip_component = subject.get_component(types.TOOLTIP_COMPONENT)
        if subject_tooltip_component is None:
            logger.error("The Transfer Custom Tooltip Info loot tuned on: '{}' has a subject with no Tooltip Component.", self)
            return
        if target is None:
            logger.error("The Transfer Custom Tooltip Info loot tuned on: '{}' has a target participant of None value.", self)
            return
        if subject_tooltip_component.custom_tooltips is None:
            logger.error("The Transfer Custom Tooltip Info loot tuned on: '{}' has a subject with no Custom Tooltip in the Tooltip Component.", self)
            return
        target_tooltip_component = target.get_component(types.TOOLTIP_COMPONENT)
        if target_tooltip_component is None:
            logger.error("The Transfer Custom Tooltip Info loot tuned on: '{}' has a target with no Tooltip Component.", self)
            return
        target_tooltip_component.custom_tooltips = subject_tooltip_component.custom_tooltips
        subject_tooltip_component.update_object_tooltip()
        target_tooltip_component.update_object_tooltip()

class TooltipProvidingComponentMixin:

    def on_added_to_inventory(self):
        if self.hovertip_requested:
            self.owner.update_ui_metadata(use_cache=False)
TooltipPriorityData = namedtuple('TooltipPriorityData', ('field_data', 'field_priority'))
class TooltipComponent(Component, TooltipProvidingComponentMixin, HasTunableFactory, AutoFactoryInit, component_name=types.TOOLTIP_COMPONENT):
    FACTORY_TUNABLES = {'custom_tooltips': TunableList(description='\n            List of possible tooltips that will be displayed on an object when\n            moused over.\n            Each tooltip has its set of tests which will be evaluated whenever\n            the object its created or when its state changes.  The test that \n            passes its the tooltip that the object will display.\n            ', tunable=TunableTuple(description='\n                Variation of tooltips that may show when an object is hover \n                over.\n                Which tooltip is shows will depend on the object_tests that are \n                tuned.    \n                ', object_tests=TunableObjectModifyTestSet(description='\n                    All least one subtest group (AKA one list item) must pass\n                    within this list for the tooltip values to be valid on the \n                    object.\n                    '), tooltip_style=TunableEnumEntry(description="\n                    Types of possible tooltips that can be displayed for an\n                    object.  It's recomended to use default or \n                    HOVER_TIP_CUSTOM_OBJECT on most objects. \n                    ", tunable_type=HovertipStyle, default=HovertipStyle.HOVER_TIP_DEFAULT), tooltip_fields=TunableMapping(description='\n                    Mapping of tooltip fields to its localized values.  Since \n                    this fields are created from a system originally created \n                    for recipes, all of them may be tuned, but these are the \n                    most common fields to show on a tooltip:\n                    - recipe_name = This is the actual title of the tooltip.  \n                    This is the main text\n                    - recipe_description = This description refers to the main \n                    text that will show below the title\n                    - header = Smaller text that will show just above the title\n                    - subtext = Smaller text that will show just bellow the \n                    title\n                    ', key_type=TunableEnumEntry(description='\n                        Fields to be populated in the tooltip.  These fields\n                        will be populated with the text and tokens tuned.\n                        ', tunable_type=TooltipFields, default=TooltipFields.recipe_name), value_type=TooltipText.TunableFactory()), tooltip_main_icon=OptionalTunable(description='\n                    Main icon for the tooltip. Not all tooltip styles support\n                    tunable main icons. Consult your GPE and UI partners if \n                    you are unsure if this will work for your use case.\n                    ', tunable=TunableResourceKey(resource_types=CompoundTypes.IMAGE)))), 'state_value_numbers': TunableList(description='\n            Ordered list mapping a state value to a number that will be passed\n            as token to the State Value String.  Will use the number associated\n            with the first state matched.\n            \n            e.g.\n            if the object has all the states and the list looks like:\n            state value masterwork\n            state value poor quality\n            \n            then the number passed to the State Value Strings will be the number\n            associated with the masterwork state.\n            \n            Does *not* have to be the same size or states as the state value\n            strings\n            ', tunable=TunableTuple(description='\n                Map of state value to an number that will be passed as token to\n                the state value strings   \n                ', state_value=TunableReference(description='\n                    The state value for the associated number\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', pack_safe=True), number=Tunable(description='\n                    Number passed to localization as the token for the state value\n                    strings below\n                    ', tunable_type=float, default=0))), 'state_value_strings': TunableList(description='\n            List of lists of mapping a state value to a localized string.\n            The first string mapped to a valid state in each sub list will be\n            added.\n            \n            e.g.\n            if the object has all the states and the lists look like:\n            List 1:\n                state_value masterwork\n                state_value poor quality\n            list 2:\n                state_value flirty\n                \n            then it will show the strings for masterwork and flirty, but\n            not the string for poor quality.\n            \n            Does *not* have to be the same size or states as the state value \n            numbers.  Additionally, it does *not* have to utilize the number\n            passed in as token from State Value Numbers.  i.e. if something is \n            *always* Comfort: 5, regardless of quality, the string can simply \n            be "Comfort: 5".\n            ', tunable=TunableList(description='\n                Ordered list mapping a state value to a localized string.\n                The first string mapped to a valid state will be added.\n                ', tunable=TunableTuple(description='\n                    Map of state value to a string\n                    ', state_value=TunableReference(description='\n                        The state value for the associated string\n                        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', pack_safe=True), text=TunableLocalizedStringFactoryVariant(description='\n                        Text that will be displayed if the object has the\n                        associated state value, with any number matched to a state\n                        in state value numbers passed in as {0.Number}, defaulting to\n                        0 if no state in the state value numbers matches\n                        ')))), 'tooltip_tests': TunableObjectModifyTestSet(description='\n            At least one subtest group (AKA one list item) must pass within \n            this list for the tooltip values to be shown on the object.\n            '), 'update_if_stat_changes': Tunable(description='\n            If enabled and the tooltip has a statistic based string token, any\n            change to the relevant statistic will cause the tooltip to update.\n            ', tunable_type=bool, default=False)}
    SUBTEXT_HANDLE = 'subtext'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ui_metadata_handles = {}
        self._external_field_to_data = {}
        self.hovertip_requested = False
        self._stat_update_listeners = defaultdict(list)

    def on_add(self):
        if self.update_if_stat_changes:
            resolver = SingleObjectResolver(self.owner)
            always_true_threshold = Threshold(-1, operator.ne)
            for custom_tooltip in self.custom_tooltips:
                for tooltip_value in custom_tooltip.tooltip_fields.values():
                    if tooltip_value.text_tokens is not None:
                        for text_token in tooltip_value.text_tokens.tokens:
                            if text_token.token_type == LocalizationTokens.TOKEN_STATISTIC:
                                participant = text_token.participant
                                statistic = text_token.statistic
                                for obj in resolver.get_participants(participant):
                                    if obj.has_component(objects.components.types.STATISTIC_COMPONENT):
                                        statistic_tracker = obj.get_component(objects.components.types.STATISTIC_COMPONENT).get_statistic_tracker()
                                        statistic_listener = statistic_tracker.create_and_add_listener(statistic, always_true_threshold, lambda _: self.update_object_tooltip())
                                        self._stat_update_listeners[statistic_tracker].append(statistic_listener)

    def on_remove(self):
        if self.update_if_stat_changes:
            for (tracker, listeners) in self._stat_update_listeners.items():
                for listener in listeners:
                    tracker.remove_listener(listener)
            self._stat_update_listeners.clear()

    def on_hovertip_requested(self):
        if not self.hovertip_requested:
            self.hovertip_requested = True
            self.update_object_tooltip()
            return True
        return False

    @componentmethod_with_fallback(lambda : None)
    def update_object_tooltip(self):
        if not self.hovertip_requested:
            return
        if services.client_manager() is None:
            return
        caches.clear_all_caches()
        tooltip_component = None
        tooltip_override = self.owner.get_tooltip_override()
        if tooltip_override is not None:
            tooltip_component = tooltip_override.get_component(types.TOOLTIP_COMPONENT)
        if tooltip_component is None:
            tooltip_component = self
        old_handles = dict(self._ui_metadata_handles)
        try:
            self._ui_metadata_handles = {}
            subtext_field = None
            resolver = SingleObjectResolver(self.owner)
            if self.tooltip_tests.run_tests(resolver):
                for (name, value, tooltip_override_data) in tooltip_component._ui_metadata_gen():
                    external_field_data_tuple = tooltip_component._external_field_to_data.get(name)
                    if tooltip_override_data is not None:
                        if tooltip_override_data.concatenation_type == TooltipFieldConcatenationType.CONCATENATE_BEFORE:
                            value = LocalizationHelperTuning.get_separated_string_by_style(tooltip_override_data.concatenation_style, value, external_field_data_tuple.field_data)
                        else:
                            value = LocalizationHelperTuning.get_separated_string_by_style(tooltip_override_data.concatenation_style, external_field_data_tuple.field_data, value)
                    handle = self.owner.add_ui_metadata(name, value)
                    self._ui_metadata_handles[name] = handle
                    if external_field_data_tuple and name == self.SUBTEXT_HANDLE:
                        subtext_field = value
                if tooltip_component._ui_metadata_handles:
                    subtext = tooltip_component.get_state_strings(subtext_field)
                    if subtext is not None:
                        handle = self.owner.add_ui_metadata(self.SUBTEXT_HANDLE, subtext)
                        self._ui_metadata_handles[self.SUBTEXT_HANDLE] = handle
                for index_unused in tooltip_component._external_field_to_data.keys() - self._ui_metadata_handles.keys():
                    external_field_data = tooltip_component._external_field_to_data.get(index_unused)
                    handle = self.owner.add_ui_metadata(index_unused, external_field_data.field_data)
                    self._ui_metadata_handles[index_unused] = handle
        finally:
            for handle in old_handles.values():
                self.owner.remove_ui_metadata(handle)
            self.owner.update_ui_metadata()
        if not self._ui_metadata_handles:
            self.owner.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_DISABLED

    @componentmethod_with_fallback(lambda : None)
    def get_state_strings(self, first_string=None):
        obj = self.owner
        int_token = 0
        for state_int_data in self.state_value_numbers:
            state_value = state_int_data.state_value
            if state_value is None:
                pass
            elif obj.has_state(state_value.state) and obj.get_state(state_value.state) is state_value:
                int_token = state_int_data.number
                break
        bullet_points = [] if first_string is None else [first_string]
        for state_string_datas in self.state_value_strings:
            for state_string_data in state_string_datas:
                state_value = state_string_data.state_value
                if state_value is None:
                    pass
                elif obj.has_state(state_value.state) and obj.get_state(state_value.state) is state_value:
                    bullet_point = state_string_data.text(int_token)
                    bullet_points.append(bullet_point)
                    break
        if bullet_points:
            if len(bullet_points) == 1:
                return LocalizationHelperTuning.get_raw_text(bullet_points[0])
            else:
                return LocalizationHelperTuning.get_bulleted_list((None,), bullet_points)

    def on_state_changed(self, state, old_value, new_value, from_init):
        self.update_object_tooltip()

    def _ui_metadata_gen(self):
        resolver = SingleObjectResolver(self.owner)
        for tooltip_data in self.custom_tooltips:
            object_tests = tooltip_data.object_tests
            if not object_tests or not object_tests.run_tests(resolver):
                pass
            else:
                self.owner.hover_tip = tooltip_data.tooltip_style
                for (tooltip_key, tooltip_text) in tooltip_data.tooltip_fields.items():
                    if tooltip_text.text_tokens is not None:
                        tokens = tooltip_text.text_tokens.get_tokens(resolver)
                    else:
                        tokens = ()
                    if tooltip_key == TooltipFields.rel_override_id:
                        logger.error('Attempting to set rel_override_id without a required token of type Game Object Property, Object Type Rel Id. Tooltip Field not created on object')
                        break
                        yield (TooltipFieldsComplete(tooltip_key).name, tokens[0], tooltip_text.override_component_information)
                    else:
                        yield (TooltipFieldsComplete(tooltip_key).name, tooltip_text.text(*tokens), tooltip_text.override_component_information)
                if tooltip_data.tooltip_main_icon is not None:
                    icon_data = sims4.resources.get_protobuff_for_key(tooltip_data.tooltip_main_icon)
                    yield (TooltipFieldsComplete.main_icon.name, icon_data, None)

    @componentmethod_with_fallback(lambda *args, **kwargs: False)
    def update_tooltip_field(self, field_id, field_data, priority=0, should_update=False):
        field_string = TooltipFieldsComplete(field_id).name
        data_priority_tuple = self._external_field_to_data.get(field_string)
        self._external_field_to_data[field_string] = TooltipPriorityData(field_data, priority)
        if (data_priority_tuple is None or priority >= data_priority_tuple.field_priority) and should_update:
            self.update_object_tooltip()

    @componentmethod_with_fallback(lambda *args, **kwargs: None)
    def get_tooltip_field(self, field, context=None, target=None):
        if field == TooltipFields.relic_description:
            sim = context.sim
            if sim is None:
                return
            return sim.sim_info.relic_tracker.get_description_for_objects(self.owner, target)
        name = TooltipFieldsComplete(field).name
        existing_handle = self._ui_metadata_handles.get(name, None)
        if existing_handle is not None:
            (_, _, value) = self.owner.get_ui_metadata(existing_handle)
            return value
        tooltip_component = None
        tooltip_override = self.owner.get_tooltip_override()
        if tooltip_override is not None:
            tooltip_component = tooltip_override.get_component(types.TOOLTIP_COMPONENT)
        if tooltip_component is None:
            tooltip_component = self
        tooltip_text = None
        resolver = SingleObjectResolver(self.owner)
        for tooltip_data in tooltip_component.custom_tooltips:
            object_tests = tooltip_data.object_tests
            if object_tests and not object_tests.run_tests(resolver):
                pass
            else:
                tooltip_text = tooltip_data.tooltip_fields.get(field, tooltip_text)
        if tooltip_text is not None:
            if tooltip_text.text_tokens is not None:
                tokens = tooltip_text.text_tokens.get_tokens(resolver)
                if None in tokens:
                    return
            else:
                tokens = ()
            text = tooltip_text.text(*tokens)
            external_field_data_tuple = tooltip_component._external_field_to_data.get(name)
            if external_field_data_tuple:
                tooltip_override_data = tooltip_text.override_component_information
                if tooltip_override_data is not None:
                    if tooltip_override_data.concatenation_type == TooltipFieldConcatenationType.CONCATENATE_BEFORE:
                        text = LocalizationHelperTuning.get_separated_string_by_style(tooltip_override_data.concatenation_style, text, external_field_data_tuple.field_data)
                    else:
                        text = LocalizationHelperTuning.get_separated_string_by_style(tooltip_override_data.concatenation_style, external_field_data_tuple.field_data, text)
            if tooltip_component._ui_metadata_handles:
                subtext = tooltip_component.get_state_strings(text)
                if subtext is not None:
                    text = subtext
            handle = self.owner.add_ui_metadata(name, text)
            self._ui_metadata_handles[name] = handle
            return text

    @componentmethod
    def get_tooltip_override(self, *args, **kwargs):
        pass
