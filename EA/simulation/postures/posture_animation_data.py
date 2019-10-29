from animation import get_throwaway_animation_contextfrom animation.asm import create_asmfrom interactions.constraint_variants import TunableConstraintVariantfrom interactions.utils.animation_reference import TunableAnimationReferencefrom sims.occult.occult_enums import OccultTypefrom sims.sim_info_types import Speciesfrom sims4.tuning.tunable import TunableTuple, TunableResourceKey, Tunable, AutoFactoryInit, HasTunableSingletonFactory, TunableMapping, TunableEnumEntry, TunableFactory, OptionalTunable, TunableListfrom sims4.tuning.tunable_base import SourceQueriesimport sims4.resources
class _TunableAnimationData(TunableTuple):
    ASM_SOURCE = '_asm_key'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, _asm_key=TunableResourceKey(description='\n                The posture ASM.\n                ', default=None, resource_types=[sims4.resources.Types.STATEMACHINE], category='asm', pack_safe=True), _actor_param_name=Tunable(description="\n                The name of the actor parameter in this posture's ASM. By\n                default, this is x, and you should probably not change it.\n                ", tunable_type=str, default='x', source_location=self.ASM_SOURCE, source_query=SourceQueries.ASMActorSim), _target_name=Tunable(description="\n                The actor name for the target object of this posture. Leave\n                empty for postures with no target. In the case of a posture\n                that targets an object, it should be the name of the object\n                actor in this posture's ASM.\n                ", tunable_type=str, default=None, source_location=self.ASM_SOURCE, source_query=SourceQueries.ASMActorAll), _jig_name=Tunable(description='\n                The actor name for the jig created by this posture, if a jig is\n                tuned.\n                ', tunable_type=str, default=None, source_location=self.ASM_SOURCE, source_query=SourceQueries.ASMActorObject), _enter_state_name=Tunable(description='\n                The name of the entry state for the posture in the ASM. All\n                postures should have two public states, not including entry\n                and exit. This should be the first of the two states.\n                ', tunable_type=str, default=None, source_location=self.ASM_SOURCE, source_query=SourceQueries.ASMState), _exit_state_name=Tunable(description='\n                The name of the exit state in the ASM. By default, this is\n                exit.\n                ', tunable_type=str, default='exit', source_location=self.ASM_SOURCE, source_query=SourceQueries.ASMState), _state_name=Tunable(description='\n                The main state name for the looping posture pose in the\n                ASM. All postures should have two public states, not\n                including entry and exit. This should be the second of the\n                two states.\n                ', tunable_type=str, default=None, source_location=self.ASM_SOURCE, source_query=SourceQueries.ASMState), _idle_animation=TunableAnimationReference(description='\n                The animation for a Sim to play while in this posture and\n                waiting for interaction behavior to start.\n                ', callback=None, pack_safe=True), _idle_animation_occult_overrides=TunableMapping(description='\n                A mapping of occult type to idle animation override data.\n                ', key_type=TunableEnumEntry(description='\n                    The occult type of the Sim.\n                    ', tunable_type=OccultType, default=OccultType.HUMAN), value_type=TunableAnimationReference(description='\n                    Idle animation overrides to use for a Sim based on their \n                    occult type.\n                    ', callback=None, pack_safe=True)), _set_locomotion_surface=Tunable(description='\n                If checked, then the Sim\'s locomotion surface is set to the\n                target of this posture, if it exists.\n                \n                The locomotion surface affects the sound of the Sim\'s footsteps\n                when locomoting. Generally, this should be unset, since most\n                Sims don\'t route on objects as part of postures. For the cases\n                where they do, however, we need to ensure the sound is properly\n                overridden.\n                \n                e.g. The "Sit" posture for Cats includes sitting on objects.\n                Some of those transitions involve Cats walking across the sofa.\n                We need to ensure that the sound of the footsteps matches the\n                fabric, instead of the floor/ground.\n                ', tunable_type=bool, default=False), _carry_constraint=OptionalTunable(description='\n                If enabled, Sims in this posture need to be picked up using this\n                specific constraint.\n                ', tunable=TunableList(tunable=TunableConstraintVariant(description='\n                        A constraint that must be fulfilled in order to pick up\n                        this Sim.\n                        ')), enabled_name='Override', disabled_name='From_Carryable_Component'), **kwargs)

