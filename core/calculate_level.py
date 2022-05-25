from math import floor


level_exp = 12

def get_level(exp):
    return floor(exp / level_exp)  # update this eventually


def next_level(exp):
    return floor(exp / level_exp) * level_exp + level_exp


def level_to_exp(level):
    return level * level_exp
