from mptypes import (mp, mpf, mpmathify, inf,
   eps, nstr, make_mpf, AS_POINTS)

from functions import pi, exp, log, ldexp

from libmpf import mpf_neg

import math

def NEG(x):
    return make_mpf(mpf_neg(x._mpf_))

def transform(f, a, b):
    """
    Given an integrand f defined over the interval [a, b], return an
    equivalent integrand g defined on the standard interval [-1, 1].

    If a and b are finite, this is achived by means of a linear change
    of variables. If at least one point is infinite, the substitution
    t = 1/x is used.
    """
    a = mpmathify(a)
    b = mpmathify(b)
    if (a, b) == (-1, 1):
        return f
    one = mpf(1)
    half = mpf(0.5)
    # The transformation 1/x sends [1, inf] to [0, 1], which in turn
    # can be transformed to [-1, 1] the usual way. For a double
    # infinite interval, we simply evaluate the function symmetrically
    if (a, b) == (-inf, inf):
        # return transform(lambda x: (f(-1/x+1)+f(1/x-1))/x**2, 0, 1)
        def y(x):
            u = 2/(x+one)
            w = one - u
            return half * (f(w)+f(-w)) * u**2
        return y
    if a == -inf:
        # return transform(lambda x: f(-1/x+b+1)/x**2, 0, 1)
        b1 = b+1
        def y(x):
            u = 2/(x+one)
            return half * f(b1-u) * u**2
        return y
    if b == inf:
        # return transform(lambda x: f(1/x+a-1)/x**2, 0, 1)
        a1 = a-1
        def y(x):
            u = 2/(x+one)
            return half * f(a1+u) * u**2
        return y
    # Simple linear change of variables
    C = (b-a)/2
    D = (b+a)/2
    def g(x):
        return C * f(D + C*x)
    return g


