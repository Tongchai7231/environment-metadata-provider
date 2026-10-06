from __future__ import annotations

import os
import platform
import socket
import sys
import time
from types import MappingProxyType
from typing import Callable, Mapping


class EnvironmentMetadata(Mapping[str, object]):
    """
    Immutable view of the environment metadata collected at provider construction.

    Wraps a ``MappingProxyType`` so callers cannot mutate the captured snapshot.
    ``Mapping`` subclassing is used rather than a plain ``dict`` subclass because
    ``MappingProxyType`` is itself read-only but not a ``Mapping``; implementing
    the abstract methods gives callers the full mapping protocol (``.get``,
    iteration, ``in``) without re-exposing a mutable backing store.
    """

    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, object]) -> None:
        self._data = MappingProxyType(dict(data))

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def as_dict(self) -> dict:
        """Return a shallow mutable copy of the captured metadata."""
        return dict(self._data)


class EnvironmentMetadataProvider:
    """
    Collects hostname, process ID, Python version, and boot time once at
    construction, then exposes them as a frozen mapping for log record
    enrichment.

    The boot time is captured relative to a ``clock`` callable so that tests can
    pass a deterministic clock. This is the only time-dependent behaviour; no
    other field changes after construction.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        gethostname: Callable[[], str] = socket.gethostname,
        getpid: Callable[[], int] = os.getpid,
        python_version: str | None = None,
    ) -> None:
        self._clock = clock
        self._data = EnvironmentMetadata(
            {
                "hostname": gethostname(),
                "pid": getpid(),
                "python_version": python_version if python_version is not None else platform.python_version(),
                "boot_time": clock(),
            }
        )

    def metadata(self) -> EnvironmentMetadata:
        """Return the frozen environment metadata captured at construction."""
        return self._data

    def enrich(self, record: dict) -> dict:
        """
        Return a copy of ``record`` with the environment metadata merged in.

        Existing keys in ``record`` are preserved — environment fields are only
        added where the record does not already define them. This prevents the
        provider from clobbering per-log-call context such as a request-scoped
        ``hostname``.
        """
        enriched = dict(self._data)
        enriched.update(record)
        return enriched
