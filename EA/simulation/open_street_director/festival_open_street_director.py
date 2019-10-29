from collections import namedtuplefrom date_and_time import create_time_span, TimeSpanfrom open_street_director.festival_situations import BaseGenericFestivalSituationfrom open_street_director.open_street_director import OpenStreetDirectorBase, OpenStreetDirectorPriorityfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import HasTunableFactory, TunableList, TunableTuple, TunableRange, TunableReference, TunableSimMinute, AutoFactoryInit, OptionalTunable, TunableEnumEntry, TunableSetfrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import classpropertyfrom situations.situation_guest_list import SituationGuestListfrom tag import Tagimport alarmsimport build_buyimport servicesimport sims4.resourcesimport taglogger = sims4.log.Logger('OpenStreetDirector', default_owner='jjacobson')
class FestivalAlarmData:

    def __init__(self, should_persist, alarm_handle):
        self.should_persist = should_persist
        self.alarm_handle = alarm_handle

class BaseFestivalState(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'_situations': TunableList(description='\n            The different Situations that should be running at this time.\n            ', tunable=TunableTuple(description='\n                The Tunables for a single entry in this list.  Each entry\n                includes a minimum number of situations that we want to have\n                running from this entry and a list of weighted Situations.\n                We try and ensure a minimum number of the situations specified\n                within the Situations list will exist.\n                ', number_of_situations=TunableRange(description='\n                    The number of situations that we want to have running from\n                    this entry.  This is the Minimum number of situations that\n                    we try and maintain.  If the number of situations exceeds\n                    this we will not destroy situations to reduce ourself to\n                    this value.\n                    ', tunable_type=int, default=1, minimum=1), object_tag_requirement=OptionalTunable(description='\n                    If enabled then we will cap the number of situations\n                    created by this entry at either the minimum of objects\n                    created for this situation by tuned tag or the Number of\n                    Situations tunable.\n                    ', tunable=TunableEnumEntry(description='\n                        A specific tag that an object on this lot must have for this\n                        situation to be allowed to start.\n                        ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,))), situations=TunableList(description='\n                    A weighted list of situations that can be chosen for this\n                    state in the festival.\n                    ', tunable=TunableTuple(description='\n                        A pair between a weight and a situation that can be\n                        chosen.\n                        ', weight=TunableRange(description='\n                            Weight for each of the different situations that\n                            can be chosen.\n                            ', tunable_type=float, default=1, minimum=1), situation=TunableReference(description='\n                            The situation that can be chosen.  We will run any\n                            tests that GPEs have added to determine if this\n                            situation has been valid before actually selecting\n                            it.\n                            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=(BaseGenericFestivalSituation,))))))}

    @classproperty
    def priority(cls):
        return OpenStreetDirectorPriority.FESTIVAL

    CHECK_SITUATIONS_ALARM_TIME = 10
    CHECK_SITUATION_ALARM_KEY = 'check_situation_alarm'

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._check_situations_alarm_handle = None
        self._alarms = {}

    @classproperty
    def key(cls):
        raise NotImplementedError

    def _test_situation(self, situation):
        return situation.situation_meets_starting_requirements()

    def _create_required_number_of_situations(self):
        situation_manager = services.get_zone_situation_manager()
        running_situations = [type(situation) for situation in self._owner.get_running_festival_situations()]
        for situation_entry in self._situations:
            number_of_situations_running = 0
            for situation_type_entry in situation_entry.situations:
                number_of_situations_running += running_situations.count(situation_type_entry.situation)
            if situation_entry.object_tag_requirement is None:
                required_situations = situation_entry.number_of_situations
            else:
                tagged_objects = 0
                for obj in self._owner.get_all_layer_created_objects():
                    if build_buy.get_object_has_tag(obj.definition.id, situation_entry.object_tag_requirement):
                        tagged_objects += 1
                required_situations = min(tagged_objects, situation_entry.number_of_situations)
            if number_of_situations_running < required_situations:
                possible_situations = [(situation_type_entry.weight, situation_type_entry.situation) for situation_type_entry in situation_entry.situations if self._test_situation(situation_type_entry.situation)]
                if possible_situations:
                    for _ in range(situation_entry.number_of_situations - number_of_situations_running):
                        situation = weighted_random_item(possible_situations)
                        guest_list = situation.get_predefined_guest_list()
                        if guest_list is None:
                            guest_list = SituationGuestList(invite_only=True)
                        situation_id = situation_manager.create_situation(situation, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False)
                        self._owner._add_created_situation(situation_id)

    def _create_situations_callback(self, _):
        self._create_required_number_of_situations()

    def on_state_activated(self, reader=None, preroll_time_override=None):
        self.schedule_alarm(self.CHECK_SITUATION_ALARM_KEY, self.CHECK_SITUATIONS_ALARM_TIME, self._create_situations_callback, repeating=True, should_persist=False, reader=reader)

    def on_state_deactivated(self):
        for alarm_data in self._alarms.values():
            alarms.cancel_alarm(alarm_data.alarm_handle)

    def on_layer_loaded(self, conditional_layer):
        pass

    def on_layer_objects_destroyed(self, conditional_layer):
        pass

    def save(self, writer):
        for (alarm_key, alarm_data) in self._alarms.items():
            if alarm_data.should_persist:
                writer.write_float(alarm_key, alarm_data.alarm_handle.get_remaining_time().in_minutes())

    def schedule_alarm(self, alarm_key, alarm_time, callback, repeating=False, should_persist=True, reader=None):
        if reader is not None:
            alarm_time = reader.read_float(alarm_key, alarm_time)
        alarm_handle = alarms.add_alarm(self, create_time_span(minutes=alarm_time), callback, repeating=repeating)
        self._alarms[alarm_key] = FestivalAlarmData(should_persist, alarm_handle)

    def _run_preroll(self):
        self._create_required_number_of_situations()

    def _get_fake_preroll_time(self):
        pass

    def _preroll_end_of_state(self):
        raise NotImplementedError

    def preroll(self, time_to_preroll):
        if time_to_preroll is None:
            return
        self._run_preroll()
        time_spent = self._get_fake_preroll_time()
        if time_spent is None:
            return TimeSpan(0)
        time_left = time_to_preroll - time_spent
        if time_left > TimeSpan.ZERO:
            self._preroll_end_of_state()
        return time_left

