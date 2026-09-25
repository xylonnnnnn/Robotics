from glob import glob
from setuptools import setup

package_name = 'turtle_bringup'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROS course student',
    maintainer_email='student@example.com',
    description='Launch the standard turtlesim node for ROS 2 practice 02.',
    license='Apache-2.0',
)
