# coding=utf-8
import os


_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_fixture(*args):
    return os.path.join(_ROOT, *args)
