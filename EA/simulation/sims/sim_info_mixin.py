
class HasSimInfoBasicMixin:

    @property
    def account(self):
        return self.sim_info.account

    @property
    def account_id(self):
        return self.sim_info.account_id

    @property
    def client(self):
        return self.sim_info.client

    @property
    def zone_id(self):
        if self.sim_info is not None:
            return self.sim_info.zone_id

    @property
    def age(self):
        return self.sim_info.age

    @property
    def aspiration_tracker(self):
        return self.sim_info.aspiration_tracker

    @property
    def career_tracker(self):
        return self.sim_info.career_tracker

    @property
    def family_funds(self):
        return self.household.funds

    @property
    def first_name(self):
        return self.sim_info.first_name

    @first_name.setter
    def first_name(self, value):
        self.sim_info.first_name = value

    @property
    def full_name(self):
        return self.sim_info.full_name

    @property
    def gender(self):
        return self.sim_info.gender

    @property
    def clothing_preference_gender(self):
        return self.sim_info.clothing_preference_gender

    @property
    def species(self):
        return self.sim_info.species

    @property
    def extended_species(self):
        return self.sim_info.extended_species

    @property
    def grubby(self):
        return self.sim_info.grubby

    @grubby.setter
    def grubby(self, value):
        self.sim_info.grubby = value

    @property
    def household(self):
        return self.sim_info.household

    @property
    def household_id(self):
        return self.sim_info.household_id

    @property
    def icon_info(self):
        return self.sim_info.icon_info

    @property
    def is_ghost(self):
        return self.sim_info.is_ghost

    @property
    def is_human(self):
        return self.sim_info.is_human

    @property
    def is_pet(self):
        return self.sim_info.is_pet

    @property
    def is_npc(self):
        return self.sim_info.is_npc

    @property
    def is_at_home(self):
        return self.sim_info.is_at_home

    @property
    def is_player_sim(self):
        return self.sim_info.is_player_sim

    @property
    def is_selectable(self):
        return self.sim_info.is_selectable

    @property
    def last_name(self):
        return self.sim_info.last_name

    @last_name.setter
    def last_name(self, value):
        self.sim_info.last_name = value

    @property
    def manager_id(self):
        return self.sim_info.manager.id

    @property
    def on_fire(self):
        return self.sim_info.on_fire

    @property
    def pregnancy_progress(self):
        return self.sim_info.pregnancy_progress

    @pregnancy_progress.setter
    def pregnancy_progress(self, value):
        self.sim_info.pregnancy_progress = value

    @property
    def relationship_tracker(self):
        return self.sim_info.relationship_tracker

    @property
    def sim_id(self):
        return self.sim_info.sim_id

    @property
    def singed(self):
        return self.sim_info.singed

    @singed.setter
    def singed(self, value):
        self.sim_info.singed = value

    @property
    def spouse_sim_id(self):
        return self.sim_info.spouse_sim_id

    @property
    def trait_tracker(self):
        return self.sim_info.trait_tracker

    @property
    def travel_group(self):
        return self.sim_info.travel_group

    @property
    def voice_actor(self):
        return self.sim_info.voice_actor

    @voice_actor.setter
    def voice_actor(self, value):
        self.sim_info.voice_actor = value

    @property
    def voice_pitch(self):
        return self.sim_info.voice_pitch

    @voice_pitch.setter
    def voice_pitch(self, value):
        self.sim_info.voice_pitch = value

    @property
    def world_id(self):
        return self.sim_info.world_id

    @world_id.setter
    def world_id(self, value):
        self.sim_info.world_id = value

    def add_preload_outfit(self, *args, **kwargs):
        return self.sim_info.add_preload_outfit(*args, **kwargs)

    def get_current_outfit(self):
        return self.sim_info.get_current_outfit()

    def set_current_outfit(self, outfit_category_and_index) -> bool:
        return self.sim_info.set_current_outfit(outfit_category_and_index)

    def get_icon_info_data(self):
        return self.sim_info.get_icon_info_data()

    def get_outfits(self):
        return self.sim_info.get_outfits()

    def get_permission(self, permission_type):
        return self.sim_info.get_permission(permission_type)

    def get_significant_other_sim_info(self):
        return self.sim_info.get_significant_other_sim_info()

    def get_fiance_sim_info(self):
        return self.sim_info.get_fiance_sim_info()

    def get_spouse_sim_info(self):
        return self.sim_info.get_spouse_sim_info()

    def get_feud_target(self):
        return self.sim_info.get_feud_target()

    @property
    def squad_members(self):
        return self.sim_info.squad_members

    def add_trait(self, *args, **kwargs):
        return self.sim_info.add_trait(*args, **kwargs)

    def has_trait(self, trait):
        return self.sim_info.has_trait(trait)

    def remove_trait(self, *args, **kwargs):
        return self.sim_info.remove_trait(*args, **kwargs)

