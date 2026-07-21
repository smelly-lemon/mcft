"""Paired era-E vs era-F ablation orchestrator (runs ON the Studio).

Owns the whole stack for the duration of a run: pauses the live show
(watchdog stands down via /tmp/mcft_maintenance), then for each episode
restores the era-E end world onto the EVAL server, configures Mindcraft
for the arm (E = intent off, F = intent on + pristine graph), lets the
bots play for a fixed wall-clock budget, and harvests steps/journals.
Arms alternate E,F,E,F so time-of-day effects cancel. On exit (success,
failure, or Ctrl-C) it restores the live configuration and relaunches
the show.

Python 3.9 stdlib only (the Studio has no mcft install).

Residual risk: a kill -9 skips the finally-restore, leaving settings.js
pointed at the eval server until the 6h-stale maintenance flag clears.
Recovery: copy each file in ablation/run-*/stash/ back to its live path
(the STASH dict below maps stash name -> live path), then restart the stack.

Usage (on tim4, from ~/Desktop/mindcraft):
    nohup python3 ops/ablation_runner.py --pairs 3 --minutes 35 \
        >> ablation/run.log 2>&1 &

Selftest (safe anywhere, mutates nothing):
    python3 ops/ablation_runner.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import struct
import subprocess
import sys
import tarfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Studio runs Python 3.9; datetime.UTC arrived in 3.11
UTC = timezone.utc  # noqa: UP017

HOME = Path.home()
MC = HOME / "Desktop" / "mindcraft"
EVAL = HOME / "Desktop" / "mc-eval-server"
ARCHIVES = HOME / "Backups" / "mcft"
WORLD_TAR = ARCHIVES / "world-eraE-end-2026-07-21.tgz"
FLAG = Path("/tmp/mcft_maintenance")
NODE_BIN = HOME / ".nvm" / "versions" / "node" / "v20.20.2" / "bin"
EVAL_GAME_PORT = 25567
BOTS = ("Sable", "Jolt")
PROFILE_IDS = ("sable", "jolt")

ASSETS = MC / "ablation" / "assets"
# stash name -> live path; distinct names because two memory.json + profile
# sable.json would collide in a flat stash dir
STASH = {
    "settings.js": MC / "settings.js",
    "mcft_intent.json": MC / "mcft_intent.json",
    "profile_sable.json": MC / "profiles" / "sable.json",
    "profile_jolt.json": MC / "profiles" / "jolt.json",
    "journal_Sable.json": MC / "bots" / "Sable" / "memory.json",
    "journal_Jolt.json": MC / "bots" / "Jolt" / "memory.json",
    "server.properties": EVAL / "server.properties",
}


def log(msg: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{stamp} {msg}", flush=True)


# ---------- text mutations (selftest-covered) ----------


def mutate_settings(text: str, port: int, intent: bool) -> str:
    out, n1 = re.subn(r'("port":\s*)\d+', rf"\g<1>{port}", text, count=1)
    flag = "true" if intent else "false"
    out, n2 = re.subn(
        r'("mcft_intent":\s*)(true|false)',
        rf"\g<1>{flag}",
        out,
        count=1,
    )
    if n1 != 1 or n2 != 1:
        raise RuntimeError(f"settings.js mutation failed (port={n1}, intent={n2})")
    return out


def mutate_properties(text: str, level_name: str) -> str:
    out, n = re.subn(r"(?m)^level-name=.*$", f"level-name={level_name}", text, count=1)
    if n != 1:
        raise RuntimeError("server.properties level-name mutation failed")
    return out


# ---------- rcon ----------


def eval_props() -> dict:
    props = {}
    for line in (EVAL / "server.properties").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            props[k] = v
    return props


def rcon(command: str, timeout: float = 5.0) -> str:
    props = eval_props()
    sock = socket.create_connection(("127.0.0.1", int(props["rcon.port"])), timeout=timeout)
    try:

        def send(rid: int, ptype: int, body: str) -> None:
            payload = struct.pack("<ii", rid, ptype) + body.encode() + b"\x00\x00"
            sock.sendall(struct.pack("<i", len(payload)) + payload)

        def recv() -> tuple[int, str]:
            raw = b""
            while len(raw) < 4:
                chunk = sock.recv(4 - len(raw))
                if not chunk:
                    raise ConnectionError("rcon closed")
                raw += chunk
            (length,) = struct.unpack("<i", raw)
            data = b""
            while len(data) < length:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    raise ConnectionError("rcon closed")
                data += chunk
            rid = struct.unpack("<i", data[:4])[0]
            return rid, data[8:-2].decode(errors="replace")

        send(1, 3, props["rcon.password"])
        rid, _ = recv()
        if rid == -1:
            raise PermissionError("rcon auth failed")
        send(2, 2, command)
        _, body = recv()
        return body
    finally:
        sock.close()


# ---------- process management ----------


def stop_mindcraft() -> None:
    subprocess.run(["pkill", "-f", "init_agent.js"], check=False)
    subprocess.run(["pkill", "-f", "node main.js"], check=False)
    time.sleep(4)


def start_mindcraft(logfile: Path) -> None:
    env = dict(**__import__("os").environ)
    env["PATH"] = f"{NODE_BIN}:{env['PATH']}"
    with open(logfile, "a") as fh:
        subprocess.Popen(
            [str(NODE_BIN / "node"), "main.js"],
            cwd=str(MC),
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )


def start_eval_server() -> subprocess.Popen:
    jar = next(EVAL.glob("paper-*.jar"))
    with open(EVAL / "console.log", "a") as fh:
        proc = subprocess.Popen(
            ["/usr/bin/java", "-Xms2G", "-Xmx6G", "-jar", jar.name, "nogui"],
            cwd=str(EVAL),
            stdout=fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"eval server exited early (code {proc.returncode})")
        try:
            rcon("list", timeout=3)
            log("eval server up")
            return proc
        except Exception:
            time.sleep(3)
    proc.terminate()
    raise RuntimeError("eval server did not accept RCON within 180s")


def stop_eval_server(proc: subprocess.Popen | None) -> None:
    try:
        rcon("stop", timeout=3)
    except Exception:
        pass
    # never pkill by jar name here: the LIVE bot server runs the same jar
    if proc is not None:
        try:
            proc.wait(timeout=60)
            return
        except subprocess.TimeoutExpired:
            proc.kill()
    time.sleep(2)


# ---------- world / arm setup ----------


def restore_world() -> None:
    for name in ("worldE", "worldE_nether", "worldE_the_end"):
        shutil.rmtree(EVAL / name, ignore_errors=True)
    with tarfile.open(WORLD_TAR) as tar:
        tar.extractall(EVAL)
    log("worldE restored from era-E snapshot")


def configure_arm(arm: str, stash: Path) -> None:
    settings = (stash / "settings.js").read_text()
    (MC / "settings.js").write_text(mutate_settings(settings, EVAL_GAME_PORT, intent=(arm == "F")))
    for pid in PROFILE_IDS:
        shutil.copy2(ASSETS / f"profiles_{arm}" / f"{pid}.json", MC / "profiles" / f"{pid}.json")
    for bot in BOTS:
        shutil.copy2(ASSETS / "journals" / bot / "memory.json", MC / "bots" / bot / "memory.json")
    if arm == "F":
        shutil.copy2(ASSETS / "mcft_intent.seed.json", MC / "mcft_intent.json")


def preload_model() -> None:
    profile = json.loads((ASSETS / "profiles_F" / "sable.json").read_text())
    body = json.dumps(
        {
            "model": profile["model"]["model"],
            "messages": [{"role": "user", "content": "ok"}],
            "stream": False,
            "keep_alive": -1,
            "options": {"num_ctx": 16384, "num_predict": 1},
        }
    ).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=600).read()
    log("model preloaded")


# ---------- harvest ----------


def harvest(run_dir: Path, label: str, before: set[str], started: str) -> dict:
    episodes_dir = MC / "data" / "raw" / "episodes"
    new_eps = sorted(set(p.name for p in episodes_dir.iterdir()) - before)
    dest = run_dir / label
    dest.mkdir(parents=True, exist_ok=True)
    for ep in new_eps:
        # MOVE, not copy: ablation steps must never leak into the live-era corpus
        shutil.move(str(episodes_dir / ep), str(dest / ep))
    for bot in BOTS:
        src = MC / "bots" / bot / "memory.json"
        if src.exists():
            shutil.copy2(src, dest / f"journal_{bot}.json")
    if (MC / "mcft_intent.json").exists():
        shutil.copy2(MC / "mcft_intent.json", dest / "mcft_intent.final.json")
    manifest = {
        "label": label,
        "started": started,
        "ended": datetime.now(UTC).isoformat(),
        "episode_dirs": new_eps,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log(f"harvested {label}: {len(new_eps)} episode dirs")
    return manifest


# ---------- main flow ----------


def run(pairs: int, minutes: int) -> None:
    for path in [
        WORLD_TAR,
        ASSETS / "profiles_E" / "sable.json",
        ASSETS / "profiles_F" / "sable.json",
        ASSETS / "journals" / "Sable" / "memory.json",
        ASSETS / "mcft_intent.seed.json",
    ]:
        if not path.exists():
            raise SystemExit(f"missing asset: {path} (run staging first)")

    run_id = datetime.now().strftime("run-%Y%m%d-%H%M")
    run_dir = MC / "ablation" / run_id
    run_dir.mkdir(parents=True)
    stash = run_dir / "stash"
    stash.mkdir()

    log(f"=== ablation {run_id}: {pairs} pairs x {minutes} min per arm ===")
    FLAG.touch()
    for name, live in STASH.items():
        shutil.copy2(live, stash / name)

    log("pausing live show")
    stop_mindcraft()
    preload_model()

    (EVAL / "server.properties").write_text(
        mutate_properties((stash / "server.properties").read_text(), "worldE")
    )

    manifests = []
    eval_proc = None
    try:
        for i in range(pairs):
            for arm in ("E", "F"):
                label = f"{arm}{i + 1}"
                FLAG.touch()  # refresh so watchdog staleness never fires mid-run
                log(f"--- episode {label} ---")
                restore_world()
                eval_proc = start_eval_server()
                configure_arm(arm, stash)
                before = set(p.name for p in (MC / "data" / "raw" / "episodes").iterdir())
                started = datetime.now(UTC).isoformat()
                start_mindcraft(run_dir / f"mindcraft-{label}.log")
                time.sleep(minutes * 60)
                stop_mindcraft()
                manifests.append(harvest(run_dir, label, before, started))
                stop_eval_server(eval_proc)
                eval_proc = None
    finally:
        log("restoring live configuration")
        stop_mindcraft()
        if eval_proc is not None:
            stop_eval_server(eval_proc)
        for name, live in STASH.items():
            shutil.copy2(stash / name, live)
        (run_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "pairs": pairs,
                    "minutes": minutes,
                    "world_tar": WORLD_TAR.name,
                    "episodes": manifests,
                },
                indent=2,
            )
        )
        start_mindcraft(MC / "mindcraft.log")
        # hold the flag while agents spawn so the watchdog doesn't see a
        # half-started stack and churn-restart it
        time.sleep(120)
        FLAG.unlink(missing_ok=True)
        log("live show relaunched, watchdog re-armed")

    log(f"=== ablation {run_id} complete: {len(manifests)} episodes ===")


def selftest() -> None:
    settings = (MC / "settings.js").read_text()
    mutated = mutate_settings(settings, EVAL_GAME_PORT, intent=False)
    assert f'"port": {EVAL_GAME_PORT}' in mutated
    assert '"mcft_intent": false' in mutated
    mutated = mutate_settings(settings, EVAL_GAME_PORT, intent=True)
    assert '"mcft_intent": true' in mutated
    props = (EVAL / "server.properties").read_text()
    assert "level-name=worldE" in mutate_properties(props, "worldE")
    assert "level-name=arena" in mutate_properties(props, "arena")
    for path in [WORLD_TAR, *STASH.values()]:
        assert path.exists(), f"missing: {path}"
    print("selftest OK: mutations valid, stash files and world tar present")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=3)
    parser.add_argument("--minutes", type=int, default=35)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        sys.exit(0)
    run(args.pairs, args.minutes)
