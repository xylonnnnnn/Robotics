"""Run the same zero-frequency experiment against broken and fixed patrol."""

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from turtlesim.msg import Pose

ROOT = Path(__file__).resolve().parents[1]


class Observer(Node):
    def __init__(self):
        super().__init__('pr04_observer')
        self.samples = []
        self.pose = None
        self.create_subscription(Twist, '/turtle1/cmd_vel', self.on_command, 10)
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)

    def on_command(self, message):
        self.samples.append((time.monotonic(), message.linear.x, message.angular.z))

    def on_pose(self, message):
        self.pose = message


def spin_for(node, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=max(0.0, min(0.05, end - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-defect', action='store_true')
    parser.add_argument('--defect-commit', help='Load historical parameters.py in an isolated package')
    args = parser.parse_args()
    out = Path(os.environ.get('PR04_EVIDENCE_DIR', ROOT / 'evidence/pr04'))
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['ROS_DOMAIN_ID'] = os.environ.get('PR04_DOMAIN_ID', '221')
    env['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['ROS_DOMAIN_ID'] = env['ROS_DOMAIN_ID']
    processes = []
    transcript = []
    temporary = tempfile.TemporaryDirectory(prefix='pr04-defect-')
    if args.defect_commit:
        assert args.expect_defect
        package = Path(temporary.name) / 'patrol'
        shutil.copytree(ROOT / 'src/patrol/patrol', package,
                        ignore=shutil.ignore_patterns('__pycache__'))
        historical = subprocess.check_output(
            ['git', 'show', f'{args.defect_commit}:PRO4/src/patrol/patrol/parameters.py'],
            cwd=ROOT, text=True)
        (package / 'parameters.py').write_text(historical)
        env['PYTHONPATH'] = temporary.name + os.pathsep + env.get('PYTHONPATH', '')

    def start(name, command):
        transcript.append('$ ' + ' '.join(command))
        with (out / f'{name}.txt').open('w') as stream:
            process = subprocess.Popen(command, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(process)
        return process

    def command(command, timeout=25):
        try:
            result = subprocess.run(command, env=env, text=True, capture_output=True,
                                    timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            # A crashed parameter server cannot answer the outstanding CLI request.
            stdout = error.stdout or b''
            stderr = error.stderr or b''
            if isinstance(stdout, bytes):
                stdout = stdout.decode()
            if isinstance(stderr, bytes):
                stderr = stderr.decode()
            result = subprocess.CompletedProcess(command, 124, stdout,
                                                  stderr + 'CLI timeout\n')
        result.stdout += result.stderr
        result.stderr = ''
        text = f"$ {' '.join(command)}\nexit={result.returncode}\n{result.stdout}{result.stderr}"
        transcript.append(text)
        print(text, flush=True)
        return result

    def rate(label, target):
        # Drain samples accumulated while CLI commands were running.
        spin_for(observer, 0.6)
        observer.samples.clear()
        begin = time.monotonic()
        spin_for(observer, 4.0)
        elapsed = time.monotonic() - begin
        samples = list(observer.samples)
        hz = len(samples) / elapsed
        result = {'messages': len(samples), 'seconds': elapsed, 'hz': hz,
                  'last_twist': list(samples[-1][1:]) if samples else None}
        transcript.append(f'{label}: {json.dumps(result)}')
        print(label, result, flush=True)
        assert abs(hz - target) < max(0.7, target * 0.15), (label, result)
        return result

    rclpy.init()
    observer = Observer()
    try:
        start('turtlesim', ['ros2', 'run', 'turtlesim', 'turtlesim_node'])
        for _ in range(150):
            spin_for(observer, 0.1)
            if observer.pose is not None:
                break
        assert observer.pose is not None, 'No turtlesim pose'
        patrol = start('patrol', ['ros2', 'run', 'patrol', 'patrol', '--ros-args',
                                  '-r', 'cmd_vel:=/turtle1/cmd_vel'])
        for _ in range(150):
            spin_for(observer, 0.1)
            if observer.samples:
                break
        assert observer.samples, 'No patrol commands'
        result = {'initial': rate('initial 10 Hz', 10.0)}
        assert command(['ros2', 'topic', 'type', '/turtle1/pose']).returncode == 0
        changed = command(['ros2', 'param', 'set', '/patrol', 'publish_hz', '5.0'])
        assert 'Set parameter successful' in changed.stdout
        result['changed'] = rate('changed 5 Hz', 5.0)
        assert result['changed']['last_twist'] == [0.5, 0.3]
        zero = command(['ros2', 'param', 'set', '/patrol', 'publish_hz', '0.0'], timeout=10)
        if args.expect_defect:
            patrol.wait(timeout=10)
            spin_for(observer, 0.8)
            result['after_zero'] = rate('broken stream', 0.0)
            log = (out / 'patrol.txt').read_text()
            assert 'ZeroDivisionError' in log and patrol.returncode != 0, log
            result['exit_code'] = patrol.returncode
            result['defect_reproduced'] = True
        else:
            assert 'Setting parameter failed' in zero.stdout
            assert 'publish_hz must be in [1.0, 30.0]' in zero.stdout
            get = command(['ros2', 'param', 'get', '/patrol', 'publish_hz'])
            assert '5.0' in get.stdout
            assert patrol.poll() is None
            result['after_zero'] = rate('preserved 5 Hz after zero', 5.0)
            for value in ('-1.0', '.nan'):
                rejected = command(['ros2', 'param', 'set', '/patrol', 'publish_hz', value])
                assert 'Setting parameter failed' in rejected.stdout
            for name, value in [('linear_speed', '0.8'), ('turn_rate', '-0.6')]:
                accepted = command(['ros2', 'param', 'set', '/patrol', name, value])
                assert 'Set parameter successful' in accepted.stdout
            before = (observer.pose.x, observer.pose.y)
            result['speeds'] = rate('new speeds, still 5 Hz', 5.0)
            after = (observer.pose.x, observer.pose.y)
            assert result['speeds']['last_twist'] == [0.8, -0.6]
            assert sum((a-b)**2 for a, b in zip(before, after)) > 0.01
            result['motion'] = {'before': before, 'after': after}
            clear = command(['ros2', 'service', 'call', '/clear', 'std_srvs/srv/Empty', '{}'])
            assert clear.returncode == 0 and 'response:' in clear.stdout
            actions = command(['ros2', 'action', 'list', '-t'])
            assert actions.returncode == 0
            assert '/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]' in actions.stdout
            result['defect_fixed'] = True
        (out / 'capture-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        temporary.cleanup()
        (out / 'commands.txt').write_text('\n\n'.join(transcript) + '\n')


if __name__ == '__main__':
    main()
