#!/usr/bin/env python3
"""Cross-platform setup/run helper for the Dark Patterns ABM monorepo.

Replaces the old setup-local / run-local .bat / .ps1 / .sh trios with a single
script that works identically on Windows, macOS, and Linux.

Usage (from the repository root):

    python dev.py setup    # create backend venv, install deps, write frontend/.env
    python dev.py run      # start backend (:8000) and frontend (:5173); Ctrl+C stops both

On macOS/Linux you can also run it as ./dev.py once it is executable.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = os.name == "nt"

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
API_BASE = "http://localhost:8000/api"
PORTS = (8000, 5173)


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def venv_python() -> Path:
    """Path to the Python interpreter inside backend/.venv for this OS."""
    if IS_WINDOWS:
        return BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / ".venv" / "bin" / "python"


def npm_invocation(arg_string: str) -> tuple:
    """Return (command, shell) for invoking npm on this OS.

    On Windows npm is a .cmd shim that CreateProcess cannot launch directly,
    so we go through the shell; on Unix a plain argv list is enough.
    """
    if IS_WINDOWS:
        return (f"npm {arg_string}", True)
    return (["npm", *arg_string.split()], False)


def require_npm() -> None:
    if shutil.which("npm") is None:
        sys.exit("npm not found on PATH. Install Node.js 20+ (https://nodejs.org/).")


def run_checked(cmd, cwd: Path | None = None, shell: bool = False) -> None:
    """Run a command to completion, aborting the script on a non-zero exit."""
    result = subprocess.run(cmd, cwd=(str(cwd) if cwd else None), shell=shell)
    if result.returncode != 0:
        printable = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
        sys.exit(f"Command failed (exit {result.returncode}): {printable}")


def set_env_var(path: Path, key: str, value: str) -> None:
    """Set or append KEY=value in a .env file, preserving other lines."""
    line = f"{key}={value}"
    if not path.exists():
        path.write_text(line + "\n", encoding="utf-8")
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, existing in enumerate(lines):
        if existing.startswith(f"{key}="):
            lines[i] = line
            break
    else:
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Process management (run)
# --------------------------------------------------------------------------- #
def spawn(cmd, cwd: Path, shell: bool = False) -> subprocess.Popen:
    """Start a long-running child in its own process group/session.

    Isolating the child lets us later kill the whole tree (npm -> node -> vite,
    uvicorn reloader -> worker) and keeps the parent's Ctrl+C from racing it.
    """
    kwargs = {"cwd": str(cwd), "shell": shell}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def terminate(proc: subprocess.Popen | None) -> None:
    """Kill a child process and all of its descendants."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass


def free_port(port: int) -> None:
    """Best-effort: kill whatever is listening on a TCP port (plus children).

    Stale dev servers love to squat on 8000/5173 after a hard crash; this clears
    them before we start so we always own the ports. Silently skips if the
    platform tools aren't available.
    """
    try:
        if IS_WINDOWS:
            out = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True
            ).stdout
            for line in out.splitlines():
                parts = line.split()
                if (
                    len(parts) >= 5
                    and parts[3] == "LISTENING"
                    and parts[1].endswith(f":{port}")
                    and parts[4].isdigit()
                ):
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", parts[4]],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
        else:
            lsof = shutil.which("lsof")
            if lsof:
                out = subprocess.run(
                    [lsof, "-ti", f"tcp:{port}"], capture_output=True, text=True
                ).stdout
                for pid in out.split():
                    if pid.isdigit():
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except OSError:
                            pass
            elif shutil.which("fuser"):
                subprocess.run(
                    ["fuser", "-k", f"{port}/tcp"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_setup(_args: argparse.Namespace) -> None:
    print("Setting up backend...")
    if not (BACKEND_DIR / ".venv").exists():
        print("Creating virtual environment...")
        run_checked([sys.executable, "-m", "venv", ".venv"], cwd=BACKEND_DIR)

    py = venv_python()
    if not py.exists():
        sys.exit(f"Virtual environment creation failed or incomplete: {py}")

    print("Upgrading pip...")
    run_checked([str(py), "-m", "pip", "install", "--upgrade", "pip"], cwd=BACKEND_DIR)

    print("Installing Python dependencies...")
    run_checked(
        [str(py), "-m", "pip", "install", "-r", "requirements.txt"], cwd=BACKEND_DIR
    )

    print("Setting up frontend...")
    require_npm()
    print("Installing npm dependencies...")
    cmd, shell = npm_invocation("install")
    run_checked(cmd, cwd=FRONTEND_DIR, shell=shell)

    env_file = FRONTEND_DIR / ".env"
    env_example = FRONTEND_DIR / ".env.example"
    if env_example.exists() and not env_file.exists():
        print("Copying .env.example to .env...")
        shutil.copyfile(env_example, env_file)
    set_env_var(env_file, "VITE_API_BASE", API_BASE)

    print("Local setup complete.")


def cmd_run(_args: argparse.Namespace) -> None:
    py = venv_python()
    if not py.exists():
        sys.exit(
            f"Backend venv not found at {py}\nRun 'python dev.py setup' first."
        )
    require_npm()

    print(f"Clearing ports {PORTS[0]} and {PORTS[1]}...")
    for port in PORTS:
        free_port(port)

    backend = frontend = None
    try:
        print("Starting backend...")
        backend = spawn([str(py), "-m", "app.dev_server"], BACKEND_DIR)
        print(f"Backend started (PID: {backend.pid})")

        print("Starting frontend...")
        fcmd, fshell = npm_invocation("run dev")
        frontend = spawn(fcmd, FRONTEND_DIR, shell=fshell)
        print(f"Frontend started (PID: {frontend.pid})")

        print()
        print(f"Backend:  {BACKEND_URL}")
        print(f"Frontend: {FRONTEND_URL}")
        print("Press Ctrl+C to stop both.")
        print()

        while True:
            if backend.poll() is not None or frontend.poll() is not None:
                print("One or more services stopped.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        terminate(frontend)
        terminate(backend)
        # Belt and suspenders, in case anything was re-parented.
        for port in PORTS:
            free_port(port)
        print("Services stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dev.py",
        description="Cross-platform setup/run helper for the Dark Patterns ABM monorepo.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="Create the backend venv, install deps, write frontend/.env").set_defaults(
        func=cmd_setup
    )
    sub.add_parser("run", help="Start the backend (:8000) and frontend (:5173)").set_defaults(
        func=cmd_run
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
