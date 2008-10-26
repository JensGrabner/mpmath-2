import mpmath
from mpmath import *
from mpmath.libmpf import *
from mpmath.libmpc import *
from mpmath.libelefun import *
import sys
import os

import platform

cpuinfo = "Celeron M 520 (1.6 GHz)"
raminfo = "1 GB"

import time
timeinfo = time.strftime("%Y-%m-%d %H:%M", time.localtime())

intro = """
<html>
<head>
<title>Mpmath benchmarks</title>
<style>
table { font-family: sans-serif; font-size:12px; }
</style>
</head>

<body>

<h1>Mpmath benchmarks</h1>

<p><a href="http://code.google.com/p/mpmath/">Main mpmath website</a></p>

<h2>Benchmark information</h2>

<p><a href="http://mpmath.googlecode.com/svn/bench/mpbench.py">Benchmark source code</a></p>

<p>Date: %s</p>

<p>mpmath version: %s</p>

System information:
<ul>
  <li>CPU: %s</li>
  <li>RAM: %s</li>
  <li>OS: %s</li>
  <li>Python version: %s</li>
  <li>Python compiler: %s</li>
</ul>

<p>
In order to give an idea of the variation, three timings from
separate runs (sorted from best to worst) are printed in each cell.
For low-level benchmarks (such as addition), the difference
between best and worst time is mainly due to different paths taken
during rounding. Rounding is done to nearest;
with rounding to floor or ceiling, both
best and worst times would be slightly better.
<i>Exceptions: constant computations are only timed once.</i>
</p>

<p>
The input arguments x and y are full precision
pseudo-random numbers (actually non-exact quotients of small integers)
close to unity (circa 0.5-2.0).
Complex numbers w and z = x+y*i are used in complex benchmarks.
Each of three runs is performed with a separate x, y (or w, z) pair.
</p>

<p>Benchmarks marked with (*) involve precomputation of
some table of numbers (e.g. series coefficients or quadrature weights).
Such tables are cached by mpmath for subsequent uses.
In these cases, the "worst time" will be the time with the
precomputation included (the first call)
and the "best time" will be roughly equal to the average time
for subsequent calls.</p>

<p>Times marked <i>mpf</i> include the overhead of typechecking
and instance creation. Times marked <i>lib</i> measure the
computational performance more directly.
The difference is primarily significant for basic arithmetic at
low precision.</p>

<p>Benchmarks marked <i>psyco</i> are run with the
<a href="http://psyco.sourceforge.net/">Psyco</a>
JIT compiler enabled. This also primarily improves speed
at low precision. Some timings with psyco may be inflated disproportionately
due to initial compilation time.</p>

<p>For times marked <i>gmpy</i>,
<a href="http://code.google.com/p/gmpy">GMPY</a> is used. This
tends to slow things down slightly at low precision, while
being much faster at high precision.</p>

<p>Each benchmark is run with a precision (dps) up to a
maximum of 10<sup>6</sup> digits. Each benchmark is stopped
as soon as the time for the next run is expected to exceed 10 seconds
(based on linear interpolation from the two previous precision levels).
Benchmarks with <i>lib</i> and <i>psyco</i> are not repeated
above 10000 digits, since the difference becomes insignificant.
</p>


""" % (timeinfo, mpmath.__version__, cpuinfo, raminfo, \
    platform.platform(), platform.python_version(), platform.python_compiler())

outro = """
</body>
</html>
"""

code_template = \
"""
import os
import sys

pairs = [(2,3,5,7,11,13,19,23), (31,37,53,73,89,59,97,67),
    (101,149,127,167,139,103,181,151)]

def timing(case):
    from timeit import default_timer as _clock
    mp.dps = %DPS%
    d = pairs[case]
    x = mpf(d[0])/d[1]
    y = mpf(d[2])/d[3]
    w = mpc(x,y)
    z = mpc(mpf(d[4])/d[5], mpf(d[6])/d[7])
    if %LIB%:
        prec=mp.prec; dps=mp.dps; rnd=round_nearest
        x = x._mpf_
        y = y._mpf_
        w = w._mpc_
        z = z._mpc_
    _t1 = _clock()
    %EXPR%
    _t2 = _clock()
    _dt = _t2-_t1
    if _dt > 0.01 or %SINGLE%:
        return _dt
    _n = _N = max(int(0.001/_dt), 1)
    t1 = _clock()
    while _n:
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        %EXPR%
        _n -= 1
    _t2 = _clock()
    _dt = (_t2-_t1)/(10*_N)
    return _dt

if %PSYCO%:
    import psyco
    psyco.full()

if not %GMPY%:
    os.environ['MPMATH_NOGMPY'] = '1'

import mpmath
from mpmath import *
from mpmath.libmpf import *
from mpmath.libmpc import *
from mpmath.libelefun import *

if %SINGLE%:
    t = [timing(0)]
else:
    t = sorted([timing(0), timing(1), timing(2)])

fp = open("time.txt", "w")
fp.write(str(t))
"""

