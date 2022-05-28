from math import floor, sqrt


a = 20
b = 300
c = 200


def equation(level):
    return floor(a * pow(level, 2) + b * level + c)


def inverse(exp):
    level = floor((-b + sqrt(pow(b, 2) - 4 * a * (c - exp))) / (2 * a)) + 1
    return level if level > 0 else 0


def next_level(exp):
    return equation(inverse(exp))
