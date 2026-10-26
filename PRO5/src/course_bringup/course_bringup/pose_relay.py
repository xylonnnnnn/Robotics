"""Relay a reliable simulator pose as a best-effort sensor stream."""

import signal
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from turtlesim.msg import Pose


def sensor_qos(reliability='best_effort'):
    policies = {'best_effort': ReliabilityPolicy.BEST_EFFORT,
                'reliable': ReliabilityPolicy.RELIABLE}
    if reliability not in policies:
        raise ValueError('reliability must be best_effort or reliable')
    return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                      reliability=policies[reliability],
                      durability=DurabilityPolicy.VOLATILE)


class PoseRelay(Node):
    def __init__(self, **kwargs):
        super().__init__('pose_relay', **kwargs)
        self.publisher = self.create_publisher(Pose, 'sensor_pose', sensor_qos())
        self.subscription = self.create_subscription(Pose, 'pose', self.publisher.publish, 10)
        self.get_logger().info('Relaying pose -> sensor_pose; offered BEST_EFFORT / VOLATILE')


def run(node_type, args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = node_type()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main(args=None):
    run(PoseRelay, args)
