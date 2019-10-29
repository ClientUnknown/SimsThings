import functoolsfrom event_testing.test_constants import SIM_INSTANCE, TARGET_SIM_ID, FROM_EVENT_DATA, FROM_DATA_OBJECT, OBJECTIVE_GUID64from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.utils import decoratorimport cachesimport sims4.loglogger = sims4.log.Logger('EventManager')
class TestEvent(DynamicEnum):
    Invalid = 0
    SkillValueChange = 1
    ObjectAdd = 2
    InteractionComplete = 3
    SituationEnded = 4
    ItemCrafted = 5
    InteractionAtEvent = 6
    SimoleonsEarned = 7
    UpdateAllEvent = 8
    TraitAddEvent = 9
    MotiveLevelChange = 10
    TestTotalTime = 11
    SimTravel = 12
    AddRelationshipBit = 13
    RemoveRelationshipBit = 14
    BuffBeganEvent = 15
    BuffEndedEvent = 16
    WorkdayComplete = 17
    MoodChange = 18
    HouseholdChanged = 19
    InteractionStart = 20
    AspirationTrackSelected = 21
    PrerelationshipChanged = 22
    RelationshipChanged = 23
    CollectionChanged = 24
    FamilyTrigger = 25
    InteractionStaged = 26
    InteractionExitedPipeline = 27
    UITraitsPanel = 28
    UICareerPanel = 29
    UIAspirationsPanel = 30
    UIRelationshipPanel = 31
    UISkillsPanel = 32
    UISimInventory = 33
    UIPhoneButton = 34
    UIAchievementPanel = 35
    UICameraButton = 36
    UIBuildButton = 37
    WhimCompleted = 38
    ObjectStateChange = 39
    OffspringCreated = 40
    CareerEvent = 41
    BuffUpdateEvent = 42
    InteractionUpdate = 43
    StatValueUpdate = 44
    LoadingScreenLifted = 45
    OnExitBuildBuy = 46
    OnBuildBuyReset = 47
    OnSimReset = 48
    UIMemoriesPanel = 49
    ReadyToAge = 50
    BillsDelivered = 51
    UnlockEvent = 52
    SimActiveLotStatusChanged = 53
    OnInventoryChanged = 54
    UpdateObjectiveData = 55
    ObjectDestroyed = 56
    CollectedItem = 57
    GenerationCreated = 58
    WhimBucksChanged = 59
    SituationStarted = 60
    SkillLevelChange = 61
    WorkdayStart = 62
    ClubMemberAdded = 63
    LeaderAssigned = 64
    PerkPurchased = 65
    ClubBucksEarned = 66
    TimeInClubGathering = 67
    AgedUp = 68
    SpouseEvent = 69
    ClubMemberRemoved = 70
    EncouragedInteractionStarted = 71
    GroupWaitingToBeSeated = 72
    RestaurantFoodOrdered = 73
    RestaurantOrderDelivered = 74
    RestaurantTableClaimed = 75
    SimDeathTypeSet = 76
    FestivalStarted = 77
    BucksPerkUnlocked = 78
    RankedStatisticChange = 79
    AvailableDaycareSimsChanged = 80
    DiagnosisUpdated = 81
    BusinessClosed = 82
    SeasonChanged = 83
    SeasonChangedNoSim = 84
    CareerPromoted = 85
    AwayActionStart = 86
    AwayActionStop = 87
    AspirationChanged = 88
    MainSituationGoalComplete = 89
    TraitRemoveEvent = 90
    NarrativesUpdated = 91
    GlobalPolicyProgress = 92
    PhotoTaken = 93
    ExitedPhotoMode = 94
    UnlockTrackerItemUnlocked = 95
CONTENT_SET_GEN_PROCESS_HOUSEHOLD_EVENT_CACHE_GROUP = 'CONTENT_SET_GEN_PROCESS_HOUSEHOLD_EVENT_CACHE_GROUP'
@decorator
def cached_test(fn):

    @functools.wraps(fn)
    def wrapper(test, **kwargs):
        if caches.skip_cache:
            return fn(test, **kwargs)
        cache = wrapper.cache
        if caches.global_cache_version != wrapper.cache_version:
            cache.clear()
            wrapper.cache_version = caches.global_cache_version
        key = (test, frozenset(kwargs.items()))
        try:
            result = cache[key]
        except KeyError:
            cache[key] = result = fn(test, **kwargs)
        return result

    wrapper.cache = {}
    wrapper.cache_version = caches.global_cache_version
    caches.all_cached_functions.add(wrapper)
    return wrapper
