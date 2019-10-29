import operatorimport randomfrom filters.household_template import HouseholdTemplatefrom sims.sim_info_types import Agefrom sims4.service_manager import Servicefrom sims4.tuning.geometric import TunableCurve, TunableWeightedUtilityCurvefrom sims4.tuning.tunable import TunableList, Tunable, TunableMapping, TunableTuple, AutoFactoryInit, HasTunableSingletonFactory, TunableRegionDescription, TunableHouseDescription, TunableRange, TunableWorldDescriptionimport clockimport element_utilsimport elementsimport servicesimport sims4.loglogger = sims4.log.Logger('NeighborhoodPopulation')GENERATE_HOUSEHOLD_ID = 0
class _BasePopulationRequest:

    def __init__(self, account, num_to_fill, neighborhood_id, completion_callback):
        self._account = account
        self._num_to_fill = num_to_fill
        self._neighborhood_id = neighborhood_id
        self._completion_callback = completion_callback

    def _get_region_household_population_data_and_neighborhood_proto(self):
        neighborhood_proto = services.get_persistence_service().get_neighborhood_proto_buff(self._neighborhood_id)
        region_id = neighborhood_proto.region_id
        return (NeighborhoodPopulationService.REGION_TO_HOUSEHOLD_POPULATION_DATA.get(region_id), neighborhood_proto)

    def _create_household_from_template_and_add_to_zone(self, household_template, neighborhood_proto, zone_id, creation_source:str='neigh_pop_service : Unknown'):
        household = household_template.create_household(zone_id, self._account, creation_source=creation_source)
        self._move_household_into_zone(household, neighborhood_proto, zone_id)

    def _move_household_into_zone(self, household, neighborhood_proto, zone_id):
        household.move_into_zone(zone_id)

    def process_completed(self, result):
        if self._completion_callback is not None:
            self._completion_callback(result)