def katime(expr, prec, config, single=False):
    fp = open("temp.py", "w")
    code = code_template
    code = code.replace("%EXPR%", str(expr))
    code = code.replace("%DPS%", str(prec))
    code = code.replace("%LIB%", str('lib' in config))
    code = code.replace("%GMPY%", str('gmpy' in config))
    code = code.replace("%PSYCO%", str('psyco' in config))
    code = code.replace("%SINGLE%", str(single))
    fp.write(code)
    fp.close()
    os.system("temp.py")
    t = eval(open("time.txt").read())
    return t

titles = []
code_info = {}
data = {}

configs = ['mpf', 'mpf+psyco', 'lib', 'lib+psyco', 'gmpy+mpf', 'gmpy+mpf+psyco', 'gmpy+lib', 'gmpy+lib+psyco']
precs = [15, 30, 100, 300, 1000, 3000, 10**4, 30000, 10**5, 300000, 10**6]

def benchmark(title, expr, libexpr=None, single=False, maxprec=None):
    print title, "..."
    if title not in titles:
        titles.append(title)
        code_info[title] = expr, libexpr
    data[title] = data.get(title, {})
    for config in configs:
        if 'lib' in config and not libexpr:
            continue
        last_time = 1e-10
        for prec in precs:
            if maxprec and prec > maxprec:
                break
            if (prec > 10000 or single) and ('lib' in config or 'psyco' in config):
                continue
            print config, prec
            if single:
                t = data[title][(prec, config)] = katime(expr, prec, config, single=True)
            else:
                if 'lib' in config:
                    t = data[title][(prec, config)] = katime(libexpr, prec, config)
                else:
                    t = data[title][(prec, config)] = katime(expr, prec, config)
            t = max(t)
            if prec > 100 and t * (t / last_time) > 10.0:
                break
            last_time = t

    fp = open("mpbench.html", "w")
    print >> fp, intro
    output(fp)
    print >> fp, outro