class Quadrature(object):
    """
    Quadrature rules are implemented using this class, in order to
    simplify the code and provide a common infrastructure
    for tasks such as error estimation and node caching.
    You can implement a custom quadrature rule by subclassing
    :class:`Quadrature` and implementing the appropriate
    methods. The subclass can then be used by :func:`quad` by
    passing it as the *method* argument.

    :class:`Quadrature` instances are supposed to be singletons.
    :class:`Quadrature` therefore implements instance caching
    in :func:`__new__`.
    """

    def __new__(cls):
        if hasattr(cls, "_instance"):
            return cls._instance
        q = object.__new__(cls)
        q.cached_nodes = {}
        cls._instance = q
        return q

    def get_nodes(self, prec, degree, verbose=False):
        """
        Return nodes for given precision and degree. The nodes
        are retrieved from a cache if already computed; otherwise
        they are computed by calling :func:`calc_nodes` and
        are then cached.
        
        Subclasses should probably not implement this method,
        and instead implement :func:`calc_nodes` for the actual
        node computation.
        """
        if (prec, degree) in self.cached_nodes:
            return self.cached_nodes[prec, degree]
        orig = mp.prec
        try:
            nodes = self.calc_nodes(prec, degree, verbose)
        finally:
            mp.prec = orig
        self.cached_nodes[prec, degree] = nodes
        return nodes

    def calc_nodes(self, prec, degree, verbose=False):
        """
        Compute nodes. Subclasses should implement this method,
        but use the existing :func:`get_nodes` method to
        retrieve the nodes.
        """
        raise NotImplementedError

    def guess_degree(self, prec):
        """
        Given a desired precision `p` in bits, estimate the degree `m`
        of the quadrature required to accomplish full accuracy for
        typical integrals. By default, :func:`quad` will perform up
        to `m` iterations. The value of `m` should be a slight
        overestimate, so that "slightly bad" integrals can be dealt
        with automatically using a few extra iterations. On the
        other hand, it should not be too big, so :func:`quad` can
        quit within a reasonable amount of time when it is given
        an "unsolvable" integral.

        The default formula used by :func:`guess_degree` is tuned
        for both :class:`TanhSinh` and :class:`GaussLegendre`.
        The output is roughly as follows:

            +---------+---------+
            | `p`     | `m`     |
            +=========+=========+
            | 50      | 6       |
            +---------+---------+
            | 100     | 7       |
            +---------+---------+
            | 500     | 10      |
            +---------+---------+
            | 3000    | 12      |
            +---------+---------+

        This formula is based purely on a limited amount of
        experimentation and will sometimes be wrong.
        """
        # Expected degree
        g = int(4 + max(0, log(prec/30.0, 2)))
        # Reasonable "worst case"
        g += 2
        return g

    def estimate_error(self, results, prec, epsilon):
        r"""
        Given results from integrations `[I_1, I_2, \ldots, I_k]` done
        with a quadrature of rule of degree `1, 2, \ldots, k`, estimate
        the error of `I_k`.

        For `k = 2`, we estimate  `|I_{\infty}-I_2|` as `|I_2-I_1|`.

        For `k > 2`, we extrapolate `|I_{\infty}-I_k| \approx |I_{k+1}-I_k|`
        from `|I_k-I_{k-1}|` and `|I_k-I_{k-2}|` under the assumption
        that each degree increment roughly doubles the accuracy of
        the quadrature rule (this is true for both :class:`TanhSinh`
        and :class:`GaussLegendre`). The extrapolation formula is given
        by Borwein, Bailey & Girgensohn. Although not very conservative,
        this method seems to be very robust in practice.
        """
        if len(results) == 2:
            return abs(results[0]-results[1])
        try:
            if results[-1] == results[-2] == results[-3]:
                return mpf(0)
            D1 = log(abs(results[-1]-results[-2]), 10)
            D2 = log(abs(results[-1]-results[-3]), 10)
        except ValueError:
            return epsilon
        D3 = -prec
        D4 = min(0, max(D1**2/D2, 2*D1, D3))
        return mpf(10) ** int(D4)

    def summation(self, f, points, prec, epsilon, max_degree, verbose=False):
        """
        Main summation function. Computes the 1D integral over
        the interval specified by *points*. For each subinterval,
        performs quadrature of degree from 1 up to *max_degree*
        until :func:`estimate_error` signals convergence.

        :func:`summation` transforms each subintegration to
        the standard interval and then calls calls :func:`sum_next`.
        """
        I = err = mpf(0)
        for i in xrange(len(points)-1):
            a, b = points[i], points[i+1]
            if a == b:
                continue
            g = transform(f, a, b)
            results = []
            for degree in xrange(1, max_degree+1):
                if verbose:
                    print "Integrating from %s to %s (degree %s of %s)" % \
                        (nstr(a), nstr(b), degree, max_degree)
                results.append(self.sum_next(g, prec, degree, results, verbose))
                if degree > 1:
                    err = self.estimate_error(results, prec, epsilon)
                    if err <= epsilon:
                        break
                    if verbose:
                        print "Estimated error:", nstr(err)
            I += results[-1]
        if err > epsilon:
            if verbose:
                print "Failed to reach full accuracy. Estimated error:", nstr(err)
        return I, err

    def sum_next(self, f, prec, degree, results, verbose=False):
        r"""
        This method should integrate `f(x)\,dx` over the standard interval
        `[-1, 1]`. Subclasses need to implement this method, unless they
        overwrite :func:`summation` to implement a custom scheme.
        A typical implementation of :func:`sum_next` might look roughly
        like this::

            return sum(w*f(x) for (x, w) in self.get_nodes(prec, degree))

        :func:`summation` will supply the list *results* of
        values computed by :func:`sum_next` at previous degrees, in
        case the quadrature rule is able to reuse them.
        """
        raise NotImplementedError

