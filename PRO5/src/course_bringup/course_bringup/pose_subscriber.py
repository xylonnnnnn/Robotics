"""Subscriber whose startup parameter demonstrates QoS compatibility."""

from rclpy.node import Node
from turtlesim.msg import Pose
from course_bringup.pose_relay import run, sensor_qos


class PoseSubscriber(Node):
    def __init__(self, **kwargs):
        super().__init__('pose_subscriber', **kwargs)
        reliability = self.declare_parameter('reliability', 'best_effort').value
        self.received = 0
        self.subscription = self.create_subscription(
            Pose, 'sensor_pose', self.on_pose, sensor_qos(reliability))
        self.get_logger().info(f'Requested {reliability}; received=0')

    def on_pose(self, pose):
        self.received += 1
        if self.received == 1 or self.received % 50 == 0:
            self.get_logger().info(
                f'received={self.received} x={pose.x:.4f} y={pose.y:.4f}')


def main(args=None):
    run(PoseSubscriber, args)
