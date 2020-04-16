#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from Crypto.PublicKey import RSA

from lib.keys_wrapper import PrivateKey

__SAGE__ = True

# This code is taken from https://github.com/mimoo/RSA-and-LLL-attacks
import time

############################################
# Config
##########################################

"""
Setting debug to true will display more informations
about the lattice, the bounds, the vectors...
"""
debug = False

"""
Setting strict to true will stop the algorithm (and
return (-1, -1)) if we don't have a correct
upperbound on the determinant. Note that this
doesn't necesseraly mean that no solutions
will be found since the theoretical upperbound is
usualy far away from actual results. That is why
you should probably use `strict = False`
"""
strict = False

"""
This is experimental, but has provided remarkable results
so far. It tries to reduce the lattice as much as it can
while keeping its efficiency. I see no reason not to use
this option, but if things don't work, you should try
disabling it
"""
helpful_only = True
dimension_min = 7  # stop removing if lattice reaches that dimension


############################################
# Functions
##########################################


def helpful_vectors(BB, modulus):
    """display stats on helpful vectors"""
    nothelpful = 0
    for ii in range(BB.dimensions()[0]):
        if BB[ii, ii] >= modulus:
            nothelpful += 1

    # print nothelpful, "/", BB.dimensions()[0], " vectors are not helpful"


def matrix_overview(BB, bound):
    """display matrix picture with 0 and X"""
    for ii in range(BB.dimensions()[0]):
        a = ('%02d ' % ii)
        for jj in range(BB.dimensions()[1]):
            a += '0' if BB[ii, jj] == 0 else 'X'
            if BB.dimensions()[0] < 60:
                a += ' '
        if BB[ii, ii] >= bound:
            a += '~'
        # print a


def remove_unhelpful(BB, monomials, bound, current):
    """tries to remove unhelpful vectors
       we start at current = n-1 (last vector)
    """
    # end of our recursive function
    if current == -1 or BB.dimensions()[0] <= dimension_min:
        return BB

    # we start by checking from the end
    for ii in range(current, -1, -1):
        # if it is unhelpful:
        if BB[ii, ii] >= bound:
            affected_vectors = 0
            affected_vector_index = 0
            # let's check if it affects other vectors
            for jj in range(ii + 1, BB.dimensions()[0]):
                # if another vector is affected:
                # we increase the count
                if BB[jj, ii] != 0:
                    affected_vectors += 1
                    affected_vector_index = jj

            # level:0
            # if no other vectors end up affected
            # we remove it
            if affected_vectors == 0:
                # print "* removing unhelpful vector", ii
                BB = BB.delete_columns([ii])
                BB = BB.delete_rows([ii])
                monomials.pop(ii)
                BB = remove_unhelpful(BB, monomials, bound, ii - 1)
                return BB

            # level:1
            # if just one was affected we check
            # if it is affecting someone else
            elif affected_vectors == 1:
                affected_deeper = True
                for kk in range(affected_vector_index + 1, BB.dimensions()[0]):
                    # if it is affecting even one vector
                    # we give up on this one
                    if BB[kk, affected_vector_index] != 0:
                        affected_deeper = False
                # remove both it if no other vector was affected and
                # this helpful vector is not helpful enough
                # compared to our unhelpful one
                if affected_deeper and abs(bound - BB[affected_vector_index, affected_vector_index]) < abs(
                        bound - BB[ii, ii]):
                    # print "* removing unhelpful vectors", ii, "and", affected_vector_index
                    BB = BB.delete_columns([affected_vector_index, ii])
                    BB = BB.delete_rows([affected_vector_index, ii])
                    monomials.pop(affected_vector_index)
                    monomials.pop(ii)
                    BB = remove_unhelpful(BB, monomials, bound, ii - 1)
                    return BB
    # nothing happened
    return BB


