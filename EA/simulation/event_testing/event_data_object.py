from date_and_time import TimeSpan, DateAndTime, MINUTES_PER_HOURfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.event_data_const import ObjectiveDataStorageTypefrom event_testing.event_manager_service import DataMapHandlerimport enumimport event_testing.event_data_const as data_constimport event_testing.test_events as test_eventsimport servicesimport sims4.loglogger = sims4.log.Logger('EventDataObject')
class EventDataObject:

    def __init__(self):
        self._data = {}
        self._data[data_const.DataType.ObjectiveCount] = ObjectiveData()
        self._data[data_const.DataType.RelationshipData] = RelationshipData()
        self._data[data_const.DataType.SimoleanData] = SimoleonData()
        self._data[data_const.DataType.TimeData] = TimeData()
        self._data[data_const.DataType.TravelData] = TravelData()
        self._data[data_const.DataType.CareerData] = CareerData()
        self._data[data_const.DataType.TagData] = TagData()
        self._data[data_const.DataType.RelativeStartingData] = RelativeStartingData()
        self._data[data_const.DataType.ClubBucks] = ClubBucksData()
        self._data[data_const.DataType.TimeInClubGatherings] = ClubGatheringTimeData()
        self._data[data_const.DataType.Mood] = MoodData()

    @property
    def data(self):
        return self._data

    def add_objective_id(self, objective_uid, id_to_add):
        self._data[data_const.DataType.ObjectiveCount].add_id(objective_uid, id_to_add)

    def get_objective_count(self, objective):
        return self._data[data_const.DataType.ObjectiveCount].get_count(objective)

    def get_objective_count_data(self):
        return self._data[data_const.DataType.ObjectiveCount].get_data()

    def add_objective_value(self, objective, value):
        self._data[data_const.DataType.ObjectiveCount].add_value(objective, value)

    def set_objective_value(self, objective, value):
        self._data[data_const.DataType.ObjectiveCount].set_value(objective, value)

    def set_starting_values(self, obj_guid64, values):
        self._data[data_const.DataType.RelativeStartingData].set_starting_values(obj_guid64, values)

    def get_starting_values(self, obj_guid64):
        return self._data[data_const.DataType.RelativeStartingData].get_starting_values(obj_guid64)

    def reset_objective_count(self, objective_uid):
        self._data[data_const.DataType.ObjectiveCount].reset_objective_count(objective_uid)

    def add_time_data(self, time_type, time_add):
        self._data[data_const.DataType.TimeData].add_time_data(time_type, time_add)

    def get_time_data(self, time_type):
        return self._data[data_const.DataType.TimeData].get_time_data(time_type)

    @DataMapHandler(test_events.TestEvent.SimTravel)
    def add_zone_traveled(self, zone_id=None, **kwargs):
        self._data[data_const.DataType.TravelData].add_travel_data(zone_id)

    def get_zones_traveled(self):
        return self._data[data_const.DataType.TravelData].get_travel_amount()

    @DataMapHandler(test_events.TestEvent.AddRelationshipBit)
    def add_relationship_bit_event(self, relationship_bit=None, sim_id=None, target_sim_id=None, **kwargs):
        self._data[data_const.DataType.RelationshipData].add_relationship_bit(relationship_bit, sim_id, target_sim_id)

    @DataMapHandler(test_events.TestEvent.RemoveRelationshipBit)
    def remove_relationship_bit_event(self, relationship_bit=None, sim_id=None, target_sim_id=None, **kwargs):
        self._data[data_const.DataType.RelationshipData].remove_relationship_bit(relationship_bit, sim_id, target_sim_id)

    def get_total_relationships(self, relationship_bit):
        return self._data[data_const.DataType.RelationshipData].get_total_relationship_number(relationship_bit)

    def get_current_total_relationships(self, relationship_bit):
        return self._data[data_const.DataType.RelationshipData].get_current_relationship_number(relationship_bit)

    @DataMapHandler(test_events.TestEvent.SimoleonsEarned)
    def add_simoleons_earned(self, simoleon_data_type=None, amount=None, **kwargs):
        if amount <= 0:
            return
        self._data[data_const.DataType.SimoleanData].add_simoleons(simoleon_data_type, amount)

    def get_simoleons_earned(self, simoleon_data_type):
        return self._data[data_const.DataType.SimoleanData].get_simoleon_data(simoleon_data_type)

    @DataMapHandler(test_events.TestEvent.WorkdayComplete)
    def add_career_data_event(self, career=None, time_worked=None, money_made=None, **kwargs):
        self._data[data_const.DataType.CareerData].add_career_data(career, time_worked, money_made)

    def get_career_data(self, career):
        return self._data[data_const.DataType.CareerData].get_career_data(career)

    def get_career_data_by_name(self, career_name):
        return self._data[data_const.DataType.CareerData].get_career_data_by_name(career_name)

    def get_all_career_data(self):
        return self._data[data_const.DataType.CareerData]._careers

    @DataMapHandler(test_events.TestEvent.InteractionComplete)
    def add_tag_time_from_interaction(self, interaction=None, **kwargs):
        if interaction is None:
            return
        type = data_const.DataType.TagData
        for tag in interaction.get_category_tags():
            time_update = interaction.consecutive_running_time_span
            if tag in self._data[type].interactions[interaction.id]:
                time_update -= self._data[type].interactions[interaction.id][tag]
            self._data[type].time_added(tag, time_update)

    @DataMapHandler(test_events.TestEvent.InteractionUpdate)
    def add_tag_time_update_from_interaction(self, interaction=None, **kwargs):
        if interaction is None:
            return
        type = data_const.DataType.TagData
        if interaction.id not in self._data[type].interactions:
            self._data[type].interactions[interaction.id] = {}
        for tag in interaction.get_category_tags():
            previous = TimeSpan(0)
            if tag in self._data[type].interactions[interaction.id]:
                previous = self._data[type].interactions[interaction.id][tag]
            time_update = interaction.consecutive_running_time_span - previous
            self._data[type].time_added(tag, time_update)
            self._data[type].interactions[interaction.id][tag] = interaction.consecutive_running_time_span

    @DataMapHandler(test_events.TestEvent.SimoleonsEarned)
    def add_tag_simoleons_earned(self, tags=(), amount=0, **kwargs):
        if amount <= 0 or tags is None:
            return
        for tag in tags:
            self._data[data_const.DataType.TagData].simoleons_added(tag, amount)

    def get_total_tag_interaction_time_elapsed(self, tag):
        return self._data[data_const.DataType.TagData].get_total_interaction_time_elapsed(tag)

    def get_total_tag_simoleons_earned(self, tag):
        return self._data[data_const.DataType.TagData].get_total_simoleons_earned(tag)

    @DataMapHandler(test_events.TestEvent.ClubBucksEarned)
    def add_club_bucks_earned(self, amount=0):
        self._data[data_const.DataType.ClubBucks].add_club_bucks(amount)

    def get_total_club_bucks_earned(self):
        return self._data[data_const.DataType.ClubBucks].get_club_bucks_data()

    @DataMapHandler(test_events.TestEvent.TimeInClubGathering)
    def add_time_in_club_gathering(self, amount=0):
        self._data[data_const.DataType.TimeInClubGatherings].add_sim_minutes_spent_in_gathering(amount)

    def get_total_time_in_club_gatherings(self):
        return self._data[data_const.DataType.TimeInClubGatherings].get_sim_hours_in_gatherings()

    @DataMapHandler(test_events.TestEvent.MoodChange)
    def on_mood_changed(self, **kwargs):
        self._data[data_const.DataType.Mood].on_sim_changed_mood(**kwargs)

    def get_last_time_in_mood(self, mood):
        return self._data[data_const.DataType.Mood].get_last_time_in_mood(mood)

    def save(self, complete_event_data_blob):
        for data in self._data.values():
            data.save(complete_event_data_blob.data)

    def load(self, complete_event_data_blob):
        for data in self._data.values():
            data.load(complete_event_data_blob.data)

