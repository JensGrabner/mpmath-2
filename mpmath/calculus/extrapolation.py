from calculus import defun
from itertools import izip

@defun
def richardson(ctx, seq):
    r"""
    Given a list ``seq`` of the first `N` elements of a slowly convergent
    infinite sequence, :func:`richardson` computes the `N`-term
    Richardson extrapolate for the limit.

    :func:`richardson` returns `(v, c)` where `v` is the estimated
    limit and `c` is the magnitude of the largest weight used during the
    computation. The weight provides an estimate of the precision
    lost to cancellation. Due to cancellation effects, the sequence must
    be typically be computed at a much higher precision than the target
    accuracy of the extrapolation.

    **Applicability and issues**

    The `N`-step Richardson extrapolation algorithm used by
    :func:`richardson` is described in [1].

    Richardson extrapolation only works for a specific type of sequence,
    namely one converging like partial sums of
    `P(1)/Q(1) + P(2)/Q(2) + \ldots` where `P` and `Q` are polynomials.
    When the sequence does not convergence at such a rate
    :func:`richardson` generally produces garbage.

    Richardson extrapolation has the advantage of being fast: the `N`-term
    extrapolate requires only `O(N)` arithmetic operations, and usually
    produces an estimate that is accurate to `O(N)` digits. Contrast with
    the Shanks transformation (see :func:`shanks`), which requires
    `O(N^2)` operations.

    :func:`richardson` is unable to produce an estimate for the
    approximation error. One way to estimate the error is to perform
    two extrapolations with slightly different `N` and comparing the
    results.

    Richardson extrapolation does not work for oscillating sequences.
    As a simple workaround, :func:`richardson` detects if the last
    three elements do not differ monotonically, and in that case
    applies extrapolation only to the even-index elements.

    **Example**

    Applying Richardson extrapolation to the Leibniz series for `\pi`::

        >>> from mpmath import *
        >>> mp.dps = 30; mp.pretty = True
        >>> S = [4*sum(mpf(-1)**n/(2*n+1) for n in range(m))
        ...     for m in range(1,30)]
        >>> v, c = richardson(S[:10])
        >>> v
        3.2126984126984126984126984127
        >>> nprint([v-pi, c])
        [0.0711058, 2.0]

        >>> v, c = richardson(S[:30])
        >>> v
        3.14159265468624052829954206226
        >>> nprint([v-pi, c])
        [1.09645e-9, 20833.3]

    **References**

    1. C. M. Bender & S. A. Orszag, "Advanced Mathematical Methods for
       Scientists and Engineers", Springer 1999, pp. 375-376

    """
    assert len(seq) >= 3
    if ctx.sign(seq[-1]-seq[-2]) != ctx.sign(seq[-2]-seq[-3]):
        seq = seq[::2]
    N = len(seq)//2-1
    s = ctx.zero
    # The general weight is c[k] = (N+k)**N * (-1)**(k+N) / k! / (N-k)!
    # To avoid repeated factorials, we simplify the quotient
    # of successive weights to obtain a recurrence relation
    c = (-1)**N * N**N / ctx.mpf(ctx._ifac(N))
    maxc = 1
    for k in xrange(N+1):
        s += c * seq[N+k]
        maxc = max(abs(c), maxc)
        c *= (k-N)*ctx.mpf(k+N+1)**N
        c /= ((1+k)*ctx.mpf(k+N)**N)
    return s, maxc

