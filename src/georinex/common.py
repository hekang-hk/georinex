from __future__ import annotations
import typing as T
from pathlib import Path
from datetime import timedelta
import numpy as np
import logging

try:
    import psutil
except ImportError:
    psutil = None


def check_unique_times(times: np.ndarray) -> bool:
    Nuniq = np.unique(times).size
    Ntimes = times.size

    if not (ok := Ntimes == Nuniq):
        logging.error(f"only {Nuniq} times out of {Ntimes} are unique times")

    return ok


def rinex_string_to_float(s: str) -> float:
    return float(s.replace("D", "E"))


def check_ram(memneed: int, fn: T.TextIO | Path):
    if psutil is None:
        return

    mem = psutil.virtual_memory()

    if memneed > 0.5 * mem.available:  # because of array copy Numpy => Xarray
        errmsg = (
            f"needs {memneed / 1e9} GBytes RAM, but only {mem.available / 1e9} Gbytes available \n"
            "try fast=False to reduce RAM usage, raise a GitHub Issue to let us help"
        )
        if isinstance(fn, Path):
            errmsg = f"{fn}" + errmsg
        raise RuntimeError(errmsg)


def determine_time_system(header: dict[T.Hashable, T.Any]) -> str:
    """Determine which time system is used in an observation file."""
    # Current implementation is quite inconsistent in terms what is put into
    # header.
    try:
        file_type = header["RINEX VERSION / TYPE"][40]
    except KeyError:
        file_type = header["systems"]

    match file_type:
        case "G":
            ts = "GPS"
        case "R":
            ts = "GLO"
        case "E":
            ts = "GAL"
        case "J":
            ts = "QZS"
        case "C":
            ts = "BDT"
        case "I":
            ts = "IRN"
        case "M":
            ts = header["TIME OF FIRST OBS"][48:51].strip()
        # Else the type is mixed and the time system must be specified in
        # TIME OF FIRST OBS row.
        case _:
            raise ValueError(f"unknown file type {file_type}")

    return ts


def check_time_interval(interval: float | int | timedelta | None) -> timedelta | None:
    if isinstance(interval, (float, int)):
        if interval < 0:
            raise ValueError("time interval must be non-negative")
        interval = timedelta(seconds=interval)
    elif isinstance(interval, timedelta):
        pass
    elif interval is None:
        pass
    else:
        raise TypeError("expect time interval in seconds (float,int) or datetime.timedelta")

    return interval
