"""Capture the PR01 ROS graph experiment from an installed Jazzy environment.

Run inside Linux with ROS sourced and turtlesim plus Xvfb installed. The script
records raw CLI output and never substitutes expected output for observations.
"""

from __future__ import annotations

import json
import os
import pty
import shutil
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "pr01"
OUT.mkdir(parents=True, exist_ok=True)
BASE_DOMAIN = int(os.environ.get("PR01_DOMAIN_ID", "216"))
OTHER_DOMAIN = BASE_DOMAIN + 1
PROCESSES: list[subprocess.Popen] = []


def env(domain: int) -> dict[str, str]:
    return {**os.environ, "ROS_DOMAIN_ID": str(domain), "DISPLAY": ":99"}


def run(name: str, args: list[str], domain: int, timeout: int = 20) -> dict:
    try:
        result = subprocess.run(args, env=env(domain), text=True,
                                capture_output=True, timeout=timeout, check=False)
        status, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        status = 124
        output = (exc.stdout or b"") + (exc.stderr or b"")
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
    (OUT / f"{name}.txt").write_text(
        f"$ {' '.join(args)}\nROS_DOMAIN_ID={domain}\nexit={status}\n{output}",
        encoding="utf-8",
    )
    return {"command": args, "domain": domain, "exit": status, "output": output}


def start(args: list[str], domain: int, logfile: str) -> subprocess.Popen:
    stream = (OUT / logfile).open("w", encoding="utf-8")
    proc = subprocess.Popen(args, env=env(domain), stdout=stream,
                            stderr=subprocess.STDOUT, start_new_session=True)
    stream.close()
    PROCESSES.append(proc)
    return proc


def teleop(domain: int) -> tuple[subprocess.Popen, int]:
    master, slave = pty.openpty()
    log = (OUT / f"teleop-{domain}.txt").open("wb")
    proc = subprocess.Popen(["ros2", "run", "turtlesim", "turtle_teleop_key"],
                            env=env(domain), stdin=slave, stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    os.close(slave)
    log.close()
    PROCESSES.append(proc)
    time.sleep(2)
    for _ in range(5):
        os.write(master, b"\x1b[A")
        time.sleep(0.15)
    return proc, master


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def main() -> None:
    for command in ("ros2", "Xvfb"):
        if not shutil.which(command):
            raise SystemExit(f"Missing {command}")
    xvfb = start(["Xvfb", ":99", "-screen", "0", "1024x768x24", "-nolisten", "tcp"],
                 BASE_DOMAIN, "xvfb.txt")
    try:
        time.sleep(2)
        sim = start(["ros2", "run", "turtlesim", "turtlesim_node"],
                    BASE_DOMAIN, "turtlesim.txt")
        for _ in range(15):
            nodes = run("nodes-wait", ["ros2", "node", "list", "--no-daemon", "--spin-time", "2"],
                        BASE_DOMAIN)
            if "/turtlesim" in nodes["output"]:
                break
            time.sleep(1)
        else:
            raise SystemExit("turtlesim did not become visible")

        teleop_a, fd_a = teleop(BASE_DOMAIN)
        run("doctor", ["ros2", "doctor", "--report"], BASE_DOMAIN, 45)
        run("nodes-before", ["ros2", "node", "list", "--no-daemon", "--spin-time", "2"], BASE_DOMAIN)
        run("topics-before", ["ros2", "topic", "list", "-t"], BASE_DOMAIN)
        run("node-info", ["ros2", "node", "info", "/turtlesim"], BASE_DOMAIN)
        pose_type = run("pose-type", ["ros2", "topic", "type", "/turtle1/pose"], BASE_DOMAIN)["output"].strip()
        if not pose_type:
            raise SystemExit("Pose type not found")
        run("pose-before", ["ros2", "topic", "echo", "/turtle1/pose", "--once"], BASE_DOMAIN)
        run("pose-hz", ["ros2", "topic", "hz", "/turtle1/pose"], BASE_DOMAIN, 12)

        stop(teleop_a)
        os.close(fd_a)
        teleop_b, fd_b = teleop(OTHER_DOMAIN)
        run("nodes-broken", ["ros2", "node", "list", "--no-daemon", "--spin-time", "2"], OTHER_DOMAIN)
        broken = run("pose-broken", ["ros2", "topic", "echo", "/turtle1/pose", pose_type, "--once"], OTHER_DOMAIN, 5)
        run("pose-original-during-break", ["ros2", "topic", "echo", "/turtle1/pose", "--once"], BASE_DOMAIN)

        stop(teleop_b)
        os.close(fd_b)
        teleop_fixed, fd_fixed = teleop(BASE_DOMAIN)
        run("nodes-fixed", ["ros2", "node", "list", "--no-daemon", "--spin-time", "2"], BASE_DOMAIN)
        fixed = run("pose-fixed", ["ros2", "topic", "echo", "/turtle1/pose", pose_type, "--once"], BASE_DOMAIN, 5)
        stop(teleop_fixed)
        os.close(fd_fixed)
        (OUT / "capture-summary.json").write_text(json.dumps({
            "base_domain": BASE_DOMAIN,
            "other_domain": OTHER_DOMAIN,
            "pose_type": pose_type,
            "broken_exit": broken["exit"],
            "fixed_exit": fixed["exit"],
        }, indent=2) + "\n", encoding="utf-8")
        print((OUT / "capture-summary.json").read_text())
        stop(sim)
    finally:
        for proc in reversed(PROCESSES):
            stop(proc)


if __name__ == "__main__":
    main()
