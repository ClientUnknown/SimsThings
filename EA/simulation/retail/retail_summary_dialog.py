import operatorfrom protocolbuffers import DistributorOps_pb2import protocolbuffersfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollback, ProtocolBufferRollbackExpectedfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom sims4.localization import LocalizationHelperTuning
class RetailSummaryDialog:

    @classmethod
    def show_dialog(cls, retail_manager, is_from_close=False):
        business_tuning = retail_manager.tuning_data
        report_msg = protocolbuffers.Dialog_pb2.RetailSummaryDialog()
        report_msg.name = LocalizationHelperTuning.get_raw_text(retail_manager.get_lot_name())
        report_msg.subtitle = business_tuning.summary_dialog_subtitle
        report_msg.icon = create_icon_info_msg(IconInfoData(business_tuning.summary_dialog_icon))
        timespan_since_open = retail_manager.get_timespan_since_open(is_from_close)
        report_msg.hours_open = round(timespan_since_open.in_hours()) if timespan_since_open is not None else 0
        report_msg.total_amount = retail_manager.get_daily_net_profit()
        if retail_manager.is_open:
            report_msg.total_amount -= retail_manager.get_total_employee_wages()
        items_sold_line_item = report_msg.line_items.add()
        items_sold_line_item.name = business_tuning.summary_dialog_transactions_header
        items_sold_line_item.item_type = business_tuning.summary_dialog_transactions_text(retail_manager.daily_items_sold)
        items_sold_line_item.value = retail_manager.daily_revenue
        for sim_info in sorted(retail_manager.get_employees_on_payroll(), key=operator.attrgetter('last_name')):
            current_career_level = retail_manager.get_employee_career_level(sim_info)
            with ProtocolBufferRollback(report_msg.line_items) as line_item_msg:
                payroll_entries = []
                for (career_level, hours_worked) in sorted(retail_manager.get_employee_wages_breakdown_gen(sim_info), key=lambda wage: -wage[0].simoleons_per_hour):
                    if hours_worked or career_level is not current_career_level:
                        pass
                    else:
                        payroll_entries.append(business_tuning.summary_dialog_payroll_text(career_level.title(sim_info), career_level.simoleons_per_hour, hours_worked))
                if not payroll_entries:
                    raise ProtocolBufferRollbackExpected
                line_item_msg.name = business_tuning.summary_dialog_payroll_header(sim_info)
                line_item_msg.item_type = LocalizationHelperTuning.get_new_line_separated_strings(*payroll_entries)
                line_item_msg.value = -retail_manager.get_employee_wages(sim_info)
        wages_owed_line_item = report_msg.line_items.add()
        wages_owed_line_item.name = business_tuning.summary_dialog_wages_owed_header
        wages_owed_line_item.item_type = business_tuning.summary_dialog_wages_owed_text(retail_manager.get_total_employee_wages())
        wages_owed_line_item.value = -retail_manager.get_total_employee_wages()
        for (entry_name, entry_value) in retail_manager.get_funds_category_entries_gen():
            with ProtocolBufferRollback(report_msg.line_items) as line_item_msg:
                line_item_msg.name = LocalizationHelperTuning.get_raw_text('')
                line_item_msg.item_type = entry_name
                line_item_msg.value = -entry_value
        report_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.RETAIL_SUMMARY_DIALOG, report_msg)
        Distributor.instance().add_op_with_no_owner(report_op)
