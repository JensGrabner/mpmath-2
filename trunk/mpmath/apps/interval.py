from mpmath.mptypes import *

class mpi:
    """Interval arithmetic class. Precision is controlled by mpf.prec."""

    def __init__(self, a, b=None):
        if isinstance(a, mpi):
            self.a = a.a
            self.b = a.b
            return
        if b is None:
            b = a
        mpf.round_down()
        self.a = mpf(a)
        mpf.round_up()
        self.b = mpf(b)
        mpf.round_default()
        if isnan(self.a) or isnan(self.b):
            self.a, self.b = -inf, inf
        assert self.a <= self.b, "endpoints must be properly ordered"

    @property
    def delta(self):
        mpf.round_up()
        d = self.b - self.a
        mpf.round_default()
        return d

    @property
    def mid(self):
        return (self.b + self.a) / 2

    def __repr__(self):
        mpf.dps += 5
        s = "[%s, %s]"% (str(self.a), str(self.b))
        mpf.dps -= 5
        return s

    def __contains__(self, t):
        t = mpi(t)
        return (self.a <= t.a) and (t.b <= self.b)

    def __eq__(s, t):
        t = mpi(t)
        return s.a == t.a and s.b == t.b

    def __neg__(self):
        return 0 - self

    def __add__(s, t):
        t = mpi(t)
        mpf.round_down()
        a = s.a + t.a
        mpf.round_up()
        b = s.b + t.b
        mpf.round_default()
        return mpi(a, b)

    __radd__ = __add__

    def __sub__(s, t):
        t = mpi(t)
        mpf.round_down()
        a = s.a - t.b
        mpf.round_up()
        b = s.b - t.a
        mpf.round_default()
        return mpi(a, b)

    def __rsub__(s, t):
        return mpi(t) - s

    def __mul__(s, t):
        t = mpi(t)
        mpf.round_down()
        xd, yd, zd, wd = s.a*t.a, s.a*t.b, s.b*t.a, s.b*t.b
        a = min(xd,yd,zd,wd)
        mpf.round_up()
        xu, yu, zu, wu = s.a*t.a, s.a*t.b, s.b*t.a, s.b*t.b
        b = max(xu,yu,zu,wu)
        mpf.round_default()
        if True in map(isnan, [xd,yd,zd,wd,xu,yu,zu,wu]):
            return mpi(-inf, inf)
        return mpi(a, b)

    __rmul__ = __mul__

    def __div__(s, t):
        t = mpi(t)
        if 0 in t:
            return mpi(-inf, inf)
        mpf.round_down()
        xd, yd, zd, wd = s.a/t.a, s.a/t.b, s.b/t.a, s.b/t.b
        mpf.round_up()
        xu, yu, zu, wu = s.a/t.a, s.a/t.b, s.b/t.a, s.b/t.b
        mpf.round_default()
        if True in map(isnan, [xd,yd,zd,wd,xu,yu,zu,wu]):
            return mpi(-inf, inf)
        a = min(xd,yd,zd,wd,xu,yu,zu,wu)
        b = max(xd,yd,zd,wd,xu,yu,zu,wu)
        return mpi(a, b)

    def __rdiv__(s, t):
        return mpi(t) / s

    __truediv__ = __div__
    __rtruediv__ = __rdiv__
    __floordiv__ = __div__
    __rfloordiv__ = __rdiv__

    def __pow__(s, t):
        if not isinstance(t, mpi) and 0 < s.a:
            n = int(t)
            if n == t:
                mpf.round_down()
                a = s.a ** n
                b = s.b ** n
                mpf.round_up()
                c = s.a ** n
                d = s.b ** n
                mpf.round_default()
                aa = min(a,b,c,d)
                bb = max(a,b,c,d)
                return mpi(aa, bb)
        t = mpi(t)
        if 0 < s.a <= 1 and 0 < s.b <= 1:
            return 1 / (s ** (-t))
        else:
            assert s.a >= 1 and s.b >= 1
        assert s.a >= 0 and s.b >= 0
        mpf.round_down()
        a = exp(t.a*log(s.a))
        mpf.round_up()
        b = exp(t.b*log(s.b))
        mpf.round_default()
        return mpi(a, b)

