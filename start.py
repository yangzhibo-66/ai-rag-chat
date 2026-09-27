import os, shutil, signal, socket, subprocess, sys, threading, time, urllib.request, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_URL = "http://localhost:5173"

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

def venv_python():
    candidate = BACKEND / ".venv" / ("Scripts\\python.exe" if sys.platform == "win32" else "bin/python")
    return str(candidate)

def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def ensure_backend_env():
    """Fresh clone: create backend/.env from .env.example so required settings exist."""
    env = BACKEND / ".env"
    if env.exists():
        return
    example = BACKEND / ".env.example"
    if example.exists():
        shutil.copyfile(example, env)
        print("[env] created backend/.env from .env.example")
        print("[env] NOTICE: fill in OPENAI_API_KEY / DASHSCOPE_API_KEY / SECRET_KEY for full features;")
        print("[env] the backend still starts without them (AI features degrade).")
    else:
        print("[env] WARN: no backend/.env or backend/.env.example found - backend may fail to start.")

def ensure_venv():
    if Path(venv_python()).is_file():
        print("[deps] backend .venv exists; skipping venv creation.")
        return
    print("[deps] creating backend/.venv (first run only) ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(BACKEND / ".venv")])

def install_deps():
    ensure_venv()
    vp = venv_python()
    if Path(vp).is_file():
        print("[deps] installing backend requirements (first run may take minutes) ...")
        subprocess.check_call([vp, "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])
    else:
        print("[deps] WARN: venv python not found; skipping backend pip install.")
    if not (FRONTEND / "node_modules").exists():
        print("[deps] installing frontend dependencies (npm install) ...")
        subprocess.check_call([npm(), "install"], cwd=str(FRONTEND))
    else:
        print("[deps] frontend node_modules exists; skipping npm install.")

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
    if shutil.which(npm()) is None:
        print("[frontend] WARN: npm not found - frontend will NOT start. Install Node.js and rerun.")
        return
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

def open_browser():
    try:
        webbrowser.open(FRONTEND_URL)
    except Exception as e:
        print(f"[browser] could not open automatically: {e} - visit {FRONTEND_URL}")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    skip_install = "--skip-install" in sys.argv or os.getenv("SKIP_INSTALL", "").strip().lower() in ("1", "true")

    ensure_backend_env()

    if port_in_use(BACKEND_PORT):
        print(f"[backend] port {BACKEND_PORT} is already in use - another backend instance may be running.")
        print("[backend] stop it first (or set BACKEND_PORT to another port) and retry.")
        sys.exit(1)

    try:
        if not skip_install:
            install_deps()
        else:
            print("[deps] SKIP_INSTALL set - skipping dependency installation.")

        start_backend()
        wait_backend()
        start_frontend()
        print()
        print("=" * 60)
        print(f"  Backend  : http://localhost:{BACKEND_PORT}")
        print(f"  Frontend : {FRONTEND_URL}")
        print("=" * 60)
        print("  Press Ctrl+C to stop.")
        threading.Timer(3.0, open_browser).start()
        threading.Thread(target=pipe, args=(backend_proc, "backend"), daemon=True).start()
        if frontend_proc:
            threading.Thread(target=pipe, args=(frontend_proc, "frontend"), daemon=True).start()
        while backend_proc.poll() is None and (frontend_proc is None or frontend_proc.poll() is None):
            time.sleep(0.5)
        cleanup()
    except Exception as e:
        print(f"Fatal: {e}")
        cleanup()
        sys.exit(1)
