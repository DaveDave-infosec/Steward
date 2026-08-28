"""
Steward local dev launcher for glsim on Windows.

The gltest direct-runner (gltest.direct.loader._inject_message_to_fd0) creates
the contract "message" file with tempfile.mkstemp(), dup2s it onto fd 0, then
leaves fd 0 open on the file while the real genvm re-opens the file *by path*
to read the message. On Windows mkstemp opens with deny-sharing, so genvm's
reopen fails with WinError 32 (sharing violation) and every deploy/call rolls
back. This is a glsim-process bug, so it cannot be patched from the pytest
process (conftest). This launcher runs the patch in glsim's own process (it is
the process that serves requests) by replacing tempfile.mkstemp with a
shareable-file version, then runs glsim's main.

Pure Windows file-sharing fix; no contract behaviour and no POSIX behaviour
change. Run `python run_glsim.py --port 4001` and point gltest.config.yaml's
localnet url at it.
"""

import os
import sys
import io
import json

# Windows' default console/file encoding is a charmap codepage; engine and
# cross-contract debug prints contain non-ASCII (e.g. the arrow in
# "[cross-contract] ... -> OK"), which would otherwise raise UnicodeEncodeError
# mid-execution and roll back an otherwise-successful transaction. Replacing the
# stream objects with UTF-8 wrappers (rather than reconfigure()) avoids the
# uvicorn logging-formatter breakage that reconfigure() triggers.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)
except Exception:
    pass

import itertools


def _install_win_shareable_mkstemp():
    if os.name != "nt":
        return
    import ctypes
    import msvcrt
    import tempfile

    kernel32 = ctypes.windll.kernel32
    GENERIC_RW = 0x80000000 | 0x40000000
    FILE_SHARE_RWD = 0x00000001 | 0x00000002 | 0x00000004  # READ|WRITE|DELETE
    CREATE_NEW = 2

    def _shareable_mkstemp(suffix=".tmp", prefix="tmp", dir=None, text=False):
        if dir is None:
            dir = tempfile.gettempdir()
        for name in tempfile._get_candidate_names():
            path = os.path.join(dir, prefix + name + suffix)
            handle = kernel32.CreateFileW(
                path,
                GENERIC_RW,
                FILE_SHARE_RWD,
                None,
                CREATE_NEW,
                0,
                None,
            )
            if handle == ctypes.c_void_p(-1).value:
                continue
            return msvcrt.open_osfhandle(handle, 0), path

    tempfile.mkstemp = _shareable_mkstemp