class TanhSinh(Quadrature):
    r"""
    This class implements "tanh-sinh" or "doubly exponential"
    quadrature. This quadrature rule is based on the Euler-Maclaurin
    integral formula. By performing a change of variables involving
    nested exponentials / hyperbolic functions (hence the name), the
    derivatives at the endpoints vanish rapidly. Since the error term
    in the Euler-Maclaurin formula depends on the derivatives at the
    endpoints, a simple step sum becomes extremely accurate. In
    practice, this means that doubling the number of evaluation
    points roughly doubles the number of accurate digits.

    Comparison to Gauss-Legendre:
      * Initial computation of nodes is usually faster
      * Handles endpoint singularities better
      * Handles infinite integration intervals better
      * Is slower for smooth integrands once nodes have been computed

    The implementation of the tanh-sinh algorithm is based on the
    description given in Borwein, Bailey & Girgensohn, "Experimentation
    in Mathematics - Computational Paths to Discovery", A K Peters,
    2003, pages 312-313. In the present implementation, a few
    improvements have been made:

      * A more efficient scheme is used to compute nodes (exploiting
        recurrence for the exponential function)
      * The nodes are computed successively instead of all at once

    Various documents describing the algorithm are available online, e.g.:

      * http://crd.lbl.gov/~dhbailey/dhbpapers/dhb-tanh-sinh.pdf
      * http://users.cs.dal.ca/~jborwein/tanh-sinh.pdf
    """

    def sum_next(self, f, prec, degree, previous, verbose=False):
        """
        Step sum for tanh-sinh quadrature of degree `m`. We exploit the
        fact that half of the abscissas at degree `m` are precisely the
        abscissas from degree `m-1`. Thus reusing the result from
        the previous level allows a 2x speedup.
        """
        h = mpf(2)**(-degree)
        # Abscissas overlap, so reusing saves half of the time
        if previous:
            S = previous[-1]/(h*2)
        else:
            S = mpf(0)
        for x, w in self.get_nodes(prec, degree, verbose=False):
            S += w*(f(NEG(x)) + f(x))
        return h*S

    def calc_nodes(self, prec, degree, verbose=False):
        r"""
        The abscissas and weights for tanh-sinh quadrature of degree
        `m` are given by

        .. math::

            x_k = \tanh(\pi/2 \sinh(t_k))

            w_k = \pi/2 \cosh(t_k) / \cosh(\pi/2 \sinh(t_k))^2

        where `t_k = t_0 + hk` for a step length `h \sim 2^{-m}`. The
        list of nodes is actually infinite, but the weights die off so
        rapidly that only a few are needed.
        """
        nodes = []

        extra = 20
        mp.prec += extra
        eps = ldexp(1, -prec-10)
        pi4 = pi/4

        # For simplicity, we work in steps h = 1/2^n, with the first point
        # offset so that we can reuse the sum from the previous degree

        # We define degree 1 to include the "degree 0" steps, including
        # the point x = 0. (It doesn't work well otherwise; not sure why.)
        t0 = ldexp(1, -degree)
        if degree == 1:
            nodes.append((mpf(0), pi4))
            h = t0
        else:
            h = t0*2

        # Since h is fixed, we can compute the next exponential
        # by simply multiplying by exp(h)
        expt0 = exp(t0)
        a = pi4 * expt0
        b = pi4 / expt0
        udelta = exp(h)
        urdelta = 1/udelta

        for k in xrange(0, 20*2**degree+1):
            # Reference implementation:
            # t = t0 + k*h
            # x = tanh(pi/2 * sinh(t))
            # w = pi/2 * cosh(t) / cosh(pi/2 * sinh(t))**2

            # Fast implementation. Note that c = exp(pi/2 * sinh(t))
            c = exp(a-b)
            d = 1/c
            co = (c+d)/2
            si = (c-d)/2
            x = si / co
            w = (a+b) / co**2
            diff = abs(x-1)
            if diff <= eps:
                break

            nodes.append((x, w))
            a *= udelta
            b *= urdelta

            if verbose and k % 300 == 150:
                # Note: the number displayed is rather arbitrary. Should
                # figure out how to print something that looks more like a
                # percentage
                print "Calculating nodes:", nstr(-log(diff, 10) / prec)

        mp.prec -= extra
        return nodes