@defun
def shanks(ctx, seq, table=None, randomized=False):
    r"""
    Given a list ``seq`` of the first `N` elements of a slowly
    convergent infinite sequence `(A_k)`, :func:`shanks` computes the iterated
    Shanks transformation `S(A), S(S(A)), \ldots, S^{N/2}(A)`. The Shanks
    transformation often provides strong convergence acceleration,
    especially if the sequence is oscillating.

    The iterated Shanks transformation is computed using the Wynn
    epsilon algorithm (see [1]). :func:`shanks` returns the full
    epsilon table generated by Wynn's algorithm, which can be read
    off as follows:

    * The table is a list of lists forming a lower triangular matrix,
      where higher row and column indices correspond to more accurate
      values.
    * The columns with even index hold dummy entries (required for the
      computation) and the columns with odd index hold the actual
      extrapolates.
    * The last element in the last row is typically the most
      accurate estimate of the limit.
    * The difference to the third last element in the last row
      provides an estimate of the approximation error.
    * The magnitude of the second last element provides an estimate
      of the numerical accuracy lost to cancellation.

    For convenience, so the extrapolation is stopped at an odd index
    so that ``shanks(seq)[-1][-1]`` always gives an estimate of the
    limit.

    Optionally, an existing table can be passed to :func:`shanks`.
    This can be used to efficiently extend a previous computation after
    new elements have been appended to the sequence. The table will
    then be updated in-place.

    **The Shanks transformation**

    The Shanks transformation is defined as follows (see [2]): given
    the input sequence `(A_0, A_1, \ldots)`, the transformed sequence is
    given by

    .. math ::

        S(A_k) = \frac{A_{k+1}A_{k-1}-A_k^2}{A_{k+1}+A_{k-1}-2 A_k}

    The Shanks transformation gives the exact limit `A_{\infty}` in a
    single step if `A_k = A + a q^k`. Note in particular that it
    extrapolates the exact sum of a geometric series in a single step.

    Applying the Shanks transformation once often improves convergence
    substantially for an arbitrary sequence, but the optimal effect is
    obtained by applying it iteratively:
    `S(S(A_k)), S(S(S(A_k))), \ldots`.

    Wynn's epsilon algorithm provides an efficient way to generate
    the table of iterated Shanks transformations. It reduces the
    computation of each element to essentially a single division, at
    the cost of requiring dummy elements in the table. See [1] for
    details.

    **Precision issues**

    Due to cancellation effects, the sequence must be typically be
    computed at a much higher precision than the target accuracy
    of the extrapolation.

    If the Shanks transformation converges to the exact limit (such
    as if the sequence is a geometric series), then a division by
    zero occurs. By default, :func:`shanks` handles this case by
    terminating the iteration and returning the table it has
    generated so far. With *randomized=True*, it will instead
    replace the zero by a pseudorandom number close to zero.
    (TODO: find a better solution to this problem.)

    **Examples**

    We illustrate by applying Shanks transformation to the Leibniz
    series for `\pi`::

        >>> from mpmath import *
        >>> mp.dps = 50
        >>> S = [4*sum(mpf(-1)**n/(2*n+1) for n in range(m))
        ...     for m in range(1,30)]
        >>>
        >>> T = shanks(S[:7])
        >>> for row in T:
        ...     nprint(row)
        ...
        [-0.75]
        [1.25, 3.16667]
        [-1.75, 3.13333, -28.75]
        [2.25, 3.14524, 82.25, 3.14234]
        [-2.75, 3.13968, -177.75, 3.14139, -969.937]
        [3.25, 3.14271, 327.25, 3.14166, 3515.06, 3.14161]

    The extrapolated accuracy is about 4 digits, and about 4 digits
    may have been lost due to cancellation::

        >>> L = T[-1]
        >>> nprint([abs(L[-1] - pi), abs(L[-1] - L[-3]), abs(L[-2])])
        [2.22532e-5, 4.78309e-5, 3515.06]

    Now we extend the computation::

        >>> T = shanks(S[:25], T)
        >>> L = T[-1]
        >>> nprint([abs(L[-1] - pi), abs(L[-1] - L[-3]), abs(L[-2])])
        [3.75527e-19, 1.48478e-19, 2.96014e+17]

    The value for pi is now accurate to 18 digits. About 18 digits may
    also have been lost to cancellation.

    Here is an example with a geometric series, where the convergence
    is immediate (the sum is exactly 1)::

        >>> mp.dps = 15
        >>> for row in shanks([0.5, 0.75, 0.875, 0.9375, 0.96875]):
        ...     nprint(row)
        [4.0]
        [8.0, 1.0]

    **References**

    1. P. R. Graves-Morris, D. E. Roberts, A. Salam, "The epsilon
       algorithm and related topics", Journal of Computational and
       Applied Mathematics, Volume 122, Issue 1-2  (October 2000)

    2. C. M. Bender & S. A. Orszag, "Advanced Mathematical Methods for
       Scientists and Engineers", Springer 1999, pp. 368-375

    """
    assert len(seq) >= 2
    if table:
        START = len(table)
    else:
        START = 0
        table = []
    STOP = len(seq) - 1
    if STOP & 1:
        STOP -= 1
    one = ctx.one
    eps = +ctx.eps
    if randomized:
        from random import Random
        rnd = Random()
        rnd.seed(START)
    for i in xrange(START, STOP):
        row = []
        for j in xrange(i+1):
            if j == 0:
                a, b = 0, seq[i+1]-seq[i]
            else:
                if j == 1:
                    a = seq[i]
                else:
                    a = table[i-1][j-2]
                b = row[j-1] - table[i-1][j-1]
            if not b:
                if randomized:
                    b = rnd.getrandbits(10)*eps
                elif i & 1:
                    return table[:-1]
                else:
                    return table
            row.append(a + one/b)
        table.append(row)
    return table

