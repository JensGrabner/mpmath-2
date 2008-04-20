# TODO: there are too many tests in this file. they should be separated.

from mpmath.lib import *
from mpmath import *
import random
import time
import math
import cmath

#----------------------------------------------------------------------------
# Low-level tests
#

# Advanced rounding test
def test_add_rounding():
    mp.dps = 15
    mp.rounding = 'up'
    assert (mpf(1) + 1e-50) - 1 == 2.2204460492503131e-16
    assert mpf(1) - 1e-50 == 1.0
    mp.rounding = 'down'
    assert 1 - (mpf(1) - 1e-50) == 1.1102230246251565e-16
    assert mpf(1) + 1e-50 == 1.0
    mp.rounding = 'default'

def test_almost_equal():
    assert mpf(1.2).ae(mpf(1.20000001), 1e-7)
    assert not mpf(1.2).ae(mpf(1.20000001), 1e-9)
    assert not mpf(-0.7818314824680298).ae(mpf(-0.774695868667929))


#----------------------------------------------------------------------------
# Test basic arithmetic
#

# Test that integer arithmetic is exact
def test_aintegers():
    random.seed(0)
    for prec in [6, 10, 25, 40, 100, 250, 725]:
      for rounding in ['down', 'up', 'floor', 'ceiling', 'nearest']:
        mp.rounding = rounding
        mp.dps = prec
        M = 10**(prec-2)
        M2 = 10**(prec//2-2)
        for i in range(10):
            a = random.randint(-M, M)
            b = random.randint(-M, M)
            assert mpf(a) == a
            assert int(mpf(a)) == a
            assert int(mpf(str(a))) == a
            assert mpf(a) + mpf(b) == a + b
            assert mpf(a) - mpf(b) == a - b
            assert -mpf(a) == -a
            a = random.randint(-M2, M2)
            b = random.randint(-M2, M2)
            assert mpf(a) * mpf(b) == a*b
    mp.rounding = 'default'
    mp.dps = 15

def test_exact_sqrts():
    for i in range(20000):
        assert sqrt(mpf(i*i)) == i
    random.seed(1)
    for prec in [100, 300, 1000, 10000]:
        mp.dps = prec
        for i in range(20):
            A = random.randint(10**(prec//2-2), 10**(prec//2-1))
            assert sqrt(mpf(A*A)) == A
    mp.dps = 15
    for i in range(100):
        for a in [1, 8, 25, 112307]:
            assert sqrt(mpf((a*a, 2*i))) == mpf((a, i))
            assert sqrt(mpf((a*a, -2*i))) == mpf((a, -i))

def test_sqrt_rounding():
    for i in [2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]:
        for dps in [7, 15, 83, 106, 2000]:
            mp.dps = dps
            mp.rounding = 'down'
            assert (mpf(i)**0.5)**2 < i
            mp.rounding = 'up'
            assert (mpf(i)**0.5)**2 > i
    mp.dps = 15
    mp.rounding = 'default'
        
def test_odd_int_bug():
    assert to_int(from_int(3), round_nearest) == 3



#----------------------------------------------------------------------------
# Constants and functions
#

tpi = "3.1415926535897932384626433832795028841971693993751058209749445923078\
1640628620899862803482534211706798"
te = "2.71828182845904523536028747135266249775724709369995957496696762772407\
663035354759457138217852516642743"
tdegree = "0.017453292519943295769236907684886127134428718885417254560971914\
4017100911460344944368224156963450948221"
teuler = "0.5772156649015328606065120900824024310421593359399235988057672348\
84867726777664670936947063291746749516"
tln2 = "0.693147180559945309417232121458176568075500134360255254120680009493\
393621969694715605863326996418687542"
tln10 = "2.30258509299404568401799145468436420760110148862877297603332790096\
757260967735248023599720508959829834"
tcatalan = "0.91596559417721901505460351493238411077414937428167213426649811\
9621763019776254769479356512926115106249"
tkhinchin = "2.6854520010653064453097148354817956938203822939944629530511523\
4555721885953715200280114117493184769800"
tglaisher = "1.2824271291006226368753425688697917277676889273250011920637400\
2174040630885882646112973649195820237439420646"
tapery = "1.2020569031595942853997381615114499907649862923404988817922715553\
4183820578631309018645587360933525815"
tphi = "1.618033988749894848204586834365638117720309179805762862135448622705\
26046281890244970720720418939113748475"

def test_constants():
    for prec in [3, 7, 10, 15, 20, 37, 80, 100, 29]:
        mp.dps = prec
        assert pi == mpf(tpi)
        assert e == mpf(te)
        assert degree == mpf(tdegree)
        assert euler == mpf(teuler)
        assert ln2 == mpf(tln2)
        assert ln10 == mpf(tln10)
        assert catalan == mpf(tcatalan)
        assert khinchin == mpf(tkhinchin)
        assert glaisher == mpf(tglaisher)
        assert phi == mpf(tphi)
    mp.dps = 15

def test_str_1000_digits():
    mp.dps = 1001
    # last digit may be wrong
    assert str(mpf(2)**0.5)[-10:-1] == '9518488472'[:9]
    assert str(pi)[-10:-1] == '2164201989'[:9]
    mp.dps = 15

def test_str_10000_digits():
    mp.dps = 10001
    # last digit may be wrong
    assert str(mpf(2)**0.5)[-10:-1] == '5873258351'[:9]
    assert str(pi)[-10:-1] == '5256375678'[:9]
    mp.dps = 15

def test_float_sqrt():
    mp.dps = 15
    # These should round identically
    for x in [0, 1e-7, 0.1, 0.5, 1, 2, 3, 4, 5, 0.333, 76.19]:
        assert sqrt(mpf(x)) == float(x)**0.5
    assert sqrt(-1) == 1j
    assert sqrt(-2).ae(cmath.sqrt(-2))
    assert sqrt(-3).ae(cmath.sqrt(-3))
    assert sqrt(-100).ae(cmath.sqrt(-100))
    assert sqrt(1j).ae(cmath.sqrt(1j))
    assert sqrt(-1j).ae(cmath.sqrt(-1j))
    assert sqrt(math.pi + math.e*1j).ae(cmath.sqrt(math.pi + math.e*1j))
    assert sqrt(math.pi - math.e*1j).ae(cmath.sqrt(math.pi - math.e*1j))

def test_hypot():
    assert hypot(0, 0) == 0
    assert hypot(0, 0.33) == mpf(0.33)
    assert hypot(0.33, 0) == mpf(0.33)
    assert hypot(-0.33, 0) == mpf(0.33)
    assert hypot(3, 4) == mpf(5)

def test_exp():
    assert exp(0) == 1
    assert exp(10000).ae(mpf('8.8068182256629215873e4342'))
    assert exp(-10000).ae(mpf('1.1354838653147360985e-4343'))
    a = exp(mpf((1, 8198646019315405L, -53, 53)))
    assert(a.bc == bitcount(a.man))
    mp.prec = 67
    a = exp(mpf((1, 1781864658064754565L, -60, 61)))
    assert(a.bc == bitcount(a.man))
    mp.prec = 53
    assert exp(ln2 * 10).ae(1024)
    assert exp(2+2j).ae(cmath.exp(2+2j))

def test_issue_33():
    mp.dps = 512
    a = exp(-1)
    b = exp(1)
    mp.dps = 15
    assert (+a).ae(0.36787944117144233)
    assert (+b).ae(2.7182818284590451)

def test_log():
    assert log(1) == 0
    for x in [0.5, 1.5, 2.0, 3.0, 100, 10**50, 1e-50]:
        assert log(x).ae(math.log(x))
        assert log(x, x) == 1
    assert log(1024, 2) == 10
    assert log(10**1234, 10) == 1234
    assert log(2+2j).ae(cmath.log(2+2j))

def test_trig_hyperb_basic():
    for x in (range(100) + range(-100,0)):
        t = x / 4.1
        assert cos(mpf(t)).ae(math.cos(t))
        assert sin(mpf(t)).ae(math.sin(t))
        assert tan(mpf(t)).ae(math.tan(t))
        assert cosh(mpf(t)).ae(math.cosh(t))
        assert sinh(mpf(t)).ae(math.sinh(t))
        assert tanh(mpf(t)).ae(math.tanh(t))
    assert sin(1+1j).ae(cmath.sin(1+1j))
    assert sin(-4-3.6j).ae(cmath.sin(-4-3.6j))
    assert cos(1+1j).ae(cmath.cos(1+1j))
    assert cos(-4-3.6j).ae(cmath.cos(-4-3.6j))

def test_degrees():
    assert cos(0*degree) == 1
    assert cos(90*degree).ae(0)
    assert cos(180*degree).ae(-1)
    assert cos(270*degree).ae(0)
    assert cos(360*degree).ae(1)
    assert sin(0*degree) == 0
    assert sin(90*degree).ae(1)
    assert sin(180*degree).ae(0)
    assert sin(270*degree).ae(-1)
    assert sin(360*degree).ae(0)

def random_complexes(N):
    random.seed(1)
    a = []
    for i in range(N):
        x1 = random.uniform(-10, 10)
        y1 = random.uniform(-10, 10)
        x2 = random.uniform(-10, 10)
        y2 = random.uniform(-10, 10)
        z1 = complex(x1, y1)
        z2 = complex(x2, y2)
        a.append((z1, z2))
    return a

def test_complex_powers():
    for dps in [15, 30, 100]:
        # Check accuracy for complex square root
        mp.dps = dps
        a = mpc(1j)**0.5
        assert a.real == a.imag == mpf(2)**0.5 / 2
    mp.dps = 15
    random.seed(1)
    for (z1, z2) in random_complexes(100):
        assert (mpc(z1)**mpc(z2)).ae(z1**z2, 1e-12)
    assert (e**(-pi*1j)).ae(-1)
    mp.dps = 50
    assert (e**(-pi*1j)).ae(-1)
    mp.dps = 15

def test_complex_sqrt_accuracy():
    def test_mpc_sqrt(lst):
      for a, b in lst:
        z = mpc(a + j*b)
        assert abs(sqrt(z*z) - z) <  10**-dps
        z = mpc(-a + j*b)
        assert abs(sqrt(z*z) + z) <  10**-dps
        z = mpc(a - j*b)
        assert abs(sqrt(z*z) - z) <  10**-dps
        z = mpc(-a - j*b)
        assert abs(sqrt(z*z) + z) <  10**-dps
    random.seed(2)
    N = 10
    mp.dps = 30
    dps = mp.dps
    test_mpc_sqrt([(random.uniform(0, 10),random.uniform(0, 10)) for i in range(N)])
    test_mpc_sqrt([(i + 0.1, (i + 0.2)*10**i) for i in range(N)])
    mp.dps = 15

def test_atan():
    assert atan(-2.3).ae(math.atan(-2.3))
    assert atan2(1,1).ae(math.atan2(1,1))
    assert atan2(1,-1).ae(math.atan2(1,-1))
    assert atan2(-1,-1).ae(math.atan2(-1,-1))
    assert atan2(-1,1).ae(math.atan2(-1,1))
    assert atan2(-1,0).ae(math.atan2(-1,0))
    assert atan2(1,0).ae(math.atan2(1,0))
    assert atan2(0,0) == 0
    assert atan(1e-50) == 1e-50
    assert atan(1e50).ae(pi/2)
    assert atan(-1e-50) == -1e-50
    assert atan(-1e50).ae(-pi/2)
    for dps in [25, 70, 100, 300, 1000]:
        mp.dps = dps
        assert (4*atan(1)).ae(pi)
    mp.dps = 15

def test_areal_inverses():
    assert asin(mpf(0)) == 0
    assert asinh(mpf(0)) == 0
    assert acosh(mpf(1)) == 0
    assert isinstance(asin(mpf(0.5)), mpf)
    assert isinstance(asin(mpf(2.0)), mpc)
    assert isinstance(acos(mpf(0.5)), mpf)
    assert isinstance(acos(mpf(2.0)), mpc)
    assert isinstance(atanh(mpf(0.1)), mpf)
    assert isinstance(atanh(mpf(1.1)), mpc)

    random.seed(1)
    for i in range(50):
        x = random.uniform(0, 1)
        assert asin(mpf(x)).ae(math.asin(x))
        assert acos(mpf(x)).ae(math.acos(x))

        x = random.uniform(-10, 10)
        assert asinh(mpf(x)).ae(cmath.asinh(x).real)
        assert isinstance(asinh(mpf(x)), mpf)
        x = random.uniform(1, 10)
        assert acosh(mpf(x)).ae(cmath.acosh(x).real)
        assert isinstance(acosh(mpf(x)), mpf)
        x = random.uniform(-10, 0.999)
        assert isinstance(acosh(mpf(x)), mpc)

        x = random.uniform(-1, 1)
        assert atanh(mpf(x)).ae(cmath.atanh(x).real)
        assert isinstance(atanh(mpf(x)), mpf)

def test_complex_functions():
    for x in (range(10) + range(-10,0)):
        for y in (range(10) + range(-10,0)):
            z = complex(x, y)/4.3 + 0.01j
            assert exp(mpc(z)).ae(cmath.exp(z))
            assert log(mpc(z)).ae(cmath.log(z))
            assert cos(mpc(z)).ae(cmath.cos(z))
            assert sin(mpc(z)).ae(cmath.sin(z))
            assert tan(mpc(z)).ae(cmath.tan(z))
            assert sinh(mpc(z)).ae(cmath.sinh(z))
            assert cosh(mpc(z)).ae(cmath.cosh(z))
            assert tanh(mpc(z)).ae(cmath.tanh(z))

def test_complex_inverse_functions():
    for (z1, z2) in random_complexes(30):
        # apparently cmath uses a different branch, so we
        # can't use it for comparison
        assert sinh(asinh(z1)).ae(z1)
        #
        assert acosh(z1).ae(cmath.acosh(z1))
        assert atanh(z1).ae(cmath.atanh(z1))
        assert atan(z1).ae(cmath.atan(z1))
        # the reason we set a big eps here is that the cmath
        # functions are inaccurate
        assert asin(z1).ae(cmath.asin(z1), rel_eps=1e-12)
        assert acos(z1).ae(cmath.acos(z1), rel_eps=1e-12)
        one = mpf(1)
    for i in range(-9, 10, 3):
        for k in range(-9, 10, 3):
            a = 0.9*j*10**k + 0.8*one*10**i
            b = cos(acos(a))
            assert b.ae(a)
            b = sin(asin(a))
            assert b.ae(a)
    one = mpf(1)
    err = 2*10**-15
    for i in range(-9, 9, 3):
        for k in range(-9, 9, 3):
            a = -0.9*10**k + j*0.8*one*10**i
            b = cosh(acosh(a))
            assert b.ae(a, err)
            b = sinh(asinh(a))
            assert b.ae(a, err)

def test_reciprocal_functions():
    assert sec(3).ae(-1.01010866590799375)
    assert csc(3).ae(7.08616739573718592)
    assert cot(3).ae(-7.01525255143453347)
    assert sech(3).ae(0.0993279274194332078)
    assert csch(3).ae(0.0998215696688227329)
    assert coth(3).ae(1.00496982331368917)
    assert asec(3).ae(1.23095941734077468)
    assert acsc(3).ae(0.339836909454121937)
    assert acot(3).ae(0.321750554396642193)
    assert asech(0.5).ae(1.31695789692481671)
    assert acsch(3).ae(0.327450150237258443)
    assert acoth(3).ae(0.346573590279972655)

def test_ldexp():
    mp.dps = 15
    assert ldexp(mpf(2.5), 0) == 2.5
    assert ldexp(mpf(2.5), -1) == 1.25
    assert ldexp(mpf(2.5), 2) == 10
    assert ldexp(mpf('inf'), 3) == mpf('inf')

def test_misc_bugs():
    # test that this doesn't raise an exception
    mp.dps = 1000
    log(1302)
    mp.dps = 15
