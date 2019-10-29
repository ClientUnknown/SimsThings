from numbers import Numberimport randomfrom protocolbuffers.Localization_pb2 import LocalizedString, LocalizedStringTokenfrom distributor.rollback import ProtocolBufferRollbackfrom sims4.tuning.tunable import Tunable, get_default_display_name, TunableVariant, TunableList, TunableFactoryfrom sims4.tuning.tunable_base import Attributesfrom singletons import DEFAULTfrom snippets import define_snippetimport enumimport sims4.loglogger = sims4.log.Logger('Localization', default_owner='epanero')
class ConcatenationStyle(enum.Int):
    COMMA_SEPARATION = 0
    NEW_LINE_SEPARATION = 1
    CONCATENATE_SEPARATION = 2

def _create_localized_string(string_id, *tokens) -> LocalizedString:
    proto = LocalizedString()
    proto.hash = string_id
    create_tokens(proto.tokens, tokens)
    return proto

def create_sub_token_list(token_msg, token):
    try:
        for sub_token in token:
            if hasattr(sub_token, 'populate_localization_token'):
                token_msg.type = LocalizedStringToken.SIM_LIST
                with ProtocolBufferRollback(token_msg.sim_list) as sub_token_msg:
                    sub_token.populate_localization_token(sub_token_msg)
            else:
                raise
    except:
        logger.error('Trying to populate localization token with invalid token: {}.', token)
        return False

def create_tokens(tokens_msg, *tokens):
    for token in tokens:
        token_msg = tokens_msg.add()
        token_msg.type = LocalizedStringToken.INVALID
        if token is not None:
            if hasattr(token, 'populate_localization_token'):
                token.populate_localization_token(token_msg)
            elif isinstance(token, Number):
                token_msg.type = LocalizedStringToken.NUMBER
                token_msg.number = token
            elif isinstance(token, str):
                token_msg.type = LocalizedStringToken.RAW_TEXT
                token_msg.raw_text = token
            elif isinstance(token, LocalizedString):
                token_msg.type = LocalizedStringToken.STRING
                token_msg.text_string = token
            else:
                create_sub_token_list(token_msg, token)
with sims4.reload.protected(globals()):
    NULL_LOCALIZED_STRING = _create_localized_string(0)
    NULL_LOCALIZED_STRING_FACTORY = lambda *_, **__: NULL_LOCALIZED_STRING
class TunableLocalizedStringFactory(Tunable):

    class _Wrapper:
        __slots__ = ('_string_id',)

        def __init__(self, string_id):
            self._string_id = string_id

        def __call__(self, *tokens):
            return _create_localized_string(self._string_id, tokens)

        def __bool__(self):
            if self._string_id:
                return True
            return False

    def __init__(self, *, default=DEFAULT, description='A localized string that may use tokens.', allow_none=False, allow_catalog_name=False, **kwargs):
        if default is DEFAULT:
            default = 0
        super().__init__(int, default=default, description=description, needs_tuning=False, **kwargs)
        self._allow_none = allow_none
        self._allow_catalog_name = allow_catalog_name
        self.cache_key = 'LocalizedStringFactory'

    @property
    def export_class(self):
        return 'TunableLocalizedString'

    @property
    def display_name(self):
        if self._display_name is None:
            name = self.name
            if self.name.startswith('create_'):
                name = name[7:]
            return get_default_display_name(name)
        return super().display_name

    def export_desc(self):
        export_dict = super().export_desc()
        if self._allow_none:
            export_dict[Attributes.AllowNone] = self._allow_none
        if self._allow_catalog_name:
            export_dict[Attributes.AllowCatalogName] = self._allow_catalog_name
        return export_dict

    def _export_default(self, value):
        if value is not None:
            return hex(value)
        return str(value)

    def _convert_to_value(self, string_id):
        if string_id is None:
            return
        if isinstance(string_id, str):
            string_id = int(string_id, 0)
        return TunableLocalizedStringFactory._Wrapper(string_id)

