from sims4.log import Loggerfrom sims4.tuning.dynamic_enum import DynamicEnumimport enumlogger = Logger('Interactions')
class PipelineProgress(enum.Int, export=False):
    NONE = 0
    QUEUED = 1
    PRE_TRANSITIONING = 2
    PREPARED = 3
    RUNNING = 4
    STAGED = 5
    EXITED = 6

class TargetType(enum.IntFlags):
    ACTOR = 1
    TARGET = 2
    GROUP = 4
    OBJECT = 8
    FILTERED_TARGET = 16
    TARGET_AND_GROUP = TARGET | GROUP

class ParticipantType(enum.LongFlags):
    _enum_export_path = 'interactions.ParticipantType'
    Invalid = 0
    Actor = 1
    Object = 2
    TargetSim = 4
    Listeners = 8
    All = 16
    AllSims = 32
    Lot = 64
    CraftingProcess = 128
    JoinTarget = 256
    CarriedObject = 512
    Affordance = 1024
    InteractionContext = 2048
    CustomSim = 4096
    AllRelationships = 8192
    CraftingObject = 16384
    ActorSurface = 32768
    ObjectChildren = 65536
    LotOwners = 131072
    CreatedObject = 262144
    PickedItemId = 524288
    StoredSim = 1048576
    PickedObject = 2097152
    SocialGroup = 4194304
    OtherSimsInteractingWithTarget = 8388608
    PickedSim = 16777216
    ObjectParent = 33554432
    SignificantOtherActor = 67108864
    SignificantOtherTargetSim = 134217728
    OwnerSim = 268435456
    StoredSimOnActor = 536870912
    Unlockable = 1073741824
    LiveDragActor = 2147483648
    LiveDragTarget = 4294967296
    PickedZoneId = 8589934592
    SocialGroupSims = 17179869184
    PregnancyPartnerActor = 34359738368
    PregnancyPartnerTargetSim = 68719476736
    SocialGroupAnchor = 137438953472
    TargetSurface = 274877906944
    ActiveHousehold = 549755813888
    ActorPostureTarget = 1099511627776
    InventoryObjectStack = 2199023255552
    AllOtherInstancedSims = 4398046511104
    CareerEventSim = 8796093022208
    StoredSimOnPickedObject = 17592186044416
    SavedActor1 = 35184372088832
    SavedActor2 = 70368744177664
    SavedActor3 = 140737488355328
    SavedActor4 = 281474976710656
    LotOwnerSingleAndInstanced = 562949953421312
    LinkedPostureSim = 1125899906842624
    AssociatedClub = 2251799813685248
    AssociatedClubMembers = 4503599627370496
    AssociatedClubLeader = 9007199254740992
    AssociatedClubGatheringMembers = 18014398509481984
    ActorEnsemble = 36028797018963968
    TargetEnsemble = 72057594037927936
    TargetSimPostureTarget = 144115188075855872
    ActorEnsembleSansActor = 288230376151711744
    ActorDiningGroupMembers = 576460752303423488
    TableDiningGroupMembers = 1152921504606846976
    StoredSimOrNameData = 2305843009213693952
    TargetDiningGroupMembers = 4611686018427387904
    LinkedObjects = 9223372036854775808
    RoutingMaster = 18446744073709551616
    RoutingSlaves = 36893488147419103232
    SituationParticipants1 = 73786976294838206464
    SituationParticipants2 = 147573952589676412928
    ObjectCrafter = 295147905179352825856
    MissingPet = 590295810358705651712
    TargetTeleportPortalObjectDestinations = 1180591620717411303424
    ActorFeudTarget = 2361183241434822606848
    TargetFeudTarget = 4722366482869645213696
    ActorSquadMembers = 9444732965739290427392
    TargetSquadMembers = 18889465931478580854784
    AllInstancedSims = 37778931862957161709568
    StoredObjectsOnActor = 75557863725914323419136
    StoredObjectsOnTarget = 151115727451828646838272
    ObjectInventoryOwner = 302231454903657293676544
    LotOwnersOrRenters = 604462909807314587353088
    ActorFiance = 1208925819614629174706176
    TargetFiance = 2417851639229258349412352
    RandomInventoryObject = 4835703278458516698824704
    SituationParticipants3 = 9671406556917033397649408
    Familiar = 19342813113834066795298816
    PhotographyTargets = 154742504910672534362390528
    FamiliarOfTarget = 309485009821345068724781056

