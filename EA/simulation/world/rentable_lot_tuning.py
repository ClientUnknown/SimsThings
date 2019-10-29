from sims4.tuning.tunable import TunableTuple, Tunablefrom sims4.tuning.tunable_base import ExportModes
class RentableZoneTuning:
    PRICE_MODIFIERS = TunableTuple(description='\n        Global price modifiers for all rentable zones.\n        ', add=Tunable(description='\n            Add modifier for the price to rent a lot.\n            ', tunable_type=float, default=0.0), multiply=Tunable(description='\n            Multiplier for the price to rent a lot.\n            ', tunable_type=float, default=1.0), export_class_name='TunablePriceModifiers', export_modes=ExportModes.All)
