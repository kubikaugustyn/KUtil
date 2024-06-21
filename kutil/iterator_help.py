"""
This is the iterator module of KUtil containing iteration helpers.
"""
#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from itertools import *
from functools import partial

from kutil.math_help import PreciseFloat, decimal, DEFAULT_PRECISION, toDecimal, isfinite, pi
from kutil.typing_help import Iterator, overload, Optional, Final, LiteralTrue, LiteralFalse


# Useful functions
# @formatter:off
@overload
def rangeFloat(end: PreciseFloat, *, step: PreciseFloat = 1.0, precision: int = DEFAULT_PRECISION, eMax: int = decimal.MAX_EMAX, eMin: int = decimal.MIN_EMIN, toFloat: LiteralTrue = True) -> Iterator[float]: ...
@overload
def rangeFloat(end: PreciseFloat, *, step: PreciseFloat = 1.0, precision: int = DEFAULT_PRECISION, eMax: int = decimal.MAX_EMAX, eMin: int = decimal.MIN_EMIN, toFloat: LiteralFalse = False) -> Iterator[decimal.Decimal]: ...


@overload
def rangeFloat(start: PreciseFloat, end: PreciseFloat, *, step: PreciseFloat = 1.0, precision: int = DEFAULT_PRECISION, eMax: int = decimal.MAX_EMAX, eMin: int = decimal.MIN_EMIN, toFloat: LiteralTrue = True) -> Iterator[float]: ...
@overload
def rangeFloat(start: PreciseFloat, end: PreciseFloat, *, step: PreciseFloat = 1.0, precision: int = DEFAULT_PRECISION, eMax: int = decimal.MAX_EMAX, eMin: int = decimal.MIN_EMIN, toFloat: LiteralFalse = False) -> Iterator[decimal.Decimal]: ...
# @formatter:on


def rangeFloat(start_or_only_end: PreciseFloat, end: Optional[PreciseFloat] = None, *,
               step: PreciseFloat = 1, precision: int = DEFAULT_PRECISION, eMax: int =
               decimal.MAX_EMAX, eMin: int = decimal.MIN_EMIN, toFloat: bool = False) -> \
        Iterator[float | decimal.Decimal]:
    """
    A range generator for floats. Used instead of range() which doesn't support floats.
    This is a general description of rangeFloat(), see its overloaded versions for more information.

    See https://docs.python.org/3/library/decimal.html#decimal.Context for more information about
    the precision, eMax and eMin parameters as well as the input floats for the range.

    :param start_or_only_end: EITHER the start of the range (inclusive) OR the end if the end
     parameter is None. Cannot be inf or -inf.
    :param end: The end of the range (exclusive). Cannot be inf or -inf. If not provided, the
     range will be in the interval [0, start_or_only_end).
    :param step: The step the range should change by. Cannot be inf or -inf.
    :param precision: The precision of the floats to use. Set to 5 by default.
    :param eMax: The maximum exponent value.
    :param eMin: The minimum exponent value.
    :param toFloat: Whether the range should convert the decimals to floats before yielding them.

    >>> list(rangeFloat(2, step=".5"))
    [Decimal('0'), Decimal('0.5'), Decimal('1.0'), Decimal('1.5')]

    >>> list(rangeFloat(2, step=".5", toFloat=True))
    [0.0, 0.5, 1.0, 1.5]

    >>> list(rangeFloat(-2, step="-.5", toFloat=True))
    [0.0, -0.5, -1.0, -1.5]

    >>> list(rangeFloat(-2, 3, step="1.5", toFloat=True))
    [-2.0, -0.5, 1.0, 2.5]

    Note that in the following example, pi may not be precisely converted to decimal.Decimal!

    >>> list(rangeFloat(7, step=decimal.Decimal(pi), toFloat=True, precision=3))
    [0.0, 3.14, 6.28]
    """
    finalStart: Final[PreciseFloat] = 0 if end is None else start_or_only_end
    finalEnd: Final[PreciseFloat] = start_or_only_end if end is None else end

    # The actual iteration must be done with Decimal, so 0.1 + 0.2 != 0.30000000000000004
    convert: partial = partial(toDecimal, precision=precision, eMax=eMax,
                               eMin=eMin)  # Remove boilerplate
    startDec: Final[decimal.Decimal] = convert(finalStart)
    endDec: Final[decimal.Decimal] = convert(finalEnd)
    stepDec: Final[decimal.Decimal] = convert(step)
    # startDec, endDec and stepDec are finally the values we'll count with

    # Check the values
    if not isfinite(startDec):
        raise ValueError("Cannot use infinity, -infinity or NaN in rangeFloat as a starting value")
    elif not isfinite(endDec):
        raise ValueError("Cannot use infinity, -infinity or NaN in rangeFloat as an ending value")
    elif not isfinite(stepDec) or stepDec == 0:
        raise ValueError("Cannot use infinity, -infinity, NaN or 0 in rangeFloat as a step")

    # Check if the range would loop forever
    if startDec == endDec:
        return  # No output because finalEnd is excluded
    elif startDec < endDec:
        if stepDec < 0:
            raise ValueError("Cannot use a negative step value in rangeFloat "
                             "when the start value is lower than the end value")
    elif startDec > endDec:
        if stepDec > 0:
            raise ValueError("Cannot use a positive step value in rangeFloat "
                             "when the start value is higher than the end value")

    # Prepare the context
    with decimal.localcontext() as ctx:
        ctx.prec = precision
        ctx.Emax = eMax
        ctx.Emin = eMin

        # Finally, the range itself
        state: decimal.Decimal = startDec
        while (state < endDec) if stepDec > 0 else (state > endDec):  # Support negative ranges!
            yield float(state) if toFloat else state
            state += stepDec
