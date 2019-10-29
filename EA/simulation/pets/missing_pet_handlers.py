from sims4.gsi.dispatcher import GsiHandler
    return_pet_cheat.add_token_param('household_id')
    post_alert_cheat.add_token_param('household_id')
@GsiHandler('missing_pets_schema_view', missing_pet_schema)
def generate_missing_pet_view():
    missing_pet_data = []
    for household in services.household_manager().values():
        gsi_data = household.missing_pet_tracker.get_missing_pet_data_for_gsi()
        missing_pet_data.append(gsi_data)
    return missing_pet_data
