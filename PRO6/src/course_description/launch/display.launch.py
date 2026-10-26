from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('course_description')
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value=PathJoinSubstitution(
            [share, 'urdf', 'vehicle.urdf.xacro'])),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             output='screen', parameters=[{'robot_description': ParameterValue(
                 Command([FindExecutable(name='xacro'), ' ', LaunchConfiguration('model')]),
                 value_type=str)}]),
        Node(package='rviz2', executable='rviz2', output='screen',
             arguments=['-d', PathJoinSubstitution([share, 'rviz', 'vehicle.rviz'])],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