def boneh_durfee(pol, modulus, mm, tt, XX, YY):
    """
    Boneh and Durfee revisited by Herrmann and May

    finds a solution if:
    * d < N**delta
    * |x| < e**delta
    * |y| < e**0.5
    whenever delta < 1 - sqrt(2)/2 ~ 0.292

    Returns:
    * 0,0   if it fails
    * -1,-1 if `strict=true`, and determinant doesn't bound
    * x0,y0 the solutions of `pol`
    """
    from sage.all import ZZ, floor, Matrix, log, PolynomialRing

    # substitution (Herrman and May)
    PR = PolynomialRing(ZZ, ['u', 'x', 'y'])
    u, x, y = PR.gens()
    Q = PR.quotient(x * y + 1 - u)  # u = xy + 1
    polZ = Q(pol).lift()

    UU = XX * YY + 1

    # x-shifts
    gg = []
    for kk in range(mm + 1):
        for ii in range(mm - kk + 1):
            xshift = x ** ii * modulus ** (mm - kk) * polZ(u, x, y) ** kk
            gg.append(xshift)
    gg.sort()

    # x-shifts list of monomials
    monomials = []
    for polynomial in gg:
        for monomial in polynomial.monomials():
            if monomial not in monomials:
                monomials.append(monomial)
    monomials.sort()

    # y-shifts (selected by Herrman and May)
    for jj in range(1, tt + 1):
        for kk in range(floor(mm / tt) * jj, mm + 1):
            yshift = y ** jj * polZ(u, x, y) ** kk * modulus ** (mm - kk)
            yshift = Q(yshift).lift()
            gg.append(yshift)  # substitution

    # y-shifts list of monomials
    for jj in range(1, tt + 1):
        for kk in range(floor(mm / tt) * jj, mm + 1):
            monomials.append(u ** kk * y ** jj)

    # construct lattice B
    nn = len(monomials)
    BB = Matrix(ZZ, nn)
    for ii in range(nn):
        BB[ii, 0] = gg[ii](0, 0, 0)
        for jj in range(1, ii + 1):
            if monomials[jj] in gg[ii].monomials():
                BB[ii, jj] = gg[ii].monomial_coefficient(monomials[jj]) * monomials[jj](UU, XX, YY)

    # Prototype to reduce the lattice
    if helpful_only:
        # automatically remove
        BB = remove_unhelpful(BB, monomials, modulus ** mm, nn - 1)
        # reset dimension
        nn = BB.dimensions()[0]
        if nn == 0:
            # print "failure"
            return 0, 0

    # check if vectors are helpful
    if debug:
        helpful_vectors(BB, modulus ** mm)

    # check if determinant is correctly bounded
    det = BB.det()
    bound = modulus ** (mm * nn)
    if det >= bound:
        # print "We do not have det < bound. Solutions might not be found."
        # print "Try with highers m and t."
        if debug:
            diff = (log(det) - log(bound)) / log(2)
            print("size det(L) - size e**(m*n) = ", floor(diff))
        if strict:
            return -1, -1
    # else:
    # print "det(L) < e**(m*n) (good! If a solution exists < N**delta, it will be found)"

    # display the lattice basis
    if debug:
        matrix_overview(BB, modulus ** mm)

    # LLL
    BB = BB.LLL()

    # transform vector 1 & 2 -> polynomials 1 & 2
    w, z = PolynomialRing(ZZ, ['w', 'z']).gens()
    pol1 = pol2 = 0
    for jj in range(nn):
        pol1 += monomials[jj](w * z + 1, w, z) * BB[0, jj] / monomials[jj](UU, XX, YY)
        pol2 += monomials[jj](w * z + 1, w, z) * BB[1, jj] / monomials[jj](UU, XX, YY)

    # resultant
    q = PolynomialRing(ZZ, 'q').gen()
    rr = pol1.resultant(pol2)

    if rr.is_zero() or rr.monomials() == [1]:
        # print "the two first vectors are not independant"
        return 0, 0

    rr = rr(q, q)

    # solutions
    soly = rr.roots()

    if len(soly) == 0:
        # print "Your prediction (delta) is too small"
        return 0, 0

    soly = soly[0][0]
    ss = pol1(q, soly)
    solx = ss.roots()[0][0]

    return solx, soly


def factor(N, e):
    from sage.all import ZZ, log, floor, PolynomialRing

    ############################################
    # How To Use
    ##########################################

    # the hypothesis on the private exponent (max 0.292)
    delta = .26  # d < N**delta

    #
    # Lattice (tweak those values)
    #

    # you should tweak this (after a first run)
    m = 4  # size of the lattice (bigger the better/slower)

    # might not be a good idea to tweak these
    t = int((1 - 2 * delta) * m)  # optimization from Herrmann and May
    X = 2 * floor(N ** delta)  # this _might_ be too much
    Y = floor(N ** (1 / 2))  # correct if p, q are ~ same size

    #
    # Don't touch anything below
    #

    # Problem put in equation
    x, y = PolynomialRing(ZZ, ['x', 'y']).gens()
    A = int((N + 1) / 2)
    pol = 1 + x * (A + y)

    #
    # Find the solutions!
    #

    # Checking bounds
    if debug:
        print("=== checking values ===")
        print("* delta:", delta)
        print("* delta < 0.292", delta < 0.292)
        print("* size of e:", int(log(e) / log(2)))
        print("* size of N:", int(log(N) / log(2)))
        print("* m:", m, ", t:", t)

    # boneh_durfee
    if debug:
        print("=== running algorithm ===")
        start_time = time.time()

    solx, soly = boneh_durfee(pol, e, m, t, X, Y)

    d = None
    if solx > 0:
        # print("=== solutions found ===")
        if debug:
            print("x:", solx)
            print("y:", soly)

        d = int(pol(solx, soly) / e)

    if debug:
        print("=== %s seconds ===" % (time.time() - start_time))
    return d


def attack(attack_rsa_obj, publickey, cipher=[]):
    """Use boneh durfee method, should return a d value, else returns 0
       only works if the sageworks() function returned True
       many of these problems will be solved by the wiener attack module but perhaps some will fall through to here
    """
    try:
        sageresult = factor(publickey.n, publickey.e)
    except OverflowError:
        return (None, None)
    if sageresult is not None:
        tmp_priv = RSA.construct((int(publickey.n), int(publickey.e), int(sageresult)))
        publickey.p = tmp_priv.p
        publickey.q = tmp_priv.q
        privatekey = PrivateKey(
            int(publickey.p), int(publickey.q), int(publickey.e), int(publickey.n)
        )
        return (privatekey, None)
    return (None, None)
