#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import logging
import requests
from lib.rsalibnum import invmod
from Crypto.PublicKey import RSA
from lib.keys_wrapper import PrivateKey
from lib.exceptions import FactorizationError

logger = logging.getLogger("global_logger")


def solveforp(equation):
    """Parse factordb response
    """
    try:
        if "^" in equation:
            k, j = equation.split("^")
        if "-" in j:
            j, sub = j.split("-")
        eq = list(map(int, [k, j, sub]))
        return pow(eq[0], eq[1]) - eq[2]
    except Exception as e:
        logger.error(
            "[*] FactorDB gave something we couldn't parse sorry (%s). Got error: %s"
            % (equation, e)
        )
        raise FactorizationError()


def attack(attack_rsa_obj, publickey, cipher=[]):
    """Factors available online?
    """
    try:
        url_1 = "http://factordb.com/index.php?query=%i"
        url_2 = "http://factordb.com/index.php?id=%s"
        s = requests.Session()
        r = s.get(url_1 % publickey.n, verify=False)
        regex = re.compile(r"index\.php\?id\=([0-9]+)", re.IGNORECASE)
        ids = regex.findall(r.text)
        # check if only 1 factor is returned
        if len(ids) == 2:
            # theres a chance that the only factor returned is prime, and so we can derive the priv key from it
            regex = re.compile(r"<td>P<\/td>")
            prime = regex.findall(r.text)
            if len(prime) == 1:
                # n is prime, so lets get the key from it
                d = invmod(publickey.e, publickey.n - 1)
                # construct key using only n and d
                priv_key = PrivateKey(e=int(publickey.e), n=int(publickey.n), d=d)
                return (priv_key, None)

        try:
            regex = re.compile(r'value="([0-9\^\-]+)"', re.IGNORECASE)
            p_id = ids[1]
            r_1 = s.get(url_2 % p_id, verify=False)
            key_p = regex.findall(r_1.text)[0]
            publickey.p = int(key_p) if key_p.isdigit() else solveforp(key_p)

            q_id = ids[2]
            r_2 = s.get(url_2 % q_id, verify=False)
            key_q = regex.findall(r_2.text)[0]
            publickey.q = int(key_q) if key_q.isdigit() else solveforp(key_q)
        except IndexError:
            return (None, None)

        if publickey.p == publickey.q == publickey.n:
            return (None, None)
        priv_key = PrivateKey(
            p=int(publickey.p),
            q=int(publickey.q),
            e=int(publickey.e),
            n=int(publickey.n),
        )

        return (priv_key, None)
    except:
        return (None, None)
