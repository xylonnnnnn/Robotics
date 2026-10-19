from math import isclose
import unittest

from turtlesim.msg import Pose

from patrol.patrol import command_for_pose


class PatrolCommandTests(unittest.TestCase):
    def test_no_pose_publishes_zero_twist(self):
        command = command_for_pose(None)
        self.assertEqual(command.linear.x, 0.0)
        self.assertEqual(command.angular.z, 0.0)

    def test_pose_enables_fixed_motion(self):
        pose = Pose(x=5.5, y=5.5, theta=0.0)
        command = command_for_pose(pose)
        self.assertTrue(isclose(command.linear.x, 0.5))
        self.assertTrue(isclose(command.angular.z, 0.3))
        self.assertEqual(command.linear.y, 0.0)
        self.assertEqual(command.angular.x, 0.0)
        self.assertEqual(command.angular.y, 0.0)