class HasSimInfoMixin(HasSimInfoBasicMixin):

    @property
    def Buffs(self):
        return self.sim_info.Buffs

    @property
    def careers(self):
        return self.sim_info.careers

    @property
    def commodity_tracker(self):
        return self.sim_info.commodity_tracker

    @property
    def static_commodity_tracker(self):
        return self.sim_info.static_commodity_tracker

    @property
    def statistic_tracker(self):
        return self.sim_info.statistic_tracker

    @property
    def lifestyle_brand_tracker(self):
        return self.sim_info.lifestyle_brand_tracker

    def add_buff(self, *args, **kwargs):
        return self.sim_info.add_buff(*args, **kwargs)

    def add_buff_from_op(self, *args, **kwargs):
        return self.sim_info.add_buff_from_op(*args, **kwargs)

    def add_modifiers_for_interaction(self, interaction, sequence):
        return self.sim_info.add_modifiers_for_interaction(interaction, sequence)

    def add_statistic_modifier(self, modifier, interaction_modifier=False):
        return self.sim_info.add_statistic_modifier(modifier, interaction_modifier)

    def buff_commodity_changed(self, *args, **kwargs):
        return self.sim_info.buff_commodity_changed(*args, **kwargs)

    def check_affordance_for_suppression(self, sim, aop, user_directed):
        return self.sim_info.check_affordance_for_suppression(sim, aop, user_directed)

    def create_statistic_tracker(self):
        self.sim_info.create_statistic_tracker()

    def debug_add_buff_by_type(self, *args, **kwargs):
        return self.sim_info.debug_add_buff_by_type(*args, **kwargs)

    def effective_skill_modified_buff_gen(self, *args, **kwargs):
        return self.sim_info.effective_skill_modified_buff_gen(*args, **kwargs)

    def enter_distress(self, commodity):
        self.sim_info.enter_distress(commodity)

    def exit_distress(self, commodity):
        self.sim_info.exit_distress(commodity)

    def get_active_buff_types(self, *args, **kwargs):
        return self.sim_info.get_active_buff_types(*args, **kwargs)

    def get_actor_scoring_modifier(self, *args, **kwargs):
        return self.sim_info.get_actor_scoring_modifier(*args, **kwargs)

    def get_actor_success_modifier(self, *args, **kwargs):
        return self.sim_info.get_actor_success_modifier(*args, **kwargs)

    def get_actor_new_pie_menu_icon_and_parent_name(self, *args, **kwargs):
        return self.sim_info.get_actor_new_pie_menu_icon_and_parent_name(*args, **kwargs)

    def get_actor_basic_extras_reversed_gen(self, *args, **kwargs):
        yield from self.sim_info.get_actor_basic_extras_reversed_gen(*args, **kwargs)

    def test_pie_menu_modifiers(self, *args, **kwargs):
        return self.sim_info.test_pie_menu_modifiers(*args, **kwargs)

    def get_all_stats_gen(self):
        return self.sim_info.get_all_stats_gen()

    def get_effective_skill_level(self, *args, **kwargs):
        return self.sim_info.get_effective_skill_level(*args, **kwargs)

    def get_initial_commodities(self, *args, **kwargs):
        return self.sim_info.get_initial_commodities(*args, **kwargs)

    def get_mood(self, *args, **kwargs):
        return self.sim_info.get_mood(*args, **kwargs)

    def get_mood_animation_param_name(self, *args, **kwargs):
        return self.sim_info.get_mood_animation_param_name(*args, **kwargs)

    def get_mood_intensity(self, *args, **kwargs):
        return self.sim_info.get_mood_intensity(*args, **kwargs)

    def get_off_lot_autonomy_rule(self):
        return self.sim_info.get_off_lot_autonomy_rule()

    def get_resolver(self, *args, **kwargs):
        return self.sim_info.get_resolver(*args, **kwargs)

    def get_score_multiplier(self, stat_type):
        return self.sim_info.get_score_multiplier(stat_type)

    def get_stat_instance(self, stat_type, **kwargs):
        return self.sim_info.get_stat_instance(stat_type, **kwargs)

    def get_stat_multiplier(self, stat_type, participant_type):
        return self.sim_info.get_stat_multiplier(stat_type, participant_type)

    def get_stat_value(self, stat_type):
        return self.sim_info.get_stat_value(stat_type)

    def get_statistic(self, stat, add=True):
        return self.sim_info.get_statistic(stat, add=add)

    def get_success_chance_modifier(self, *args, **kwargs):
        return self.sim_info.get_success_chance_modifier(*args, **kwargs)

    def get_tracker(self, *args, **kwargs):
        return self.sim_info.get_tracker(*args, **kwargs)

    def with_skill_bar_suppression(self, *args, **kwargs):
        return self.sim_info.with_skill_bar_suppression(*args, **kwargs)

    def has_buff(self, *args, **kwargs):
        return self.sim_info.has_buff(*args, **kwargs)

    def is_in_distress(self):
        return self.sim_info.is_in_distress()

    def is_locked(self, stat):
        return self.sim_info.is_locked(stat)

    def is_scorable(self, stat_type):
        return self.sim_info.is_scorable(stat_type)

    def remove_buff(self, *args, **kwargs):
        return self.sim_info.remove_buff(*args, **kwargs)

    def remove_buff_entry(self, *args, **kwargs):
        return self.sim_info.remove_buff_entry(*args, **kwargs)

    def remove_buff_by_type(self, *args, **kwargs):
        return self.sim_info.remove_buff_by_type(*args, **kwargs)

    def remove_statistic_modifier(self, handle):
        return self.sim_info.remove_statistic_modifier(handle)

    def set_buff_reason(self, *args, **kwargs):
        return self.sim_info.set_buff_reason(*args, **kwargs)

    def set_preload_outfits(self, *args, **kwargs):
        return self.sim_info.set_preload_outfits(*args, **kwargs)

    def set_stat_value(self, stat_type, *args, **kwargs):
        self.sim_info.set_stat_value(stat_type, *args, **kwargs)

    def update_all_commodities(self):
        return self.sim_info.update_all_commodities()

    def force_allow_fame(self, allow_fame):
        self.sim_info.force_allow_fame(allow_fame)

    def set_freeze_fame(self, freeze_fame):
        self.sim_info.set_freeze_fame(freeze_fame)

    @property
    def allow_fame(self):
        return self.sim_info.allow_fame

    @allow_fame.setter
    def allow_fame(self, value):
        self.sim_info.allow_fame = value

    @property
    def allow_reputation(self):
        return self.sim_info.allow_reputation

    @allow_reputation.setter
    def allow_reputation(self, value):
        self.sim_info.allow_reputation = value
