#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"


def format_time_ns(time_ns: int, insertSpace: bool = False) -> str:
    space: str = " " if insertSpace else ""
    if time_ns > 1e9:
        duration_str = f"{time_ns / 1e9:.3f}{space}s"
    elif time_ns > 1e6:
        duration_str = f"{time_ns / 1e6:.3f}{space}ms"
    elif time_ns > 1e3:
        duration_str = f"{time_ns / 1e3:.3f}{space}us"
    else:
        duration_str = f"{time_ns}{space}ns"
    return duration_str