@defun
def sumem(ctx, f, interval, tol=None, reject=10, integral=None,
    adiffs=None, bdiffs=None, verbose=False, error=False):
    r"""
    Uses the Euler-Maclaurin formula to compute an approximation accurate
    to within ``tol`` (which defaults to the present epsilon) of the sum

    .. math ::

        S = \sum_{k=a}^b f(k)

    where `(a,b)` are given by ``interval`` and `a` or `b` may be
    infinite. The approximation is

    .. math ::

        S \sim \int_a^b f(x) \,dx + \frac{f(a)+f(b)}{2} +
        \sum_{k=1}^{\infty} \frac{B_{2k}}{(2k)!}
        \left(f^{(2k-1)}(b)-f^{(2k-1)}(a)\right).

    The last sum in the Euler-Maclaurin formula is not generally
    convergent (a notable exception is if `f` is a polynomial, in
    which case Euler-Maclaurin actually gives an exact result).

    The summation is stopped as soon as the quotient between two
    consecutive terms falls below *reject*. That is, by default
    (*reject* = 10), the summation is continued as long as each
    term adds at least one decimal.

    Although not convergent, convergence to a given tolerance can
    often be "forced" if `b = \infty` by summing up to `a+N` and then
    applying the Euler-Maclaurin formula to the sum over the range
    `(a+N+1, \ldots, \infty)`. This procedure is implemented by
    :func:`nsum`.

    By default numerical quadrature and differentiation is used.
    If the symbolic values of the integral and endpoint derivatives
    are known, it is more efficient to pass the value of the
    integral explicitly as ``integral`` and the derivatives
    explicitly as ``adiffs`` and ``bdiffs``. The derivatives
    should be given as iterables that yield
    `f(a), f'(a), f''(a), \ldots` (and the equivalent for `b`).

    **Examples**

    Summation of an infinite series, with automatic and symbolic
    integral and derivative values (the second should be much faster)::

        >>> from mpmath import *
        >>> mp.dps = 50; mp.pretty = True
        >>> sumem(lambda n: 1/n**2, [32, inf])
        0.03174336652030209012658168043874142714132886413417
        >>> I = mpf(1)/32
        >>> D = adiffs=((-1)**n*fac(n+1)*32**(-2-n) for n in xrange(999))
        >>> sumem(lambda n: 1/n**2, [32, inf], integral=I, adiffs=D)
        0.03174336652030209012658168043874142714132886413417

    An exact evaluation of a finite polynomial sum::

        >>> sumem(lambda n: n**5-12*n**2+3*n, [-100000, 200000])
        10500155000624963999742499550000.0
        >>> print sum(n**5-12*n**2+3*n for n in xrange(-100000, 200001))
        10500155000624963999742499550000

    """
    tol = tol or +ctx.eps
    interval = ctx._as_points(interval)
    a = ctx.convert(interval[0])
    b = ctx.convert(interval[-1])
    err = ctx.zero
    prev = 0
    M = 10000
    if a == ctx.ninf: adiffs = (0 for n in xrange(M))
    else:             adiffs = adiffs or ctx.diffs(f, a)
    if b == ctx.inf:  bdiffs = (0 for n in xrange(M))
    else:             bdiffs = bdiffs or ctx.diffs(f, b)
    orig = ctx.prec
    #verbose = 1
    try:
        ctx.prec += 10
        s = ctx.zero
        for k, (da, db) in enumerate(izip(adiffs, bdiffs)):
            if k & 1:
                term = (db-da) * ctx.bernoulli(k+1) / ctx.factorial(k+1)
                mag = abs(term)
                if verbose:
                    print "term", k, "magnitude =", ctx.nstr(mag)
                if k > 4 and mag < tol:
                    s += term
                    break
                elif k > 4 and abs(prev) / mag < reject:
                    if verbose:
                        print "Failed to converge"
                    err += mag
                    break
                else:
                    s += term
                prev = term
        # Endpoint correction
        if a != ctx.ninf: s += f(a)/2
        if b != ctx.inf: s += f(b)/2
        # Tail integral
        if verbose:
            print "Integrating f(x) from x = %s to %s" % (ctx.nstr(a), ctx.nstr(b))
        if integral:
            s += integral
        else:
            integral, ierr = ctx.quad(f, interval, error=True)
            if verbose:
                print "Integration error:", ierr
            s += integral
            err += ierr
    finally:
        ctx.prec = orig
    if error:
        return s, err
    else:
        return s

