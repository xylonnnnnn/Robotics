from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, GroupAction, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        DeclareLaunchArgument('record', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('bag_dir', default_value='bag'),
        DeclareLaunchArgument('subscriber_reliability', default_value='best_effort',
                              choices=['best_effort', 'reliable']),
        LogInfo(msg=['Starting patrol in /', namespace, '; record=',
                     LaunchConfiguration('record')]),
        Node(package='turtlesim', executable='turtlesim_node', output='screen'),
        GroupAction([
            PushRosNamespace(namespace),
            Node(package='patrol', executable='patrol', output='screen',
                 remappings=[('pose', '/turtle1/pose'), ('cmd_vel', '/turtle1/cmd_vel')]),
            Node(package='course_bringup', executable='pose_relay', output='screen',
                 remappings=[('pose', '/turtle1/pose')]),
            Node(package='course_bringup', executable='pose_subscriber', output='screen',
                 parameters=[{'reliability': LaunchConfiguration('subscriber_reliability')}]),
        ]),
        ExecuteProcess(
            cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', LaunchConfiguration('bag_dir'),
                 '--topics', PathJoinSubstitution(['/', namespace, 'sensor_pose'])],
            condition=IfCondition(LaunchConfiguration('record')), output='screen'),
    ])
