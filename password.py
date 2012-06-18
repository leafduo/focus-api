#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

from passlib.hash import sha512_crypt

class Password:
    """Encrypting and verifying passwords for our application."""

    @classmethod
    def encrypt(cls, password, rounds=50000):
        return sha512_crypt.encrypt(password, rounds=rounds)

    @classmethod
    def verify(cls, password, password_hash):
        return sha512_crypt.verify(password, password_hash)