@defun
def adaptive_extrapolation(ctx, update, emfun, kwargs):
    option = kwargs.get
    tol = option('tol', ctx.eps/2**10)
    verbose = option('verbose', False)
    maxterms = option('maxterms', ctx.dps*10)
    method = option('method', 'r+s').split('+')
    skip = option('skip', 0)
    steps = iter(option('steps', xrange(10, 10**9, 10)))
    strict = option('strict')
    #steps = (10 for i in xrange(1000))
    if 'd' in method or 'direct' in method:
        TRY_RICHARDSON = TRY_SHANKS = TRY_EULER_MACLAURIN = False
    else:
        TRY_RICHARDSON = ('r' in method) or ('richardson' in method)
        TRY_SHANKS = ('s' in method) or ('shanks' in method)
        TRY_EULER_MACLAURIN = ('e' in method) or \
            ('euler-maclaurin' in method)

    last_richardson_value = 0
    shanks_table = []
    index = 0
    step = 10
    partial = []
    best = ctx.zero
    orig = ctx.prec
    try:
        if TRY_RICHARDSON or TRY_SHANKS:
            ctx.prec *= 4
        else:
            ctx.prec += 30
        while 1:
            if index >= maxterms:
                break

            # Get new batch of terms
            try:
                step = steps.next()
            except StopIteration:
                pass
            if verbose:
                print "-"*70
                print "Adding terms #%i-#%i" % (index, index+step)
            update(partial, xrange(index, index+step))
            index += step

            # Check direct error
            best = partial[-1]
            error = abs(best - partial[-2])
            if verbose:
                print "Direct error: %s" % ctx.nstr(error)
            if error <= tol:
                return best

            # Check each extrapolation method
            if TRY_RICHARDSON:
                value, maxc = ctx.richardson(partial)
                # Convergence
                richardson_error = abs(value - last_richardson_value)
                if verbose:
                    print "Richardson error: %s" % ctx.nstr(richardson_error)
                # Convergence
                if richardson_error <= tol:
                    return value
                last_richardson_value = value
                # Unreliable due to cancellation
                if ctx.eps*maxc > tol:
                    if verbose:
                        print "Ran out of precision for Richardson"
                    TRY_RICHARDSON = False
                if richardson_error < error:
                    error = richardson_error
                    best = value
            if TRY_SHANKS:
                shanks_table = ctx.shanks(partial, shanks_table, randomized=True)
                row = shanks_table[-1]
                if len(row) == 2:
                    est1 = row[-1]
                    shanks_error = 0
                else:
                    est1, maxc, est2 = row[-1], abs(row[-2]), row[-3]
                    shanks_error = abs(est1-est2)
                if verbose:
                    print "Shanks error: %s" % ctx.nstr(shanks_error)
                if shanks_error <= tol:
                    return est1
                if ctx.eps*maxc > tol:
                    if verbose:
                        print "Ran out of precision for Shanks"
                    TRY_SHANKS = False
                if shanks_error < error:
                    error = shanks_error
                    best = est1
            if TRY_EULER_MACLAURIN:
                if ctx.mpc(ctx.sign(partial[-1]) / ctx.sign(partial[-2])).ae(-1):
                    if verbose:
                        print ("NOT using Euler-Maclaurin: the series appears"
                            " to be alternating, so numerical\n quadrature"
                            " will most likely fail")
                    TRY_EULER_MACLAURIN = False
                else:
                    value, em_error = emfun(index, tol)
                    value += partial[-1]
                    if verbose:
                        print "Euler-Maclaurin error: %s" % ctx.nstr(em_error)
                    if em_error <= tol:
                        return value
                    if em_error < error:
                        best = value
    finally:
        ctx.prec = orig
    if strict:
        raise ctx.NoConvergence
    if verbose:
        print "Warning: failed to converge to target accuracy"
    return best