class ObjectiveData:

    class BaseObjectiveData:
        __slots__ = ()

        def get_count(self):
            raise NotImplementedError

        def add_value(self, value):
            raise NotImplementedError

        def set_value(self, value):
            raise NotImplementedError

        def reset(self):
            raise NotImplementedError

        def save(self, save_data):
            raise NotImplementedError

        def load(self, save_data):
            raise NotImplementedError

        def should_save(self):
            raise NotImplementedError

        def should_load(self, save_data):
            raise NotImplementedError

    class CountData(BaseObjectiveData):
        __slots__ = ('_count',)

        def __init__(self):
            self._count = 0

        def get_count(self):
            return self._count

        def add_value(self, value):
            self._count += value

        def set_value(self, value):
            self._count = value

        def reset(self):
            self._count = 0

        def save(self, save_data):
            save_data.amount = int(self._count)

        def load(self, save_data):
            if save_data.amount > self._count:
                self._count = save_data.amount

        def should_save(self):
            return self._count > 0

        def should_load(self, save_data):
            return save_data.amount > 0

    class IdData(BaseObjectiveData):
        __slots__ = ('_ids',)

        def __init__(self):
            self._ids = set()

        def get_count(self):
            return len(self._ids)

        def add_value(self, value):
            self._ids.add(value)

        def set_value(self, value):
            self._ids = value

        def reset(self):
            self._ids.clear()

        def save(self, save_data):
            save_data.ids.extend(self._ids)

        def load(self, save_data):
            self._ids.update({id_to_add for id_to_add in save_data.ids})

        def should_save(self):
            return len(self._ids) > 0

        def should_load(self, save_data):
            return len(save_data.ids) > 0

    __slots__ = ('_stored_objective_count_data',)

    def __init__(self):
        self._stored_objective_count_data = {}

    def get_data(self):
        return self._stored_objective_count_data

    def _get_objective_data(self, objective, should_add=True):
        objective_uid = objective.guid64
        if objective_uid not in self._stored_objective_count_data:
            if not should_add:
                return
            if objective.data_type == ObjectiveDataStorageType.CountData:
                self._stored_objective_count_data[objective_uid] = ObjectiveData.CountData()
            elif objective.data_type == ObjectiveDataStorageType.IdData:
                self._stored_objective_count_data[objective_uid] = ObjectiveData.IdData()
            else:
                logger.exception('Trying to add objective data for objective {} with invalid data type {}', objective, objective.data_type, owner='jjacobson')
        return self._stored_objective_count_data[objective_uid]

    def reset_objective_count(self, objective):
        objective_data = self._get_objective_data(objective, should_add=False)
        if objective_data is not None:
            objective_data.reset()

    def get_count(self, objective):
        objective_data = self._get_objective_data(objective, should_add=False)
        if objective_data is not None:
            return objective_data.get_count()
        return 0

    def add_value(self, objective, value):
        objective_data = self._get_objective_data(objective)
        objective_data.add_value(value)

    def set_value(self, objective, value):
        objective_data = self._get_objective_data(objective)
        objective_data.set_value(value)

    def save(self, event_data_blob):
        for (objective_uid, objective_data) in self._stored_objective_count_data.items():
            if not objective_data.should_save():
                pass
            else:
                objective_save_data = event_data_blob.objective_data.add()
                objective_save_data.enum = objective_uid
                objective_data.save(objective_save_data)

    def load(self, event_data_blob):
        objective_manager = services.get_instance_manager(sims4.resources.Types.OBJECTIVE)
        for objective_data_proto in event_data_blob.objective_data:
            objective = objective_manager.get(objective_data_proto.enum)
            if objective is None:
                logger.debug('Objective of guid {} saved but not found in objective manager.  This is valid in the case of an uninstall.', objective_data_proto.enum, owner='jjacobson')
            else:
                objective_data = self._stored_objective_count_data.get(objective.guid64)
                if objective_data is None:
                    if objective.data_type == ObjectiveDataStorageType.CountData:
                        objective_data = ObjectiveData.CountData()
                    elif objective.data_type == ObjectiveDataStorageType.IdData:
                        objective_data = ObjectiveData.IdData()
                    if not objective_data.should_load(objective_data_proto):
                        pass
                    else:
                        objective_data.load(objective_data_proto)
                        self._stored_objective_count_data[objective.guid64] = objective_data
                        objective_data.load(objective_data_proto)
                else:
                    objective_data.load(objective_data_proto)

