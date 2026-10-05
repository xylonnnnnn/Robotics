"""Minimal PR03 controller: remember the last pose, publish at 10 Hz."""

from geometry_msgs.msg import Twist
from rclpy.node import Node
import rclpy
from turtlesim.msg import Pose


def command_for_pose(pose: Pose | None) -> Twist:
    """Return a safe stop before the first pose and a fixed command thereafter."""
    command = Twist()
    if pose is not None:
        command.linear.x = 0.5
        command.angular.z = 0.3
    return command


class Patrol(Node):
    def __init__(self) -> None:
        super().__init__('patrol')
        self.last_pose: Pose | None = None
        self.pose_subscription = self.create_subscription(
            Pose, '/turtle1/pose', self.on_pose, 10
        )
        # Deliberately relative. The PR03 defect and its fix use a ROS remap.
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.command_timer = self.create_timer(0.1, self.on_timer)

    def on_pose(self, pose: Pose) -> None:
        self.last_pose = pose

    def on_timer(self) -> None:
        self.command_publisher.publish(command_for_pose(self.last_pose))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Patrol()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # This is a best-effort stop. The normal experiment waits for turtlesim
        # to exit, because a stopped publisher does not retain a lasting brake.
        if rclpy.ok():
            node.command_publisher.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
