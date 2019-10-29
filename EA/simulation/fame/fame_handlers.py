from gsi_handlers.sim_handlers import _get_sim_info_by_idfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemalifestyle_brand_schema = GsiGridSchema(label='Lifestyle Brand', sim_specific=True)lifestyle_brand_schema.add_field('brand_name', 'Brand Name')lifestyle_brand_schema.add_field('target_market', 'Target Market')lifestyle_brand_schema.add_field('product', 'Product')lifestyle_brand_schema.add_field('days_active', 'Days Active')lifestyle_brand_schema.add_field('next_payout', 'Next Payout')
@GsiHandler('lifestyle_brand_view', lifestyle_brand_schema)
def generate_lifestyle_brand_data(sim_id:int=None):
    cur_sim_info = _get_sim_info_by_id(sim_id)
    lifestyle_brand_tracker = cur_sim_info.lifestyle_brand_tracker
    if lifestyle_brand_tracker is None:
        return {}
    entry = {'brand_name': lifestyle_brand_tracker.brand_name, 'target_market': str(lifestyle_brand_tracker.target_market), 'product': str(lifestyle_brand_tracker.product_choice), 'days_active': str(lifestyle_brand_tracker.days_active), 'next_payout': str(lifestyle_brand_tracker.get_payout_amount())}
    return entry
