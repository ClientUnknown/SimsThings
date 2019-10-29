from sims4.utils import flexmethod
class CareerKnowledgeMixin:

    @flexmethod
    def show_knowledge_notification(cls, inst, sim_info, resolver):
        inst_or_cls = inst if inst is not None else cls
        notification = inst_or_cls.current_track_tuning.knowledge_notification(sim_info, resolver=resolver)
        notification.show_dialog(additional_tokens=inst_or_cls.get_career_text_tokens())
