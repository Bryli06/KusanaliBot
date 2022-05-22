from math import floor


def get_level(exp):
    return floor(exp / 1000)  # update this eventually


def next_level(exp):
    return floor(exp / 1000) * 1000 + 1000


def level_to_exp(level):
    return level * 1000