class CareerData:

    class Data:
        __slots__ = ('_time_worked', '_money_earned')

        def __init__(self):
            self._time_worked = 0
            self._money_earned = 0

        def increment_data(self, time_worked, money_earned):
            self._time_worked += time_worked
            self._money_earned += money_earned

        def set_data(self, time_worked, money_earned):
            self._time_worked = time_worked
            self._money_earned = money_earned

        def get_hours_worked(self):
            date_and_time = DateAndTime(self._time_worked)
            return date_and_time.absolute_hours()

        def get_money_earned(self):
            return self._money_earned

    __slots__ = ('_careers',)

    def __init__(self):
        self._careers = {}

    def get_career_data(self, career):
        career_name = type(career).__name__
        return self.get_career_data_by_name(career_name)

    def get_career_data_by_name(self, career_name):
        if career_name not in self._careers:
            self._careers[career_name] = CareerData.Data()
        return self._careers[career_name]

    def set_career_data_by_name(self, career_name, time_worked, money_earned):
        if career_name not in self._careers:
            self._careers[career_name] = CareerData.Data()
        self._careers[career_name].set_data(time_worked, money_earned)

    def add_career_data(self, career, time_worked, money_earned):
        self.get_career_data(career).increment_data(time_worked, money_earned)

    def save(self, event_data_blob):
        for career_name in self._careers.keys():
            career_data = event_data_blob.career_data.add()
            career_data.name = career_name
            career_data.time = self._careers[career_name]._time_worked
            career_data.money = self._careers[career_name]._money_earned

    def load(self, event_data_blob):
        for career in event_data_blob.career_data:
            self.set_career_data_by_name(career.name, career.time, career.money)