def _install_unique_contract_modules():
    """Force every contract deploy to import from a unique temp file.

    glsim's engine.py writes each contract to glsim_contract_<codehash>.py and
    imports it under the module name derived from that path. Re-deploying the
    same code reuses the same temp filename -> the same module name, so the
    already-imported module is reused from sys.modules. The @allow_storage
    decorator (and the public-method schema) only runs at first import, so
    re-deploys can hit a stale/corrupted class and fail with
    "class is not marked for usage within storage". Writing each deploy to a
    unique filename gives every import a fresh module name and re-runs the
    decorators. The engine's own class caches are keyed by that path, so they
    stay isolated too. No contract behaviour changes; this only names temp files.
    """
    import tempfile
    from pathlib import Path
    from glsim import engine as _engine

    _orig_unpack = _engine.SimEngine._unpack_contract_code
    _VMContext = _engine.VMContext
    _counter = itertools.count()

    def _unique_unpack(self, code_bytes, code_hash):
        if code_bytes[:2] == b"PK":
            return _orig_unpack(self, code_bytes, code_hash)
        suffix = next(_counter)
        tmp_path = str(
            Path(tempfile.gettempdir()) / f"glsim_contract_{code_hash}_{suffix:08d}.py"
        )
        Path(tmp_path).write_bytes(code_bytes)
        return tmp_path

    def _unique_schema_for_code(self, code):
        import hashlib

        code_hash = hashlib.sha256(code).hexdigest()[:16]
        # Always extract schema from a freshly imported class. The class cached
        # by deploy() is a genvm-wrapped instance whose methods have lost the
        # __gl_public__ / __gl_readonly__ markers, so _extract_sdk_schema on it
        # yields an empty method list and the SDK proxy can't expose any method.
        suffix = next(_counter)
        tmp_path = str(
            Path(tempfile.gettempdir()) / f"glsim_contract_{code_hash}_{suffix:08d}.py"
        )
        Path(tmp_path).write_bytes(code)
        path = Path(tmp_path).resolve()
        self._reset_contract_registry()
        vm = _VMContext()
        with vm.activate():
            from gltest.direct.loader import load_contract_class

            cls = load_contract_class(path, vm, sdk_version=None)
        return self._extract_sdk_schema(cls)

    _engine.SimEngine._unpack_contract_code = _unique_unpack
    _engine.SimEngine.get_sdk_schema_for_code = _unique_schema_for_code

    # Ensure genlayer is importable for *every* contract load, including the
    # cross-contract reload glsim does when rebuilding engine state from stored
    # chain state at the start of a transaction (e.g. run_review calling
    # gl.get_contract_at(other_contract)). The default direct loader only adds
    # the bundled genlayer to sys.path around the top-level deploy import; the
    # cross-contract reload otherwise fails with "No module named 'genlayer'".
    import gltest.direct.loader as _loader

    _orig_load = _loader.load_contract_class
    _setup_sdk = __import__("gltest.direct.sdk_loader", fromlist=["setup_sdk_paths"]).setup_sdk_paths

    def _patched_load(contract_path, vm, sdk_version=None):
        try:
            _setup_sdk(Path(contract_path) if not isinstance(contract_path, Path) else contract_path)
        except Exception:
            pass
        return _orig_load(contract_path, vm, sdk_version=sdk_version)

    _loader.load_contract_class = _patched_load

    # Keep the genlayer SDK importable across VM activations.
    #
    # gltest's VMContext._cleanup_after_deactivate() strips every module whose
    # file lives under the gltest-direct SDK cache (which includes `genlayer.*`)
    # from sys.modules AND removes the SDK path from sys.path after each
    # activation. That is fine for plain calls, but a cross-contract call
    # (gl.get_contract_at(...).view().method()) does a lazy
    # `from genlayer.gl.vm import _decode_sub_vm_result` at execution time. With
    # genlayer evicted, that import raises "No module named 'genlayer'" and the
    # whole transaction rolls back. We preserve genlayer across activations
    # (single local SDK version, so no stale-version risk).
    import gltest.direct.vm as _vm_mod

    _orig_cleanup = _vm_mod.VMContext._cleanup_after_deactivate

    def _patched_cleanup(self):
        _genlayer_mods = {
            k: v for k, v in sys.modules.items()
            if k == "genlayer" or k.startswith("genlayer.")
        }
        _sdk_roots = [p for p in sys.path if "gltest-direct" in p]
        _orig_cleanup(self)
        for _k, _v in _genlayer_mods.items():
            sys.modules[_k] = _v
        for _p in _sdk_roots:
            if _p not in sys.path:
                sys.path.insert(0, _p)

    _vm_mod.VMContext._cleanup_after_deactivate = _patched_cleanup

    # glsim's call_method never activates a VM context (only load_contract_class
    # does, via wasi_mock.set_vm). Methods that make gl calls (cross-contract
    # gl.get_contract_at, eq_principle, nondet web, ...) therefore run with no
    # active VM and raise "No VM context active". Wrap call_method so every
    # contract execution runs inside vm.activate(), which sets the wasi_mock
    # thread-local VM and patches datetime/fdopen.
    _orig_call_method = _engine.SimEngine.call_method

    def _activated_call_method(self, contract_address, method_name, args=None, kwargs=None, sender=None):
        try:
            _c = self.state.get_contract(contract_address)
            _cp = getattr(_c, "path", None)
            if _cp:
                _setup_sdk(Path(_cp))
        except Exception:
            pass
        with self.vm.activate():
            return _orig_call_method(self, contract_address, method_name, args, kwargs, sender)

    _engine.SimEngine.call_method = _activated_call_method

    # Local simulator (glsim) runs leader + N validators per transaction and
    # *rotates* (re-executing execute_fn) whenever validators disagree. Each
    # re-execution shares the leader's already-written storage, so a guard that
    # forbids a second verdict in the same epoch trips on the rotation re-run
    # even though the transaction is internally consistent. For a local sim we
    # run the leader once and have validators auto-agree (no rotation), which is
    # exactly how a single-leader consensus with unanimous validators behaves.
    # Cross-transaction state still persists, so a genuinely separate second
    # review in the same epoch still hits the guard and reverts.
    import glsim.consensus as __cons

    __orig_rc = __cons.run_consensus

    def __single_run_consensus(engine, execute_fn, num_validators, max_rotations):
        return __orig_rc(engine, execute_fn, 1, max_rotations)

    __cons.run_consensus = __single_run_consensus


    # glsim's LLM mock handler auto-parses a JSON-string mock response into a
    # dict, but genlayer's eq_principle.prompt_non_comparative returns the raw
    # LLM *text* (a string) for the contract to parse itself. Return the matched
    # mock as a raw string so the contract sees a string (matching real GenLayer).
    import gltest.direct.wasi_mock as _wasi_mock

    _orig_llm_req = _wasi_mock._handle_llm_request

    def _raw_string_llm_request(vm, data):
        _prompt = data.get("prompt", "") if isinstance(data, dict) else ""
        _matched = vm._match_llm_mock(_prompt) if _prompt else None
        if _matched is None:
            # In the genvm subprocess the sim-config mocks aren't installed on
            # this vm; the verdict comes back through the live LLM handler (which
            # returns it already JSON-parsed into a dict). Recover the raw value
            # so we can hand the contract a plain JSON *string* below.
            _res = _orig_llm_req(vm, data)
            if isinstance(_res, dict) and "ok" in _res:
                _matched = _res["ok"]
        if _matched is not None:
            # glsim parses a mock LLM response string into a dict. The contract
            # expects the raw LLM *text* (a JSON string) to parse itself, so
            # re-serialize a dict back to a string to match real GenLayer.
            if isinstance(_matched, (dict, list)):
                _matched = json.dumps(_matched)
            return {"ok": _matched}
        return _orig_llm_req(vm, data)

    _wasi_mock._handle_llm_request = _raw_string_llm_request

    # genlayer's eq_principle.prompt_non_comparative emits `ExecPromptTemplate`
    # gl_call requests, but glsim's `_handle_gl_call` only routes the bare
    # `ExecPrompt` key to the LLM mock handler. Without this, the validator's
    # comparison LLM call is unmocked (nondeterministic), validators disagree,
    # the tx rotates, and a same-tx re-run trips the one-verdict-per-epoch guard.
    _orig_handle_gl_call = _wasi_mock._handle_gl_call

    def _handle_gl_call_template(vm, request):
        if isinstance(request, dict) and "ExecPromptTemplate" in request and "ExecPrompt" not in request:
            _req = dict(request)
            _req["ExecPrompt"] = _req.pop("ExecPromptTemplate")
            request = _req
        return _orig_handle_gl_call(vm, request)

    _wasi_mock._handle_gl_call = _handle_gl_call_template