@defun
def nsum(ctx, f, interval, **kwargs):
    r"""
    Computes the sum

    .. math :: S = \sum_{k=a}^b f(k)

    where `(a, b)` = *interval*, and where `a = -\infty` and/or
    `b = \infty` are allowed. Two examples of
    infinite series that can be summed by :func:`nsum`, where the
    first converges rapidly and the second converges slowly, are::

        >>> from mpmath import *
        >>> mp.dps = 15; mp.pretty = True
        >>> nsum(lambda n: 1/fac(n), [0, inf])
        2.71828182845905
        >>> nsum(lambda n: 1/n**2, [1, inf])
        1.64493406684823

    When appropriate, :func:`nsum` applies convergence acceleration to
    accurately estimate the sums of slowly convergent series.
    If the sum is finite, :func:`nsum` currently does not
    attempt to perform any extrapolation, and simply calls
    :func:`fsum`.

    **Options**

    *tol*
        Desired maximum final error. Defaults roughly to the
        epsilon of the working precision.

    *method*
        Which summation algorithm to use (described below).
        Default: ``'richardson+shanks'``.

    *maxterms*
        Cancel after at most this many terms. Default: 10*dps.

    *steps*
        An iterable giving the number of terms to add between
        each extrapolation attempt. The default sequence is
        [10, 20, 30, 40, ...]. For example, if you know that
        approximately 100 terms will be required, efficiency might be
        improved by setting this to [100, 10]. Then the first
        extrapolation will be performed after 100 terms, the second
        after 110, etc.

    *verbose*
        Print details about progress.

    **Methods**

    Unfortunately, an algorithm that can efficiently sum any infinite
    series does not exist. :func:`nsum` implements several different
    algorithms that each work well in different cases. The *method*
    keyword argument selects a method.

    The default method is ``'r+s'``, i.e. both Richardson extrapolation
    and Shanks transformation is attempted. A slower method that
    handles more cases is ``'r+s+e'``. For very high precision
    summation, or if the summation needs to be fast (for example if
    multiple sums need to be evaluated), it is a good idea to
    investigate which one method works best and only use that.

    ``'richardson'`` / ``'r'``:
        Uses Richardson extrapolation. Provides useful extrapolation
        when `f(k) \sim P(k)/Q(k)` or when `f(k) \sim (-1)^k P(k)/Q(k)`
        for polynomials `P` and `Q`. See :func:`richardson` for
        additional information.

    ``'shanks'`` / ``'s'``:
        Uses Shanks transformation. Typically provides useful
        extrapolation when `f(k) \sim c^k` or when successive terms
        alternate signs. Is able to sum some divergent series.
        See :func:`shanks` for additional information.

    ``'euler-maclaurin'`` / ``'e'``:
        Uses the Euler-Maclaurin summation formula to approximate
        the remainder sum by an integral. This requires high-order
        numerical derivatives and numerical integration. The advantage
        of this algorithm is that it works regardless of the
        decay rate of `f`, as long as `f` is sufficiently smooth.
        See :func:`sumem` for additional information.

    ``'direct'`` / ``'d'``:
        Does not perform any extrapolation. This can be used
        (and should only be used for) rapidly convergent series.
        The summation automatically stops when the terms
        decrease below the target tolerance.

    **Basic examples**

    A finite sum::

        >>> nsum(lambda k: 1/k, [1, 6])
        2.45

    Summation of a series going to negative infinity and a doubly
    infinite series::

        >>> nsum(lambda k: 1/k**2, [-inf, -1])
        1.64493406684823
        >>> nsum(lambda k: 1/(1+k**2), [-inf, inf])
        3.15334809493716

    :func:`nsum` handles sums of complex numbers::

        >>> nsum(lambda k: (0.5+0.25j)**k, [0, inf])
        (1.6 + 0.8j)

    The following sum converges very rapidly, so it is most
    efficient to sum it by disabling convergence acceleration::

        >>> mp.dps = 1000
        >>> a = nsum(lambda k: -(-1)**k * k**2 / fac(2*k), [1, inf],
        ...     method='direct')
        >>> b = (cos(1)+sin(1))/4
        >>> abs(a-b) < mpf('1e-998')
        True

    **Examples with Richardson extrapolation**

    Richardson extrapolation works well for sums over rational
    functions, as well as their alternating counterparts::

        >>> mp.dps = 50
        >>> nsum(lambda k: 1 / k**3, [1, inf],
        ...     method='richardson')
        1.2020569031595942853997381615114499907649862923405
        >>> zeta(3)
        1.2020569031595942853997381615114499907649862923405

        >>> nsum(lambda n: (n + 3)/(n**3 + n**2), [1, inf],
        ...     method='richardson')
        2.9348022005446793094172454999380755676568497036204
        >>> pi**2/2-2
        2.9348022005446793094172454999380755676568497036204

        >>> nsum(lambda k: (-1)**k / k**3, [1, inf],
        ...     method='richardson')
        -0.90154267736969571404980362113358749307373971925537
        >>> -3*zeta(3)/4
        -0.90154267736969571404980362113358749307373971925538

    **Examples with Shanks transformation**

    The Shanks transformation works well for geometric series
    and typically provides excellent acceleration for Taylor
    series near the border of their disk of convergence.
    Here we apply it to a series for `\log(2)`, which can be
    seen as the Taylor series for `\log(1+x)` with `x = 1`::

        >>> nsum(lambda k: -(-1)**k/k, [1, inf],
        ...     method='shanks')
        0.69314718055994530941723212145817656807550013436025
        >>> log(2)
        0.69314718055994530941723212145817656807550013436025

    Here we apply it to a slowly convergent geometric series::

        >>> nsum(lambda k: mpf('0.995')**k, [0, inf],
        ...     method='shanks')
        200.0

    Finally, Shanks' method works very well for alternating series
    where `f(k) = (-1)^k g(k)`, and often does so regardless of
    the exact decay rate of `g(k)`::

        >>> mp.dps = 15
        >>> nsum(lambda k: (-1)**(k+1) / k**1.5, [1, inf],
        ...     method='shanks')
        0.765147024625408
        >>> (2-sqrt(2))*zeta(1.5)/2
        0.765147024625408

    The following slowly convergent alternating series has no known
    closed-form value. Evaluating the sum a second time at higher
    precision indicates that the value is probably correct::

        >>> nsum(lambda k: (-1)**k / log(k), [2, inf],
        ...     method='shanks')
        0.924299897222939
        >>> mp.dps = 30
        >>> nsum(lambda k: (-1)**k / log(k), [2, inf],
        ...     method='shanks')
        0.92429989722293885595957018136

    **Examples with Euler-Maclaurin summation**

    The sum in the following example has the wrong rate of convergence
    for either Richardson or Shanks to be effective.

        >>> f = lambda k: log(k)/k**2.5
        >>> mp.dps = 15
        >>> nsum(f, [1, inf], method='euler-maclaurin')
        0.38734195032621
        >>> -diff(zeta, 2.5)
        0.38734195032621

    Increasing ``steps`` improves speed at higher precision::

        >>> mp.dps = 50
        >>> nsum(f, [1, inf], method='euler-maclaurin', steps=[250])
        0.38734195032620997271199237593105101319948228874688
        >>> -diff(zeta, 2.5)
        0.38734195032620997271199237593105101319948228874688

    **Divergent series**

    The Shanks transformation is able to sum some *divergent*
    series. In particular, it is often able to sum Taylor series
    beyond their radius of convergence (this is due to a relation
    between the Shanks transformation and Pade approximations;
    see :func:`pade` for an alternative way to evaluate divergent
    Taylor series).

    Here we apply it to `\log(1+x)` far outside the region of
    convergence::

        >>> mp.dps = 50
        >>> nsum(lambda k: -(-9)**k/k, [1, inf],
        ...     method='shanks')
        2.3025850929940456840179914546843642076011014886288
        >>> log(10)
        2.3025850929940456840179914546843642076011014886288

    A particular type of divergent series that can be summed
    using the Shanks transformation is geometric series.
    The result is the same as using the closed-form formula
    for an infinite geometric series::

        >>> mp.dps = 15
        >>> for n in range(-8, 8):
        ...     if n == 1:
        ...         continue
        ...     print mpf(n), mpf(1)/(1-n), nsum(lambda k: n**k, [0, inf],
        ...         method='shanks')
        ...
        -8.0 0.111111111111111 0.111111111111111
        -7.0 0.125 0.125
        -6.0 0.142857142857143 0.142857142857143
        -5.0 0.166666666666667 0.166666666666667
        -4.0 0.2 0.2
        -3.0 0.25 0.25
        -2.0 0.333333333333333 0.333333333333333
        -1.0 0.5 0.5
        0.0 1.0 1.0
        2.0 -1.0 -1.0
        3.0 -0.5 -0.5
        4.0 -0.333333333333333 -0.333333333333333
        5.0 -0.25 -0.25
        6.0 -0.2 -0.2
        7.0 -0.166666666666667 -0.166666666666667

    """
    a, b = ctx._as_points(interval)
    if a == ctx.ninf:
        if b == ctx.inf:
            return f(0) + ctx.nsum(lambda k: f(-k) + f(k), [1, ctx.inf], **kwargs)
        return ctx.nsum(f, [-b, ctx.inf], **kwargs)
    elif b != ctx.inf:
        return ctx.fsum(f(ctx.mpf(k)) for k in xrange(int(a), int(b)+1))

    a = int(a)

    def update(partial_sums, indices):
        if partial_sums:
            psum = partial_sums[-1]
        else:
            psum = ctx.zero
        for k in indices:
            psum = psum + f(a + ctx.mpf(k))
            partial_sums.append(psum)

    prec = ctx.prec

    def emfun(point, tol):
        workprec = ctx.prec
        ctx.prec = prec + 10
        v = ctx.sumem(f, [a+point, ctx.inf], tol, error=1)
        ctx.prec = workprec
        return v

    return +ctx.adaptive_extrapolation(update, emfun, kwargs)

