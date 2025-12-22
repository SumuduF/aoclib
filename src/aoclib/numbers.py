"""
Functions related to number theory.
"""

def ext_gcd(a, b):
    """Find the gcd of a and b using the Extended Euclidean algorithm.
    Complexity ~ O(log max(a, b))

    Let g be the greatest common divisor of a and b; equivalently the smallest
    positive linear combination of a and b.

    Then, returns (g, x, y) where g = a*x + b*y. x and y are not unique by this
    definition; this function guarantees:

    |x| <= max(|b|/g, 1) and |y| <= max(|a|/g, 1)

    The special case ext_gcd(0, 0) return (0, 1, 0)."""

    if b:
        q, r = divmod(a, b)
        g, tx, ty = ext_gcd(b, r)
        return (g, ty, tx - q*ty)

    if a < 0:
        return (-a, -1, 0)
    else:
        return (a, 1, 0)

# Miller-Rabin probabilistic primality check. This works for values in 64 bits.
_MR_WITS = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
def is_prime_mr(n):
    if n <= 3: return (n > 1)
    if not (n & 1): return False

    # count trailing zero bits in n-1
    # n-1 looks like ....100000
    # n-2 looks like ....011111
    s = int.bit_count(n-2) - int.bit_count(n-1) + 1
    d = n-1 >> s

    for a in _MR_WITS:
        x = pow(a, d, n)
        if 1 < x < n-1:
            for _ in range(s):
                x = (x*x) % n
                if x == 1:
                    return False
                if x == n-1:
                    break
            else: return False
    return True

# Lazy generator of primes using wheel sieve
# This uses mod 30 (only 8 possible remainders for odd primes)
# See also https://stackoverflow.com/a/10733621 for inspiration
_WHEEL = (1, 7, 11, 13, 17, 19, 23, 29, 31)
_IWHEEL = dict((w, i) for (i, w) in enumerate(_WHEEL))
_DWHEEL = tuple(b-a for (a, b) in zip(_WHEEL, _WHEEL[1:]))

def gen_primes():
    yield from (2, 3, 5, 7)

    from itertools import count, cycle, accumulate, islice

    sieve_primes = gen_primes()
    next(islice(sieve_primes, 3, 3), None) # skip first 3
    sieve = dict()

    def wheel_from(z, mult=1):
        k = _IWHEEL[z % 30]
        mwheel = cycle([mult*d for d in _DWHEEL])
        next(islice(mwheel, k, k), None) # rotate k steps
        return accumulate(mwheel, initial=mult*z)

    def new_sp():
        sp = next(sieve_primes)
        mults = wheel_from(sp, mult=sp)
        first = next(mults) # should be sp*sp
        sieve[first] = mults
        return first

    sp2 = new_sp()
    for t in wheel_from(11):
        if t not in sieve: # t is prime
            yield t
            continue

        mults = sieve.pop(t)
        # advance to next value not already in sieve
        while (m := next(mults)) in sieve: pass
        sieve[m] = mults

        # include next prime if we hit sp2
        if t == sp2: sp2 = new_sp()
