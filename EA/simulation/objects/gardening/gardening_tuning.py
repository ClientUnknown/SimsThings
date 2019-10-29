from objects.collection_manager import ObjectCollectionRarityfrom objects.components.state import ObjectState, ObjectStateValuefrom seasons.seasons_tuning import SeasonsTuningfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.tunable import TunableList, TunableRange, TunableInterval, TunableMapping, TunableReference, TunableEnumEntry, TunableTuple, TunableVariant, TunablePercent, Tunable, TunableSetfrom statistics.commodity import Commodityfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.resources
class GardeningTuning:
    INHERITED_STATE = ObjectState.TunableReference(description='\n        Controls the state value that will be inherited by offspring.\n        ')
    SPONTANEOUS_GERMINATION_COMMODITY = Commodity.TunableReference()
    SPONTANEOUS_GERMINATION_COMMODITY_VARIANCE = TunableRange(description='\n        Max variance to apply when the spawn commodity is reset.  This helps\n        plants all not to sprout from seeds at the same time.\n        ', tunable_type=int, default=10, minimum=0)
    SCALE_COMMODITY = Commodity.TunableReference()
    SCALE_VARIANCE = TunableInterval(description="\n        Control how much the size of child fruit can vary from its father's\n        size.\n        ", tunable_type=float, default_lower=0.8, default_upper=1.2)
    EVOLUTION_STATE = ObjectState.TunableReference(description='\n        Object state which will represent the icon behind the main icon of \n        the gardening tooltip.  This should be tied to the evolution state\n        of gardening objects.\n        ')
    SHOOT_DESCRIPTION_STRING = TunableLocalizedString(description="\n        Text that will be given to a shoot description following ':' to its \n        fruit name.\n        e.g. 'Shoot taken from: Apple'\n        ")
    DISABLE_DETAILS_STATE_VALUES = TunableList(description='\n            List of object state values where the gardening details should not \n            be shown.  This is for cases like Wild plants where we dont want\n            details that will not be used.\n            ', tunable=ObjectStateValue.TunableReference(description='\n                The state that will disable the plant additional information.\n                '))
    DISABLE_TOOLTIP_STATE_VALUES = TunableList(description='\n            List of object state values where the gardening object will disable \n            its tooltip.\n            ', tunable=ObjectStateValue.TunableReference(description='\n                The state that will disable the object tooltip.\n                '))
    SPLICED_PLANT_NAME = TunableLocalizedStringFactory(description='\n        Localized name to be set when a plant is spliced. \n        ')
    SPLICED_STATE_VALUE = ObjectStateValue.TunableReference(description='\n        The state that will mean this plant has been already spliced.  \n        ')
    PICKUP_STATE_MAPPING = TunableMapping(description='\n        Mapping that will set a state that should be set on the fruit when \n        its picked up, depending on a state fruit is currently in.\n        ', key_type=ObjectStateValue.TunableReference(), value_type=ObjectStateValue.TunableReference())
    GARDENING_SLOT = TunableReference(description='\n        Slot type used by the gardening system to create its fruit.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))
    GERMINATE_FAILURE_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        Notification that will tell the player that the plant has failed to\n        germinate.\n        ')
    UNIDENTIFIED_STATE_VALUE = ObjectStateValue.TunableReference(description='\n        The state value all unidentified plants will have.  Remember to add this\n        as the default value for a state in the identifiable plants state\n        component tuning.\n        ')
    SEASONALITY_STATE = ObjectState.TunablePackSafeReference(description="\n        A reference to the state that determines whether a plant is\n        Dormant/Indoors/In Season/Out of Season.\n        \n        The state value's display data is used in the UI tooltip for the plant.\n        ")
    SEASONALITY_IN_SEASON_STATE_VALUE = ObjectStateValue.TunablePackSafeReference(description='\n        A reference to the state value that marks a plant as being In Season.\n        \n        This state value is determined to detect seasonality.\n        ')
    SEASONALITY_ALL_SEASONS_TEXT = TunableLocalizedString(description='\n        The seasons text to display if the plant has no seasonality.\n        ')
    PLANT_SEASONALITY_TEXT = TunableLocalizedStringFactory(description="\n        The text to display for the plant's seasonality.\n        e.g.:\n        Seasonality:\n{0.String}\n        ")
    FRUIT_STATES = TunableMapping(description='\n        A mapping that defines which states on plants support fruits, and the\n        behavior when plants transition out of these states.\n        ', key_type=ObjectState.TunableReference(pack_safe=True), value_type=TunableTuple(states=TunableList(description='\n                The list of states that supports fruit. If the object changes\n                state (for the specified state track) and the new value is not\n                in this list, the fruit is destroyed according to the specified\n                rule.\n                ', tunable=ObjectStateValue.TunableReference(pack_safe=True), unique_entries=True), behavior=TunableVariant(description="\n                Define the fruit's behavior when plants exit a state that\n                supports fruit.\n                ", rot=TunablePercent(description='\n                    Define the chance that the fruit falls and rots, as opposed\n                    to just being destroyed.\n                    ', default=5), locked_args={'destroy': None}, default='destroy')))
    FRUIT_DECAY_COMMODITY = TunableReference(description='\n        The commodity that defines fruit decay (e.g. rotten/ripe).\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
    FRUIT_DECAY_COMMODITY_DROPPED_VALUE = Tunable(description='\n        Value to set the Fruit Decay Commodity on a harvestable that has\n        been dropped from a plant during a seasonal transition.\n        ', tunable_type=int, default=10)
    SPAWN_WEIGHTS = TunableMapping(description="\n        A fruit's chance to be spawned in a multi-fruit plant (e.g. via\n        splicing/grafting) is determined by its rarity.\n        \n        The weight is meant to curb the chance of spawning rarer fruits growing\n        on more common plants. It would never reduce the chance of the root\n        stock from spawning on its original plant.\n        \n        e.g.\n         A common Apple on a rare Pomegranate tree spawns at a 1:1 ratio.\n         A rare Pomegranate on a common Apple tree spawns at a 1:5 ratio.\n        ", key_type=TunableEnumEntry(tunable_type=ObjectCollectionRarity, default=ObjectCollectionRarity.COMMON), value_type=TunableRange(tunable_type=int, default=1, minimum=0))
    EXCLUSIVE_FRUITS = TunableSet(description='\n        A set of fruits, which, when added onto a plant, can restrict\n        what other fruits the plant produces to this set of fruits. \n        This is done by adjusting spawn weight of non-exclusive fruits \n        on the plant to zero. \n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT), pack_safe=True))

    @classmethod
    def is_spliced(cls, obj):
        if obj.has_state(cls.SPLICED_STATE_VALUE.state) and obj.get_state(cls.SPLICED_STATE_VALUE.state) == cls.SPLICED_STATE_VALUE:
            return True
        return False

    @classmethod
    def is_unidentified(cls, obj):
        if cls.UNIDENTIFIED_STATE_VALUE is not None and obj.has_state(cls.UNIDENTIFIED_STATE_VALUE.state) and obj.get_state(cls.UNIDENTIFIED_STATE_VALUE.state) == cls.UNIDENTIFIED_STATE_VALUE:
            return True
        return False

    @classmethod
    def get_seasonality_text_from_plant(cls, plant_definition):
        season_component = plant_definition.cls._components.season_aware_component
        if season_component is not None:
            seasons = []
            season_tuned_values = season_component._tuned_values
            for (season_type, season_states) in season_tuned_values.seasonal_state_mapping.items():
                if any(s is GardeningTuning.SEASONALITY_IN_SEASON_STATE_VALUE for s in season_states):
                    season = SeasonsTuning.SEASON_TYPE_MAPPING[season_type]
                    seasons.append((season_type, season))
            if seasons:
                return GardeningTuning.PLANT_SEASONALITY_TEXT(LocalizationHelperTuning.get_comma_separated_list(*tuple(season.season_name for (_, season) in sorted(seasons))))

    ALWAYS_GERMINATE_IF_NOT_SPAWNED_STATE = ObjectStateValue.TunableReference(description='\n        If the specified state value is active on the gardening object, it will\n        have a 100% germination chance for when it is placed in the world in\n        any way other than through a spawner.\n        ')
    QUALITY_STATE_VALUE = ObjectState.TunableReference(description='\n        The quality state all gardening plants will have.  \n        ')
