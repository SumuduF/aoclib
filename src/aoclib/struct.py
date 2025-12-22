"""
Handy data structures.
"""

from collections import namedtuple

class Point2(namedtuple("Point2", "x, y")):
    __slots__ = ()

    def cross(p, q): return p[0]*q[1] - p[1]*q[0]
    def dot(p, q): return p[0]*q[0] + p[1]*q[1]

    def __add__(p, q): return Point2(p[0] + q[0], p[1] + q[1])
    def __sub__(p, q): return Point2(p[0] - q[0], p[1] - q[1])
    def __matmul__(p, q): return Point2.dot(p, q)
    def __mul__(p, k): return Point2(p[0] * k, p[1] * k)
    def __rmul__(p, k): return p * k
    def __truediv__(p, k): return Point2(p[0] / k, p[1] / k)
    def __floordiv__(p, k): return Point2(p[0] // k, p[1] // k)

class Point3(namedtuple("Point3", "x, y, z")):
    __slots__ = ()

    def cross(p, q):
        return Point3(p[1]*q[2] - p[2]*q[1],
                      p[2]*q[0] - p[0]*q[2],
                      p[0]*q[1] - p[1]*q[0])
    def dot(p, q): return p[0]*q[0] + p[1]*q[1] + p[2]*q[2]

    def __add__(p, q): return Point3(p[0] + q[0], p[1] + q[1], p[2] + q[2])
    def __sub__(p, q): return Point3(p[0] - q[0], p[1] - q[1], p[2] - q[2])
    def __matmul__(p, q): return Point3.dot(p, q)
    def __mul__(p, k): return Point3(p[0] * k, p[1] * k, p[2] * k)
    def __rmul__(p, k): return p * k
    def __truediv__(p, k): return Point3(p[0] / k, p[1] / k, p[2] / k)
    def __floordiv__(p, k): return Point3(p[0] // k, p[1] // k, p[2] // k)

class Fenwick():
    """Implements a Fenwick tree."""

    def __init__(self, n: int, zero = 0):
        """Creates an empty (all zeros) tree on n elements."""
        self._n = n
        self._v = [zero]*n
        self._zero = zero

    def add(self, val, i: int):
        """Adds val to position i."""
        # Note, internally the math is done with 1-based indices
        i += 1
        while i <= self._n:
            self._v[i-1] += val
            i += i & (-i)

    def cumul(self, i: int):
        """Returns the sum of values up to position i (inclusive)."""
        # Note, internally the math is done with 1-based indices
        i += 1
        ret = self._zero
        while i > 0:
            ret += self._v[i-1]
            i -= i & (-i)
        return ret
