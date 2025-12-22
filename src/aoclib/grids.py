"""
Functions useful when working with 2D grids.
"""

from aoclib.struct import Point2

def gnumerate(grid):
    for (i, row) in enumerate(grid):
        for (j, val) in enumerate(row):
            yield (Point2(i, j), val)

# Returns function suitable for use with filter / map
def grid_getter(grid, default=None):
    def get(pos):
        if 0 <= pos.x < len(grid) and 0 <= pos.y < len(grid[pos.x]):
            return grid[pos.x][pos.y]
        return default
    return get

# CCW from E
_OFFSETS4 = list(map(Point2._make, [(0, 1), (-1, 0), (0, -1), (1, 0)]))
def neighbors4(z):
    for t in _OFFSETS4: yield z + t

# CCW from E
_OFFSETS8 = list(map(Point2._make,
    [(0, 1), (-1, 1), (-1, 0), (-1, -1),
    (0, -1), (1, -1), (1, 0), (1, 1)]))
def neighbors8(z):
    for t in _OFFSETS8: yield z + t
