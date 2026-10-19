"""PR03 pose subscriber extended with transactional PR04 parameters."""

from geometry_msgs.msg import Twist
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
import rclpy
from turtlesim.msg import Pose

from patrol.parameters import LIMITS, Settings, updated_settings, validate_settings


def command_for_pose(pose: Pose | None, settings: Settings = Settings()) -> Twist:
    command = Twist()
    if pose is not None:
        command.linear.x = float(settings.linear_speed)
        command.angular.z = float(settings.turn_rate)
    return command


class Patrol(Node):
    def __init__(self, **kwargs) -> None:
        super().__init__('patrol', **kwargs)
        defaults = Settings()
        for name in LIMITS:
            self.declare_parameter(name, getattr(defaults, name),
                                   ParameterDescriptor(dynamic_typing=True))
        self.settings = Settings(**{name: self.get_parameter(name).value for name in LIMITS})
        try:
            validate_settings(self.settings)
        except ValueError:
            self.destroy_node()
            raise
        self.last_pose: Pose | None = None
        self.pose_subscription = self.create_subscription(
            Pose, '/turtle1/pose', self.on_pose, 10)
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.command_timer = self.create_timer(1.0 / self.settings.publish_hz, self.on_timer)
        self.add_on_set_parameters_callback(self.validate_parameters)
        self.add_post_set_parameters_callback(self.apply_parameters)

    def validate_parameters(self, parameters) -> SetParametersResult:
        try:
            updated_settings(self.settings, {p.name: p.value for p in parameters})
        except (ValueError, TypeError) as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def apply_parameters(self, parameters) -> None:
        candidate = updated_settings(self.settings, {p.name: p.value for p in parameters})
        if candidate.publish_hz != self.settings.publish_hz:
            # Prepare without starting; only one timer can publish at any instant.
            replacement = self.create_timer(1.0 / candidate.publish_hz,
                                            self.on_timer, autostart=False)
            self.command_timer.cancel()
            self.destroy_timer(self.command_timer)
            self.command_timer = replacement
            self.command_timer.reset()
        self.settings = candidate

    def on_pose(self, pose: Pose) -> None:
        self.last_pose = pose

    def on_timer(self) -> None:
        self.command_publisher.publish(command_for_pose(self.last_pose, self.settings))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = Patrol()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            if rclpy.ok():
                node.command_publisher.publish(Twist())
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
