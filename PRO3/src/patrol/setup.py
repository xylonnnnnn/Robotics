from setuptools import setup

package_name = 'patrol'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    test_suite='test',
    zip_safe=True,
    maintainer='ROS course student',
    maintainer_email='student@example.com',
    description='Pose subscriber and periodic turtle command publisher.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'patrol = patrol.patrol:main',
        ],
    },
)
