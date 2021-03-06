#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from functools import reduce
from lib.keys_wrapper import PrivateKey

logger = logging.getLogger("global_logger")


def chinese_remainder(n, a):
    sum = 0
    prod = reduce(lambda a, b: a * b, n)

    for n_i, a_i in zip(n, a):
        p = prod // n_i
        sum += a_i * mul_inv(p, n_i) * p
    return sum % prod


def mul_inv(a, b):
    b0 = b
    x0, x1 = 0, 1
    if b == 1:
        return 1
    while a > 1:
        q = a // b
        a, b = b, a % b
        x0, x1 = x1 - q * x0, x0
    if x1 < 0:
        x1 += b0
    return x1


def find_invpow(x, n):
    high = 1
    while high ** n < x:
        high *= 2
    low = high // 2
    while low < high:
        mid = (low + high) // 2
        if low < mid and mid ** n < x:
            low = mid
        elif high > mid and mid ** n > x:
            high = mid
        else:
            return mid
    return mid + 1


def attack(attack_rsa_obj, publickeys, cipher=[]):
    """Hastad attack for low public exponent
       this has found success for e = 3, and e = 5 previously
    """
    if not isinstance(publickeys, list):
        return (None, None)

    c = []
    for _ in cipher:
        c.append(int.from_bytes(_, byteorder="big"))

    n = []
    e = []
    for publickey in publickeys:
        if publickey.e < 11:
            n.append(publickey.n)
            e.append(publickey.e)

    e = set(e)
    if len(e) != 1:
        return (None, None)
    e = e.pop()

    result = chinese_remainder(n, c)
    unciphered = hex(find_invpow(result, e))[2:]
    unciphered = bytes.fromhex(unciphered)
    return (None, unciphered)
