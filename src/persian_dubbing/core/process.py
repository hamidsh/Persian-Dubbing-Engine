"""Bounded, cancellable subprocesses; no shell interpolation."""
import subprocess, tempfile, time, threading
from pathlib import Path
import psutil

class Cancelled(RuntimeError):
    pass

class Cancellation:
    def __init__(self):
        self.event = threading.Event()
    def cancel(self):
        self.event.set()
    def check(self):
        if self.event.is_set():
            raise Cancelled("Operation cancelled")

def kill_tree(pid):
    try:
        root = psutil.Process(pid)
        children = root.children(recursive=True)
        for proc in reversed(children):
            try: proc.kill()
            except psutil.NoSuchProcess: pass
        root.kill()
        psutil.wait_procs(children + [root], timeout=3)
    except psutil.NoSuchProcess:
        pass

def run(args, *, cwd=None, cancel=None, timeout=1200, log_path=None):
    if cancel: cancel.check()
    # File-backed output prevents pipe deadlocks and unbounded in-memory logs.
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen([str(a) for a in args], cwd=cwd, stdout=log,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        start = time.monotonic()
        try:
            while proc.poll() is None:
                if cancel: cancel.check()
                if time.monotonic() - start > timeout:
                    raise TimeoutError(f"Process exceeded {timeout}s: {Path(str(args[0])).name}")
                time.sleep(0.08)
        except BaseException:
            kill_tree(proc.pid)
            proc.wait()
            raise
        finally:
            if log_path:
                log.seek(0)
                with open(log_path, "wb") as dest:
                    import shutil
                    shutil.copyfileobj(log, dest)
        log.seek(0, 2)
        log.seek(max(0, log.tell() - 32000))
        output = log.read().decode("utf-8", errors="replace")
        if proc.returncode:
            raise RuntimeError(f"{Path(str(args[0])).name} exited {proc.returncode}:\n{output}")
        return output