class SimoleonData:
    __slots__ = ('_stored_simoleon_data',)

    def __init__(self):
        self._stored_simoleon_data = {}
        for item in data_const.SimoleonData:
            self._stored_simoleon_data[item] = 0

    def get_simoleon_data(self, simoleon_type):
        return self._stored_simoleon_data[simoleon_type]

    def add_simoleons(self, simoleon_type, amount):
        self._stored_simoleon_data[simoleon_type] += amount

    def save(self, event_data_blob):
        for (enum, amount) in self._stored_simoleon_data.items():
            simoleon_data = event_data_blob.simoleon_data.add()
            simoleon_data.enum = enum
            simoleon_data.amount = amount

    def load(self, event_data_blob):
        for simoleon_data in event_data_blob.simoleon_data:
            self._stored_simoleon_data[simoleon_data.enum] = simoleon_data.amount

class TimeData:
    __slots__ = ('_stored_time_data',)

    def __init__(self):
        self._stored_time_data = {}
        for item in data_const.TimeData:
            self._stored_time_data[item] = 0

    def get_time_data(self, time_type):
        return self._stored_time_data[time_type]

    def add_time_data(self, time_type, amount):
        self._stored_time_data[time_type] += amount

    def save(self, event_data_blob):
        for (enum, amount) in self._stored_time_data.items():
            time_data = event_data_blob.time_data.add()
            time_data.enum = enum
            time_data.amount = amount

    def load(self, event_data_blob):
        for time_data in event_data_blob.time_data:
            self._stored_time_data[time_data.enum] = time_data.amount

class TravelData:
    __slots__ = ('_lots_traveled',)

    def __init__(self):
        self._lots_traveled = set()

    def get_travel_amount(self):
        return len(self._lots_traveled)

    def add_travel_data(self, zone_id):
        if zone_id is not None:
            self._lots_traveled.add(zone_id)

    def save(self, event_data_blob):
        for lot in self._lots_traveled:
            event_data_blob.travel_data.append(lot)

    def load(self, event_data_blob):
        for lot in event_data_blob.travel_data:
            self._lots_traveled.add(lot)

