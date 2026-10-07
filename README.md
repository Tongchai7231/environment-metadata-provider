# Environment Metadata Provider

Collects hostname, process ID, Python version, and boot time once at construction, then exposes them as a frozen mapping for log record enrichment.

```python
from environment_metadata_provider import EnvironmentMetadataProvider

provider = EnvironmentMetadataProvider()
meta = provider.metadata()      # EnvironmentMetadata (read-only Mapping)
record = provider.enrich({"message": "hello"})  # dict with env fields added
```

## Why

Log records often need stable host and process context attached to every line. Doing that lookup per-record is wasteful and racy — the values don't move during a process's life. This provider captures them once and hands out an immutable view.

The trade-off: the snapshot is taken at construction, not at import. A long-running daemon that re-exec's or changes hostname after the provider is built will keep reporting the original values. If you need fresh values, construct a new provider.

## Behaviour notes

- `metadata()` returns an `EnvironmentMetadata` — a read-only `Mapping`. Call `.as_dict()` if you need a mutable copy.
- `enrich(record)` returns a new `dict`. Keys already present in `record` are preserved; environment fields only fill gaps. This keeps per-call context (e.g. a request-scoped hostname) from being overwritten.
- `boot_time` is the provider's construction instant, not the OS boot time. The constructor takes an injectable `clock` callable so tests can pass a deterministic clock rather than comparing against wall-clock time.

## Edge you will hit

`socket.gethostname()` can raise on hosts with no configured hostname. The provider does not catch that — it fails fast at construction, which is preferable to silently logging a placeholder in every record. If your environment is hostname-unstable, pass a `gethostname` callable that returns a stable fallback.

## Exports

- `EnvironmentMetadataProvider` — the collector. Constructor keyword args: `clock`, `gethostname`, `getpid`, `python_version` (all optional with sensible defaults).
- `EnvironmentMetadata` — the frozen mapping type returned by `metadata()`. Subclasses `Mapping[str, object]`; also exposes `as_dict()`.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
