from sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableColor, TunableFactory, Tunable, TunableTuple, TunableList, TunableVariant, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom singletons import DEFAULTimport interactionsimport servicesimport sims4.reloadimport sims4.resourceswith sims4.reload.protected(globals()):
    SNIPPETS = {}
    SNIPPET_CLASS_NAMES = {}
    SNIPPET_VARIANTS = {}
    SNIPPET_REFERENCES = {}
    SNIPPET_VARIANT_LISTS = {}
    SNIPPET_VARIANT_LIST_NAMES = {}
    SNIPPET_VARIANT_LIST_REFERENCES = {}
def define_snippet(snippet_type, snippet, use_list_reference=False):
    module_dict = globals()
    name = snippet_type.title().replace('_', '')
    SNIPPET_CLASS_NAMES[snippet_type] = name
    module_name = module_dict['__name__']
    snippet_manager = services.snippet_manager()
    bases = ()
    class_dict = {'__module__': module_name, 'snippet_type': snippet_type}
    SnippetInstance = SnippetInstanceMetaclass.__new__(SnippetInstanceMetaclass, name, bases, class_dict, manager=snippet_manager)

    class SnippetReference(TunableSnippetReference):

        def __init__(self, description=DEFAULT, **kwargs):
            if description is DEFAULT:
                description = 'A reference to a {} tuning snippet.'.format(name)
            super().__init__(SnippetInstance, description=description, **kwargs)

    SnippetReference.__name__ = 'Tunable{}Reference'.format(name)
    SNIPPET_REFERENCES[snippet_type] = SnippetReference

    class SnippetVariant(TunableSnippet):

        def __init__(self, allow_list_reference=use_list_reference, **kwargs):
            super().__init__(snippet_type, allow_list_reference=allow_list_reference, **kwargs)

    SnippetVariant.__name__ = 'Tunable{}Snippet'.format(name)
    SNIPPET_VARIANTS[snippet_type] = SnippetVariant
    backup_dict = module_dict.copy()
    with sims4.reload.protected(module_dict):
        module_dict[name] = SnippetInstance
        module_dict[SnippetVariant.__name__] = SnippetVariant
        module_dict[SnippetReference.__name__] = SnippetReference
    sims4.reload.update_module_dict(backup_dict, module_dict)
    if isinstance(snippet, type):
        snippet = snippet()
    SnippetInstance.add_tunable_to_instance('value', snippet)
    SNIPPETS[snippet_type] = snippet
    if use_list_reference:
        list_name = '{}List'.format(name)
        SNIPPET_VARIANT_LIST_NAMES[snippet_type] = list_name
        SnippetVariantListInstance = SnippetInstanceMetaclass.__new__(SnippetInstanceMetaclass, list_name, bases, class_dict, manager=snippet_manager)
        SnippetVariantListInstance.is_list = True

        class SnippetVariantList(TunableSnippetVariantList):

            def __init__(self, **kwargs):
                super().__init__(SnippetVariant, **kwargs)

        SnippetVariantList.__name__ = '{}SnippetVariantList'.format(name)
        SNIPPET_VARIANT_LISTS[snippet_type] = SnippetVariantList

        class SnippetVariantListReference(TunableSnippetVariantListReference):

            def __init__(self, **kwargs):
                super().__init__(SnippetVariantListInstance, **kwargs)

        SnippetVariantListReference.__name__ = '{}SnippetVariantListReference'.format(name)
        SNIPPET_VARIANT_LIST_REFERENCES[snippet_type] = SnippetVariantListReference
        backup_dict = module_dict.copy()
        with sims4.reload.protected(module_dict):
            module_dict[list_name] = SnippetVariantListInstance
            module_dict[SnippetVariantList.__name__] = SnippetVariantList
            module_dict[SnippetVariantListReference.__name__] = SnippetVariantListReference
        sims4.reload.update_module_dict(backup_dict, module_dict)
        SnippetVariantListInstance.add_tunable_to_instance('value', SnippetVariantList(allow_list_reference=False))
    return (SnippetReference, SnippetVariant)

def is_snippet_list(snippet):
    if isinstance(snippet, SnippetInstanceMetaclass) and snippet.is_list:
        return True
    return False

def flatten_snippet_list(snippets):
    flattened_snippets = []
    for snippet in snippets:
        if is_snippet_list(snippet):
            flattened_snippets.extend(snippet)
        else:
            flattened_snippets.append(snippet)
    return flattened_snippets

class SnippetInstanceMetaclass(TunedInstanceMetaclass):

    def __bool__(self):
        return True

    def __len__(self):
        return len(self.value)

    def __getitem__(self, key):
        return self.value.__getitem__(key)

    def __iter__(self):
        return self.value.__iter__()

    def __call__(self, *args, **kwargs):
        return self.value.__call__(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.value, name)

    is_list = False