class _FillZonePopulationRequest(_BasePopulationRequest):
    RELATIONSHIP_DEPTH_WEIGHT = Tunable(description='\n        Multiplier used to modify relationship depth to determine how\n        important depth is in weight.  The higher the multiplier the\n        more relationship depth is added to weight score.  The lower the\n        weight the less likely household will be moved in.\n        ', tunable_type=float, default=0.5)
    RELATIONSHIP_TRACK_MULTIPLIER = Tunable(description='\n        Multiply the number of tracks by this multiplier to provide an\n        additional score to determine if household should be moved in. The\n        higher the multiplier the more the number of tracks bonus is added to\n        weight.  The lower the weight the less likely household will be moved\n        in.\n        ', tunable_type=float, default=2)
    RELATIONSHIP_UTILITY_CURVE = TunableWeightedUtilityCurve(description='\n        Based on the relationship score for a household apply a multiplier to\n        weight for determining score for moving household in.\n        ', x_axis_name='overall_score_for_household', y_axis_name='multiplier_to_apply')

    def __init__(self, *args, available_zone_ids=(), try_existing_households=False):
        super().__init__(*args)
        self._available_zone_ids = list(available_zone_ids)
        self._try_existing_households = try_existing_households

    def _add_household_template_to_zone(self, household_templates, total_beds, lot_has_double_beds, lot_has_kid_beds, neighborhood_proto, zone_id):
        households = []
        household_templates = [template_data for template_data in household_templates if template_data.household_template.get_number_of_guaranteed_members() <= total_beds]
        for template_data in household_templates:
            weight = template_data.weight
            household_template = template_data.household_template
            num_sims_in_template = household_template.get_number_of_guaranteed_members()
            nums_sims_to_weight_bonus = NeighborhoodPopulationService.NUM_BEDS_TO_IDEAL_HOUSEHOLD_CURVE.get(total_beds)
            if nums_sims_to_weight_bonus is not None:
                weight *= nums_sims_to_weight_bonus.get(num_sims_in_template)
            if weight <= 0:
                pass
            else:
                if household_template.has_teen_or_below:
                    weight *= NeighborhoodPopulationService.KID_TO_KID_BED_MULTIPLIER
                if household_template.has_spouse:
                    weight *= NeighborhoodPopulationService.SIGNIFICANT_OTHER_MULTIPLIER
                households.append((weight, household_template))
        if households:
            household_template = sims4.random.weighted_random_item(households)
            self._create_household_from_template_and_add_to_zone(household_template, neighborhood_proto, zone_id, creation_source='neigh_pop_service: residents')
            return True
        return False

    def _get_available_households(self, total_beds, lot_has_double_beds, lot_has_kid_beds):
        household_manager = services.household_manager()
        weighted_households = []
        for household in tuple(household_manager.values()):
            if not household.available_to_populate_zone():
                pass
            else:
                num_sims = len(household)
                if not num_sims:
                    pass
                else:
                    nums_sims_to_weight_bonus = NeighborhoodPopulationService.NUM_BEDS_TO_IDEAL_HOUSEHOLD_CURVE.get(total_beds)
                    if nums_sims_to_weight_bonus is not None:
                        weight = nums_sims_to_weight_bonus.get(num_sims)
                    else:
                        weight = 1
                    if weight <= 0:
                        pass
                    else:
                        household_has_married_sims = False
                        household_has_kids = False
                        total_household_relationship_weight = 0
                        sim_info_manager = services.sim_info_manager()
                        for sim_info in household:
                            if lot_has_double_beds:
                                spouse_sim_id = sim_info.spouse_sim_id
                                if household.get_sim_info_by_id(spouse_sim_id):
                                    household_has_married_sims = True
                            if sim_info.age <= Age.TEEN:
                                household_has_kids = True
                            total_sim_info_weight = 0
                            for relationship in sim_info.relationship_tracker:
                                target_sim_info = sim_info_manager.get(relationship.get_other_sim_id(sim_info.sim_id))
                                if target_sim_info is not None and target_sim_info.is_player_sim:
                                    total_sim_info_weight = relationship.get_relationship_depth(sim_info.sim_id)*self.RELATIONSHIP_DEPTH_WEIGHT
                                    total_sim_info_weight += len(relationship.relationship_track_tracker)*self.RELATIONSHIP_TRACK_MULTIPLIER
                            total_household_relationship_weight += total_sim_info_weight
                        total_household_relationship_weight /= num_sims
                        if self.RELATIONSHIP_UTILITY_CURVE is not None:
                            weight *= self.RELATIONSHIP_UTILITY_CURVE.get(total_household_relationship_weight)
                        if household_has_kids:
                            weight *= NeighborhoodPopulationService.KID_TO_KID_BED_MULTIPLIER
                        if household_has_married_sims:
                            weight *= NeighborhoodPopulationService.SIGNIFICANT_OTHER_MULTIPLIER
                        weighted_households.append((weight, household.id))
        return weighted_households

    def _get_household_templates_and_bed_data(self, zone_id, household_population_data):
        total_beds = 0
        lot_has_double_bed = False
        lot_has_kid_bed = False
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data.gameplay_zone_data.HasField('bed_info_data'):
            world_description_id = services.get_world_description_id(zone_data.world_id)
            household_templates = household_population_data.street_description_to_templates.get(world_description_id)
            total_beds = zone_data.gameplay_zone_data.bed_info_data.num_beds
            lot_has_double_bed = zone_data.gameplay_zone_data.bed_info_data.double_bed_exist
            lot_has_kid_bed = zone_data.gameplay_zone_data.bed_info_data.kid_bed_exist
            if total_beds == 0:
                total_beds = zone_data.gameplay_zone_data.bed_info_data.alternative_sleeping_spots
        else:
            house_description_id = persistence_service.get_house_description_id(zone_id)
            household_templates = household_population_data.household_description_to_templates.get(house_description_id)
            if household_templates:
                household_template = household_templates[0].household_template
                total_beds = household_template.get_number_of_guaranteed_members()
        return (household_templates, total_beds, lot_has_double_bed, lot_has_kid_bed)

    def process_request_gen(self, timeline):
        (household_population_data, neighborhood_proto) = self._get_region_household_population_data_and_neighborhood_proto()
        if household_population_data or not self._try_existing_households:
            logger.debug('There is no HouseholdPopulationRegionData for region: {}', neighborhood_proto.region_id)
            return
        while self._num_to_fill > 0 and self._available_zone_ids:
            zone_id = self._available_zone_ids.pop(random.randint(0, len(self._available_zone_ids) - 1))
            templates_and_bed_data = self._get_household_templates_and_bed_data(zone_id, household_population_data)
            (household_templates, total_beds, lot_has_double_bed, lot_has_kid_bed) = templates_and_bed_data
            if total_beds <= 0:
                pass
            else:
                moved_household_into_zone = False
                if self._try_existing_households:
                    weighted_households = self._get_available_households(total_beds, lot_has_double_bed, lot_has_kid_bed)
                    if household_templates:
                        ideal_household_curve = NeighborhoodPopulationService.NUM_BEDS_TO_IDEAL_HOUSEHOLD_CURVE.get(total_beds, None)
                        if ideal_household_curve is not None:
                            ideal_household_weight = next(iter(sorted(ideal_household_curve.points, key=operator.itemgetter(1), reverse=True)))
                            weighted_households.append((ideal_household_weight[1], GENERATE_HOUSEHOLD_ID))
                    if weighted_households:
                        household_id = sims4.random.weighted_random_item(weighted_households)
                        if household_id != GENERATE_HOUSEHOLD_ID:
                            household = services.household_manager().get(household_id)
                            if household is not None:
                                self._move_household_into_zone(household, neighborhood_proto, zone_id)
                                moved_household_into_zone = True
                if household_templates:
                    moved_household_into_zone = self._add_household_template_to_zone(household_templates, total_beds, lot_has_double_bed, lot_has_kid_bed, neighborhood_proto, zone_id)
                if moved_household_into_zone or moved_household_into_zone:
                    self._num_to_fill -= 1
                yield from element_utils.run_child(timeline, element_utils.sleep_until_next_tick_element())

