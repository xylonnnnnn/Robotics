import pytest
import rclpy
from rclpy.qos import QoSCompatibility, qos_check_compatible
from rclpy.parameter import Parameter
from course_bringup.pose_relay import PoseRelay, sensor_qos
from course_bringup.pose_subscriber import PoseSubscriber


@pytest.mark.parametrize('requested,compatible', [('reliable', False), ('best_effort', True)])
def test_requested_offered_compatibility(requested, compatible):
    result = qos_check_compatible(sensor_qos(), sensor_qos(requested))
    assert (result[0] != QoSCompatibility.ERROR) == compatible


def test_invalid_reliability_rejected():
    with pytest.raises(ValueError):
        sensor_qos('reliabl')


def test_relative_topics_follow_namespace_and_remaps():
    rclpy.init()
    relay = subscriber = None
    try:
        relay = PoseRelay(namespace='/robot_b', cli_args=['--ros-args', '-r',
                                                        'pose:=/turtle1/pose'])
        subscriber = PoseSubscriber(namespace='/robot_b', parameter_overrides=[
            Parameter('reliability', value='reliable')])
        assert relay.publisher.topic_name == '/robot_b/sensor_pose'
        assert relay.subscription.topic_name == '/turtle1/pose'
        assert subscriber.subscription.topic_name == '/robot_b/sensor_pose'
        assert subscriber.subscription.qos_profile == sensor_qos('reliable')
    finally:
        for node in (subscriber, relay):
            if node is not None:
                node.destroy_node()
        rclpy.shutdown()


def test_idle_subscriber_exits_cleanly_on_sigint():
    """No data arrives to wake an idle reader; SIGINT must still finish its executor."""
    import signal
    import subprocess
    import sys
    import time
    rclpy.init()
    observer = rclpy.create_node('shutdown_test_observer')
    process = subprocess.Popen(
        [sys.executable, '-c',
         'from course_bringup.pose_subscriber import main; '
         'main(["--ros-args", "-r", "__ns:=/shutdown_test"])'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 10
        while ('pose_subscriber', '/shutdown_test') not in observer.get_node_names_and_namespaces():
            assert time.monotonic() < deadline and process.poll() is None
            rclpy.spin_once(observer, timeout_sec=0.05)
        process.send_signal(signal.SIGINT)
        output, _ = process.communicate(timeout=5)
        assert process.returncode == 0, output
        assert 'Traceback' not in output
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        observer.destroy_node()
        rclpy.shutdown()
