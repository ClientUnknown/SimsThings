import operatorimport randomfrom careers.career_event_zone_director import CareerEventZoneDirectorfrom date_and_time import create_time_spanfrom sims4.tuning.tunable import TunableSimMinute, HasTunableSingletonFactory, AutoFactoryInit, TunableRange, Tunable, TunablePercent, TunableList, TunableTuple, TunableMappingfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestListimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('Doctor', default_owner='rfleig')EMERGENCY_COUNT = 'emergency_count'
class EmergencyFrequency(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'max_emergency_situations_per_shift': TunableRange(description='\n            The maximum number of times during a shift that an emergency\n            situation can be created/started.\n            ', tunable_type=int, default=1, minimum=0), 'inital_lockout_in_sim_minutes': TunableSimMinute(description='\n            The time, in Sim minutes, that pass at the beginning of a shift\n            before the first check for creating/starting an emergency happens.\n            ', default=60), 'cool_down_in_sim_minutes': TunableSimMinute(description='\n            How often a check for whether or not to create/start an emergency\n            happens.\n            ', default=60), 'percent_chance_of_emergency': TunablePercent(description='\n            The percentage chance that on any given check an emergency is to\n            to be created/started.\n            ', default=30), 'weighted_situations': TunableList(description='\n            A weighted list of situations to be used as emergencies. When a\n            check passes to create/start an emergency, this is the list\n            of emergency situations that will be chosen from.\n            ', tunable=TunableTuple(situation=Situation.TunableReference(), weight=Tunable(tunable_type=int, default=1)))}

class DoctorCareerEventZoneDirector(CareerEventZoneDirector):
    INSTANCE_TUNABLES = {'emergency_frequency': TunableMapping(description='\n            Each entry in the emergency frequency has two components. The first\n            component is the career level that it applies to.\n            \n            The second component is that actual tuning for how frequently an \n            emergency should occur.\n            \n            The entry that is closest to the current career level of the Sim \n            without exceeding the career level will be used.\n            \n            For example, given the following tuning:\n               career_level     emergency_frequency:\n               1                Tuning A,\n               4                Tuning B,\n               9                Tuning C\n               \n            If Sim is at career level 1, 2, or 3 then Tuning A will be used.\n            If Sim is at career level 4, 5, 6, 7, or 8 then Tuning B will be used.\n            If sim is at career level 9, 10 then Tuning C will be used.\n            ', key_name='career_level', key_type=Tunable(description='\n            \n                ', tunable_type=int, default=1), value_name='frequency_tuning', value_type=EmergencyFrequency.TunableFactory())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._emergency_count = 0
        self._emergency_alarm_handle = None

    def on_startup(self):
        super().on_startup()
        emergency_tuning = self._get_current_level_tuning()
        if emergency_tuning is not None:
            self._emergency_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=emergency_tuning.inital_lockout_in_sim_minutes), self._on_create_emergency_request, repeating=True, repeating_time_span=create_time_span(minutes=emergency_tuning.cool_down_in_sim_minutes))

    def on_shutdown(self):
        if self._emergency_alarm_handle is not None:
            alarms.cancel_alarm(self._emergency_alarm_handle)
            self._emergency_alarm_handle = None
        super().on_shutdown()

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if reader is not None:
            self._emergency_count = reader.read_int32(EMERGENCY_COUNT, 0)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        writer.write_int32(EMERGENCY_COUNT, self._emergency_count)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _on_create_emergency_request(self, *_, **__):
        emergency_tuning = self._get_current_level_tuning()
        if emergency_tuning.max_emergency_situations_per_shift <= self._emergency_count:
            return False
        if random.random() <= emergency_tuning.percent_chance_of_emergency:
            situation_manager = services.get_zone_situation_manager()
            situation = self._get_emergency_situation(emergency_tuning)
            guest_list = situation.get_predefined_guest_list()
            if guest_list is None:
                guest_list = SituationGuestList(invite_only=True)
            situation_id = situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False, creation_source=self.instance_name)
            self._situation_ids.append(situation_id)
            self._emergency_count += 1

    def _get_sorted_emergency_tuning(self):
        emergency_tuning = []
        for (career_level, tuning) in self.emergency_frequency.items():
            emergency_tuning.append((career_level, tuning))
        emergency_tuning.sort(key=operator.itemgetter(0))
        return emergency_tuning

    def _get_current_level_tuning(self):
        career_level = self._career_event.career.user_level
        sorted_tuning = self._get_sorted_emergency_tuning()
        if len(sorted_tuning) == 0:
            return
        entry = sorted_tuning[-1]
        tuning = entry[1]
        for entry in sorted_tuning:
            if entry[0] <= career_level:
                tuning = entry[1]
            else:
                break
        return tuning

    def _get_emergency_situation(self, emergency_tuning):
        weighted_situations = tuple((item.weight, item.situation) for item in emergency_tuning.weighted_situations)
        situation = sims4.random.weighted_random_item(weighted_situations)
        return situation
