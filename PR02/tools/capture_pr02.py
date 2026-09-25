"""Record the PR02 topic-name defect and correction in a real ROS graph."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "pr02"
OUT.mkdir(parents=True, exist_ok=True)
DOMAIN = int(os.environ.get("PR02_DOMAIN_ID", "218"))
PROCESSES: list[subprocess.Popen] = []
MESSAGE = "{linear: {x: 1.0}, angular: {z: 0.5}}"


def env() -> dict[str, str]:
    return {**os.environ, "ROS_DOMAIN_ID": str(DOMAIN), "DISPLAY": ":98"}


def run(name: str, args: list[str], timeout: int = 20) -> dict:
    try:
        result = subprocess.run(args, env=env(), text=True,
                                capture_output=True, timeout=timeout, check=False)
        status, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        status = 124
        output = (exc.stdout or b"") + (exc.stderr or b"")
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
    (OUT / f"{name}.txt").write_text(
        f"$ {' '.join(args)}\nROS_DOMAIN_ID={DOMAIN}\nexit={status}\n{output}",
        encoding="utf-8",
    )
    return {"exit": status, "output": output}


def start(args: list[str], name: str) -> subprocess.Popen:
    stream = (OUT / f"{name}.txt").open("w", encoding="utf-8")
    proc = subprocess.Popen(args, env=env(), stdout=stream,
                            stderr=subprocess.STDOUT, start_new_session=True)
    stream.close()
    PROCESSES.append(proc)
    return proc


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def pose(name: str) -> dict[str, float]:
    output = run(name, ["ros2", "topic", "echo", "/turtle1/pose", "--once"])
    if output["exit"] != 0:
        raise RuntimeError(f"Cannot obtain {name}: {output['output']}")
    result = {}
    for key in ("x", "y", "theta", "linear_velocity", "angular_velocity"):
        match = re.search(rf"^{key}:\s*([-\d.eE+]+)", output["output"], re.MULTILINE)
        if match:
            result[key] = float(match.group(1))
    return result


def main() -> None:
    for command in ("ros2", "Xvfb"):
        if not shutil.which(command):
            raise SystemExit(f"Missing {command}")
    start(["Xvfb", ":98", "-screen", "0", "1024x768x24", "-nolisten", "tcp"], "xvfb")
    try:
        time.sleep(2)
        launch = start(["ros2", "launch", "turtle_bringup", "sim.launch.py"], "launch")
        for _ in range(15):
            nodes = run("nodes-wait", ["ros2", "node", "list", "--no-daemon", "--spin-time", "2"])
            if "/turtlesim" in nodes["output"]:
                break
            time.sleep(1)
        else:
            raise SystemExit("Launched turtlesim did not become visible")
        run("nodes", ["ros2", "node", "list", "--no-daemon", "--spin-time", "2"])
        run("twist-interface", ["ros2", "interface", "show", "geometry_msgs/msg/Twist"])
        run("pose-type", ["ros2", "topic", "type", "/turtle1/pose"])
        run("command-type", ["ros2", "topic", "type", "/turtle1/cmd_vel"])
        before = pose("pose-before")

        wrong = start(["ros2", "topic", "pub", "--rate", "1",
                       "--wait-matching-subscriptions", "0", "/cmd_vel",
                       "geometry_msgs/msg/Twist", MESSAGE], "publisher-wrong")
        time.sleep(4)
        run("wrong-topic-info", ["ros2", "topic", "info", "/cmd_vel", "--verbose"])
        run("expected-topic-info-during-break", ["ros2", "topic", "info", "/turtle1/cmd_vel", "--verbose"])
        broken = pose("pose-broken")
        stop(wrong)

        correct = start(["ros2", "topic", "pub", "--rate", "1",
                         "--wait-matching-subscriptions", "0", "/turtle1/cmd_vel",
                         "geometry_msgs/msg/Twist", MESSAGE], "publisher-fixed")
        time.sleep(4)
        run("fixed-topic-info", ["ros2", "topic", "info", "/turtle1/cmd_vel", "--verbose"])
        fixed = pose("pose-fixed")
        stop(correct)
        run("stop-command", ["ros2", "topic", "pub", "--once", "/turtle1/cmd_vel",
                             "geometry_msgs/msg/Twist", "{}"])
        stop(launch)
        summary = {"domain": DOMAIN, "before": before, "broken": broken, "fixed": fixed}
        (OUT / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
    finally:
        for proc in reversed(PROCESSES):
            stop(proc)


if __name__ == "__main__":
    main()
