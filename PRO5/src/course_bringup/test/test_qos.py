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