class RelationshipData:

    class Data:
        __slots__ = ('_stored_relationship_data',)

        def __init__(self):
            self._stored_relationship_data = {}
            for item in data_const.RelationshipData:
                self._stored_relationship_data[item] = 0

    __slots__ = ('_relationships',)

    def __init__(self):
        self._relationships = {}

    def get_relationship_data(self, relationship):
        return self.get_relationship_data_by_id(relationship.guid64)

    def get_relationship_data_by_id(self, bit_instance_id):
        if bit_instance_id not in self._relationships:
            self._relationships[bit_instance_id] = RelationshipData.Data()
        return self._relationships[bit_instance_id]._stored_relationship_data

    def set_relationship_data_by_id(self, bit_instance_id, enum, quantity):
        data = self.get_relationship_data_by_id(bit_instance_id)
        data[enum] = quantity

    def add_relationship_bit(self, new_relationship_bit, sim_id, target_sim_id):
        new_relationship_data = self.get_relationship_data(new_relationship_bit)
        new_relationship_data[data_const.RelationshipData.CurrentRelationships] += 1
        new_relationship_data[data_const.RelationshipData.TotalRelationships] += 1

    def remove_relationship_bit(self, removed_relationship_bit, sim_id, target_sim_id):
        removed_relationship_data = self.get_relationship_data(removed_relationship_bit)
        removed_relationship_data[data_const.RelationshipData.CurrentRelationships] -= 1

    def get_current_relationship_number(self, relationship):
        return self.get_relationship_data(relationship)[data_const.RelationshipData.CurrentRelationships]

    def get_total_relationship_number(self, relationship):
        return self.get_relationship_data(relationship)[data_const.RelationshipData.TotalRelationships]

    def save(self, event_data_blob):
        for relationship_id in self._relationships.keys():
            relationship_data = event_data_blob.relationship_data.add()
            for (enum, data) in self.get_relationship_data_by_id(relationship_id).items():
                this_enum = relationship_data.enums.add()
                this_enum.enum = enum
                this_enum.amount = data
            relationship_data.relationship_id = relationship_id

    def load(self, event_data_blob):
        for relationship in event_data_blob.relationship_data:
            for enum in relationship.enums:
                self.set_relationship_data_by_id(relationship.relationship_id, enum.enum, enum.amount)

class RelativeStartingData:

    def __init__(self):
        self._objective_relative_values = {}

    def set_starting_values(self, obj_guid64, values):
        self._objective_relative_values[obj_guid64] = values

    def get_starting_values(self, obj_guid64):
        if obj_guid64 in self._objective_relative_values:
            return self._objective_relative_values[obj_guid64]

    def save(self, event_data_blob):
        for (objective_guid64, start_values) in self._objective_relative_values.items():
            obj_start_value = event_data_blob.relative_start_data.add()
            obj_start_value.objective_guid64 = objective_guid64
            obj_start_value.starting_values.extend(start_values)

    def load(self, event_data_blob):
        for obj_value_pair in event_data_blob.relative_start_data:
            self.set_starting_values(obj_value_pair.objective_guid64, obj_value_pair.starting_values)