class GaussLegendre(Quadrature):
    """
    This class implements Gauss-Legendre quadrature, which is
    exceptionally efficient for polynomials and polynomial-like (i.e.
    very smooth) integrands.

    The abscissas and weights are given by roots and values of
    Legendre polynomials, which are the orthogonal polynomials
    on `[-1, 1]` with respect to the unit weight
    (see :func:`legendre`).

    In this implementation, we take the "degree" `m` of the quadrature
    to denote a Gauss-Legendre rule of degree `3 \cdot 2^m` (following
    Borwein, Bailey & Girgensohn). This way we get quadratic, rather
    than linear, convergence as the degree is incremented.

    Comparison to tanh-sinh quadrature:
      * Is faster for smooth integrands once nodes have been computed
      * Initial computation of nodes is usually slower
      * Handles endpoint singularities worse
      * Handles infinite integration intervals worse

    """

    def calc_nodes(self, prec, degree, verbose=False):
        """
        Calculates the abscissas and weights for Gauss-Legendre
        quadrature of degree of given degree (actually `3 \cdot 2^m`).
        """
        # It is important that the epsilon is set lower than the
        # "real" epsilon
        epsilon = ldexp(1, -prec-8)
        # Fairly high precision might be required for accurate
        # evaluation of the roots
        orig = mp.prec
        mp.prec = int(prec*1.5)
        nodes = []
        n = 3*2**(degree-1)
        upto = n//2 + 1
        for j in xrange(1, upto):
            # Asymptotic formula for the roots
            r = mpf(math.cos(math.pi*(j-0.25)/(n+0.5)))
            # Newton iteration
            while 1:
                t1, t2 = 1, 0
                # Evaluates the Legendre polynomial using its defining
                # recurrence relation
                for j1 in xrange(1,n+1):
                    t3, t2, t1 = t2, t1, ((2*j1-1)*r*t1 - (j1-1)*t2)/j1
                t4 = n*(r*t1- t2)/(r**2-1)
                t5 = r
                a = t1/t4
                r = r - a
                if abs(a) < epsilon:
                    break
            x = r
            w = 2/((1-r**2)*t4**2)
            if verbose  and j % 30 == 15:
                print "Computing nodes (%i of %i)" % (j, upto)
            nodes.append((x, w))
        mp.prec = orig
        return nodes

    def sum_next(self, f, prec, degree, previous, verbose=False):
        """Simple step sum. Uses symmetry of the weights."""
        s = mpf(0)
        for x, w in self.get_nodes(prec, degree, verbose):
            s += w * (f(NEG(x)) + f(x))
        return s

