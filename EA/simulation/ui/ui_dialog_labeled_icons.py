from protocolbuffers import Dialog_pb2from distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, OptionalTunable, Tunable, TunableVariantfrom ui.ui_dialog import UiDialogOk, UiDialogOkCancelimport servicesimport sims4.resourcesimport sims4.loglogger = sims4.log.Logger('UiDialogLabeledIcons', default_owner='rmccord')
class UiDialogLabeledIcons(UiDialogOk):
    FACTORY_TUNABLES = {'labeled_icons': TunableList(TunableTuple(description='\n            A list of icons and labels to display in the UI dialog.\n            ', icon=TunableIcon(), label=TunableLocalizedStringFactory()))}

    def build_msg(self, additional_tokens=(), additional_icons=None, **kwargs):
        msg = super().build_msg(additional_tokens=additional_tokens, **kwargs)
        msg.dialog_type = Dialog_pb2.UiDialogMessage.ICONS_LABELS
        for labeled_icon in self.labeled_icons:
            msg.icon_infos.append(create_icon_info_msg(IconInfoData(labeled_icon.icon), name=self._build_localized_string_msg(labeled_icon.label, additional_tokens)))
        if additional_icons:
            msg.icon_infos.extend(additional_icons)
        return msg

class UiDialogAspirationProgress(UiDialogOk):
    FACTORY_TUNABLES = {'aspirations': TunableList(description='\n            A list of aspirations we are tracking to show progress for in the\n            dialog.\n            ', tunable=TunableReference(description='\n                An aspiration we want to show progress for.\n                \n                Currently, only Career Aspirations are supported.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationCareer')), 'progress_description': OptionalTunable(description='\n            If enabled, we will replace the description for the aspiration with\n            this text, which has tokens for the progress.\n            ', tunable=TunableTuple(description='\n                Tuning for the description to show aspiration progress.\n                ', complete=TunableLocalizedStringFactory(description='\n                    The localized description for a completed aspiration.\n                    Tokens:\n                    0: Sim\n                    1: # Progress Completed\n                    2: # Goal\n                    Example: "Progress (1.Number/2.Number)"\n                    '), incomplete=TunableLocalizedStringFactory(description='\n                    The localized description for an incomplete aspiration.\n                    Tokens:\n                    0: Sim\n                    1: # Progress Completed\n                    2: # Goal\n                    Example: "Progress (1.Number/2.Number)"\n                    '))), 'use_description_for_tooltip': Tunable(description='\n            If enabled, we will use the aspiration description as the\n            tooltip.\n            ', tunable_type=bool, default=False)}

    def build_msg(self, **kwargs):
        msg = super().build_msg(**kwargs)
        msg.dialog_type = Dialog_pb2.UiDialogMessage.ICONS_LABELS
        sim_info = self.owner.sim_info
        if sim_info is None:
            logger.error('Sim Info was None for {}', self._target_sim_id)
            return msg
        progress_description = self.progress_description
        aspiration_tracker = sim_info.aspiration_tracker
        if progress_description is not None:
            complete_loc_string = progress_description.complete(sim_info)
        for aspiration in self.aspirations:
            icon_resource = None
            if aspiration.display_icon is not None:
                icon_resource = aspiration.display_icon
            name = None
            if aspiration.display_name is not None:
                name = aspiration.display_name(sim_info)
            desc = None
            if progress_description is not None:
                aspiration_completed = aspiration_tracker.milestone_completed(aspiration)
                num_objectives = len(aspiration.objectives)
                if num_objectives == 0:
                    logger.error('Aspiration {} has no objectives.', aspiration)
                    num_progress = 0
                    num_goal = 0
                if num_objectives == 1:
                    num_progress = aspiration_tracker.get_objective_count(aspiration.objectives[0])
                    num_goal = aspiration.objectives[0].goal_value()
                else:
                    num_progress = sum(aspiration_tracker.objective_completed(objective) for objective in aspiration.objectives)
                    num_goal = aspiration.objective_completion_count()
                if aspiration_completed:
                    desc = complete_loc_string
                else:
                    desc = progress_description.incomplete(sim_info, num_progress, num_goal)
            elif aspiration.display_description is not None:
                desc = aspiration.display_description(sim_info)
            tooltip = None
            if self.use_description_for_tooltip or aspiration.display_tooltip is not None:
                tooltip = aspiration.display_tooltip(sim_info)
            elif aspiration.display_description is not None:
                tooltip = aspiration.display_description(sim_info)
            icon_data = IconInfoData(icon_resource=icon_resource)
            msg.icon_infos.append(create_icon_info_msg(icon_data, name=name, desc=desc, tooltip=tooltip))
        return msg

class TunableUiDialogVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, dialog_ok=UiDialogOk.TunableFactory(), dialog_ok_cancel=UiDialogOkCancel.TunableFactory(), dialog_icon_label=UiDialogLabeledIcons.TunableFactory(), default='dialog_ok', **kwargs)