class TunableLocalizedString(TunableLocalizedStringFactory):

    def __init__(self, *, default=DEFAULT, description='A localized string that may NOT require tokens.', **kwargs):
        super().__init__(description=description, default=default, **kwargs)
        self.cache_key = 'LocalizedString'

    def _convert_to_value(self, string_id):
        if string_id is None:
            return
        return super()._convert_to_value(string_id)()

class TunableLocalizedStringFactoryVariant(TunableVariant):
    is_factory = True

    class TunableLocalizedStringFactoryVariation(TunableFactory):

        @staticmethod
        def _factory(*args, variations, **kwargs):
            variation = random.choice(variations)
            return variation(*args, **kwargs)

        FACTORY_TYPE = _factory

        def __init__(self, description='A list of possible localized string variations.', allow_none=False, **kwargs):
            super().__init__(variations=TunableList(TunableLocalizedStringFactory(allow_none=allow_none)), description=description, **kwargs)

    class TunableLocalizedStringVariation(TunableLocalizedStringFactoryVariation):

        @staticmethod
        def _factory(variations):
            variation = random.choice(variations)
            return variation()

    class TunableLocalizedStringFactoryConcatenation(TunableFactory):

        @staticmethod
        def _factory(*args, concatenations, **kwargs):
            return LocalizationHelperTuning.get_new_line_separated_strings(*(c(*args, **kwargs) for c in concatenations))

        FACTORY_TYPE = _factory

        def __init__(self, description='A list of localized string concatenations. These strings will be joined together into single line-separated string', allow_none=False, **kwargs):
            super().__init__(concatenations=TunableList(TunableLocalizedStringSnippet(pack_safe=True)), description=description, **kwargs)

    class TunableLocalizedStringConcatenation(TunableLocalizedStringFactoryConcatenation):

        @staticmethod
        def _factory(concatenations):
            return LocalizationHelperTuning.get_new_line_separated_strings(*(c() for c in concatenations))

    def __init__(self, description='A localization string. This may either be a single string, a set to pick a random string from, or concatenation from list of string.', allow_none=False, **kwargs):
        super().__init__(single=TunableLocalizedStringFactory(allow_none=allow_none) if self.is_factory else TunableLocalizedString(allow_none=allow_none), variation=self.TunableLocalizedStringFactoryVariation(allow_none=allow_none) if self.is_factory else self.TunableLocalizedStringVariation(allow_none=allow_none), concatenation=self.TunableLocalizedStringFactoryConcatenation(allow_none=allow_none) if self.is_factory else self.TunableLocalizedStringConcatenation(allow_none=allow_none), default='single', description=description, **kwargs)

    @property
    def display_name(self):
        if self._display_name is DEFAULT:
            name = self.name
            if self.name.startswith('create_'):
                name = name[7:]
            return get_default_display_name(name)
        return super().display_name

class TunableLocalizedStringVariant(TunableLocalizedStringFactoryVariant):
    is_factory = False