@defun
def nprod(ctx, f, interval, **kwargs):
    """
    Computes the product

    .. math :: P = \prod_{k=a}^b f(k)

    where `(a, b)` = *interval*, and where `a = -\infty` and/or
    `b = \infty` are allowed.

    This function is essentially equivalent to applying :func:`nsum`
    to the logarithm of the product (which, of course, becomes a
    series). All keyword arguments passed to :func:`nprod` are
    forwarded verbatim to :func:`nsum`.

    **Examples**

    A simple finite product::

        >>> from mpmath import *
        >>> mp.dps = 15; mp.pretty = True
        >>> nprod(lambda k: k, [1, 4])
        24.0

    A large number of infinite products have known exact values,
    and can therefore be used as a reference. Most of the following
    examples are taken from MathWorld [1].

    A few infinite products with simple values are::

        >>> 2*nprod(lambda k: (4*k**2)/(4*k**2-1), [1, inf])
        3.14159265358979
        >>> nprod(lambda k: (1+1/k)**2/(1+2/k), [1, inf])
        2.0
        >>> nprod(lambda k: (k**3-1)/(k**3+1), [2, inf])
        0.666666666666667
        >>> nprod(lambda k: (1-1/k**2), [2, inf])
        0.5

    Next, several more infinite products with more complicated
    values::

        >>> nprod(lambda k: exp(1/k**2), [1, inf])
        5.18066831789712
        >>> exp(pi**2/6)
        5.18066831789712

        >>> nprod(lambda k: (k**2-1)/(k**2+1), [2, inf])
        0.272029054982133
        >>> pi*csch(pi)
        0.272029054982133

        >>> nprod(lambda k: (k**4-1)/(k**4+1), [2, inf])
        0.8480540493529
        >>> pi*sinh(pi)/(cosh(sqrt(2)*pi)-cos(sqrt(2)*pi))
        0.8480540493529

        >>> nprod(lambda k: (1+1/k+1/k**2)**2/(1+2/k+3/k**2), [1, inf])
        1.84893618285824
        >>> 3*sqrt(2)*cosh(pi*sqrt(3)/2)**2*csch(pi*sqrt(2))/pi
        1.84893618285824

        >>> nprod(lambda k: (1-1/k**4), [2, inf])
        0.919019477593744
        >>> sinh(pi)/(4*pi)
        0.919019477593744

        >>> nprod(lambda k: (1-1/k**6), [2, inf])
        0.982684277742192
        >>> (1+cosh(pi*sqrt(3)))/(12*pi**2)
        0.982684277742192

        >>> nprod(lambda k: (1+1/k**2), [2, inf])
        1.83803895518749
        >>> sinh(pi)/(2*pi)
        1.83803895518749

        >>> nprod(lambda n: (1+1/n)**n * exp(1/(2*n)-1), [1, inf])
        1.44725592689037
        >>> exp(1+euler/2)/sqrt(2*pi)
        1.44725592689037

    The following two products are equivalent and can be evaluated in
    terms of a Jacobi theta function. Pi can be replaced by any value
    (as long as convergence is preserved)::

        >>> nprod(lambda k: (1-pi**-k)/(1+pi**-k), [1, inf])
        0.383845120748167
        >>> nprod(lambda k: tanh(k*log(pi)/2), [1, inf])
        0.383845120748167
        >>> jtheta(4,0,1/pi)
        0.383845120748167

    This product does not have a known closed form value::

        >>> nprod(lambda k: (1-1/2**k), [1, inf])
        0.288788095086602

    **References**

    1. E. W. Weisstein, "Infinite Product",
       http://mathworld.wolfram.com/InfiniteProduct.html,
       MathWorld

    """
    a, b = ctx._as_points(interval)
    if a != ctx.ninf and b != ctx.inf:
        return ctx.fprod(f(ctx.mpf(k)) for k in xrange(int(a), int(b)+1))

    orig = ctx.prec
    try:
        # TODO: we are evaluating log(1+eps) -> eps, which is
        # inaccurate. This currently works because nsum greatly
        # increases the working precision. But we should be
        # more intelligent and handle the precision here.
        ctx.prec += 10
        v = ctx.nsum(lambda n: ctx.ln(f(n)), interval, **kwargs)
    finally:
        ctx.prec = orig
    return +ctx.exp(v)

