from interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedString, LocalizationHelperTuningfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableList, TunableTuple, TunableRange, Tunable, OptionalTunableimport servicesimport sims4.loglogger = sims4.log.Logger('Prep Tasks', default_owner='jdimailig')
class PrepTask(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            Statistic that is tracked by this prep task.\n            ', manager=services.get_instance_manager(Types.STATISTIC)), 'linked_statistics': TunableList(description='\n            If specified, these are statistics whose value updates\n            are linked to the specified statistic.\n            \n            Value changes to the linked statistic are applied with\n            the tuned multiplier to the statistic.\n            ', tunable=TunableTuple(stat_type=TunableReference(manager=services.get_instance_manager(Types.STATISTIC)), multiplier=TunableRange(tunable_type=float, minimum=0.0, default=1.0))), 'task_icon': TunableIcon(description='\n            The icon to use in displaying the prep task.\n            '), 'task_description': TunableLocalizedStringFactory(description='\n            A description of the prep task. {0.String}\n            is the thresholded description.\n            '), 'task_tooltip': OptionalTunable(description='\n            If enabled, tooltip will show up on the preptask.\n            ', tunable=TunableLocalizedStringFactory(description='\n                A tooltip of the prep task. \n                ')), 'thresholded_descriptions': TunableList(description='\n            A list of thresholds and the text describing it. The\n            thresholded description will be largest threshold\n            value in this list that the commodity is >= to.\n            ', tunable=TunableTuple(threshold=Tunable(description='\n                    Threshold that the commodity must >= to.\n                    ', tunable_type=float, default=0.0), text=TunableLocalizedString(description='\n                    Description for meeting this threshold.\n                    ')))}

    def get_prep_task_progress_thresholds(self, sim_info):
        lower_threshold = None
        upper_threshold = None
        stat = sim_info.get_statistic(self.statistic)
        value = stat.get_value()
        for threshold in self.thresholded_descriptions:
            if lower_threshold is None or threshold.threshold > lower_threshold.threshold:
                lower_threshold = threshold
            if not upper_threshold is None:
                if threshold.threshold < upper_threshold.threshold:
                    upper_threshold = threshold
            upper_threshold = threshold
        return (lower_threshold, upper_threshold)

    def get_prep_task_display_name(self, sim_info):
        loc_strings = []
        lower_threshold = None
        stat = sim_info.get_statistic(self.statistic)
        if stat is not None:
            (lower_threshold, _) = self.get_prep_task_progress_thresholds(sim_info)
        if lower_threshold:
            description = self.task_description(lower_threshold.text)
        else:
            description = self.task_description()
        loc_strings.append(description)
        if loc_strings:
            return LocalizationHelperTuning.get_new_line_separated_strings(*loc_strings)

    def is_completed(self, sim_info):
        stat = sim_info.get_statistic(self.statistic)
        if stat is None:
            return False
        return stat.get_value() >= stat.max_value