def quad(f, *points, **kwargs):
    r"""
    Computes a single, double or triple integral over a given
    1D interval, 2D rectangle, or 3D cuboid. A basic example::

        >>> from mpmath import *
        >>> mp.dps = 15
        >>> print quad(sin, [0, pi])
        2.0

    A basic 2D integral::

        >>> f = lambda x, y: cos(x+y/2)
        >>> print quad(f, [-pi/2, pi/2], [0, pi])
        4.0

    **Interval format**

    The integration range for each dimension may be specified
    using a list or tuple. Arguments are interpreted as follows:

    ``quad(f, [x1, x2])`` -- calculates
    `\int_{x_1}^{x_2} f(x) \, dx`

    ``quad(f, [x1, x2], [y1, y2])`` -- calculates
    `\int_{x_1}^{x_2} \int_{y_1}^{y_2} f(x,y) \, dy \, dx`

    ``quad(f, [x1, x2], [y1, y2], [z1, z2])`` -- calculates
    `\int_{x_1}^{x_2} \int_{y_1}^{y_2} \int_{z_1}^{z_2} f(x,y,z)
    \, dz \, dy \, dx`

    Endpoints may be finite or infinite. An interval descriptor
    may also contain more than two points. In this
    case, the integration is split into subintervals, between
    each pair of consecutive points. This is useful for
    dealing with mid-interval discontinuities, or integrating
    over large intervals where the function is irregular or
    oscillates.

    **Options**

    :func:`quad` recognizes the following keyword arguments:

    *method*
        Chooses integration algorithm (described below).
    *error*
        If set to true, :func:`quad` returns `(v, e)` where `v` is the
        integral and `e` is the estimated error.
    *maxdegree*
        Maximum degree of the quadrature rule to try before
        quitting.
    *verbose*
        Print details about progress.

    **Algorithms**

    Mpmath presently implements two integration algorithms: tanh-sinh
    quadrature and Gauss-Legendre quadrature. These can be selected
    using *method='tanh-sinh'* or *method='gauss-legendre'* or by
    passing the classes *method=TanhSinh*, *method=GaussLegendre*.
    The functions :func:`quadts` and :func:`quadgl` are also available
    as shortcuts.

    Both algorithms have the property that doubling the number of
    evaluation points roughly doubles the accuracy, so both are ideal
    for high precision quadrature (hundreds or thousands of digits).

    At high precision, computing the nodes and weights for the
    integration can be expensive (more expensive than computing the
    function values). To make repeated integrations fast, nodes
    are automatically cached.

    The advantages of the tanh-sinh algorithm are that it tends to
    handle endpoint singularities well, and that the nodes are cheap
    to compute on the first run. For these reasons, it is used by
    :func:`quad` as the default algorithm.

    Gauss-Legendre quadrature often requires fewer function
    evaluations, and is therefore often faster for repeated use, but
    the algorithm does not handle endpoint singularities as well and
    the nodes are more expensive to compute. Gauss-Legendre quadrature
    can be a better choice if the integrand is smooth and repeated
    integrations are required (e.g. for multiple integrals).

    See the documentation for :class:`TanhSinh` and
    :class:`GaussLegendre` for additional details.

    **Examples of 1D integrals**

    Intervals may be infinite or half-infinite. The following two
    examples evaluate the limits of the tangent function
    (`\int 1/(1+x) = \tan x`), and the Gaussian integral
    `\int_{\infty}^{\infty} \exp(-x^2)\,dx = \sqrt{\pi}`::

        >>> mp.dps = 15
        >>> print quad(lambda x: 2/(x**2+1), [0, inf])
        3.14159265358979
        >>> print quad(lambda x: exp(-x**2), [-inf, inf])**2
        3.14159265358979

    Integrals can typically be resolved to high precision.
    The following computes 50 digits of `\pi` by integrating the
    area of the half-circle defined by `x^2 + y^2 \le 1`,
    `-1 \le x \le 1`, `y \ge 0`::

        >>> mp.dps = 50
        >>> print 2*quad(lambda x: sqrt(1-x**2), [-1, 1])
        3.1415926535897932384626433832795028841971693993751

    One can just as well compute 1000 digits (output truncated)::

        >>> mp.dps = 1000
        >>> print 2*quad(lambda x: sqrt(1-x**2), [-1, 1])  #doctest:+ELLIPSIS
        3.141592653589793238462643383279502884...216420198

    Complex integrals are supported. The following computes
    a residue at `z = 0` by integrating counterclockwise along the
    diamond-shaped path from `1` to `+i` to `-1` to `-i` to `1`::

        >>> mp.dps = 15
        >>> print quad(lambda z: 1/z, [1,j,-1,-j,1])
        (0.0 + 6.28318530717959j)

    **Examples of 2D and 3D integrals**

    Here are several nice examples of analytically solvable
    2D integrals (taken from MathWorld [1]) that can be evaluated
    to high precision fairly rapidly by :func:`quad`::

        >>> mp.dps = 30
        >>> f = lambda x, y: (x-1)/((1-x*y)*log(x*y))
        >>> print quad(f, [0, 1], [0, 1])
        0.577215664901532860606512090082
        >>> print euler
        0.577215664901532860606512090082

        >>> f = lambda x, y: 1/sqrt(1+x**2+y**2)
        >>> print quad(f, [-1, 1], [-1, 1])
        3.17343648530607134219175646705
        >>> print 4*log(2+sqrt(3))-2*pi/3
        3.17343648530607134219175646705

        >>> f = lambda x, y: 1/(1-x**2 * y**2)
        >>> print quad(f, [0, 1], [0, 1])
        1.23370055013616982735431137498
        >>> print pi**2 / 8
        1.23370055013616982735431137498

        >>> print quad(lambda x, y: 1/(1-x*y), [0, 1], [0, 1])
        1.64493406684822643647241516665
        >>> print pi**2 / 6
        1.64493406684822643647241516665

    Multiple integrals may be done over infinite ranges::

        >>> mp.dps = 15
        >>> print quad(lambda x,y: exp(-x-y), [0, inf], [1, inf])
        0.367879441171442
        >>> print 1/e
        0.367879441171442

    For nonrectangular areas, one can call :func:`quad` recursively.
    For example, we can replicate the earlier example of calculating
    `\pi` by integrating over the unit-circle, and actually use double
    quadrature to actually measure the area circle::

        >>> f = lambda x: quad(lambda y: 1, [-sqrt(1-x**2), sqrt(1-x**2)])
        >>> print quad(f, [-1, 1])
        3.14159265358979

    Here is a simple triple integral::

        >>> mp.dps = 15
        >>> f = lambda x,y,z: x*y/(1+z)
        >>> print quad(f, [0,1], [0,1], [1,2], method='gauss-legendre')
        0.101366277027041
        >>> print (log(3)-log(2))/4
        0.101366277027041

    **Singularities**

    Both tanh-sinh and Gauss-Legendre quadrature are designed to
    integrate smooth (infinitely differentiable) functions. Neither
    algorithm copes well with mid-interval singularities (such as
    mid-interval discontinuities in `f(x)` or `f'(x)`).
    The best solution is to split the integral into parts::

        >>> mp.dps = 15
        >>> print quad(lambda x: abs(sin(x)), [0, 2*pi])   # Bad
        3.99900894176779
        >>> print quad(lambda x: abs(sin(x)), [0, pi, 2*pi])  # Good
        4.0

    The tanh-sinh rule often works well for integrands having a
    singularity at one or both endpoints::

        >>> mp.dps = 15
        >>> print quad(log, [0, 1], method='tanh-sinh')  # Good
        -1.0
        >>> print quad(log, [0, 1], method='gauss-legendre')  # Bad
        -0.999932197413801

    However, the result may still be inaccurate for some functions::

        >>> print quad(lambda x: 1/sqrt(x), [0, 1], method='tanh-sinh')
        1.99999999946942

    This problem is not due to the quadrature rule per se, but to
    numerical amplification of errors in the nodes. The problem can be
    circumvented by temporarily increasing the precision::

        >>> mp.dps = 30
        >>> a = quad(lambda x: 1/sqrt(x), [0, 1], method='tanh-sinh')
        >>> mp.dps = 15
        >>> print +a
        2.0

    **Highly variable functions**

    For functions that are smooth (in the sense of being infinitely
    differentiable) but contain sharp mid-interval peaks or many
    "bumps", :func:`quad` may fail to provide full accuracy. For
    example, with default settings, :func:`quad` is able to integrate
    `\sin(x)` accurately over an interval of length 100 but not over
    length 1000::

        >>> print quad(sin, [0, 100]), 1-cos(100)   # Good
        0.137681127712316 0.137681127712316
        >>> print quad(sin, [0, 1000]), 1-cos(1000)   # Bad
        -37.8587612408485 0.437620923709297

    One solution is to break the integration into 10 intervals of
    length 100::

        >>> print quad(sin, linspace(0, 1000, 10))   # Good
        0.437620923709297

    Another is to increase the degree of the quadrature::

        >>> print quad(sin, [0, 1000], maxdegree=10)   # Also good
        0.437620923709297

    Whether splitting the interval or increasing the degree is
    more efficient differs from case to case. Another example is the
    function `1/(1+x^2)`, which has a sharp peak centered around
    `x = 0`::

        >>> f = lambda x: 1/(1+x**2)
        >>> print quad(f, [-100, 100])   # Bad
        3.64804647105268
        >>> print quad(f, [-100, 100], maxdegree=10)   # Good
        3.12159332021646
        >>> print quad(f, [-100, 0, 100])   # Also good
        3.12159332021646

    **References**

    1. http://mathworld.wolfram.com/DoubleIntegral.html

    """
    rule = kwargs.get('method', TanhSinh)
    if type(rule) is str:
        rule = {'tanh-sinh':TanhSinh, 'gauss-legendre':GaussLegendre}[rule]
    rule = rule()
    verbose = kwargs.get('verbose')
    dim = len(points)
    orig = prec = mp.prec
    epsilon = eps/8
    m = kwargs.get('maxdegree') or rule.guess_degree(prec)
    points = [AS_POINTS(p) for p in points]
    try:
        mp.prec += 20
        if dim == 1:
            v, err = rule.summation(f, points[0], prec, epsilon, m, verbose)
        elif dim == 2:
            v, err = rule.summation(lambda x: \
                    rule.summation(lambda y: f(x,y), \
                    points[1], prec, epsilon, m)[0],
                points[0], prec, epsilon, m, verbose)
        elif dim == 3:
            v, err = rule.summation(lambda x: \
                    rule.summation(lambda y: \
                        rule.summation(lambda z: f(x,y,z), \
                        points[2], prec, epsilon, m)[0],
                    points[1], prec, epsilon, m)[0],
                points[0], prec, epsilon, m, verbose)
        else:
            raise NotImplementedError("quadrature must have dim 1, 2 or 3")
    finally:
        mp.prec = orig
    if kwargs.get("error"):
        return +v, err
    return +v