class _CreateHomelessHouseholdRequest(_BasePopulationRequest):

    def process_request_gen(self, timeline):
        households = [(template_data.weight, template_data.household_template) for template_data in NeighborhoodPopulationService.HOMELESS_HOUSEHOLD_TEMPLATES]
        if not households:
            return
        while self._num_to_fill > 0:
            household_template = sims4.random.weighted_random_item(households)
            self._create_household_from_template_and_add_to_zone(household_template, None, 0, creation_source='neigh_pop_service: homeless')
            self._num_to_fill -= 1
            yield from element_utils.run_child(timeline, element_utils.sleep_until_next_tick_element())

class _FillRentableLotRequest(_BasePopulationRequest):

    def __init__(self, *args, available_zone_ids=None, region_renting_data=None):
        super().__init__(*args)
        self._region_renting_data = region_renting_data
        self._available_zone_ids = available_zone_ids

    def _get_max_travel_group_size(self, zone_id):
        max_group_size = 0
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data.gameplay_zone_data.HasField('bed_info_data'):
            total_beds = min(zone_data.gameplay_zone_data.bed_info_data.num_beds, max(self._region_renting_data.bed_count_to_travel_group_size.keys()))
            max_group_size_interval = self._region_renting_data.bed_count_to_travel_group_size.get(total_beds)
            max_group_size = max_group_size_interval.random_int() if max_group_size_interval is not None else 0
        else:
            house_description_id = persistence_service.get_house_description_id(zone_id)
            travel_group_size = self._region_renting_data.household_description_to_ideal_travel_group_size.get(house_description_id)
            if travel_group_size is None:
                return (0, 0)
            max_group_size = travel_group_size.random_int()
            total_beds = max_group_size
        return (max_group_size, total_beds)

    def _find_households_to_rent_lot(self):
        possible_travel_groups = []
        household_manager = services.household_manager()
        for household in household_manager.values():
            if household.hidden:
                pass
            elif household.any_member_in_travel_group():
                pass
            else:
                sim_infos_that_can_lead_travel_group = []
                sim_infos_available_for_vacation = []
                for sim_info in household:
                    if sim_info.is_instanced():
                        pass
                    else:
                        if sim_info.is_young_adult_or_older and sim_info.is_human:
                            sim_infos_that_can_lead_travel_group.append(sim_info)
                        if not sim_info.is_baby:
                            sim_infos_available_for_vacation.append(sim_info)
                if sim_infos_that_can_lead_travel_group:
                    possible_travel_groups.append((sim_infos_that_can_lead_travel_group, sim_infos_available_for_vacation))
        return possible_travel_groups

    def _send_sims_on_vacation(self, zone_id, sim_infos_to_send_to_vacation, duration):
        create_timestamp = services.time_service().sim_now
        end_timestamp = create_timestamp + clock.interval_in_sim_days(duration)
        travel_group_manager = services.travel_group_manager()
        travel_group_created = travel_group_manager.create_travel_group_and_rent_zone(sim_infos=sim_infos_to_send_to_vacation, zone_id=zone_id, played=False, create_timestamp=create_timestamp, end_timestamp=end_timestamp)
        if travel_group_created:
            for sim_info in sim_infos_to_send_to_vacation:
                sim_info.inject_into_inactive_zone(zone_id)
            return True
        return False

    def process_request_gen(self, timeline):
        if self._region_renting_data is None:
            return
        while self._num_to_fill > 0 and self._available_zone_ids:
            zone_id = random.choice(self._available_zone_ids)
            self._available_zone_ids.remove(zone_id)
            (max_group_size, total_sleeping_spots) = self._get_max_travel_group_size(zone_id)
            if not max_group_size == 0:
                if total_sleeping_spots == 0:
                    pass
                else:
                    possible_travel_groups = self._find_households_to_rent_lot()
                    if possible_travel_groups:
                        (sim_infos_that_can_lead_travel_group, sim_infos_available_for_vacation) = random.choice(possible_travel_groups)
                        sim_to_lead_group = random.choice(sim_infos_that_can_lead_travel_group)
                        sim_infos_available_for_vacation.remove(sim_to_lead_group)
                        random_sample_size = max_group_size - 1
                        sim_infos_to_send_to_vacation = []
                        if random_sample_size > 0:
                            if random_sample_size < len(sim_infos_available_for_vacation):
                                sim_infos_to_send_to_vacation = random.sample(sim_infos_available_for_vacation, random_sample_size)
                            else:
                                sim_infos_to_send_to_vacation = sim_infos_available_for_vacation
                        sim_infos_to_send_to_vacation.append(sim_to_lead_group)
                    else:
                        household_template = self._region_renting_data.travel_group_size_to_household_template(max_group_size)
                        if household_template is None:
                            pass
                        else:
                            household = household_template.create_household(zone_id, self._account, creation_source='neigh_pop_service:rentable_lot')
                            sim_infos_to_send_to_vacation = [sim_info for sim_info in household]
                            if self._send_sims_on_vacation(zone_id, sim_infos_to_send_to_vacation, self._region_renting_data.duration.random_int()):
                                self._num_to_fill -= 1
                            yield from element_utils.run_child(timeline, element_utils.sleep_until_next_tick_element())
                    if self._send_sims_on_vacation(zone_id, sim_infos_to_send_to_vacation, self._region_renting_data.duration.random_int()):
                        self._num_to_fill -= 1
                    yield from element_utils.run_child(timeline, element_utils.sleep_until_next_tick_element())

