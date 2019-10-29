from business.business_summary_dialog import BusinessSummaryDialogimport sims4logger = sims4.log.Logger('Business', default_owner='jdimailig')
class VetClinicSummaryDialog(BusinessSummaryDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._advertising_cost = 0
        self._employee_wages = 0

    def _calculated_profit(self):
        return self._business_manager.daily_revenue - self._employee_wages - self._advertising_cost

    def _add_line_entries(self):
        self._add_daily_revenue_line_entry()
        self._add_employee_wages_line_entry()
        self._add_advertising_costs()
        self._employee_wages = self._business_manager.get_total_employee_wages()
        self._advertising_cost = self._business_manager.get_current_advertising_cost()
