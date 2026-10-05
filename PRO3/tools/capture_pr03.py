"""Reproduce the PR03 topic-name defect and its remap in a real ROS graph."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from turtlesim.msg import Pose


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('PR03_EVIDENCE_DIR', ROOT / 'evidence' / 'pr03'))
OUT.mkdir(parents=True, exist_ok=True)
DOMAIN = os.environ.get('PR03_DOMAIN_ID', '220')
PROCESSES: list[subprocess.Popen] = []


class Observer(Node):
    def __init__(self) -> None:
        super().__init__('pr03_observer')
        self.pose: Pose | None = None
        self.last_command: Twist | None = None
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
        self.wrong_times: list[float] = []
        self.fixed_times: list[float] = []

    def on_pose(self, message: Pose) -> None:
        self.pose = message

    def on_wrong_command(self, message: Twist) -> None:
        self.wrong_times.append(time.monotonic())
        self.last_command = message

    def on_fixed_command(self, message: Twist) -> None:
        self.fixed_times.append(time.monotonic())
        self.last_command = message


def spin_for(node: Node, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=min(0.1, end - time.monotonic()))


def pose_dict(pose: Pose | None) -> dict[str, float] | None:
    if pose is None:
        return None
    return {'x': pose.x, 'y': pose.y, 'theta': pose.theta}


def start(name: str, args: list[str]) -> subprocess.Popen:
    stream = (OUT / f'{name}.txt').open('w', encoding='utf-8')
    process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                               start_new_session=True, env=os.environ.copy())
    stream.close()
    PROCESSES.append(process)
    return process


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGINT)
    try:
        process.wait(timeout=6)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=6)


def command(name: str, args: list[str]) -> str:
    result = subprocess.run(args, text=True, capture_output=True, timeout=20,
                            env=os.environ.copy(), check=False)
    content = f"$ {' '.join(args)}\nexit={result.returncode}\n{result.stdout}{result.stderr}"
    (OUT / f'{name}.txt').write_text(content, encoding='utf-8')
    if result.returncode != 0:
        raise RuntimeError(content)
    return content


def wait_for_topic_info(name: str, topic: str) -> str:
    for attempt in range(10):
        try:
            return command(name, ['ros2', 'topic', 'info', topic])
        except RuntimeError:
            if attempt == 9:
                raise
            time.sleep(1)
    raise AssertionError('unreachable')


def metrics(times: list[float], start_time: float, end_time: float) -> dict[str, float]:
    selected = [stamp for stamp in times if start_time <= stamp <= end_time]
    return {'messages': len(selected), 'seconds': end_time - start_time,
            'hz': len(selected) / (end_time - start_time)}


def main() -> None:
    os.environ['ROS_DOMAIN_ID'] = DOMAIN
    os.environ['DISPLAY'] = ':98'
    start('xvfb', ['Xvfb', ':98', '-screen', '0', '1024x768x24', '-nolisten', 'tcp'])
    time.sleep(1)
    launch = start('turtlesim-launch', ['ros2', 'launch', 'turtle_bringup', 'sim.launch.py'])
    rclpy.init()
    observer = Observer()
    try:
        for _ in range(100):
            spin_for(observer, 0.1)
            if observer.pose is not None:
                break
        else:
            raise RuntimeError('No pose from turtlesim')
        initial_pose = pose_dict(observer.pose)
        command('pose-type', ['ros2', 'topic', 'type', '/turtle1/pose'])
        wrong = start('patrol-wrong', ['ros2', 'run', 'patrol', 'patrol'])
        spin_for(observer, 2)
        wrong_info = wait_for_topic_info('wrong-topic-info', '/cmd_vel')
        expected_info = wait_for_topic_info('expected-topic-info', '/turtle1/cmd_vel')
        wrong_subscription = observer.create_subscription(
            Twist, '/cmd_vel', observer.on_wrong_command, 10)
        wrong_before = pose_dict(observer.pose)
        wrong_start = time.monotonic()
        spin_for(observer, 10)
        wrong_end = time.monotonic()
        wrong_after = pose_dict(observer.pose)
        wrong_rate = metrics(observer.wrong_times, wrong_start, wrong_end)
        observer.destroy_subscription(wrong_subscription)
        stop(wrong)

        fixed = start('patrol-fixed', ['ros2', 'run', 'patrol', 'patrol',
                                      '--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel'])
        spin_for(observer, 2)
        fixed_info = wait_for_topic_info('fixed-topic-info', '/turtle1/cmd_vel')
        fixed_subscription = observer.create_subscription(
            Twist, '/turtle1/cmd_vel', observer.on_fixed_command, 10)
        fixed_before = pose_dict(observer.pose)
        fixed_start = time.monotonic()
        spin_for(observer, 10)
        fixed_end = time.monotonic()
        fixed_after = pose_dict(observer.pose)
        fixed_rate = metrics(observer.fixed_times, fixed_start, fixed_end)
        observer.destroy_subscription(fixed_subscription)
        stop(fixed)
        stop(launch)

        result = {
            'domain': int(DOMAIN),
            'initial_pose': initial_pose,
            'wrong': {'before': wrong_before, 'after': wrong_after,
                      'rate': wrong_rate, 'topic_info': wrong_info,
                      'expected_topic_info': expected_info},
            'fixed': {'before': fixed_before, 'after': fixed_after,
                      'rate': fixed_rate, 'topic_info': fixed_info},
        }
        (OUT / 'capture-summary.json').write_text(json.dumps(result, indent=2) + '\n',
                                                   encoding='utf-8')
        print(json.dumps(result, indent=2))
        assert 'Subscription count: 0' in wrong_info
        assert 'Publisher count: 0' in expected_info
        assert 'Subscription count: 1' in fixed_info
        assert wrong_rate['messages'] >= 80
        assert fixed_rate['messages'] >= 80
        assert abs(wrong_after['x'] - wrong_before['x']) < 0.02
        assert abs(wrong_after['y'] - wrong_before['y']) < 0.02
        assert abs(fixed_after['x'] - fixed_before['x']) > 0.1
    finally:
        observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for process in reversed(PROCESSES):
            stop(process)


if __name__ == '__main__':
    main()
