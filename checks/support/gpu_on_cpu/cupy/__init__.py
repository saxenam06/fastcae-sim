"""A stand-in for CuPy on the CPU, for the checks only (LOP-33): NumPy under CuPy's name, so the
optimiser's and FE's GPU paths run on a machine without a card (CI, a cloud session) and the moved
code can be compared with the prototype's on the same inputs. Never on the product's path: it is
put on `sys.path` by the checks that ask for it (`checks/support/gpu_on_cpu/__init__.py`)."""

import contextlib

import numpy as _np
from numpy import *  # noqa: F401,F403  (CuPy's array API is NumPy's)
from numpy import add, fft, float32, float64, int32, int64, linalg, random  # noqa: F401

CPU_STAND_IN = True


def asnumpy(a, *args, **kwargs):
    return _np.asarray(a)


class _Pool:
    def free_all_blocks(self) -> None:
        pass

    def used_bytes(self) -> int:
        return 0

    def total_bytes(self) -> int:
        return 0


_POOL = _Pool()


def get_default_memory_pool() -> _Pool:
    return _POOL


def get_default_pinned_memory_pool() -> _Pool:
    return _POOL


class _Device(contextlib.AbstractContextManager):
    def __init__(self, device: int = 0):
        self.id = device

    def __exit__(self, *exc):
        return None

    def synchronize(self) -> None:
        pass


class _Runtime:
    class CUDARuntimeError(RuntimeError):
        pass

    @staticmethod
    def getDeviceCount() -> int:  # noqa: N802  (CuPy's name)
        return 0


class cuda:  # noqa: N801  (CuPy's module name)
    Device = _Device
    runtime = _Runtime
