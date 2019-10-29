from distributor.ops import Opfrom distributor.system import Distributorfrom interactions.liability import Liabilityfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom protocolbuffers import UI_pb2, DistributorOps_pb2import sims4.loglogger = sims4.log.Logger('ObjectRelationshipSocialTrigger', default_owner='jdimailig')
class ObjectRelationshipSocialTrigger(XevtTriggeredElement):
    FACTORY_TUNABLES = {'description': '\n            This will cause a pseudo-social interaction to trigger, use this to tag object interactions \n            where you would like the Relationship Inspector to appear.\n\n            Add this to the beginning of the interaction as a basic extra.\n\n            Example of use of this is the talking toilet object.\n            '}

    def _do_behavior(self, *args, **kwargs):
        if self.interaction.target is None:
            logger.error('ObjectRelationshipSocialTrigger: Trying to perform op on non-existent target. {}', self.interaction)
            return
        if self.interaction.target.objectrelationship_component is None:
            logger.error('ObjectRelationshipSocialTrigger: Trying to perform op on target without object relationship component. {}', self.interaction)
            return
        if not self.interaction.get_liability(ObjectRelationshipSocialLiability.LIABILITY_TOKEN):
            self.interaction.add_liability(ObjectRelationshipSocialLiability.LIABILITY_TOKEN, ObjectRelationshipSocialLiability())

class ObjectRelationshipSocialLiability(Liability):
    LIABILITY_TOKEN = 'ObjectRelationshipSocialLiability'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._isActive = False

    def _trigger_social_start(self, sim):
        if self._objectrelationship_component and not self._isActive:
            self._isActive = True
            self._objectrelationship_component.on_social_start(sim)

    def _trigger_social_end(self):
        if self._objectrelationship_component and self._isActive:
            self._isActive = False
            self._objectrelationship_component.on_social_end()

    def on_add(self, interaction):
        self._target = interaction.target
        if self._target:
            self._objectrelationship_component = interaction.target.objectrelationship_component
            self._trigger_social_start(interaction.sim)

    def release(self):
        if self._target:
            self._trigger_social_end()

class ObjectRelationshipSocialMixin:

    def __init__(self, source_sim, object_id, relationship):
        self._source_sim = source_sim
        self._object_id = object_id
        self._relationship = relationship

    def send_social_start_message(self):
        Distributor.instance().add_op(self._source_sim, ObjectRelationshipSocialUpdate(UI_pb2.ObjectRelationshipUpdate.TYPE_START, self._object_id, self._relationship.get_value()))

    def send_social_update_message(self):
        Distributor.instance().add_op(self._source_sim, ObjectRelationshipSocialUpdate(UI_pb2.ObjectRelationshipUpdate.TYPE_UPDATE, self._object_id, self._relationship.get_value()))

    def send_social_end_message(self):
        Distributor.instance().add_op(self._source_sim, ObjectRelationshipSocialUpdate(UI_pb2.ObjectRelationshipUpdate.TYPE_STOP, self._object_id, self._relationship.get_value()))

class ObjectRelationshipSocialUpdate(Op):

    def __init__(self, msg_type, target_id, value=None):
        super().__init__()
        self.op = UI_pb2.ObjectRelationshipUpdate()
        self.op.type = msg_type
        self.op.target_id = target_id
        self.op.value = value

    def write(self, msg):
        self.serialize_op(msg, self.op, DistributorOps_pb2.Operation.OBJECT_RELATIONSHIP_UPDATE)