def quadts(*args, **kwargs):
    """
    Performs tanh-sinh quadrature. The call

        quadts(func, *points, ...)

    is simply a shortcut for:

        quad(func, *points, ..., method=TanhSinh)

    For example, a single integral and a double integral:

        quadts(lambda x: exp(cos(x)), [0, 1])
        quadts(lambda x, y: exp(cos(x+y)), [0, 1], [0, 1])

    See the documentation for quad for information about how points
    arguments and keyword arguments are parsed.

    See documentation for TanhSinh for algorithmic information about
    tanh-sinh quadrature.
    """
    kwargs['method'] = TanhSinh
    return quad(*args, **kwargs)

def quadgl(*args, **kwargs):
    """
    Performs Gauss-Legendre quadrature. The call

        quadgl(func, *points, ...)

    is simply a shortcut for:

        quad(func, *points, ..., method=TanhSinh)

    For example, a single integral and a double integral:

        quadgl(lambda x: exp(cos(x)), [0, 1])
        quadgl(lambda x, y: exp(cos(x+y)), [0, 1], [0, 1])

    See the documentation for quad for information about how points
    arguments and keyword arguments are parsed.

    See documentation for TanhSinh for algorithmic information about
    tanh-sinh quadrature.
    """
    kwargs['method'] = GaussLegendre
    return quad(*args, **kwargs)