class TunableSnippet(TunableVariant):
    __slots__ = ('_snippet_type',)

    def __init__(self, snippet_type, description=None, allow_list_reference=False, pack_safe=False, **kwargs):
        snippet_description = "This may be tuned in place here using 'literal' or as a reference to a {} tuning snippet.".format(SNIPPET_CLASS_NAMES[snippet_type])
        if description:
            description = '{} ({})'.format(description, snippet_description)
        else:
            description = snippet_description
        self._snippet_type = snippet_type
        if allow_list_reference:
            kwargs['list_reference'] = SNIPPET_VARIANT_LIST_REFERENCES[snippet_type](pack_safe=pack_safe)
        super().__init__(literal=SNIPPETS[snippet_type], reference=SNIPPET_REFERENCES[snippet_type](pack_safe=pack_safe), default='literal', description=description, **kwargs)

class TunableSnippetReference(TunableReference):

    def __init__(self, snippet_class, **kwargs):
        super().__init__(services.snippet_manager(), class_restrictions=snippet_class, **kwargs)

class TunableSnippetVariantList(TunableList):

    def __init__(self, snippet_variant_class, allow_list_reference=False, **kwargs):
        super().__init__(tunable=snippet_variant_class(allow_list_reference=allow_list_reference), **kwargs)

class TunableSnippetVariantListReference(TunableReference):

    def __init__(self, snippet_variant_list_instance, **kwargs):
        super().__init__(services.snippet_manager(), class_restrictions=snippet_variant_list_instance, **kwargs)
AFFORDANCE_FILTER = 'affordance_filter'AFFORDANCE_LIST = 'affordance_list'ANIMATION = 'animation'ANIMATION_LIST = 'animation_list'ANIMATION_TRIPLET = 'animation_triplet'ANIMATION_TRIPLET_LIST = 'animation_triplet_list'COLOR = 'color'POSTURE_TYPE_LIST = 'posture_type_list'OBJECT_LIST = 'objects_list'VENUE_LIST = 'venue_list'SCREEN_SLAM = 'screen_slam'ANIMATION_ACTOR_MAP = 'animation_actor_map'MUSIC_TRACK_DATA = 'music_track_data'(TunableAffordanceListReference, TunableAffordanceListSnippet) = define_snippet(AFFORDANCE_LIST, TunableList(TunableReference(services.affordance_manager(), pack_safe=True)))(TunableVenueListReference, TunableVenueListSnippet) = define_snippet(VENUE_LIST, TunableList(TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True, tuning_group=GroupNames.VENUES)))
class _TunableAffordanceFilter(TunableFactory, is_fragment=True):

    @staticmethod
    def _filter(affordance, default_inclusion, affordance_types=None, allow_ignore_exclude_all=False):
        affordance = affordance.affordance
        if affordance_types is None:
            if hasattr(affordance, '__mro__'):
                affordance_types = set(affordance.__mro__)
            else:
                affordance_types = {affordance}
        excluded_affordances = set(default_inclusion.exclude_affordances)
        for affordance_list in default_inclusion.exclude_lists:
            excluded_affordances.update(affordance_list)
        included_affordances = set(default_inclusion.include_affordances)
        for affordance_list in default_inclusion.include_lists:
            included_affordances.update(affordance_list)
        if default_inclusion.include_all_by_default or allow_ignore_exclude_all and affordance.ignore_exclude_all_compatibility:
            excluded_affordances -= included_affordances
            return not affordance_types & excluded_affordances
        else:
            included_affordances -= excluded_affordances
            return affordance_types & included_affordances

    FACTORY_TYPE = _filter

    def __init__(self, description='An affordance filter.', **kwargs):
        AffordanceReference = TunableReference(services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)
        super().__init__(default_inclusion=TunableVariant(include_all=TunableTuple(include_all_by_default=Tunable(bool, True, description=''), include_affordances=TunableList(AffordanceReference, display_name='Filter Exception Items'), exclude_affordances=TunableList(AffordanceReference, display_name='Blacklist Items'), include_lists=TunableList(TunableAffordanceListReference(pack_safe=True), display_name='Filter Exception Lists'), exclude_lists=TunableList(TunableAffordanceListReference(pack_safe=True), display_name='Blacklist Lists'), locked_args={'include_all_by_default': True}, description='\n                        This will create compatibility with all interactions by default,\n                        except those that are blacklisted, from which you can define\n                        exceptions.'), exclude_all=TunableTuple(include_all_by_default=Tunable(bool, False, description=''), include_affordances=TunableList(AffordanceReference, display_name='Whitelist Items'), exclude_affordances=TunableList(AffordanceReference, display_name='Filter Exception Items'), include_lists=TunableList(TunableAffordanceListReference(pack_safe=True), display_name='Whitelist Lists'), exclude_lists=TunableList(TunableAffordanceListReference(pack_safe=True), display_name='Filter Exception Lists'), locked_args={'include_all_by_default': False}, description='\n                        This will create incompatibility with all interactions by\n                        default, except those that are whitelisted, from which you\n                        can define exceptions.'), default='include_all', description='\n                    This defines the default compatibility with other interactions.'), description=description, **kwargs)
(TunableAffordanceFilterReference, TunableAffordanceFilterSnippet) = define_snippet(AFFORDANCE_FILTER, _TunableAffordanceFilter)(TunableColorReference, TunableColorSnippet) = define_snippet(COLOR, TunableColor())