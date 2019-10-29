import enum
class PathSplitType(enum.Int, export=False):
    PathSplitType_DontSplit = 0
    PathSplitType_Split = 1
    PathSplitType_LadderSplit = 2