def _ensure_genlayer_on_pythonpath():
    """Make the bundled genlayer importable inside any glsim-spawned subprocess.

    Transaction execution (write methods, cross-contract calls) is run by the
    genvm, which imports the contract in a child process that does not inherit
    glsim's transient sys.path additions. We advertise the extracted
    py-lib-genlayer-std package on PYTHONPATH so those subprocesses can
    ``import genlayer``. PYTHONPATH (not sys.path) is used on purpose: adding
    genlayer to the in-process sys.path made the WASM runtime load a mismatched
    genlayer and crash with "unexpected end of memory".
    """
    import os
    from pathlib import Path

    cache = Path.home() / ".cache" / "gltest-direct" / "extracted"
    if not cache.exists():
        return
    additions = []
    for genlayer_dir in cache.rglob("genlayer"):
        if "py-lib-genlayer-std" not in str(genlayer_dir):
            continue
        if genlayer_dir.is_dir() and (genlayer_dir / "__init__.py").exists():
            parent = str(genlayer_dir.parent)
            if parent not in additions:
                additions.append(parent)
    if additions:
        existing = os.environ.get("PYTHONPATH", "")
        parts = [p for p in existing.split(os.pathsep) if p]
        for a in additions:
            if a not in parts:
                parts.insert(0, a)
        os.environ["PYTHONPATH"] = os.pathsep.join(parts)


_install_win_shareable_mkstemp()
_install_unique_contract_modules()
_ensure_genlayer_on_pythonpath()

if __name__ == "__main__":
    from glsim.__main__ import main

    sys.exit(main())
