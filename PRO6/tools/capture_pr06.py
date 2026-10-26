"""Replay the historical parent defect and verify fixed tf and late-joiner QoS."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformListener
import xacro

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/course_description/urdf/vehicle.urdf.xacro'
TEST = ROOT / 'src/course_description/test/test_model.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--defect-commit', default=(ROOT / 'defect-commit.txt').read_text().strip())
    parser.add_argument('--rviz-screenshot', action='store_true')
    args = parser.parse_args()
    out = Path(os.environ.get('PR06_EVIDENCE_DIR', ROOT / 'evidence/pr06')).resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ['ROS_DOMAIN_ID'] = os.environ.get('PR06_DOMAIN_ID', '226')
    os.environ['PYTHONUNBUFFERED'] = '1'
    processes = []
    checks = []
    qos = []
    transforms = {}

    def command(args, target, expected=0, env=None):
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=60, cwd=out, env=env)
        text = f"$ {' '.join(args)}\n{result.stdout}\nexit={result.returncode}\n"
        target.append(text)
        print(text, flush=True)
        assert result.returncode == expected, text
        return result.stdout

    def start(label, args, env=None):
        with (out / (label + '.txt')).open('w') as stream:
            process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True, cwd=out, env=env)
        processes.append(process)
        return process

    def stop(process):
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                raise AssertionError('Process did not shut down cleanly')

    historical = subprocess.check_output(
        ['git', 'show', f'{args.defect_commit}:PRO6/src/course_description/urdf/vehicle.urdf.xacro'],
        cwd=ROOT, text=True)
    broken = out / 'historical.urdf.xacro'
    broken.write_text(historical)
    try:
        for label, source, expected_position in [
                ('broken', broken, [0.56, 0.0, 0.76]),
                ('fixed', SOURCE, [0.28, 0.0, 0.38])]:
            urdf = out / (label + '.urdf')
            urdf.write_text(xacro.process_file(str(source)).toxml())
            command(['check_urdf', str(urdf)], checks)
            env = os.environ.copy()
            env['COURSE_MODEL_XACRO'] = str(source)
            result = command(['python3', '-m', 'pytest', '-q', str(TEST), '-k', 'lidar_parent'],
                             checks, expected=1 if label == 'broken' else 0, env=env)
            if label == 'broken':
                assert '1 failed' in result and 'camera_link' in result
            # New context/buffer for each run prevents cached transforms hiding the defect.
            rclpy.init()
            observer = Node('pr06_observer')
            buffer = Buffer(node=observer)
            listener = TransformListener(buffer, observer)

            def spin(seconds):
                end = time.monotonic() + seconds
                while time.monotonic() < end:
                    rclpy.spin_once(observer, timeout_sec=min(0.05, max(0., end-time.monotonic())))

            launch = start(label + '-launch', ['ros2', 'launch', 'course_description',
                           'display.launch.py', 'rviz:=false', 'model:=' + str(source)])
            try:
                for _ in range(150):
                    spin(.1)
                    if buffer.can_transform('base_link', 'lidar_link', Time()):
                        break
                transform = buffer.lookup_transform('base_link', 'lidar_link', Time())
                t = transform.transform.translation
                position = [t.x, t.y, t.z]
                assert all(abs(a-b) < 1e-8 for a, b in zip(position, expected_position)), position
                transforms[label] = position
                checks.append(f'{label}: base_link -> lidar_link = {position}\n')
                command(['timeout', '4s', 'ros2', 'run', 'tf2_ros', 'tf2_echo',
                         'base_link', 'lidar_link'], checks, expected=124)
                command(['ros2', 'run', 'tf2_tools', 'view_frames'], checks)
                (out / (label + '-frames.yaml')).write_text(buffer.all_frames_as_yaml())
                if label == 'fixed':
                    # Publisher has sent the static batch before these CLI readers join.
                    info = command(['ros2', 'topic', 'info', '/tf_static', '--verbose'], qos)
                    assert 'RELIABLE' in info and 'TRANSIENT_LOCAL' in info
                    echo = ['timeout', '4s', 'ros2', 'topic', 'echo', '/tf_static', '--once',
                            '--qos-reliability', 'reliable', '--qos-durability']
                    latched = command(echo + ['transient_local'], qos)
                    assert 'lidar_link' in latched and 'imu_link' in latched
                    volatile = command(echo + ['volatile'], qos, expected=124)
                    assert 'child_frame_id' not in volatile
                    command(['ros2', 'topic', 'info', '/tf', '--verbose'], qos)
                    if args.rviz_screenshot:
                        # Joint states only for the illustration; fixed-sensor QoS needs none.
                        publisher = observer.create_publisher(JointState, '/joint_states', 10)
                        def publish_joints():
                            msg = JointState()
                            msg.header.stamp = observer.get_clock().now().to_msg()
                            msg.name = [f'front_{s}_steering_joint' for s in ('left', 'right')]
                            msg.name += [f'{e}_{s}_wheel_joint' for e in ('front', 'rear')
                                         for s in ('left', 'right')]
                            msg.position = [0.] * len(msg.name)
                            publisher.publish(msg)
                        timer = observer.create_timer(.1, publish_joints)
                        display = ':' + os.environ.get('PR06_X_DISPLAY', '96')
                        xvfb = start('xvfb', ['Xvfb', display, '-screen', '0', '1280x900x24'])
                        spin(1)
                        env = os.environ.copy()
                        env.update(DISPLAY=display, QT_QPA_PLATFORM='xcb', LIBGL_ALWAYS_SOFTWARE='1')
                        rviz = start('rviz', ['rviz2', '-d', str(ROOT /
                                     'src/course_description/rviz/vehicle.rviz')], env=env)
                        spin(9)
                        assert rviz.poll() is None, 'RViz exited unexpectedly'
                        command(['import', '-window', 'root', str(out / 'rviz.png')], checks, env=env)
                        stop(rviz)
                        stop(xvfb)
                        observer.destroy_timer(timer)
            finally:
                stop(launch)
                listener.unregister()
                observer.destroy_node()
                rclpy.shutdown()
        qos.append('/tf_static: RELIABLE + TRANSIENT_LOCAL, фиксированные связи; поздний '
                   'transient_local-подписчик получает сохранённую пачку, volatile ждёт новую. '
                   '/tf: RELIABLE + VOLATILE, динамические связи публикуются по joint_states; '
                   'старые отсчёты позднему подписчику не выдаются.\n')
        result = {'defect_commit': args.defect_commit, 'lidar_positions': transforms,
                  'broken_parent_test_failed': True, 'fixed_parent_test_passed': True,
                  'both_models_structurally_valid': True,
                  'late_transient_local_exit': 0, 'late_volatile_exit': 124}
        (out / 'capture-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        for process in reversed(processes):
            stop(process)
        (out / 'model-check.txt').write_text('\n'.join(checks))
        (out / 'tf-qos.txt').write_text('\n'.join(qos))


if __name__ == '__main__':
    main()
