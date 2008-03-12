from mpmath.lib import *
from mpmath import *

try:
    r = round_half_even
    ctx = mpf
except NameError, AttributeError:
    r = round_nearest
    ctx = mp

x15 = fsqrt(from_int(3), 53, r)
y15 = fsqrt(from_int(5), 53, r)

ctx.dps = 15
mx15 = mpf(3) ** 0.5
my15 = mpf(5) ** 0.5

x50 = fsqrt(from_int(3), 170, r)
y50 = fsqrt(from_int(5), 170, r)

ctx.dps = 50
mx50 = mpf(3) ** 0.5
my50 = mpf(5) ** 0.5

def test_lib_mul_15():
    """fmul(x,y), round to nearest, 15-digit prec, 8x"""
    fmul(x15, y15, 53, r); fmul(x15, y15, 53, r)
    fmul(x15, y15, 53, r); fmul(x15, y15, 53, r)
    fmul(x15, y15, 53, r); fmul(x15, y15, 53, r)
    fmul(x15, y15, 53, r); fmul(x15, y15, 53, r)

def test_lib_mul_50():
    """fmul(x,y), round to nearest, 50-digit prec, 8x"""
    fmul(x50, y50, 170, r); fmul(x50, y50, 170, r)
    fmul(x50, y50, 170, r); fmul(x50, y50, 170, r)
    fmul(x50, y50, 170, r); fmul(x50, y50, 170, r)
    fmul(x50, y50, 170, r); fmul(x50, y50, 170, r)

def test_mpf_mul_15():
    """x * y, round to nearest, 15-digit prec, 8x"""
    ctx.dps = 15
    mx15 * my15; mx15 * my15
    mx15 * my15; mx15 * my15
    mx15 * my15; mx15 * my15
    mx15 * my15; mx15 * my15

def test_mpf_mul_50():
    """x * y, round to nearest, 50-digit prec, 8x"""
    ctx.dps = 15
    mx50 * my50; mx50 * my50
    mx50 * my50; mx50 * my50
    mx50 * my50; mx50 * my50
    mx50 * my50; mx50 * my50

def test_mpf_mul_int_15():
    """43 * x, round to nearest, 15-digit prec, 8x"""
    ctx.dps = 15
    43 * mx15; 43 * mx15
    43 * mx15; 43 * mx15
    43 * mx15; 43 * mx15
    43 * mx15; 43 * mx15

def test_mpf_mul_int_50():
    """43 * x, round to nearest, 50-digit prec, 8x"""
    ctx.dps = 50
    43 * mx50; 43 * mx50
    43 * mx50; 43 * mx50
    43 * mx50; 43 * mx50
    43 * mx50; 43 * mx50

if __name__=='__main__':
    from func_timeit import run_tests
    run_tests([test_lib_mul_15, test_lib_mul_50,
        test_mpf_mul_15, test_mpf_mul_50,
        test_mpf_mul_int_15, test_mpf_mul_int_50])
