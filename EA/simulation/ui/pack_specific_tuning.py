from sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableEnumFlags, TunableMapping, TunableReference, TunableTuplefrom sims4.tuning.tunable_base import ExportModesfrom venues.venue_tuning import VenueFlagsimport servicesimport sims4.resourceslogger = sims4.log.Logger('PackSpecificTuning', default_owner='stjulien')
def verify_venue_tuning(instance_class, tunable_name, source, value, **kwargs):
    venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
    remapped_keys = venue_manager.remapped_keys
    if remapped_keys is not None:
        for (stripped_key, pack_specific_key) in remapped_keys.items():
            if pack_specific_key.group != 0:
                venue_tuning = venue_manager.get(stripped_key)
                if venue_tuning is not None and venue_tuning.visible_in_map_view and (venue_tuning.hide_from_buildbuy_ui or value.get(venue_tuning) is None):
                    logger.error('PackSpecificTuning for venue is missing. {}', venue_tuning)

class PackSpecificTuning:
    VENUE_PACK_TUNING = TunableMapping(description="\n        Venue tuning that is needed by UI when that venue's pack is not installed.\n        ", key_name='venue_id', key_type=TunableReference(description='\n            Reference to the venue that this data represents\n            ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True), value_name='data', value_type=TunableTuple(description="\n            Venue data that is shown in the UI when this venue's pack is not installed.\n            ", venue_name=TunableLocalizedStringFactory(description='\n                Name that will be displayed for the venue when the pack containing \n                that venue is not installed\n                '), venue_flags=TunableEnumFlags(description='\n                Venue flags used to mark a venue with specific properties.\n                ', enum_type=VenueFlags, allow_no_flags=True, default=VenueFlags.NONE), export_class_name='VenueDataTuple'), tuple_name='VenuePackTuning', export_modes=ExportModes.All, verify_tunable_callback=verify_venue_tuning)