@defun
def limit(ctx, f, x, direction=1, exp=False, **kwargs):
    r"""
    Computes an estimate of the limit

    .. math ::

        \lim_{t \to x} f(t)

    where `x` may be finite or infinite.

    For finite `x`, :func:`limit` evaluates `f(x + d/n)` for
    consecutive integer values of `n`, where the approach direction
    `d` may be specified using the *direction* keyword argument.
    For infinite `x`, :func:`limit` evaluates values of
    `f(\mathrm{sign}(x) \cdot n)`.

    If the approach to the limit is not sufficiently fast to give
    an accurate estimate directly, :func:`limit` attempts to find
    the limit using Richardson extrapolation or the Shanks
    transformation. You can select between these methods using
    the *method* keyword (see documentation of :func:`nsum` for
    more information).

    **Options**

    The following options are available with essentially the
    same meaning as for :func:`nsum`: *tol*, *method*, *maxterms*,
    *steps*, *verbose*.

    If the option *exp=True* is set, `f` will be
    sampled at exponentially spaced points `n = 2^1, 2^2, 2^3, \ldots`
    instead of the linearly spaced points `n = 1, 2, 3, \ldots`.
    This can sometimes improve the rate of convergence so that
    :func:`limit` may return a more accurate answer (and faster).
    However, do note that this can only be used if `f`
    supports fast and accurate evaluation for arguments that
    are extremely close to the limit point (or if infinite,
    very large arguments).

    **Examples**

    A basic evaluation of a removable singularity::

        >>> from mpmath import *
        >>> mp.dps = 30; mp.pretty = True
        >>> limit(lambda x: (x-sin(x))/x**3, 0)
        0.166666666666666666666666666667

    Computing the exponential function using its limit definition::

        >>> limit(lambda n: (1+3/n)**n, inf)
        20.0855369231876677409285296546
        >>> exp(3)
        20.0855369231876677409285296546

    A limit for `\pi`::

        >>> f = lambda n: 2**(4*n+1)*fac(n)**4/(2*n+1)/fac(2*n)**2
        >>> limit(f, inf)
        3.14159265358979323846264338328

    Calculating the coefficient in Stirling's formula::

        >>> limit(lambda n: fac(n) / (sqrt(n)*(n/e)**n), inf)
        2.50662827463100050241576528481
        >>> sqrt(2*pi)
        2.50662827463100050241576528481

    Evaluating Euler's constant `\gamma` using the limit representation

    .. math ::

        \gamma = \lim_{n \rightarrow \infty } \left[ \left(
        \sum_{k=1}^n \frac{1}{k} \right) - \log(n) \right]

    (which converges notoriously slowly)::

        >>> f = lambda n: sum([mpf(1)/k for k in range(1,n+1)]) - log(n)
        >>> limit(f, inf)
        0.577215664901532860606512090082
        >>> +euler
        0.577215664901532860606512090082

    With default settings, the following limit converges too slowly
    to be evaluated accurately. Changing to exponential sampling
    however gives a perfect result::

        >>> f = lambda x: sqrt(x**3+x**2)/(sqrt(x**3)+x)
        >>> limit(f, inf)
        0.992518488562331431132360378669
        >>> limit(f, inf, exp=True)
        1.0

    """

    if ctx.isinf(x):
        direction = ctx.sign(x)
        g = lambda k: f(ctx.mpf(k+1)*direction)
    else:
        direction *= ctx.one
        g = lambda k: f(x + direction/(k+1))
    if exp:
        h = g
        g = lambda k: h(2**k)

    def update(values, indices):
        for k in indices:
            values.append(g(k+1))

    # XXX: steps used by nsum don't work well
    if not 'steps' in kwargs:
        kwargs['steps'] = [10]

    return +ctx.adaptive_extrapolation(update, None, kwargs)
