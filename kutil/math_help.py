"""
This is the math module of KUtil containing maths helpers.
"""
#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from math import *
import decimal

from kutil.typing_help import Final

# Constants
DEFAULT_PRECISION: Final[int] = 25

# Additional types
# Can be converted to decimal.Decimal with toDecimal()
type SomeFloat = int | float | str | decimal.Decimal
# Can be converted to decimal.Decimal without loss of prec. (with good arguments put to toDecimal())
type PreciseFloat = int | str | decimal.Decimal


# Useful functions
def toDecimal(someFloat: PreciseFloat, precision: int = DEFAULT_PRECISION,
              eMax: int = decimal.MAX_EMAX, eMin: int = decimal.MIN_EMIN) -> decimal.Decimal:
    with decimal.localcontext() as ctx:
        ctx.prec = precision
        ctx.Emax = eMax
        ctx.Emin = eMin

        if isinstance(someFloat, decimal.Decimal):
            pass
        elif isinstance(someFloat, (str, int)):
            someFloat = ctx.create_decimal(someFloat)
        else:
            raise ValueError(f"Unknown type to convert: {type(someFloat)}")
    return someFloat