class ParticipantTypeSavedActor(enum.IntFlags):
    SavedActor1 = ParticipantType.SavedActor1
    SavedActor2 = ParticipantType.SavedActor2
    SavedActor3 = ParticipantType.SavedActor3
    SavedActor4 = ParticipantType.SavedActor4

class ParticipantTypeSituationSims(enum.LongFlags):
    SituationParticipants1 = ParticipantType.SituationParticipants1
    SituationParticipants2 = ParticipantType.SituationParticipants2
    SituationParticipants3 = ParticipantType.SituationParticipants3

class ParticipantTypeAnimation(enum.IntFlags):
    Invalid = ParticipantType.Invalid
    Actor = ParticipantType.Actor
    TargetSim = ParticipantType.TargetSim
    Listeners = ParticipantType.Listeners
    AllSims = ParticipantType.AllSims

class ParticipantTypeSingle(enum.LongFlags):
    Actor = ParticipantType.Actor
    TargetSim = ParticipantType.TargetSim
    CarriedObject = ParticipantType.CarriedObject
    CraftingObject = ParticipantType.CraftingObject
    StoredSim = ParticipantType.StoredSim
    StoredSimOnActor = ParticipantType.StoredSimOnActor
    StoredSimOnPickedObject = ParticipantType.StoredSimOnPickedObject
    SignificantOtherActor = ParticipantType.SignificantOtherActor
    SignificantOtherTargetSim = ParticipantType.SignificantOtherTargetSim
    PregnancyPartnerActor = ParticipantType.PregnancyPartnerActor
    PregnancyPartnerTargetSim = ParticipantType.PregnancyPartnerTargetSim
    Object = ParticipantType.Object
    SocialGroupAnchor = ParticipantType.SocialGroupAnchor
    ActorPostureTarget = ParticipantType.ActorPostureTarget
    PickedSim = ParticipantType.PickedSim
    PickedObject = ParticipantType.PickedObject
    SavedActor1 = ParticipantType.SavedActor1
    SavedActor2 = ParticipantType.SavedActor2
    SavedActor3 = ParticipantType.SavedActor3
    SavedActor4 = ParticipantType.SavedActor4
    LotOwnerSingleAndInstanced = ParticipantType.LotOwnerSingleAndInstanced
    ObjectCrafter = ParticipantType.ObjectCrafter
    MissingPet = ParticipantType.MissingPet
    OwnerSim = ParticipantType.OwnerSim
    ObjectInventoryOwner = ParticipantType.ObjectInventoryOwner
    ActorFiance = ParticipantType.ActorFiance
    TargetFiance = ParticipantType.TargetFiance
    CreatedObject = ParticipantType.CreatedObject
    RandomInventoryObject = ParticipantType.RandomInventoryObject
    Familiar = ParticipantType.Familiar
    FamiliarOfTarget = ParticipantType.FamiliarOfTarget

class ParticipantTypeReactionlet(enum.IntFlags):
    Invalid = ParticipantType.Invalid
    TargetSim = ParticipantType.TargetSim
    Listeners = ParticipantType.Listeners

class ParticipantTypeActorTargetSim(enum.IntFlags):
    Actor = ParticipantType.Actor
    TargetSim = ParticipantType.TargetSim

class ParticipantTypeResponse(enum.IntFlags):
    Invalid = ParticipantType.Invalid
    Actor = ParticipantType.Actor
    TargetSim = ParticipantType.TargetSim
    Listeners = ParticipantType.Listeners
    AllSims = ParticipantType.AllSims
    AllOtherInstancedSims = ParticipantType.AllOtherInstancedSims

class ParticipantTypeSingleSim(enum.LongFlags):
    Invalid = ParticipantType.Invalid
    Actor = ParticipantType.Actor
    TargetSim = ParticipantType.TargetSim
    PickedSim = ParticipantType.PickedSim
    StoredSim = ParticipantType.StoredSim
    RoutingMaster = ParticipantType.RoutingMaster
    ObjectCrafter = ParticipantType.ObjectCrafter
    LotOwnerSingleAndInstanced = ParticipantType.LotOwnerSingleAndInstanced
    SavedActor1 = ParticipantType.SavedActor1
    SavedActor2 = ParticipantType.SavedActor2
    SavedActor3 = ParticipantType.SavedActor3
    SavedActor4 = ParticipantType.SavedActor4

class ParticipantTypeResponsePaired(enum.IntFlags):
    TargetSim = ParticipantType.TargetSim

class ParticipantTypeLot(enum.IntFlags):
    Lot = ParticipantType.Lot
    PickedZoneId = ParticipantType.PickedZoneId

