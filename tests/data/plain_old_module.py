"""
I am a plain old module with no interesting dependencies or import machinery
fiddlery.
"""

import math


def get_sentinel_value():
    # Some proof we're even talking to the mitogen-test Docker image
    return open('/etc/sentinel').read()


def add(x, y):
    return x + y


def pow(x, y):
    return x ** y
