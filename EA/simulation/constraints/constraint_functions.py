from _math import Vector2import mathfrom sims4.math import TWO_PI
class ConstraintGoalGenerationFunctionBase:

    def __call__(self):
        return ()

class ConstraintGoalGenerationFunctionIdealRadius(ConstraintGoalGenerationFunctionBase):
    COUNT = 8

    def __init__(self, center, radius):
        self.center = Vector2(center.x, center.z)
        self.radius = radius

    def __call__(self):
        goals = []
        step = TWO_PI/self.COUNT
        for angle in range(self.COUNT):
            angle *= step
            x = math.cos(angle)*self.radius
            y = math.sin(angle)*self.radius
            v = Vector2(x, y)
            v += self.center
            goals.append(v)
        return tuple(goals)
