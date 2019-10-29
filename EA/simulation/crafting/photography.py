from crafting.crafting_tunable import CraftingTuningfrom crafting.photography_enums import CameraQuality, PhotoStyleType, CameraMode, PhotoOrientation, PhotoSizefrom crafting.photography_loots import RotateTargetPhotoLootfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleSimAndObjectResolverfrom interactions import ParticipantTypefrom objects import PaintingStatefrom objects.components.state import TunableStateValueReferencefrom objects.components.types import STORED_SIM_INFO_COMPONENTfrom objects.system import create_objectfrom sims4.tuning.tunable import TunablePackSafeReference, TunableEnumEntry, TunableList, TunableReference, TunableInterval, TunableMapping, Tunablefrom statistics.skill import Skillfrom tunable_multiplier import TunableStatisticModifierCurveimport servicesimport sims4import taglogger = sims4.log.Logger('Photography', default_owner='rrodgers')
class Photography:
    SMALL_PORTRAIT_OBJ_DEF = TunablePackSafeReference(description='\n        Object definition for a small portrait photo.\n        ', manager=services.definition_manager())
    SMALL_LANDSCAPE_OBJ_DEF = TunablePackSafeReference(description='\n        Object definition for a small landscape photo.\n        ', manager=services.definition_manager())
    MEDIUM_PORTRAIT_OBJ_DEF = TunablePackSafeReference(description='\n        Object definition for a medium portrait photo.\n        ', manager=services.definition_manager())
    MEDIUM_LANDSCAPE_OBJ_DEF = TunablePackSafeReference(description='\n        Object definition for a medium landscape photo.\n        ', manager=services.definition_manager())
    LARGE_PORTRAIT_OBJ_DEF = TunablePackSafeReference(description='\n        Object definition for a large portrait photo.\n        ', manager=services.definition_manager())
    LARGE_LANDSCAPE_OBJ_DEF = TunablePackSafeReference(description='\n        Object definition for a large landscape photo.\n        ', manager=services.definition_manager())
    PAINTING_INTERACTION_TAG = TunableEnumEntry(description='\n        Tag to specify a painting interaction.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID)
    PHOTOGRAPHY_LOOT_LIST = TunableList(description='\n        A list of loot operations to apply to the photographer when photo mode exits.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))
    FAIL_PHOTO_QUALITY_RANGE = TunableInterval(description='\n        The random quality statistic value that a failure photo will be\n        given between the min and max tuned values.\n        ', tunable_type=int, default_lower=0, default_upper=100)
    BASE_PHOTO_QUALITY_MAP = TunableMapping(description='\n        The mapping of CameraQuality value to an interval of quality values\n        that will be used to asign a random base quality value to a photo\n        as it is created.\n        ', key_type=TunableEnumEntry(description='\n            The CameraQuality value. If this photo has this CameraQuality,\n            value, then a random quality between the min value and max value\n            will be assigned to the photo.\n            ', tunable_type=CameraQuality, default=CameraQuality.CHEAP), value_type=TunableInterval(description='\n            The range of base quality values from which a random value will be\n            given to the photo.\n            ', tunable_type=int, default_lower=1, default_upper=100))
    QUALITY_MODIFIER_PER_SKILL_LEVEL = Tunable(description='\n        For each level of skill in Photography, this amount will be added to\n        the quality statistic.\n        ', tunable_type=float, default=0)
    PHOTO_VALUE_MODIFIER_MAP = TunableMapping(description='\n        The mapping of state values to Simoleon value modifiers.\n        The final value of a photo is decided based on its\n        current value multiplied by the sum of all modifiers for\n        states that apply to the photo. All modifiers are\n        added together first, then the sum will be multiplied by\n        the current price.\n        ', key_type=TunableStateValueReference(description='\n            The quality state values. If this photo has this state,\n            then a random modifier between min_value and max_value\n            will be multiplied to the current price.'), value_type=TunableInterval(description='\n            The maximum modifier multiplied to the current price based on the provided state value\n            ', tunable_type=float, default_lower=1, default_upper=1))
    PHOTO_VALUE_SKILL_CURVE = TunableStatisticModifierCurve.TunableFactory(description="\n        Allows you to adjust the final value of the photo based on the Sim's\n        level of a given skill.\n        ", axis_name_overrides=('Skill Level', 'Simoleon Multiplier'), locked_args={'subject': ParticipantType.Actor})
    PHOTOGRAPHY_SKILL = Skill.TunablePackSafeReference(description='\n        A reference to the photography skill.\n        ')
    EMOTION_STATE_MAP = TunableMapping(description="\n        The mapping of moods to states, used to give photo objects a mood\n        based state. These states are then used by the tooltip component to\n        display emotional content on the photo's tooltip.\n        ", key_type=TunableReference(description='\n            The mood to associate with a state.\n            ', manager=services.mood_manager()), value_type=TunableStateValueReference(description='\n            The state that represents the mood for the purpose of displaying\n            emotional content in a tooltip.\n            '))
    PHOTO_OBJECT_LOOT_PER_TARGET = TunableList(description='\n        A list of loots which will be applied once PER target. The participants\n        for each application will be Actor: photographer, Target: photograph\n        target and Object: the Photograph itself. If a photo interaction has 2\n        target sims, this loot will be applied twice.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True))
    MOOD_PARAM_TO_MOOD_CATEGORY_STATE = TunableMapping(description='\n        If the player took a picture in a photo mode that supports mood\n        categories, we will perform a state change to the corresponding state\n        based on the mood that each picture was taken in.\n        ', key_type=Tunable(description='\n            The mood ASM parameter value to associate with a state.\n            ', tunable_type=str, default=None), value_type=TunableStateValueReference(description='\n            The state that represents the mood category.\n            '))
    GROUP_PHOTO_X_ACTOR_TAG = TunableEnumEntry(description='\n        Tag to specify the photo studio interaction that the photo target sim\n        who should be considered the x actor will run.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,))
    GROUP_PHOTO_Y_ACTOR_TAG = TunableEnumEntry(description='\n        Tag to specify the photo studio interaction that the photo target sim\n        who should be considered the y actor will run.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,))
    GROUP_PHOTO_Z_ACTOR_TAG = TunableEnumEntry(description='\n        Tag to specify the photo studio interaction that the photo target sim\n        who should be considered the z actor will run.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,))
    NUM_PHOTOS_PER_SESSION = Tunable(description='\n        Max possible photos that can be taken during one photo session. Once\n        this number has been reached, the photo session will exit.\n        ', tunable_type=int, default=5)

    @classmethod
    def _is_fail_photo(cls, photo_style_type):
        if photo_style_type == PhotoStyleType.EFFECT_GRAINY or (photo_style_type == PhotoStyleType.EFFECT_OVERSATURATED or (photo_style_type == PhotoStyleType.EFFECT_UNDERSATURATED or (photo_style_type == PhotoStyleType.PHOTO_FAIL_BLURRY or (photo_style_type == PhotoStyleType.PHOTO_FAIL_FINGER or photo_style_type == PhotoStyleType.PHOTO_FAIL_GNOME)))) or photo_style_type == PhotoStyleType.PHOTO_FAIL_NOISE:
            return True
        return False

    @classmethod
    def _apply_quality_and_value_to_photo(cls, photographer_sim, photo_obj, photo_style, camera_quality):
        quality_stat = CraftingTuning.QUALITY_STATISTIC
        quality_stat_tracker = photo_obj.get_tracker(quality_stat)
        if cls._is_fail_photo(photo_style):
            final_quality = cls.FAIL_PHOTO_QUALITY_RANGE.random_int()
        else:
            quality_range = cls.BASE_PHOTO_QUALITY_MAP.get(camera_quality, None)
            if quality_range is None:
                logger.error('Photography tuning BASE_PHOTO_QUALITY_MAP does not have an expected quality value: []', str(camera_quality))
                return
            base_quality = quality_range.random_int()
            skill_quality_modifier = 0
            if cls.PHOTOGRAPHY_SKILL is not None:
                effective_skill_level = photographer_sim.get_effective_skill_level(cls.PHOTOGRAPHY_SKILL)
                if effective_skill_level:
                    skill_quality_modifier = effective_skill_level*cls.QUALITY_MODIFIER_PER_SKILL_LEVEL
            final_quality = base_quality + skill_quality_modifier
        quality_stat_tracker.set_value(quality_stat, final_quality)
        value_multiplier = 1
        for (state_value, value_mods) in cls.PHOTO_VALUE_MODIFIER_MAP.items():
            if photo_obj.has_state(state_value.state):
                actual_state_value = photo_obj.get_state(state_value.state)
                if state_value is actual_state_value:
                    value_multiplier *= value_mods.random_float()
                    break
        value_multiplier *= cls.PHOTO_VALUE_SKILL_CURVE.get_multiplier(SingleSimResolver(photographer_sim), photographer_sim)
        photo_obj.base_value = int(photo_obj.base_value*value_multiplier)

    @classmethod
    def _get_mood_sim_info_if_exists(cls, photographer_sim_info, target_sim_ids, camera_mode):
        if camera_mode is CameraMode.SELFIE_PHOTO:
            return photographer_sim_info
        else:
            num_target_sims = len(target_sim_ids)
            if num_target_sims == 1:
                sim_info_manager = services.sim_info_manager()
                target_sim_info = sim_info_manager.get(target_sim_ids[0])
                return target_sim_info

    @classmethod
    def _apply_mood_state_if_appropriate(cls, photographer_sim_info, target_sim_ids, camera_mode, photo_object):
        mood_sim_info = cls._get_mood_sim_info_if_exists(photographer_sim_info, target_sim_ids, camera_mode)
        if mood_sim_info:
            mood = mood_sim_info.get_mood()
            mood_state = cls.EMOTION_STATE_MAP.get(mood, None)
            if mood_state:
                photo_object.set_state(mood_state.state, mood_state)

    @classmethod
    def _apply_mood_category_state_if_appropriate(cls, selected_mood_param, camera_mode, photo_object):
        if camera_mode in (CameraMode.TRIPOD, CameraMode.SIM_PHOTO, CameraMode.PHOTO_STUDIO_PHOTO):
            mood_category_state = cls.MOOD_PARAM_TO_MOOD_CATEGORY_STATE.get(selected_mood_param, None)
            if mood_category_state:
                photo_object.set_state(mood_category_state.state, mood_category_state)

    @classmethod
    def create_photo_from_photo_data(cls, camera_mode, camera_quality, photographer_sim_id, target_obj_id, target_sim_ids, res_key, photo_style, photo_size, photo_orientation, photographer_sim_info, photographer_sim, time_stamp, selected_mood_param):
        photo_object = None
        is_paint_by_reference = camera_mode is CameraMode.PAINT_BY_REFERENCE
        if is_paint_by_reference:
            current_zone = services.current_zone()
            photo_object = current_zone.object_manager.get(target_obj_id)
            if photo_object is None:
                photo_object = current_zone.inventory_manager.get(target_obj_id)
        else:
            if photo_orientation == PhotoOrientation.LANDSCAPE:
                if photo_size == PhotoSize.LARGE:
                    photo_object_def = cls.LARGE_LANDSCAPE_OBJ_DEF
                elif photo_size == PhotoSize.MEDIUM:
                    photo_object_def = cls.MEDIUM_LANDSCAPE_OBJ_DEF
                elif photo_size == PhotoSize.SMALL:
                    photo_object_def = cls.SMALL_LANDSCAPE_OBJ_DEF
            elif photo_orientation == PhotoOrientation.PORTRAIT:
                if photo_size == PhotoSize.LARGE:
                    photo_object_def = cls.LARGE_PORTRAIT_OBJ_DEF
                elif photo_size == PhotoSize.MEDIUM:
                    photo_object_def = cls.MEDIUM_PORTRAIT_OBJ_DEF
                elif photo_size == PhotoSize.SMALL:
                    photo_object_def = cls.SMALL_PORTRAIT_OBJ_DEF
                else:
                    photo_object_def = cls.SMALL_LANDSCAPE_OBJ_DEF
            if photo_object_def is None:
                return
            photo_object = create_object(photo_object_def)
        if photo_object is None:
            logger.error('photo object could not be found.')
            return
        for target_sim_id in target_sim_ids:
            target_sim_info = services.sim_info_manager().get(target_sim_id)
            target_sim = target_sim_info.get_sim_instance()
            resolver = DoubleSimAndObjectResolver(photographer_sim, target_sim, photo_object, source=cls)
            for loot in cls.PHOTO_OBJECT_LOOT_PER_TARGET:
                loot.apply_to_resolver(resolver)
        photography_service = services.get_photography_service()
        loots = photography_service.get_loots_for_photo()
        for photoloot in loots:
            if photoloot._AUTO_FACTORY.FACTORY_TYPE is RotateTargetPhotoLoot:
                photographer_sim = photoloot.photographer
                photographer_sim_info = photographer_sim.sim_info
                break
        reveal_level = PaintingState.REVEAL_LEVEL_MIN if is_paint_by_reference else PaintingState.REVEAL_LEVEL_MAX
        painting_state = PaintingState.from_key(res_key, reveal_level, False, photo_style)
        photo_object.canvas_component.painting_state = painting_state
        photo_object.canvas_component.time_stamp = time_stamp
        photo_object.set_household_owner_id(photographer_sim.household_id)
        if selected_mood_param:
            cls._apply_mood_category_state_if_appropriate(selected_mood_param, camera_mode, photo_object)
        if not is_paint_by_reference:
            cls._apply_quality_and_value_to_photo(photographer_sim, photo_object, photo_style, camera_quality)
            cls._apply_mood_state_if_appropriate(photographer_sim_info, target_sim_ids, camera_mode, photo_object)
            photo_object.add_dynamic_component(STORED_SIM_INFO_COMPONENT, sim_id=photographer_sim.id)
            photo_object.update_object_tooltip()
            if not (photographer_sim.inventory_component.can_add(photo_object) and photographer_sim.inventory_component.player_try_add_object(photo_object)):
                logger.error("photo object could not be put in the sim's inventory, deleting photo.")
                photo_object.destroy()
        photo_targets = [services.sim_info_manager().get(sim_id) for sim_id in target_sim_ids]
        if camera_mode == CameraMode.TWO_SIM_SELFIE_PHOTO:
            photo_targets.append(photographer_sim_info)
        photo_targets = frozenset(photo_targets)
        services.get_event_manager().process_event(test_events.TestEvent.PhotoTaken, sim_info=photographer_sim_info, photo_object=photo_object, photo_targets=photo_targets)
