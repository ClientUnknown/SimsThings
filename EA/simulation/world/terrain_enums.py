from sims4 import hash_util
class TerrainTag(enum.Int):
    INVALID = 0
    SAND = hash_util.hash32('sand')
