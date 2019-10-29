from distributor.shared_messages import IconInfoDatafrom fame.fame_tuning import LifestyleBrandProduct, LifestyleBrandTargetMarketfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.tunable_icon import TunableIconFactoryfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import ObjectPickerRow
class LifestyleBrandProductsPicker(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'products': TunableList(description='\n            A list of the type of products that a lifestyle brand can be selling.\n            ', tunable=TunableTuple(description='\n                A product is represented by a type, name, description, and icon.\n                ', product_type=TunableEnumEntry(description='\n                    The enum entry that identifies what type of product this is.\n                    This will be used with the target market to determine the\n                    payout curve of the lifestyle brand.\n                    ', tunable_type=LifestyleBrandProduct, default=LifestyleBrandProduct.INVALID, invalid_enums=(LifestyleBrandProduct.INVALID,)), name=TunableLocalizedString(description='\n                    The name that is displayed in the picker for the products.\n                    '), description_text=TunableLocalizedString(description='\n                    The description for the product that is displayed in the picker.\n                    '), icon=TunableIconFactory()), unique_entries=True, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        selected_product = None
        tracker = inst_or_cls.sim.sim_info.lifestyle_brand_tracker
        selected_product = tracker.product_choice
        for product in inst_or_cls.products:
            name = product.name
            description = product.description_text
            yield ObjectPickerRow(name=name, row_description=description, icon_info=IconInfoData(icon_resource=product.icon.key), tag=product.product_type, is_selected=selected_product == product.product_type)

    def on_choice_selected(self, choice_tag, **kwargs):
        sim = self.sim
        tracker = sim.sim_info.lifestyle_brand_tracker
        if tracker is None:
            return
        tracker.product_choice = choice_tag

class LifestyleBrandTargetMarketPicker(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'target_markets': TunableList(description='\n            A list of all the tuning needed for the different target markets for\n            the lifestyle brand Perk\n            ', tunable=TunableTuple(description='\n                A Target Market consists of a type, name, and icon to be displayed.\n                ', target_type=TunableEnumEntry(description='\n                    The type of target market this is associated with.\n                    ', tunable_type=LifestyleBrandTargetMarket, default=LifestyleBrandTargetMarket.INVALID, invalid_enums=(LifestyleBrandTargetMarket.INVALID,)), name=TunableLocalizedString(description='\n                    The name of the target market that is displayed in the picker.\n                    '), icon=TunableIconFactory()), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        selected_target_market = None
        tracker = inst_or_cls.sim.sim_info.lifestyle_brand_tracker
        selected_target_market = tracker.target_market
        for target_market in inst_or_cls.target_markets:
            name = target_market.name
            yield ObjectPickerRow(name=name, icon_info=IconInfoData(icon_resource=target_market.icon.key), tag=target_market.target_type, is_selected=selected_target_market == target_market.target_type)

    def on_choice_selected(self, choice_tag, **kwargs):
        sim = self.sim
        tracker = sim.sim_info.lifestyle_brand_tracker
        if tracker is None:
            return
        tracker.target_market = choice_tag

class LifestyleBrandLogoPicker(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'logos': TunableList(description='\n            A list of all the tuning needed for the different target markets for\n            the lifestyle brand Perk\n            ', tunable=TunableIconFactory(), tuning_group=GroupNames.PICKERTUNING, unique_entries=True)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        selected_logo = None
        tracker = inst_or_cls.sim.sim_info.lifestyle_brand_tracker
        selected_logo = tracker.logo
        for logo in inst_or_cls.logos:
            yield ObjectPickerRow(icon_info=IconInfoData(icon_resource=logo.key), tag=logo.key, is_selected=selected_logo == logo.key)

    def on_choice_selected(self, choice_tag, **kwargs):
        sim = self.sim
        tracker = sim.sim_info.lifestyle_brand_tracker
        if tracker is None:
            return
        tracker.logo = choice_tag
