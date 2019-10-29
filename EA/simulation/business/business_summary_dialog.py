from protocolbuffers import DistributorOps_pb2, Business_pb2from distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorimport enumimport services
class BusinessSummaryLineItemType(enum.Int, export=False):
    ENTRY_LINE_ITEM = 0
    TOTAL_LINE_ITEM = 1
    SUB_TOTAL_LINE_ITEM = 2

class BusinessSummaryDialog:

    def __init__(self, business_manager):
        self._business_manager = business_manager
        self._business_tuning = business_manager.tuning_data
        self._report_msg = Business_pb2.BusinessSummaryDialog()

    def _build(self):
        self._add_business_data()
        self._add_employee_data()
        self._add_line_entries()
        self._add_total_entry()

    def _add_business_data(self):
        self._report_msg.business_data = Business_pb2.SetBusinessData()
        self._business_manager.construct_business_message(self._report_msg.business_data)

    def _add_employee_data(self):
        for (business_employee_type, business_employee_data) in self._business_tuning.employee_data_map.items():
            current_employees = self._business_manager.get_employees_by_type(business_employee_type)
            sim_info_manager = services.sim_info_manager()
            for employee_sim_id in current_employees:
                employee_sim_info = sim_info_manager.get(employee_sim_id)
                with ProtocolBufferRollback(self._report_msg.employees) as employee_msg:
                    self._business_manager.populate_employee_msg(employee_sim_info, employee_msg, business_employee_type, business_employee_data)

    def _add_line_entries(self):
        raise NotImplementedError('No line entries defined for business summary.')

    def _add_total_entry(self):
        self._add_net_profit(self._calculated_profit())

    def _calculated_profit(self):
        raise NotImplementedError('No way to calculate profit in business summary.')

    def _add_line_entry(self, name, entry_type:BusinessSummaryLineItemType, value):
        with ProtocolBufferRollback(self._report_msg.lines_entries) as line_entry:
            line_entry.entry_name = name
            line_entry.entry_type = entry_type
            line_entry.entry_value = value

    def _add_daily_revenue_line_entry(self):
        daily_revenue = self._business_manager.daily_revenue
        self._add_line_entry(self._business_tuning.summary_dialog_transactions_header, BusinessSummaryLineItemType.ENTRY_LINE_ITEM, self._business_tuning.summary_dialog_transactions_text(int(daily_revenue)))

    def _add_employee_wages_line_entry(self):
        employee_wages = self._business_manager.get_total_employee_wages()
        self._add_line_entry(self._business_tuning.summary_dialog_wages_owed_header, BusinessSummaryLineItemType.ENTRY_LINE_ITEM, self._business_tuning.summary_dialog_wages_owed_text(int(-employee_wages)))

    def _add_advertising_costs(self):
        advertising_cost = self._business_manager.get_current_advertising_cost()
        self._add_line_entry(self._business_tuning.summary_dialog_wages_advertising_header, BusinessSummaryLineItemType.ENTRY_LINE_ITEM, self._business_tuning.summary_dialog_transactions_text(int(-advertising_cost)))

    def _add_net_profit(self, calculated_profit):
        self._add_line_entry(self._business_tuning.summary_dialog_wages_net_profit_header, BusinessSummaryLineItemType.TOTAL_LINE_ITEM, self._business_tuning.summary_dialog_wages_net_profit_text(int(calculated_profit)))

    def show_business_summary_dialog(self):
        self._build()
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.BUSINESS_SUMMARY_DIALOG, self._report_msg)
        Distributor.instance().add_op_with_no_owner(op)