def per_second(t):
    rt = 1./t
    size = max(int(log(rt, 10)) - 2, 0)
    return int((rt // 10**size) * 10**size)

def print_time(time):
    if time < 0.1:
        return "%f ms (%i/s)" % (time*1000, per_second(time))
    else:
        return "%f s" % time

def print_times(times):
    if not times:
        return "-"
    return "<br/>".join(print_time(t) for t in times)

titles = []
code_info = {}
data = {}

def title(s):
    if (None, s) not in titles:
        titles.append((None, s))

def output(fp):
    for title in titles:
        if isinstance(title, tuple):
            print >> fp, "<h2>", title[1], "</h2>"
            continue
        dk = data[title]
        expr, libexpr = code_info[title]
        if libexpr:
            print >> fp, "<h3>%s (<tt>%s</tt>, <tt>%s</tt>)</h3>" % (title, expr, libexpr)
        else:
            print >> fp, "<h3>%s (<tt>%s</tt>)</h3>" % (title, expr)
        print >> fp, '<table border="1">'
        # Table heading
        print >> fp, "<tr><th>dps</th>"
        for config in configs:
            print >> fp, "<th>", config, "</th>"
        print >> fp, "</tr>"
        # Table content
        for prec in precs:
            print >> fp, "<tr>"
            print >> fp, "<td>", prec, "</td>"
            for config in configs:
                print >> fp, "<td>", print_times(dk.get((prec, config), 0)), "</td>"
            print >> fp, "</tr>"
        print >> fp, "</table>"

def constants_benchmark():
    title("Section 1: Mathematical constants")
    benchmark("Pi*", "+pi", single=True)
    benchmark("E*", "+e", single=True)
    benchmark("Golden ratio*", "+phi", single=True)
    benchmark("Log(2)*", "+ln2", single=True)
    benchmark("Log(10)*", "+ln10", single=True)
    benchmark("Apery's constant*", "+apery", single=True)
    benchmark("Catalan's constant*", "+catalan", single=True)
    benchmark("Euler's constant*", "+euler", single=True)
    benchmark("Glaisher's constant*", "+glaisher", single=True)
    benchmark("Khinchin's constant*", "+khinchin", single=True)

def arithmetic_benchmark():
    title("Section 2: Basic operations")
    benchmark("Convert to integer", "int(x)", "to_int(x)")
    benchmark("Convert to float", "float(x)", "to_float(x)")
    benchmark("Convert to string", "str(x)", "to_str(x,dps)")
    benchmark("Comparison", "x < y", "mpf_cmp(x,y)")
    benchmark("Addition", "x+y", "mpf_add(x,y,prec,rnd)")
    benchmark("Subtraction", "x-y", "mpf_sub(x,y,prec,rnd)")
    benchmark("Multiplication", "x*y", "mpf_mul(x,y,prec,rnd)")
    benchmark("Division", "x/y", "mpf_div(x,y,prec,rnd)")
    benchmark("Integer power", "x**5", "mpf_pow_int(x,5,prec,rnd)")
    benchmark("Square root", "sqrt(x)", "mpf_sqrt(x,prec,rnd)")
    benchmark("Cube root", "cbrt(x)", "mpf_cbrt(x,prec,rnd)")
    benchmark("Complex addition", "w+z", "mpc_add(w,z,prec,rnd)")
    benchmark("Complex subtraction", "w-z", "mpc_sub(w,z,prec,rnd)")
    benchmark("Complex multiplication", "w*z", "mpc_mul(w,z,prec,rnd)")
    benchmark("Complex division", "w/z", "mpc_div(w,z,prec,rnd)")
    benchmark("Complex integer power", "w**5", "mpc_pow_int(w,5,prec,rnd)")
    benchmark("Complex square root", "sqrt(w)", "mpc_sqrt(w,prec,rnd)")
    benchmark("Complex cube root", "cbrt(w)", "mpc_cbrt(w,prec,rnd)")
    benchmark("Complex absolute value", "abs(w)", "mpc_abs(w,prec,rnd)")
    benchmark("Complex argument", "arg(w)", "mpc_arg(w,prec,rnd)")

def functions_benchmark():
    title("Section 3: Functions")
    benchmark("Exponential", "exp(x)", "mpf_exp(x,prec,rnd)")
    benchmark("Logarithm", "log(x)", "mpf_log(x,prec,rnd)")
    benchmark("Sine", "sin(x)", "mpf_sin(x,prec,rnd)")
    benchmark("Inverse tangent", "atan(x)", "mpf_atan(x,prec,rnd)")
    benchmark("Inverse hyperbolic cotangent", "acoth(x)")
    benchmark("Error function", "erf(x)")
    benchmark("Lambert W function", "lambertw(x)")
    benchmark("Gamma function*", "gamma(x)")
    benchmark("Riemann zeta function*", "zeta(x)")
    benchmark("Complex exponential", "exp(w)", "mpc_exp(w,prec,rnd)")
    benchmark("Complex logarithm", "log(w)", "mpc_log(w,prec,rnd)")
    benchmark("Complex sine", "sin(w)", "mpc_sin(w,prec,rnd)")
    benchmark("Complex inverse tangent", "atan(w)", "mpc_atan(w,prec,rnd)")
    benchmark("Complex inverse hyperbolic cotangent", "acoth(w)")
    benchmark("Complex error function", "erf(w)")
    benchmark("Complex Lambert W function", "lambertw(w)")
    benchmark("Complex gamma function*", "gamma(w)")
    benchmark("Complex Riemann zeta function*", "zeta(w)")

def misc_benchmark():
    title("Section 4: Miscellaneous")
    benchmark("Numerical integration*", "quad(sqrt, [1, 2])", maxprec=1000)
    benchmark("Numerical double integration*", "quad(lambda x, y: sqrt(x+y), [1, 2], [1, 2])", maxprec=100)
    benchmark("Polynomial roots, deg=3", "polyroots([x*i for i in range(3+1)][::-1])")
    benchmark("Polynomial roots, deg=10", "polyroots([x*i for i in range(10+1)][::-1])")
    benchmark("Chebyshev approximation", "chebyfit(sqrt, [1, 2], mp.dps)", maxprec=100)

def all_benchmarks():
    constants_benchmark()
    arithmetic_benchmark()
    functions_benchmark()
    misc_benchmark()

#all_benchmarks()
misc_benchmark()