class TimedFestivalState(BaseFestivalState):
    FACTORY_TUNABLES = {'_duration': TunableSimMinute(description='\n            The length of time that this state will run before moving into the\n            next state.\n            ', minimum=1, default=60)}
    TIMEOUT_ALARM_KEY = 'state_timeout_alarm'

    def _get_next_state(self):
        raise NotImplementedError

    def _change_state(self):
        next_state = self._get_next_state()
        if next_state is not None:
            self._owner.change_state(next_state)
        else:
            self._owner.self_destruct()

    def _on_timeout_expired_callback(self, _):
        self._change_state()

    def on_state_activated(self, reader=None, preroll_time_override=None):
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        alarm_time = -preroll_time_override.in_minutes() if preroll_time_override is not None else self._duration
        self.schedule_alarm(self.TIMEOUT_ALARM_KEY, alarm_time, self._on_timeout_expired_callback, reader=reader)

    def _get_fake_preroll_time(self):
        return create_time_span(minutes=self._duration)

    def _preroll_end_of_state(self):
        self._change_state()

class LoadLayerFestivalState(BaseFestivalState):
    FACTORY_TUNABLES = {'_conditional_layers': TunableList(description='\n            A list of layers to be loaded.  Each one will load one after\n            another.\n            ', tunable=TunableReference(description='\n                The Conditional Layer that will be loaded.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)), unique_entries=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._layers_to_load = []

    def _get_next_state(self):
        raise NotImplementedError

    def _load_layers(self):
        self._layers_to_load = list(self._conditional_layers)
        for conditional_layer in tuple(self._layers_to_load):
            if services.current_zone().is_zone_running:
                self._owner.load_layer_gradually(conditional_layer)
            else:
                self._owner.load_layer_immediately(conditional_layer)

    def on_layer_loaded(self, conditional_layer):
        if self._owner._prerolling:
            return
        self._layers_to_load.remove(conditional_layer)
        if self._layers_to_load:
            return
        self._preroll_end_of_state()

    def on_state_activated(self, reader=None, preroll_time_override=None):
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        if len(self._conditional_layers) == 0:
            self._preroll_end_of_state()
            return
        self._load_layers()

    def _run_preroll(self):
        for conditional_layer in self._conditional_layers:
            self._owner.load_layer_immediately(conditional_layer)
        super()._run_preroll()

    def _get_fake_preroll_time(self):
        return TimeSpan.ZERO

    def _preroll_end_of_state(self):
        next_state = self._get_next_state()
        if next_state is not None:
            self._owner.change_state(next_state)
        else:
            self._owner.self_destruct()

class CleanupObjectsFestivalState(BaseFestivalState):
    FACTORY_TUNABLES = {'_conditional_layers': TunableList(description='\n            A list of layers to be destroyed.  Each one will load one after\n            another.\n            ', tunable=TunableReference(description='\n                The conditional layer that will be destroyed.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)), unique_entries=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._layers_to_destroy = []

    def _get_next_state(self):
        raise NotImplementedError

    def _destroy_layers(self):
        self._layers_to_destroy = list(self._conditional_layers)
        for conditional_layer in tuple(self._layers_to_destroy):
            self._owner.remove_layer_objects(conditional_layer)

    def on_layer_objects_destroyed(self, conditional_layer):
        super().on_layer_objects_destroyed(conditional_layer)
        if self._owner._prerolling:
            return
        self._layers_to_destroy.remove(conditional_layer)
        if self._layers_to_destroy:
            return
        next_state = self._get_next_state()
        if next_state is not None:
            self._owner.change_state(next_state)
        else:
            self._owner._ready_for_destruction = True
            self._owner.self_destruct()

    def on_state_activated(self, reader=None, preroll_time_override=None):
        self._owner.run_lot_cleanup()
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        self._destroy_layers()

    def _run_preroll(self):
        for conditional_layer in self._layers_to_destroy:
            self._owner.remove_layer_objects(conditional_layer)
        super()._run_preroll()

    def _get_fake_preroll_time(self):
        return TimeSpan.ZERO

    def _preroll_end_of_state(self):
        next_state = self._get_next_state()
        if next_state is not None:
            self._owner.change_state(next_state)
        else:
            self._owner.self_destruct()
FestivalStateInfo = namedtuple('FestivalStateInfo', ['state_type', 'factory'])
class BaseFestivalOpenStreetDirector(OpenStreetDirectorBase):
    INSTANCE_SUBCLASSES_ONLY = True
    SAVE_STATE_KEY_TOKEN = 'state_key'
    UID_KEY_TOKEN = 'uid_key'
    INSTANCE_TUNABLES = {'cleanup_situation_tags': TunableSet(description='\n            A set of tags that we will destroy all situations with at the end\n            of the festival.\n            ', tunable=TunableEnumEntry(description='\n                A tag that we will destroy all situations with.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,)))}

    @classproperty
    def priority(cls):
        return OpenStreetDirectorPriority.FESTIVAL

    def __init__(self, *args, drama_node_uid=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_state = None
        self._festival_situations = []
        self._drama_node_uid = drama_node_uid

    @classmethod
    def _states(cls):
        raise NotImplementedError

    def _get_starting_state(self):
        raise NotImplementedError

    def change_state(self, new_state, reader=None):
        if self._current_state is not None:
            self._current_state.on_state_deactivated()
        self._current_state = new_state
        if not self._prerolling:
            self._current_state.on_state_activated(reader=reader)

    def on_shutdown(self):
        self._current_state.on_state_deactivated()
        self._current_state = None
        if self._drama_node_uid is not None:
            services.drama_scheduler_service().complete_node(self._drama_node_uid)
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._festival_situations:
            situation_manager.destroy_situation_by_id(situation_id)
        for situation in situation_manager.get_situations_by_tags(self.cleanup_situation_tags):
            situation_manager.destroy_situation_by_id(situation.id)

    def _save_custom_open_street_director(self, street_director_proto, writer):
        street_director_proto.situation_ids.extend(self._festival_situations)
        if self._current_state is not None:
            writer.write_uint32(self.SAVE_STATE_KEY_TOKEN, self._current_state.key)
            self._current_state.save(writer)
        if self._drama_node_uid is not None:
            writer.write_uint64(self.UID_KEY_TOKEN, self._drama_node_uid)

    def _should_load_old_data(self, street_director_proto, reader):
        if not super()._should_load_old_data(street_director_proto, reader):
            return False
        if reader is None:
            return False
        if self._drama_node_uid is None:
            return False
        old_drama_node_uid = reader.read_uint64(self.UID_KEY_TOKEN, None)
        if old_drama_node_uid is None:
            return False
        return old_drama_node_uid == self._drama_node_uid

    def _load_custom_open_street_director(self, street_director_proto, reader):
        super()._load_custom_open_street_director(street_director_proto, reader)
        self._festival_situations = list(street_director_proto.situation_ids)
        state_key = reader.read_uint32(self.SAVE_STATE_KEY_TOKEN, 0)
        for state_info in self._states():
            if state_info.state_type.key == state_key:
                self.change_state(state_info.factory(self), reader=reader)
                break

    def on_layer_loaded(self, conditional_layer):
        super().on_layer_loaded(conditional_layer)
        self._current_state.on_layer_loaded(conditional_layer)

    def on_layer_objects_destroyed(self, conditional_layer):
        super().on_layer_objects_destroyed(conditional_layer)
        self._current_state.on_layer_objects_destroyed(conditional_layer)

    def _add_created_situation(self, situation_id):
        self._festival_situations.append(situation_id)

    def get_running_festival_situations(self):
        situation_manager = services.get_zone_situation_manager()
        running_situations = []
        for situation_id in self._festival_situations:
            situation = situation_manager.get(situation_id)
            if situation is None:
                pass
            elif not situation.is_running:
                pass
            else:
                running_situations.append(situation)
        return running_situations

    def _preroll(self, preroll_time):
        super()._preroll(preroll_time)
        time_to_preroll = services.time_service().sim_now - preroll_time
        self.change_state(self._get_starting_state())
        while time_to_preroll >= TimeSpan.ZERO:
            current_state = self._current_state
            time_to_preroll = current_state.preroll(time_to_preroll)
            if time_to_preroll > TimeSpan.ZERO and current_state is self._current_state:
                logger.error('State {} did not change the current state despite saying that there is still time left for preroll.')
                break
        preroll_time_override = time_to_preroll if time_to_preroll < TimeSpan.ZERO else None
        self._current_state.on_state_activated(preroll_time_override=preroll_time_override)
