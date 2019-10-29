from protocolbuffers import Consts_pb2from event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSingleSimfrom interactions.utils.destruction_liability import DeleteObjectLiability, DELETE_OBJECT_LIABILITYfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects.client_object_mixin import ClientObjectMixinfrom sims.funds import FundsSource, get_funds_for_sourcefrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, TunableTuple, TunableRange, TunableSet, TunableEnumWithFilterfrom singletons import DEFAULTfrom tag import Tagfrom tunable_multiplier import TunableMultiplierfrom tunable_utils.tunable_object_generator import TunableObjectGeneratorVariant
class ObjectDestructionElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'objects_to_destroy': TunableObjectGeneratorVariant(description='\n            The objects to destroy.\n            ', participant_default=ParticipantType.Object), 'tag_restriction': OptionalTunable(description='\n            If enabled, only objects that have the tag inside this tuned set\n            will get destroyed. Disable means all objects found as the\n            participant will get destroyed.\n            ', tunable=TunableSet(description='\n                Tags for the objects to delete.\n                ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['object', 'func'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True)), disabled_name='no_restriction', enabled_name='add_restriction'), 'tests': TunableTestSet(description='\n            Tests that each object to destroy must pass in order for it to\n            actually be destroyed.\n            '), 'award_value': OptionalTunable(description="\n            If necessary, define how an amount corresponding to the objects'\n            value is distributed among Sims.\n            ", tunable=TunableTuple(recipients=TunableEnumEntry(description='\n                    Who to award funds to.  If more than one participant is\n                    specified, the value will be evenly divided among the\n                    recipients.\n                    ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), multiplier=TunableRange(description='\n                    Value multiplier for the award.\n                    ', tunable_type=float, default=1.0), tested_multipliers=TunableMultiplier.TunableFactory(description='\n                    Each multiplier that passes its test set will be applied to\n                    each award payment.\n                    ')))}

    def __init__(self, interaction, **kwargs):
        super().__init__(interaction, **kwargs)
        self._destroyed_objects = []

    def _get_objects_to_destroy_gen(cls, interaction, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        sim = interaction.sim if context is DEFAULT else context.sim
        target = interaction.target if target is DEFAULT else target
        objects = cls.objects_to_destroy.get_objects(interaction, sim=sim, target=target, **interaction_parameters)
        for obj in objects:
            resolver = interaction.get_resolver(target=obj, context=context, **interaction_parameters)
            if not cls.tag_restriction is not None or not obj.definition.has_build_buy_tag(*cls.tag_restriction):
                pass
            elif not cls.tests.run_tests(resolver):
                pass
            else:
                yield obj

    def _get_object_value(cls, obj, interaction, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        award = cls.award_value
        if award is None:
            return 0
        target = interaction.target if target is DEFAULT else target
        resolver = interaction.get_resolver(target=target, context=context, **interaction_parameters)
        multiplier = award.tested_multipliers.get_multiplier(resolver)
        return int(obj.current_value*award.multiplier*multiplier)

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, object_destruction_element, object_tuning_id=DEFAULT):

        def get_simoleon_delta(interaction, target=DEFAULT, context=DEFAULT, **interaction_parameters):
            award_value = object_destruction_element.award_value
            if award_value is None:
                return (0, FundsSource.HOUSEHOLD)
            objs = tuple(ObjectDestructionElement._get_objects_to_destroy_gen(object_destruction_element, interaction, target=target, context=context, **interaction_parameters))
            value = sum(ObjectDestructionElement._get_object_value(object_destruction_element, o, interaction, target=target, context=context, **interaction_parameters) for o in objs)
            return (value, FundsSource.HOUSEHOLD)

        affordance.register_simoleon_delta_callback(get_simoleon_delta, object_tuning_id=object_tuning_id)

    def _destroy_objects(self):
        interaction = self.interaction
        sim = self.interaction.sim
        for object_to_destroy in self._destroyed_objects:
            in_use = object_to_destroy.in_use_by(sim, owner=interaction)
            if object_to_destroy.is_part:
                obj = object_to_destroy.part_owner
            else:
                obj = object_to_destroy
            if self.interaction.is_saved_participant(obj) or obj.parts and any(self.interaction.is_saved_participant(obj_part) for obj_part in obj.parts):
                obj.remove_from_client(fade_duration=ClientObjectMixin.FADE_DURATION)
                delete_liability = DeleteObjectLiability([obj])
                self.interaction.add_liability(DELETE_OBJECT_LIABILITY, delete_liability)
                return
            if in_use:
                obj.transient = True
                obj.remove_from_client(fade_duration=ClientObjectMixin.FADE_DURATION)
            else:
                if obj is interaction.target:
                    interaction.set_target(None)
                obj.destroy(source=interaction, cause='Destroying object in basic extra.', fade_duration=ClientObjectMixin.FADE_DURATION)

    def _do_behavior(self):
        value = 0
        tags = set()
        for obj in self._get_objects_to_destroy_gen(self.interaction):
            self._destroyed_objects.append(obj)
            if obj.is_part:
                obj = obj.part_owner
            value += self._get_object_value(obj, self.interaction)
            tags |= obj.get_tags()
            if obj.is_in_inventory():
                inventory = obj.get_inventory()
                inventory.try_remove_object_by_id(obj.id)
            else:
                obj.set_parent(None, transform=obj.transform, routing_surface=obj.routing_surface)
                obj_footprint_comp = obj.footprint_component
                if obj_footprint_comp is not None:
                    obj_footprint_comp.disable_footprint()
                obj.remove_from_client(fade_duration=ClientObjectMixin.FADE_DURATION)
                obj.base_value = 0
        if value:
            awardee = self.interaction.get_participant(self.award_value.recipients) if self.award_value is not None else None
            if awardee is not None:
                if self.interaction is not None:
                    tags |= self.interaction.get_category_tags()
                funds = get_funds_for_source(FundsSource.HOUSEHOLD, sim=awardee)
                funds.add(value, Consts_pb2.TELEMETRY_OBJECT_SELL, awardee, tags=tags)
        if self._destroy_objects:
            if self.interaction.is_finishing:
                self._destroy_objects()
            else:
                self.interaction.super_interaction.add_exit_function(self._destroy_objects)
