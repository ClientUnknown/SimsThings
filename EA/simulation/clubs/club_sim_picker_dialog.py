from ui.ui_dialog_picker import UiSimPicker, SimPickerRow, ObjectPickerType
class ClubSimPickerRow(SimPickerRow):

    def __init__(self, *args, failed_criteria=None, **kwargs):
        super().__init__(*args, is_enable=not failed_criteria, **kwargs)
        self.failed_criteria = failed_criteria

    def populate_protocol_buffer(self, sim_row_data):
        super().populate_protocol_buffer(sim_row_data)
        if self.failed_criteria is not None:
            sim_row_data.failed_criteria.extend(self.failed_criteria)

class UiClubSimPicker(UiSimPicker):

    def __init__(self, *args, club_building_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.SIM_CLUB
        self._club_building_info = club_building_info

    def _validate_row(self, row):
        return isinstance(row, ClubSimPickerRow)

    def _build_customize_picker(self, picker_data):
        if self._club_building_info is not None:
            picker_data.sim_picker_data.club_building_info = self._club_building_info
        return super()._build_customize_picker(picker_data)
