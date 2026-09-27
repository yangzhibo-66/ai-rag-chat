import os, signal, subprocess, sys, time, threading, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

backend_proc = None
frontend_proc = None

def find_python():
    for c in [
        str(BACKEND / ".venv" / "Scripts" / "python.exe"),
        str(BACKEND / ".venv" / "bin" / "python"),
        sys.executable,
    ]:
        if Path(c).is_file():
            return c
    return "python"

def npm():
    return "npm.cmd" if sys.platform == "win32" else "npm"

def start_backend():
    global backend_proc
    py = find_python()
    print(f"[backend] python: {py}")
    backend_proc = subprocess.Popen(
        [py, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--log-level", "info"],
        cwd=str(BACKEND),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    print(f"[backend] pid={backend_proc.pid}")

def wait_backend(timeout=30):
    url = f"http://127.0.0.1:{BACKEND_PORT}/health"
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if urllib.request.urlopen(url, timeout=2).status == 200:
                print("[backend] ready")
                return True
        except:
            pass
        time.sleep(0.5)
    print("[backend] WARN: timed out")
    return False

def start_frontend():
    global frontend_proc
    print("[frontend] npm run dev ...")
    frontend_proc = subprocess.Popen(
        [npm(), "run", "dev"],
        cwd=str(FRONTEND),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    print(f"[frontend] pid={frontend_proc.pid}")

def cleanup():
    print("\nshutting down ...")
    for name, p in [("frontend", frontend_proc), ("backend", backend_proc)]:
        if p and p.poll() is None:
            print(f"[{name}] stopping pid={p.pid}")
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
            print(f"[{name}] stopped")

def pipe(proc, label):
    if proc and proc.stdout:
        for line in proc.stdout:
            pass  # suppress verbose output

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())
    try:
        start_backend()
        wait_backend()
        start_frontend()
        print()
        print("=" * 60)
        print(f"  Backend  : http://localhost:{BACKEND_PORT}")
        print(f"  Frontend : http://localhost:5173")
        print("=" * 60)
        print("  Press Ctrl+C to stop.")
        threading.Thread(target=pipe, args=(backend_proc, "backend"), daemon=True).start()
        threading.Thread(target=pipe, args=(frontend_proc, "frontend"), daemon=True).start()
        while backend_proc.poll() is None and frontend_proc.poll() is None:
            time.sleep(0.5)
        cleanup()
    except Exception as e:
        print(f"Fatal: {e}")
        cleanup()
        sys.exit(1)
