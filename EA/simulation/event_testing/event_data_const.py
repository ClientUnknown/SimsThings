import enum
class ObjectiveDataStorageType(enum.Int, export=False):
    CountData = ...
    IdData = ...

class DataType(enum.Int, export=False):
    RelationshipData = 1
    SimoleanData = 2
    TimeData = 3
    TravelData = 5
    ObjectiveCount = 6
    CareerData = 7
    TagData = 8
    RelativeStartingData = 9
    ClubBucks = 10
    TimeInClubGatherings = 11
    Mood = 12

class RelationshipData(enum.Int, export=False):
    CurrentRelationships = 0
    TotalRelationships = 1

class SimoleonData(enum.Int):
    MoneyFromEvents = 0
    TotalMoneyEarned = 1

class TimeData(enum.Int, export=False):
    SimTime = 0
    ServerTime = 1

class TagData(enum.Int, export=False):
    SimoleonsEarned = 0
    TimeElapsed = 1