class _AnimationDataBase(HasTunableSingletonFactory, AutoFactoryInit):

    def get_animation_data(self, sim, target):
        raise NotImplementedError

    def get_provided_postures_gen(self):
        raise NotImplementedError

    def get_supported_postures_gen(self):
        raise NotImplementedError

class AnimationDataUniversal(_AnimationDataBase):

    @TunableFactory.factory_option
    def animation_data_options(locked_args=None, **tunable_data_entries):
        return {'_animation_data': _TunableAnimationData(locked_args=locked_args, **tunable_data_entries)}

    def get_animation_data(self, sim, target):
        return self._animation_data

    def get_provided_postures_gen(self):
        asm = create_asm(self._animation_data._asm_key, get_throwaway_animation_context())
        provided_postures = asm.provided_postures
        if provided_postures:
            for species in Species:
                if species == Species.INVALID:
                    pass
                else:
                    yield (species, provided_postures, asm)

    def get_supported_postures_gen(self):
        asm = create_asm(self._animation_data._asm_key, get_throwaway_animation_context())
        supported_postures = asm.get_supported_postures_for_actor(self._animation_data._actor_param_name)
        for species in Species:
            if species == Species.INVALID:
                pass
            else:
                yield (species, supported_postures, asm)

class AnimationDataByActorSpecies(_AnimationDataBase):

    @TunableFactory.factory_option
    def animation_data_options(locked_args=None, **tunable_data_entries):
        return {'_actor_species_mapping': TunableMapping(description='\n                A mapping from actor species to animation data.\n                ', key_type=TunableEnumEntry(description='\n                    Species these animations are intended for.\n                    ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=_TunableAnimationData(locked_args=locked_args, **tunable_data_entries))}

    def get_animation_data(self, sim, target):
        return self._actor_species_mapping.get(sim.species)

    def get_animation_species(self):
        return self._actor_species_mapping.keys()

    def get_provided_postures_gen(self):
        for (species, animation_data) in self._actor_species_mapping.items():
            asm = create_asm(animation_data._asm_key, get_throwaway_animation_context())
            provided_postures = asm.provided_postures
            if not provided_postures:
                pass
            else:
                yield (species, provided_postures, asm)

    def get_supported_postures_gen(self):
        for (species, animation_data) in self._actor_species_mapping.items():
            asm = create_asm(animation_data._asm_key, get_throwaway_animation_context())
            supported_postures = asm.get_supported_postures_for_actor(animation_data._actor_param_name)
            yield (species, supported_postures, asm)

class AnimationDataByActorAndTargetSpecies(_AnimationDataBase):

    @TunableFactory.factory_option
    def animation_data_options(locked_args=None, **tunable_data_entries):
        return {'_actor_species_mapping': TunableMapping(description='\n                A mapping from actor species to target-based animation data\n                mappings.\n                ', key_type=TunableEnumEntry(description='\n                    Species these animations are intended for.\n                    ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunableMapping(description='\n                    A mapping of target species to animation data.\n                    ', key_type=TunableEnumEntry(description='\n                        Species these animations are intended for.\n                        ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=_TunableAnimationData(locked_args=locked_args, **tunable_data_entries)))}

    def get_animation_data(self, sim, target):
        actor_animation_data = self._actor_species_mapping.get(sim.species)
        if actor_animation_data is not None:
            return actor_animation_data.get(target.species)

    def get_provided_postures_gen(self):
        for (species, target_species_data) in self._actor_species_mapping.items():
            animation_data = next(iter(target_species_data.values()))
            asm = create_asm(animation_data._asm_key, get_throwaway_animation_context())
            provided_postures = asm.provided_postures
            if not provided_postures:
                pass
            else:
                yield (species, provided_postures, asm)

    def get_supported_postures_gen(self):
        for (species, target_species_data) in self._actor_species_mapping.items():
            animation_data = next(iter(target_species_data.values()))
            asm = create_asm(animation_data._asm_key, get_throwaway_animation_context())
            supported_postures = asm.get_supported_postures_for_actor(animation_data._actor_param_name)
            yield (species, supported_postures, asm)
