from interactions.utils.loot_basic_op import BaseTargetedLootOperationimport sims4logger = sims4.log.Logger('PaintingTransferLoot', default_owner='rrodgers')
class TransferPaintingStateLoot(BaseTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if target is not None:
            source_canvas = subject.canvas_component
            if source_canvas is None:
                logger.error('Painting State Transfer: Subject {} has no canvas_component', subject)
                return
            target_canvas = target.canvas_component
            if target_canvas is None:
                logger.error('Painting State Transfer: target object {} has no canvas_component', target)
                return
            if target_canvas.painting_state != source_canvas.painting_state:
                target_canvas.painting_state = source_canvas.painting_state
