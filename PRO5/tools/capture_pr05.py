"""Exercise real launch, QoS mismatch, one MCAP recording and its replay."""

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.serialization import deserialize_message
import rosbag2_py
from turtlesim.msg import Pose
import yaml

ROOT = Path(__file__).resolve().parents[1]


def values(pose):
    return [pose.x, pose.y, pose.theta, pose.linear_velocity, pose.angular_velocity]


def main():
    out = Path(os.environ.get('PR05_EVIDENCE_DIR', ROOT / 'evidence/pr05')).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bag = out / 'bag'
    if bag.exists():
        raise FileExistsError(f'Refusing to overwrite {bag}; use a fresh evidence directory')
    os.environ['ROS_DOMAIN_ID'] = os.environ.get('PR05_DOMAIN_ID', '225')
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['PYTHONUNBUFFERED'] = '1'
    processes = []
    transcript = []
    before = []
    after = []
    rclpy.init()
    observer = Node('pr05_observer')
    samples = {'reliable': [], 'best_effort': []}
    for name, policy in [('reliable', ReliabilityPolicy.RELIABLE),
                         ('best_effort', ReliabilityPolicy.BEST_EFFORT)]:
        observer.create_subscription(
            Pose, '/robot_a/sensor_pose',
            lambda msg, key=name: samples[key].append(values(msg)),
            QoSProfile(depth=1000, reliability=policy))

    def spin(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(observer, timeout_sec=min(0.05, max(0., end-time.monotonic())))

    def start(label, command):
        transcript.append('$ ' + ' '.join(command))
        with (out / (label + '.txt')).open('w') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        processes.append(process)
        return process

    def stop(process):
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                raise AssertionError('Process group did not shut down cleanly')

    def command(args, target, expected=0):
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=35)
        text = f"$ {' '.join(args)}\n{result.stdout}\nexit={result.returncode}\n"
        target.append(text)
        transcript.append(text)
        assert result.returncode == expected, text
        return result.stdout

    def launch(label, reliability, record, namespace='robot_a'):
        return start(label, ['ros2', 'launch', 'course_bringup', 'patrol.launch.py',
                            'namespace:=' + namespace, 'record:=' + record,
                            'bag_dir:=' + str(bag), 'subscriber_reliability:=' + reliability])

    try:
        broken = launch('live-reliable', 'reliable', 'false')
        for _ in range(150):
            spin(0.1)
            if len(samples['best_effort']) >= 30:
                break
        assert len(samples['best_effort']) >= 30 and not samples['reliable']
        nodes = command(['ros2', 'node', 'list', '--no-daemon', '--spin-time', '2'], before)
        for node in ('/robot_a/patrol', '/robot_a/pose_relay',
                     '/robot_a/pose_subscriber', '/turtlesim'):
            assert node in nodes
        assert 'rosbag2_recorder' not in nodes and not bag.exists(), 'record:=false failed'
        command(['ros2', 'topic', 'list', '--no-daemon', '--spin-time', '2'], before)
        info = command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], before)
        assert 'BEST_EFFORT' in info and 'RELIABLE' in info
        echo = ['timeout', '4s', 'ros2', 'topic', 'echo', '/robot_a/sensor_pose', '--once',
                '--qos-durability', 'volatile', '--qos-reliability']
        command(echo + ['reliable'], before, 124)
        stop(broken)
        broken_log = (out / 'live-reliable.txt').read_text()
        assert 'Requested reliable; received=0' in broken_log
        assert 'received=1 ' not in broken_log
        before.append('Live: topic exists; BEST_EFFORT observer receives; reliable count=0.\n'
                      'Configured reliable subscriber log: received=0, no receive callback.\n'
                      'record:=false: no recorder node and no bag directory.\n')
        spin(1)
        samples['best_effort'].clear()
        fixed = launch('live-best-effort', 'best_effort', 'true')
        for _ in range(150):
            spin(0.1)
            if len(samples['best_effort']) >= 60 and any(bag.glob('*.mcap')):
                break
        spin(4)
        assert len(samples['best_effort']) >= 60 and not samples['reliable']
        command(echo + ['best_effort'], after)
        command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], after)
        stop(fixed)
        assert 'received=1 ' in (out / 'live-best-effort.txt').read_text()
        metadata = yaml.safe_load((bag / 'metadata.yaml').read_text())
        info = metadata['rosbag2_bagfile_information']
        topics = info['topics_with_message_count']
        assert info['storage_identifier'] == 'mcap'
        assert len(topics) == 1
        assert topics[0]['topic_metadata']['name'] == '/robot_a/sensor_pose'
        assert topics[0]['topic_metadata']['type'] == 'turtlesim/msg/Pose'
        (out / 'bag-metadata.yaml').write_bytes((bag / 'metadata.yaml').read_bytes())
        command(['ros2', 'bag', 'info', str(bag)], after)
        reader = rosbag2_py.SequentialReader()
        reader.open(rosbag2_py.StorageOptions(uri=str(bag), storage_id='mcap'),
                    rosbag2_py.ConverterOptions('', ''))
        expected = []
        while reader.has_next():
            topic, payload, _ = reader.read_next()
            assert topic == '/robot_a/sensor_pose'
            expected.append(values(deserialize_message(payload, Pose)))
        del reader
        assert len(expected) == info['message_count'] and len(expected) >= 50
        spin(1)
        # No live producer may remain when replay is measured.
        nodes = command(['ros2', 'node', 'list', '--no-daemon', '--spin-time', '2'], after)
        assert '/robot_a/pose_relay' not in nodes and '/turtlesim' not in nodes
        samples['best_effort'].clear()
        samples['reliable'].clear()
        player = start('replay', ['ros2', 'bag', 'play', str(bag), '--delay', '2',
                                 '--qos-profile-overrides-path',
                                 str(ROOT / 'config/qos-overrides.yaml')])
        spin(3)
        command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], after)
        # The CLI diagnostic can block the executor; depth 1000 retains the whole small bag.
        deadline = time.monotonic() + 40
        while player.poll() is None and time.monotonic() < deadline:
            spin(0.05)
        assert player.poll() == 0, 'Replay failed or timed out'
        spin(1)
        assert not samples['reliable'], 'Reliable unexpectedly matched best-effort player'
        assert samples['best_effort'] == expected, (
            f'Replay differs: {len(samples["best_effort"])} / {len(expected)} messages')
        digest = hashlib.sha256(json.dumps(expected).encode()).hexdigest()
        after.append(f'Replay of the SAME MCAP: reliable=0; best_effort={len(expected)}.\n'
                     f'Every received Pose equals the recorded sequence. SHA256={digest}\n')
        before.append('Replay offered BEST_EFFORT via the committed override: reliable=0.\n')
        # A second namespace must change all relative interfaces, including recorder topic.
        alternate = launch('namespace-check', 'best_effort', 'false', 'robot_b')
        for _ in range(150):
            spin(0.1)
            if ('pose_relay', '/robot_b') in observer.get_node_names_and_namespaces():
                break
        nodes = command(['ros2', 'node', 'list', '--no-daemon', '--spin-time', '2'], after)
        assert '/robot_b/pose_relay' in nodes and '/robot_a/pose_relay' not in nodes
        command(['timeout', '6s', 'ros2', 'topic', 'echo', '/robot_b/sensor_pose',
                 '--once', '--qos-reliability', 'best_effort'], after)
        stop(alternate)
        for label in ('live-reliable', 'live-best-effort', 'namespace-check'):
            log = (out / (label + '.txt')).read_text()
            assert 'process has died' not in log and 'Traceback' not in log, log
        result = {'live_reliable': 0, 'replay_reliable': 0,
                  'recorded_messages': len(expected), 'replayed_messages': len(expected),
                  'sequence_sha256': digest, 'single_topic_mcap': True,
                  'record_false_verified': True, 'namespace_robot_b_verified': True,
                  'replay_verified': True}
        (out / 'capture-summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        for process in reversed(processes):
            stop(process)
        observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        (out / 'qos-before.txt').write_text('\n'.join(before))
        (out / 'qos-after.txt').write_text('\n'.join(after))
        (out / 'commands.txt').write_text('\n'.join(transcript))


if __name__ == '__main__':
    main()
