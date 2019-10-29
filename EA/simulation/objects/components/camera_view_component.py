import mathfrom objects.components import Component, componentmethodfrom objects.components.types import CAMERA_VIEW_COMPONENTfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunable, TunableAngleimport sims4.math
class CameraViewComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=CAMERA_VIEW_COMPONENT):
    FACTORY_TUNABLES = {'rotation': TunableAngle(description='\n            The offset in degrees from the facing vector that we will use to \n            place the camera position.\n            ', default=0.0), 'distance': Tunable(description='\n            The distance from the owners position to place the camera.\n            ', tunable_type=float, default=1.0), 'height': Tunable(description='\n            If you want to increase the height of the camera for a specific\n            viewpoint.\n            ', tunable_type=float, default=0.0)}

    @componentmethod
    def get_camera_position(self):
        forward = self.owner.forward
        sin = math.sin(self.rotation)
        cos = math.cos(self.rotation)
        rotation = sims4.math.Vector3(forward.x*cos + forward.z*sin, forward.y, -forward.x*sin + forward.z*cos)
        final_pos = self.owner.position + rotation*self.distance
        final_pos.y += self.height
        return final_pos
