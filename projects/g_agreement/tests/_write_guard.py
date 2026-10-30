"""Per-path, concurrency-proof isolation guard for the offline tests.

The old guards snapshotted ``results/g_agreement`` and ``cache/g_agreement`` with ``rglob("*")`` at import and compared
the listing at the end of the module. Several pods and sessions write into those shared trees while the suite runs, so
the comparison failed for reasons unrelated to the code under test (HANDOFF, "To every test owner", WS4 2026-10-19).

This guard watches the test process instead of the trees. While a test module runs, it records every write this
process makes inside the protected roots: ``open``/``io.open`` in a writing mode (which covers ``Path.write_text``,
``np.save``, ``pandas.to_csv``, ``json.dump`` into a file and ``torch.save``), ``os.open`` with a writing flag,
``mkdir``/``makedirs`` of a new directory, ``rename``/``replace``, ``remove``/``unlink``/``rmdir`` and
``shutil.rmtree``. It never blocks a write; the module's guard test fails if anything was recorded, and names each path
and operation. Writes by other processes (pods, other sessions) are invisible to it by construction.

Limit: writes made by worker subprocesses that a test starts are not seen (none of the guarded modules starts any).

Usage in a test module (at module level, after ``REPO`` is defined)::

    from projects.g_agreement.tests import _write_guard as WG  # noqa: E402
    _GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement", REPO / "cache" / "g_agreement"])
    _write_guard = _GUARD.fixture()          # autouse, module-scoped

    def test_zz_results_untouched():
        _GUARD.assert_clean()

The fixture also fails the module at teardown if a test that ran after the guard test wrote into a protected root.
Set ``WRITE_GUARD_PLANT=1`` to plant one synthetic write into the first protected root at module start (intercepted,
never written to disk), which must make the guard test fail: that is the non-vacuity check.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import os
import shutil
from pathlib import Path
from typing import Any, Iterable, Iterator

import pytest

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
PROBE_NAME = ".write_guard_probe"


class _NullFile(io.StringIO):
    """Stand-in returned for the planted probe so the non-vacuity check never touches the disk."""


class ModuleWriteGuard:
    def __init__(self, roots: Iterable[Any]):
        self.roots: list[Path] = []
        for r in roots:
            if r is None:
                continue
            r = Path(r)
            for cand in (r.absolute(), r.resolve()):
                if cand not in self.roots:
                    self.roots.append(cand)
        self.violations: list[tuple[str, str]] = []
        self._active = False

    # ------------------------------------------------------------------ matching
    def _protected(self, path: Any) -> str | None:
        try:
            p = Path(os.fsdecode(os.fspath(path)))
        except TypeError:          # file descriptors and other non-path handles
            return None
        if not p.is_absolute():
            p = Path.cwd() / p
        cands = {p}
        with contextlib.suppress(OSError, RuntimeError):
            cands.add(p.resolve())
        for c in cands:
            for root in self.roots:
                if c == root or root in c.parents:
                    return str(c)
        return None

    def _record(self, op: str, path: Any) -> bool:
        hit = self._protected(path)
        if hit is not None:
            self.violations.append((op, hit))
            return True
        return False

    # ------------------------------------------------------------------ patching
    @contextlib.contextmanager
    def watching(self) -> Iterator["ModuleWriteGuard"]:
        orig = {"open": builtins.open, "os.open": os.open, "mkdir": os.mkdir, "makedirs": os.makedirs,
                "rename": os.rename, "replace": os.replace, "remove": os.remove, "unlink": os.unlink,
                "rmdir": os.rmdir, "rmtree": shutil.rmtree}
        guard = self

        def g_open(file, mode="r", *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)) and any(ch in mode for ch in "wax+"):
                if guard._record(f"open({mode!r})", file) and Path(os.fsdecode(os.fspath(file))).name == PROBE_NAME:
                    return _NullFile()
            return orig["open"](file, mode, *args, **kwargs)

        def g_os_open(path, flags, *args, **kwargs):
            if flags & _WRITE_FLAGS:
                guard._record("os.open", path)
            return orig["os.open"](path, flags, *args, **kwargs)

        def g_mkdir(path, *args, **kwargs):
            if not os.path.exists(path):
                guard._record("mkdir", path)
            return orig["mkdir"](path, *args, **kwargs)

        def g_makedirs(name, *args, **kwargs):
            if not os.path.exists(name):
                guard._record("makedirs", name)
            return orig["makedirs"](name, *args, **kwargs)

        def two(op):
            def f(src, dst, *args, **kwargs):
                guard._record(f"{op}(src)", src)
                guard._record(f"{op}(dst)", dst)
                return orig[op](src, dst, *args, **kwargs)
            return f

        def one(op):
            def f(path, *args, **kwargs):
                guard._record(op, path)
                return orig[op](path, *args, **kwargs)
            return f

        patches = [(builtins, "open", g_open), (io, "open", g_open), (os, "open", g_os_open), (os, "mkdir", g_mkdir),
                   (os, "makedirs", g_makedirs), (os, "rename", two("rename")), (os, "replace", two("replace")),
                   (os, "remove", one("remove")), (os, "unlink", one("unlink")), (os, "rmdir", one("rmdir")),
                   (shutil, "rmtree", one("rmtree"))]
        saved = [(mod, name, getattr(mod, name)) for mod, name, _ in patches]
        for mod, name, fn in patches:
            setattr(mod, name, fn)
        self._active = True
        try:
            yield self
        finally:
            self._active = False
            for mod, name, fn in saved:
                setattr(mod, name, fn)

    def fixture(self):
        guard = self

        @pytest.fixture(autouse=True, scope="module")
        def _write_guard():
            with guard.watching():
                if os.environ.get("WRITE_GUARD_PLANT") == "1" and guard.roots:
                    with builtins.open(guard.roots[0] / PROBE_NAME, "w") as fh:   # intercepted: recorded, not written
                        fh.write("probe")
                yield guard
            if guard.violations:
                pytest.fail(guard.report(), pytrace=False)

        return _write_guard

    # ------------------------------------------------------------------ reporting
    def report(self) -> str:
        lines = [f"{op} {path}" for op, path in self.violations[:20]]
        more = f" (+{len(self.violations) - 20} more)" if len(self.violations) > 20 else ""
        roots = ", ".join(str(r) for r in self.roots)
        return f"tests wrote into protected trees ({roots}): " + "; ".join(lines) + more

    def assert_clean(self) -> None:
        assert self._active, "the module's write guard fixture is not active"
        assert not self.violations, self.report()