class TagData:
    __slots__ = ('_tags', 'interactions')

    class Data:
        __slots__ = ('_stored_tag_data',)

        def __init__(self):
            self._stored_tag_data = {}
            for item in data_const.TagData:
                if item == data_const.TagData.TimeElapsed:
                    self._stored_tag_data[item] = TimeSpan.ZERO
                else:
                    self._stored_tag_data[item] = 0

    def __init__(self):
        self._tags = {}
        self.interactions = {}

    def get_tag_data(self, tag):
        if tag not in self._tags:
            self._tags[tag] = TagData.Data()
        return self._tags[tag]._stored_tag_data

    def set_tag_data(self, tag, enum, quantity):
        data = self.get_tag_data(tag)
        if enum == data_const.TagData.TimeElapsed:
            data[enum] = TimeSpan(quantity)
        else:
            data[enum] = quantity

    def time_added(self, tag, time_quantity):
        tag_data = self.get_tag_data(tag)
        tag_data[data_const.TagData.TimeElapsed] += time_quantity

    def simoleons_added(self, tag, quantity):
        tag_data = self.get_tag_data(tag)
        tag_data[data_const.TagData.SimoleonsEarned] += quantity

    def get_total_interaction_time_elapsed(self, tag):
        tag_data = self.get_tag_data(tag)
        return tag_data[data_const.TagData.TimeElapsed]

    def get_total_simoleons_earned(self, tag):
        tag_data = self.get_tag_data(tag)
        return tag_data[data_const.TagData.SimoleonsEarned]

    def save(self, event_data_blob):
        for tag in self._tags.keys():
            with ProtocolBufferRollback(event_data_blob.tag_data) as tag_data:
                for (data_type, data) in self.get_tag_data(tag).items():
                    if data_type == data_const.TagData.TimeElapsed:
                        amount = data.in_ticks()
                    else:
                        amount = data
                    if amount == 0:
                        pass
                    else:
                        with ProtocolBufferRollback(tag_data.enums) as tag_data_groups:
                            tag_data_groups.enum = data_type
                            tag_data_groups.amount = amount
                tag_data.tag_enum = tag

    def load(self, event_data_blob):
        for tag in event_data_blob.tag_data:
            for enum in tag.enums:
                self.set_tag_data(tag.tag_enum, enum.enum, enum.amount)

class ClubBucksData:
    __slots__ = ('_stored_club_bucks_data',)

    def __init__(self):
        self._stored_club_bucks_data = 0

    def get_club_bucks_data(self):
        return self._stored_club_bucks_data

    def add_club_bucks(self, amount):
        self._stored_club_bucks_data += amount
        self._stored_club_bucks_data = min(self._stored_club_bucks_data, sims4.math.MAX_INT32)

    def save(self, event_data_blob):
        event_data_blob.club_bucks_data.amount = self._stored_club_bucks_data

    def load(self, event_data_blob):
        if event_data_blob.HasField('club_bucks_data'):
            self._stored_club_bucks_data = event_data_blob.club_bucks_data.amount

class ClubGatheringTimeData:
    __slots__ = ('_sim_minutes_in_gatherings',)

    def __init__(self):
        self._sim_minutes_in_gatherings = 0

    def get_sim_hours_in_gatherings(self):
        return self._sim_minutes_in_gatherings/MINUTES_PER_HOUR

    def add_sim_minutes_spent_in_gathering(self, amount):
        self._sim_minutes_in_gatherings += amount

    def save(self, event_data_blob):
        event_data_blob.time_in_gatherings.sim_minutes = self._sim_minutes_in_gatherings

    def load(self, event_data_blob):
        if event_data_blob.HasField('time_in_gatherings'):
            self._sim_minutes_in_gatherings = event_data_blob.time_in_gatherings.sim_minutes

class MoodData:
    __slots__ = ('_last_time_in_mood',)

    def __init__(self):
        self._last_time_in_mood = {}

    def on_sim_changed_mood(self, old_mood=None, new_mood=None):
        now = services.time_service().sim_now
        if old_mood is not None:
            self._last_time_in_mood[old_mood] = now
        if new_mood is not None:
            self._last_time_in_mood[new_mood] = now

    def get_last_time_in_mood(self, mood):
        return self._last_time_in_mood.get(mood)

    def save(self, event_data_blob):
        for (mood, time) in self._last_time_in_mood.items():
            with ProtocolBufferRollback(event_data_blob.mood_data.mood_data) as mood_data:
                mood_data.mood = mood.guid64
                mood_data.last_time_in_mood = time.absolute_ticks()

    def load(self, event_data_blob):
        mood_manager = services.get_instance_manager(sims4.resources.Types.MOOD)
        for mood_data in event_data_blob.mood_data.mood_data:
            mood = mood_manager.get(mood_data.mood)
            if mood is None:
                pass
            else:
                self._last_time_in_mood[mood] = DateAndTime(mood_data.last_time_in_mood)