class LocalizationHelperTuning:
    MAX_LIST_LENGTH = 16
    BULLETED_LIST_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that will define the bulleted list start structure,\n        this item will receive a string followed by a bulleted item\n        e.g. {0.String}\n * {1.String}\n        ')
    BULLETED_ITEM_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that will define a single bulleted item.\n        e.g.  * {0.String}\n        ')
    SIM_FIRST_NAME_LOCALIZATION = TunableLocalizedStringFactory(description='\n        Localized string that will recieve a sim and will return the First Name\n        of the sim.\n        e.g. {0.SimFirstName}\n        ')
    OBJECT_NAME_LOCALIZATION = TunableLocalizedStringFactory(description='\n        Localized factory that will receive an object and will return the\n        localized catalog name of that object name\n        e.g. {0.ObjectName} \n        ')
    OBJECT_NAME_INDETERMINATE = TunableLocalizedStringFactory(description='\n        Localized factory that will receive an object and will return the object\n        name preceded by the appropriate indeterminate article.\n        e.g. A/an {0.ObjectName}\n        ')
    OBJECT_NAME_COUNT = TunableLocalizedStringFactory(description='\n        Localized string that defines the pattern for object counts.\n        e.g. {0.Number} {S0.{S1.ObjectName}}{P0.{P1.ObjectName}}\n        ')
    OBJECT_DESCRIPTION_LOCALIZATION = TunableLocalizedStringFactory(description='\n        Localized factory that will receive an object and will return the\n        localized catalog description of that object\n        e.g. {0.ObjectDescription} \n        ')
    NAME_VALUE_PAIR_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that will define the pattern for name-value pairs,\n        e.g. {0.String}: {1.String}\n        ')
    NAME_VALUE_PARENTHESIS_PAIR_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that will define the pattern for name-value pairs using\n        parenthesis. \n        \n        e.g. {0.String} ({1.String})\n        ')
    COMMA_LIST_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that defines the format for a comma-separated list.\n        \n        e.g. {0.String}, {1.String}\n        ')
    COMMA_LIST_STRUCTURE_LAST_ELEMENT = TunableLocalizedStringFactory(description='\n        Localized string that defines the format of the last element of a comma-\n        separated list. \n        \n        e.g. {0.String}, and {1.String}\n        ')
    COMMA_LIST_STRUCTURE_TWO_ELEMENTS = TunableLocalizedStringFactory(description='\n        Localized string that defines the format of a two-element sequence of a\n        comma-separated list. This does not necessarily have to include a comma.\n        \n        e.g. {0.String} and {1.String}\n        ')
    NEW_LINE_LIST_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that will define the format for two new-line-seperated strings.\n        e.g. {0.String}\n{1.String}\n        ')
    CONCATENATED_STRING_STRUCTURE = TunableLocalizedStringFactory(description='\n        Localized string that will define the format for two concatenated \n        strings.  The purpose of this string is to be able to combine two \n        strings in the game like a state of an object with its name:\n        "Tested Reaper Potion" and "Untested Reaper Potion" having the \n        "Tested" be a string and "Reaper Potion" be a second string separated\n        by a space.\n        The localized string for this concatenation WILL NOT ALWAYS be string0\n        followed by string1, since in different languages the order might\n        be different, so when using this concatenated string structure type\n        be aware of this.\n        English e.g. {0.String} {1.String} {"Untested"} {"Reaper Potion"}\n        Spanish e.g. {1.String} {0.String} {"Pocion de muerte} {"sin probar"}\n        ')
    RAW_TEXT = TunableLocalizedStringFactory(description='\n        Localized string that will define take a raw string and set it as a\n        localized string.\n        e.g. {0.String}\n        ')
    MONEY = TunableLocalizedStringFactory(description='\n        Localized string that outputs a Simoleon amount when provided a number.\n        e.g. {0.Money}\n        ')
    ELLIPSIS = TunableLocalizedStringFactory(description='\n        Localized string that outputs a string followed by ellipsis.\n        e.g. {0.String}...\n        ')
    FOR_MONEY = TunableLocalizedStringFactory(description='\n        Localized string that outputs a "For Simoleon amount" when provided a number.\n        e.g. For {0.Money}\n        ')
    START_TIME_TO_END_TIME = TunableLocalizedStringFactory(description='\n        Localized string that outputs a start to end time when provided\n        two DateAndTimes.\n        e.g. {0.TimeShort} to {1.TimeShort}\n        ')

    @classmethod
    def get_object_name(cls, obj_def):
        return cls.OBJECT_NAME_LOCALIZATION(obj_def)

    @classmethod
    def get_sim_name(cls, sim):
        return cls.SIM_FIRST_NAME_LOCALIZATION(sim)

    @classmethod
    def get_object_name_indeterminate(cls, obj_def):
        return cls.OBJECT_NAME_INDETERMINATE(obj_def)

    @classmethod
    def get_object_count(cls, count, obj_def):
        return cls.OBJECT_NAME_COUNT(count, obj_def)

    @classmethod
    def get_object_description(cls, obj_def):
        return cls.OBJECT_DESCRIPTION_LOCALIZATION(obj_def)

    @classmethod
    def get_bulleted_list(cls, header_string, *localized_strings):
        bulleted_string = None
        for list_item in tuple(filter(None, localized_strings))[:LocalizationHelperTuning.MAX_LIST_LENGTH]:
            if bulleted_string is None:
                if header_string is None:
                    bulleted_string = cls.BULLETED_ITEM_STRUCTURE(list_item)
                else:
                    bulleted_string = cls.BULLETED_LIST_STRUCTURE(header_string, list_item)
                    bulleted_string = cls.BULLETED_LIST_STRUCTURE(bulleted_string, list_item)
            else:
                bulleted_string = cls.BULLETED_LIST_STRUCTURE(bulleted_string, list_item)
        return bulleted_string

    @classmethod
    def get_name_value_pair(cls, name_string, value_string):
        return cls.NAME_VALUE_PAIR_STRUCTURE(name_string, value_string)

    @classmethod
    def get_comma_separated_list(cls, *strings):
        if len(strings) == 2:
            return cls.COMMA_LIST_STRUCTURE_TWO_ELEMENTS(strings[0], strings[1])
        return cls._get_string_separated_string(*strings, separator=cls.COMMA_LIST_STRUCTURE, last_separator=cls.COMMA_LIST_STRUCTURE_LAST_ELEMENT)

    @classmethod
    def get_comma_separated_sim_names(cls, *sims):
        return cls.get_comma_separated_list(*tuple(cls.get_sim_name(sim) for sim in sims))

    @classmethod
    def get_new_line_separated_strings(cls, *strings):
        return cls._get_string_separated_string(*strings, separator=cls.NEW_LINE_LIST_STRUCTURE)

    @classmethod
    def _get_string_separated_string(cls, *strings, separator, last_separator=None):
        if not strings:
            return
        last_separator = last_separator or separator
        strings = strings[:LocalizationHelperTuning.MAX_LIST_LENGTH]
        result = strings[0]
        for string in strings[1:-1]:
            result = separator(result, string)
        if len(strings) > 1:
            result = last_separator(result, strings[-1])
        return result

    @classmethod
    def get_separated_string_by_style(cls, separation_style, *strings):
        if separation_style == ConcatenationStyle.COMMA_SEPARATION:
            return cls.get_comma_separated_list(*strings)
        if separation_style == ConcatenationStyle.NEW_LINE_SEPARATION:
            return cls.get_new_line_separated_strings(*strings)
        if separation_style == ConcatenationStyle.CONCATENATE_SEPARATION:
            return cls._get_string_separated_string(*strings, separator=cls.CONCATENATED_STRING_STRUCTURE)
        logger.error('Separate strings got an invalid concatenation style enum {}', separation_style, owner='camilogarcia')

    @classmethod
    def get_raw_text(cls, text):
        return cls.RAW_TEXT(text)

    @classmethod
    def get_for_money(cls, money_amount):
        return cls.FOR_MONEY(money_amount)

    @classmethod
    def get_money(cls, money_amount):
        return cls.MONEY(money_amount)

    @classmethod
    def get_ellipsized_text(cls, text):
        return cls.ELLIPSIS(text)

    @classmethod
    def get_start_time_to_end_time(cls, start_time, end_time):
        return cls.START_TIME_TO_END_TIME(start_time, end_time)
(_, TunableLocalizedStringSnippet) = define_snippet('Localized_String', TunableLocalizedStringFactory())