def quadosc(f, interval, omega=None, period=None, zeros=None):
    r"""
    Calculates

    .. math ::

        I = \int_a^b f(x) dx

    where at least one of `a` and `b` is infinite and where
    `f(x) = g(x) \cos(\omega x  + \phi)` for some slowly
    decreasing function `g(x)`. With proper input, :func:`quadosc`
    can also handle oscillatory integrals where the oscillation
    rate is different from a pure sine or cosine wave.

    In the standard case when `|a| < \infty, b = \infty`,
    :func:`quadosc` works by evaluating the infinite series

    .. math ::

        I = \int_a^{x_1} f(x) dx +
        \sum_{k=1}^{\infty} \int_{x_k}^{x_{k+1}} f(x) dx

    where `x_k` are consecutive zeros (alternatively
    some other periodic reference point) of `f(x)`.
    Accordingly, :func:`quadosc` requires information about the
    zeros of `f(x)`. For a periodic function, you can specify
    the zeros by either providing the angular frequency `\omega`
    (*omega*) or the *period* `2 \pi/\omega`. In general, you can
    specify the `n`-th zero by providing the *zeros* arguments.
    Below is an example of each::

        >>> from mpmath import *
        >>> mp.dps = 15
        >>> f = lambda x: sin(3*x)/(x**2+1)
        >>> print quadosc(f, [0,inf], omega=3)
        0.37833007080198
        >>> print quadosc(f, [0,inf], period=2*pi/3)
        0.37833007080198
        >>> print quadosc(f, [0,inf], zeros=lambda n: pi*n/3)
        0.37833007080198
        >>> print (ei(3)*exp(-3)-exp(3)*ei(-3))/2  # Computed by Mathematica
        0.37833007080198

    Note that *zeros* was specified to multiply `n` by the
    *half-period*, not the full period. In theory, it does not matter
    whether each partial integral is done over a half period or a full
    period. However, if done over half-periods, the infinite series
    passed to :func:`nsum` becomes an *alternating series* and this
    typically makes the extrapolation much more efficient.

    Here is an example of an integration over the entire real line,
    and a half-infinite integration starting at `-\infty`::

        >>> print quadosc(lambda x: cos(x)/(1+x**2), [-inf, inf], omega=1)
        1.15572734979092
        >>> print pi/e
        1.15572734979092
        >>> print quadosc(lambda x: cos(x)/x**2, [-inf, -1], period=2*pi)
        -0.0844109505595739
        >>> print cos(1)+si(1)-pi/2
        -0.0844109505595738

    Of course, the integrand may contain a complex exponential just as
    well as a real sine or cosine::

        >>> print quadosc(lambda x: exp(3*j*x)/(1+x**2), [-inf,inf], omega=3)
        (0.156410688228254 + 0.0j)
        >>> print pi/e**3
        0.156410688228254
        >>> print quadosc(lambda x: exp(3*j*x)/(2+x+x**2), [-inf,inf], omega=3)
        (0.00317486988463794 - 0.0447701735209082j)
        >>> print 2*pi/sqrt(7)/exp(3*(j+sqrt(7))/2)
        (0.00317486988463794 - 0.0447701735209082j)

    **Non-periodic functions**

    If `f(x) = g(x) h(x)` for some function `h(x)` that is not
    strictly periodic, *omega* or *period* might not work, and it might
    be necessary to use *zeros*.

    A notable exception can be made for Bessel functions which, though not
    periodic, are "asymptotically periodic" in a sufficiently strong sense
    that the sum extrapolation will work out::

        >>> print quadosc(j0, [0, inf], period=2*pi)
        1.0
        >>> print quadosc(j1, [0, inf], period=2*pi)
        1.0

    More properly, one should provide the exact Bessel function zeros::

        >>> j0zero = lambda n: findroot(j0, pi*(n-0.25))
        >>> print quadosc(j0, [0, inf], zeros=j0zero)
        1.0

    For an example where *zeros* becomes necessary, consider the
    complete Fresnel integrals

    .. math ::

        \int_0^{\infty} \cos x^2\,dx = \int_0^{\infty} \sin x^2\,dx
        = \sqrt{\frac{\pi}{8}}.

    Although the integrands do not decrease in magnitude as
    `x \to \infty`, the integrals are convergent since the oscillation
    rate increases (causing consecutive periods to asymptotically
    cancel out). These integrals are virtually impossible to calculate
    to any kind of accuracy using standard quadrature rules. However,
    if one provides the correct asymptotic distribution of zeros
    (`x_n \sim \sqrt{n}`), :func:`quadosc` works::

        >>> mp.dps = 30
        >>> f = lambda x: cos(x**2)
        >>> print quadosc(f, [0,inf], zeros=lambda n:sqrt(pi*n))
        0.626657068657750125603941321203
        >>> f = lambda x: sin(x**2)
        >>> print quadosc(f, [0,inf], zeros=lambda n:sqrt(pi*n))
        0.626657068657750125603941321203
        >>> print sqrt(pi/8)
        0.626657068657750125603941321203

    (Interestingly, these integrals can still be evaluated if one
    places some other constant than `\pi` in the square root sign.)

    In general, if `f(x) \sim g(x) \cos(h(x))`, the zeros follow
    the inverse-function distribution `h^{-1}(x)`::

        >>> mp.dps = 15
        >>> f = lambda x: sin(exp(x))
        >>> print quadosc(f, [1,inf], zeros=lambda n: log(n))
        -0.25024394235267
        >>> print pi/2-si(e)
        -0.250243942352671

    **Non-alternating functions**

    If the integrand oscillates around a positive value, without
    alternating signs, the extrapolation might fail. A simple trick
    that sometimes works is to multiply or divide the frequency by 2::

        >>> f = lambda x: 1/x**2+sin(x)/x**4
        >>> print quadosc(f, [1,inf], omega=1)  # Bad
        1.28642190869921
        >>> print quadosc(f, [1,inf], omega=0.5)  # Perfect
        1.28652953559617
        >>> print 1+(cos(1)+ci(1)+sin(1))/6
        1.28652953559617

    **Fast decay**

    :func:`quadosc` is primarily useful for slowly decaying
    integrands. If the integrand decreases exponentially or faster,
    :func:`quad` will likely handle it without trouble (and generally be
    much faster than :func:`quadosc`)::

        >>> print quadosc(lambda x: cos(x)/exp(x), [0, inf], omega=1)
        0.5
        >>> print quad(lambda x: cos(x)/exp(x), [0, inf])
        0.5

    """
    a, b = AS_POINTS(interval)
    a = mpmathify(a)
    b = mpmathify(b)
    if [omega, period, zeros].count(None) != 2:
        raise ValueError( \
            "must specify exactly one of omega, period, zeros")
    if a == -inf and b == inf:
        s1 = quadosc(f, [a, 0], omega=omega, zeros=zeros, period=period)
        s2 = quadosc(f, [0, b], omega=omega, zeros=zeros, period=period)
        return s1 + s2
    if a == -inf:
        if zeros:
            return quadosc(lambda x:f(-x), [-b,-a], lambda n: zeros(-n))
        else:
            return quadosc(lambda x:f(-x), [-b,-a], omega=omega, period=period)
    if b != inf:
        raise ValueError("quadosc requires an infinite integration interval")
    if not zeros:
        if omega:
            period = 2*pi/omega
        zeros = lambda n: n*period/2
    #for n in range(1,10):
    #    p = zeros(n)
    #    if p > a:
    #        break
    #if n >= 9:
    #    raise ValueError("zeros do not appear to be correctly indexed")
    n = 1
    from calculus import nsum
    s = quadgl(f, [a, zeros(n)])
    s += nsum(lambda k: quadgl(f, [zeros(k), zeros(k+1)]), [n, inf])
    return s

if __name__ == '__main__':
    import doctest
    doctest.testmod()
