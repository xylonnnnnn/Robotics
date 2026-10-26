from glob import glob
from setuptools import setup

setup(
    name='course_bringup', version='0.1.0', packages=['course_bringup'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/course_bringup']),
        ('share/course_bringup', ['package.xml']),
        ('share/course_bringup/launch', glob('launch/*launch.py')),
    ],
    install_requires=['setuptools'], tests_require=['pytest'], zip_safe=True,
    maintainer='-xylon', maintainer_email='r.smagulov@g.nsu.ru',
    description='Namespaced patrol and reproducible QoS/MCAP experiment.',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'pose_relay = course_bringup.pose_relay:main',
        'pose_subscriber = course_bringup.pose_subscriber:main',
    ]},
)
