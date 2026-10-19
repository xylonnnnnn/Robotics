from setuptools import setup

package_name = 'patrol'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='ROS course student',
    maintainer_email='student@example.com',
    description='Turtle patrol with validated runtime motion parameters.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'patrol = patrol.patrol:main',
        ],
    },
)