class ParticipantTypeObject(enum.LongFlags):
    ActorSurface = ParticipantType.ActorSurface
    CarriedObject = ParticipantType.CarriedObject
    CraftingObject = ParticipantType.CraftingObject
    CreatedObject = ParticipantType.CreatedObject
    Object = ParticipantType.Object
    PickedObject = ParticipantType.PickedObject
    SocialGroupAnchor = ParticipantType.SocialGroupAnchor
    ObjectInventoryOwner = ParticipantType.ObjectInventoryOwner
    RandomInventoryObject = ParticipantType.RandomInventoryObject

class ParticipantTypeSim(enum.LongFlags):
    Actor = ParticipantType.Actor
    TargetSim = ParticipantType.TargetSim
    Listeners = ParticipantType.Listeners
    AllSims = ParticipantType.AllSims
    JoinTarget = ParticipantType.JoinTarget
    CustomSim = ParticipantType.CustomSim
    AllRelationships = ParticipantType.AllRelationships
    LotOwners = ParticipantType.LotOwners
    StoredSim = ParticipantType.StoredSim
    SocialGroup = ParticipantType.SocialGroup
    OtherSimsInteractingWithTarget = ParticipantType.OtherSimsInteractingWithTarget
    PickedSim = ParticipantType.PickedSim
    SignificantOtherActor = ParticipantType.SignificantOtherActor
    SignificantOtherTargetSim = ParticipantType.SignificantOtherTargetSim
    OwnerSim = ParticipantType.OwnerSim
    StoredSimOnActor = ParticipantType.StoredSimOnActor
    SocialGroupSims = ParticipantType.SocialGroupSims
    PregnancyPartnerActor = ParticipantType.PregnancyPartnerActor
    PregnancyPartnerTargetSim = ParticipantType.PregnancyPartnerTargetSim
    AllOtherInstancedSims = ParticipantType.AllOtherInstancedSims
    CareerEventSim = ParticipantType.CareerEventSim
    StoredSimOnPickedObject = ParticipantType.StoredSimOnPickedObject
    SavedActor1 = ParticipantType.SavedActor1
    SavedActor2 = ParticipantType.SavedActor2
    SavedActor3 = ParticipantType.SavedActor3
    SavedActor4 = ParticipantType.SavedActor4
    LotOwnerSingleAndInstanced = ParticipantType.LotOwnerSingleAndInstanced
    LinkedPostureSim = ParticipantType.LinkedPostureSim
    AssociatedClubMembers = ParticipantType.AssociatedClubMembers
    AssociatedClubLeader = ParticipantType.AssociatedClubLeader
    AssociatedClubGatheringMembers = ParticipantType.AssociatedClubGatheringMembers
    ActorEnsemble = ParticipantType.ActorEnsemble
    TargetEnsemble = ParticipantType.TargetEnsemble
    TargetSimPostureTarget = ParticipantType.TargetSimPostureTarget
    ActorEnsembleSansActor = ParticipantType.ActorEnsembleSansActor
    ActorDiningGroupMembers = ParticipantType.ActorDiningGroupMembers
    TableDiningGroupMembers = ParticipantType.TableDiningGroupMembers
    RoutingMaster = ParticipantType.RoutingMaster
    RoutingSlaves = ParticipantType.RoutingSlaves
    ObjectCrafter = ParticipantType.ObjectCrafter
    MissingPet = ParticipantType.MissingPet
    AllInstancedSims = ParticipantType.AllInstancedSims
    LotOwnersOrRenters = ParticipantType.LotOwnersOrRenters
    ActorFiance = ParticipantType.ActorFiance
    TargetFiance = ParticipantType.TargetFiance

class MixerInteractionGroup(DynamicEnum):
    DEFAULT = 0
DEFAULT_MIXER_GROUP_SET = frozenset((MixerInteractionGroup.DEFAULT,))
class ParticipantTypeReaction(enum.IntFlags):
    Actor = ParticipantType.Actor
    Object = ParticipantType.Object
    TargetSim = ParticipantType.TargetSim
    Listeners = ParticipantType.Listeners
    AllSims = ParticipantType.AllSims
    OtherSimsInteractingWithTarget = ParticipantType.OtherSimsInteractingWithTarget
    SignificantOtherActor = ParticipantType.SignificantOtherActor
    SignificantOtherTargetSim = ParticipantType.SignificantOtherTargetSim
    OwnerSim = ParticipantType.OwnerSim
    SocialGroupSims = ParticipantType.SocialGroupSims
    LinkedPostureSim = ParticipantType.LinkedPostureSim
