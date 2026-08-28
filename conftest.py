"""
Windows defect fix for the gltest direct-runner (glsim).

gltest.direct.loader._inject_message_to_fd0 creates the contract "message" file
with tempfile.mkstemp(), dup2s it onto fd 0, then leaves fd 0 pointing at the
open file. The real genvm execution re-opens that file *by path* to read the
message. On Windows, mkstemp opens the file with no sharing (deny read/write),
so genvm's reopen fails with WinError 32 (sharing violation) and the deploy
rolls back under glsim. (os.unlink of the still-open file also raises WinError
32, which the outer OSError shim below swallows.)

The fix: make the message temp file shareable. We monkeypatch tempfile.mkstemp
on Windows to create the file via CreateFileW with FILE_SHARE_READ|WRITE|DELETE.
Then genvm can reopen it by path, and unlink can mark it delete-pending. Nothing
here touches the Steward contracts or any test assertion.
"""

import os as _os

try:
    import tempfile as _tempfile

    if _os.name == "nt":
        import ctypes as _ctypes
        import msvcrt as _msvcrt

        _kernel32 = _ctypes.windll.kernel32
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        FILE_SHARE_DELETE = 0x00000004
        CREATE_NEW = 2

        def _shareable_mkstemp(suffix=".tmp", prefix="tmp", dir=None, text=False):
            if dir is None:
                dir = _tempfile.gettempdir()
            for name in _tempfile._get_candidate_names():
                path = _os.path.join(dir, prefix + name + suffix)
                handle = _kernel32.CreateFileW(
                    path,
                    GENERIC_READ | GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                    None,
                    CREATE_NEW,
                    0,
                    None,
                )
                if handle == _ctypes.c_void_p(-1).value:
                    continue
                fd = _msvcrt.open_osfhandle(handle, 0)
                return fd, path

        _tempfile.mkstemp = _shareable_mkstemp

except Exception:
    pass

try:
    import gltest.direct.loader as _loader

    _orig_inject = _loader._inject_message_to_fd0

    def _inject_message_to_fd0_win_safe(vm):
        try:
            return _orig_inject(vm)
        except OSError:
            if _os.name == "nt":
                return None
            raise

    _loader._inject_message_to_fd0 = _inject_message_to_fd0_win_safe
except Exception:
    pass
