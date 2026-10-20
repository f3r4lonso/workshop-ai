"""Short, bounded helper processes (version and plugin checks) shared by `wai` and the app server.

Output goes to a temporary file, not a pipe: on Windows a `.cmd` wrapper's grandchild (`node.exe`) can keep a pipe
open after the timeout kills the wrapper, and `subprocess.run` would then wait forever. On timeout the whole process
tree is ended with `taskkill /T /F` (fixed arguments, absolute path).
"""

import os
import subprocess
import tempfile


def _taskkill():
    system_root = os.environ.get("SystemRoot") or r"C:\Windows"
    path = os.path.join(system_root, "System32", "taskkill.exe")
    return path if os.path.isfile(path) else None


def _end_tree(proc):
    taskkill = _taskkill() if os.name == "nt" else None
    if taskkill:
        try:
            subprocess.run([taskkill, "/T", "/F", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        proc.kill()
        proc.wait(timeout=2)
    except (OSError, subprocess.SubprocessError):
        pass


def run_bounded(argv, timeout, env=None):
    """Run argv (shell=False) in a fresh temporary folder; return (returncode, stdout text) or None."""
    try:
        with tempfile.TemporaryDirectory(prefix="workshop-check-") as cwd, tempfile.TemporaryFile() as out:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out,
                                    stderr=subprocess.DEVNULL, shell=False,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _end_tree(proc)
                return None
            out.seek(0)
            return code, out.read().decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