class TunableHouseholdTemplateWeightTuple(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(household_template=HouseholdTemplate.TunableReference(description='\n                Household template that will be created for neighborhood population\n                ', pack_safe=True), weight=Tunable(description='\n                Weight of this template being chosen.\n                ', tunable_type=float, default=1), **kwargs)

class HouseholdPopulationData(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'household_description_to_templates': TunableMapping(description='\n            Mapping of House Description ID to household templates and weight.  This\n            is used to fill households for the different type of regions.\n            ', key_name='House Description', key_type=TunableHouseDescription(pack_safe=True), value_name='Household Templates', value_type=TunableList(tunable=TunableHouseholdTemplateWeightTuple())), 'street_description_to_templates': TunableMapping(description='\n            Mapping of World Description ID to household templates and weight.  This\n            is used to fill households for the different type of streets.\n            ', key_name='House Description', key_type=TunableWorldDescription(pack_safe=True), value_name='Household Templates', value_type=TunableList(tunable=TunableHouseholdTemplateWeightTuple()))}

class NeighborhoodPopulationService(Service):
    REGION_TO_HOUSEHOLD_POPULATION_DATA = TunableMapping(description='\n        Mapping of Region Description ID to household population data.  This is\n        used to fill households for the different type of regions.\n        ', key_name='Region Description', key_type=TunableRegionDescription(pack_safe=True), value_name='Household Population Data', value_type=HouseholdPopulationData.TunableFactory())
    HOMELESS_HOUSEHOLD_TEMPLATES = TunableList(description='\n        A List of household templates that will be considered for homelesss\n        households.\n        ', tunable=TunableHouseholdTemplateWeightTuple())
    NUM_BEDS_TO_IDEAL_HOUSEHOLD_CURVE = TunableMapping(description='\n        Based on the number of beds and the number of sims in the household, a\n        multiplier will be applied to the household to determine if household\n        will be selected and added to zone.\n        ', key_name='Num Beds', key_type=Tunable(tunable_type=int, default=1), value_name='Ideal Household Curve', value_type=TunableCurve(x_axis_name='num_sim_in_household', y_axis_name='bonus_multiplier'))
    KID_TO_KID_BED_MULTIPLIER = TunableRange(description='\n        When trying to populate a lot if lot has a kids bed and household has a\n        kid in it.  This multiplier will be applied to the weight of household\n        when selecting household to move in.\n        ', tunable_type=float, default=1, minimum=1)
    SIGNIFICANT_OTHER_MULTIPLIER = TunableRange(description='\n        When trying to populate a lot and if lot has a double bed and household\n        contains a pair of sims that are considered significant other.  This\n        multiplier will be applied to the weight of household when selecting\n        household to move in.\n        ', tunable_type=float, default=1, minimum=1)

    def __init__(self):
        self._requests = []
        self._processing_element_handle = None

    def _process_population_request_gen(self, timeline):
        while self._requests:
            request = self._requests.pop(0)
            try:
                yield from request.process_request_gen(timeline)
                request.process_completed(True)
            except GeneratorExit:
                raise
            except BaseException:
                request.process_completed(False)
                logger.exception('Exception raised while processing creating npc households')
            if self._requests:
                yield from element_utils.run_child(timeline, element_utils.sleep_until_next_tick_element())
        self._processing_element_handle = None

    def add_population_request(self, num_to_fill, neighborhood_id, completion_callback, available_zone_ids, try_existing_households):
        account = self._get_account()
        if account is None:
            return False
        request = _FillZonePopulationRequest(account, num_to_fill, neighborhood_id, completion_callback, available_zone_ids=available_zone_ids, try_existing_households=try_existing_households)
        self._add_request(request)
        return True

    def add_homeless_household_request(self, num_to_fill, completion_callback):
        account = self._get_account()
        if account is None:
            return False
        request = _CreateHomelessHouseholdRequest(account, num_to_fill, None, completion_callback)
        self._add_request(request)
        return True

    def add_rentable_lot_request(self, num_to_fill, neighborhood_id, completion_callback, available_zones, region_renting_data):
        account = self._get_account()
        if account is None:
            return False
        request = _FillRentableLotRequest(account, num_to_fill, neighborhood_id, completion_callback, available_zone_ids=available_zones, region_renting_data=region_renting_data)
        self._add_request(request)
        return True

    def _get_account(self):
        client = services.client_manager().get_first_client()
        if client.account is not None or client.household is not None:
            return client.account

    @property
    def is_processing_requests(self):
        return self._processing_element_handle or len(self._requests) > 0

    def _add_request(self, request):
        self._requests.append(request)
        if self._processing_element_handle is None:
            timeline = services.time_service().sim_timeline
            element = elements.GeneratorElement(self._process_population_request_gen)
            self._processing_element_handle = timeline.schedule(element)
