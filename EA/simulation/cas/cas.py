try:
    import _cas
except:

    class _cas:
        SimInfo = None
        OutfitData = None

        @staticmethod
        def age_up_sim(*_, **__):
            pass

        @staticmethod
        def get_buffs_from_part_ids(*_, **__):
            return []

        @staticmethod
        def get_tags_from_outfit(*_, **__):
            return set()

        @staticmethod
        def generate_offspring(*_, **__):
            pass

        @staticmethod
        def generate_household(*_, **__):
            pass

        @staticmethod
        def generate_merged_outfit(*_, **__):
            pass

        @staticmethod
        def generate_random_siminfo(*_, **__):
            pass

        @staticmethod
        def generate_occult_siminfo(*_, **__):
            pass

        @staticmethod
        def is_duplicate_merged_outfit(*_, **__):
            pass

        @staticmethod
        def is_online_entitled(*_, **__):
            pass

        @staticmethod
        def apply_siminfo_override(*_, **__):
            pass

        @staticmethod
        def randomize_part_color(*_, **__):
            pass

        @staticmethod
        def randomize_skintone_from_tags(*_, **__):
            pass

        @staticmethod
        def set_caspart(*_, **__):
            pass

        @staticmethod
        def randomize_caspart(*_, **__):
            pass

        @staticmethod
        def get_caspart_bodytype(*_, **__):
            pass

        @staticmethod
        def relgraph_set_edge(*_, **__):
            pass

        @staticmethod
        def relgraph_get_genealogy(*_, **__):
            pass

        @staticmethod
        def relgraph_set_marriage(*_, **__):
            pass

        @staticmethod
        def relgraph_add_child(*_, **__):
            pass

        @staticmethod
        def relgraph_get(*_, **__):
            pass

        @staticmethod
        def relgraph_set(*_, **__):
            pass

        @staticmethod
        def relgraph_cull(*_, **__):
            pass
BaseSimInfo = _cas.SimInfoOutfitData = _cas.OutfitDataage_up_sim = _cas.age_up_simget_buff_from_part_ids = _cas.get_buffs_from_part_idsget_tags_from_outfit = _cas.get_tags_from_outfitgenerate_offspring = _cas.generate_offspringgenerate_household = _cas.generate_householdgenerate_merged_outfit = _cas.generate_merged_outfitgenerate_random_siminfo = _cas.generate_random_siminfogenerate_occult_siminfo = _cas.generate_occult_siminfois_duplicate_merged_outfit = _cas.is_duplicate_merged_outfitis_online_entitled = _cas.is_online_entitledapply_siminfo_override = _cas.apply_siminfo_overriderandomize_part_color = _cas.randomize_part_colorrandomize_skintone_from_tags = _cas.randomize_skintone_from_tagsset_caspart = _cas.set_caspartrandomize_caspart = _cas.randomize_caspartget_caspart_bodytype = _cas.get_caspart_bodytyperelgraph_set_edge = _cas.relgraph_set_edgerelgraph_get_genealogy = _cas.relgraph_get_genealogyrelgraph_set_marriage = _cas.relgraph_set_marriagerelgraph_add_child = _cas.relgraph_add_childrelgraph_get = _cas.relgraph_getrelgraph_set = _cas.relgraph_setrelgraph_cull = _cas.relgraph_cull