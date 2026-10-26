"""Semantic geometry checks complement check_urdf's structural parser."""

import math
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest
import xacro

SOURCE = Path(os.environ.get('COURSE_MODEL_XACRO',
                             Path(__file__).resolve().parents[1] / 'urdf/vehicle.urdf.xacro'))


def model(**parameters):
    return ET.fromstring(xacro.process_file(str(SOURCE), mappings=parameters).toxml())


def joint(root, name):
    return root.find(f"joint[@name='{name}']")


def xyz(element):
    return [float(v) for v in element.find('origin').get('xyz').split()]


def test_connected_acyclic_unique_tree():
    root = model()
    links = {link.get('name') for link in root.findall('link')}
    assert len(links) == len(root.findall('link')) == 10
    parents = {}
    for j in root.findall('joint'):
        p, c = j.find('parent').get('link'), j.find('child').get('link')
        assert p in links and c in links and c not in parents
        parents[c] = p
    assert links - parents.keys() == {'base_link'}
    for child in parents:
        seen = set()
        while child in parents:
            assert child not in seen
            seen.add(child)
            child = parents[child]
        assert child == 'base_link'


def test_lidar_parent():
    assert joint(model(), 'lidar_joint').find('parent').get('link') == 'base_link'


@pytest.mark.parametrize('name', ['camera', 'lidar', 'imu'])
def test_sensor_pose_and_single_fixed_owner(name):
    j = joint(model(), name + '_joint')
    assert j.get('type') == 'fixed'
    assert xyz(j) == pytest.approx([0.28, 0, 0.38])
    assert j.find('origin').get('rpy') == '0 0 0'


@pytest.mark.parametrize('parameters', [{}, {'wheelbase': '1.0', 'track': '0.8',
                                           'wheel_radius': '0.16'}])
def test_geometry_parameters_and_joint_axes(parameters):
    root = model(**parameters)
    length = float(parameters.get('wheelbase', '0.8'))
    track = float(parameters.get('track', '0.62'))
    radius = float(parameters.get('wheel_radius', '0.12'))
    for side, sign in [('left', 1), ('right', -1)]:
        steering = joint(root, f'front_{side}_steering_joint')
        assert xyz(steering) == pytest.approx([length/2, sign*track/2, 0])
        assert steering.find('axis').get('xyz') == '0 0 1'
        assert xyz(joint(root, f'rear_{side}_wheel_joint')) == pytest.approx(
            [-length/2, sign*track/2, 0])
        for end in ('front', 'rear'):
            wheel = root.find(f"link[@name='{end}_{side}_wheel']")
            assert float(wheel.find('visual/geometry/cylinder').get('radius')) == radius
            assert joint(root, f'{end}_{side}_wheel_joint').get('type') == 'continuous'
            assert joint(root, f'{end}_{side}_wheel_joint').find('axis').get('xyz') == '0 1 0'


def test_finite_positive_geometry_and_physical_inertias():
    root = model()
    for link in root.findall('link'):
        for tag in ('visual', 'collision', 'inertial'):
            assert link.find(tag) is not None, (link.get('name'), tag)
        assert float(link.find('inertial/mass').get('value')) > 0
        inertia = link.find('inertial/inertia')
        diag = [float(inertia.get(k)) for k in ('ixx', 'iyy', 'izz')]
        assert all(math.isfinite(v) and v > 0 for v in diag)
        assert all(float(inertia.get(k)) == 0 for k in ('ixy', 'ixz', 'iyz'))
        assert 2 * max(diag) <= sum(diag) + 1e-12
        for shape in link.findall('visual/geometry/*') + link.findall('collision/geometry/*'):
            assert all(math.isfinite(float(v)) and float(v) > 0
                       for text in shape.attrib.values() for v in text.split())


def test_default_dimensions_match_pinned_sdf(tmp_path):
    # Use the exact provided archive, not an Internet download or duplicate constants.
    import tarfile
    archive = Path(__file__).resolve().parents[3] / 'course-kit/pr06-v1-w08.tar.gz'
    with tarfile.open(archive) as kit:
        sdf = ET.fromstring(kit.extractfile('v1/models/course_ackermann/model.sdf').read())
    root = model()
    plugin = sdf.find('model/plugin')
    assert xyz(joint(root, 'front_left_steering_joint'))[0] * 2 == float(plugin.findtext('wheel_base'))
    assert xyz(joint(root, 'front_left_steering_joint'))[1] * 2 == float(plugin.findtext('wheel_separation'))
    assert float(root.find("link[@name='front_left_wheel']/visual/geometry/cylinder").get('radius')) == float(plugin.findtext('wheel_radius'))
    for sensor in ('camera', 'lidar', 'imu'):
        pose = [float(v) for v in sdf.findtext(f"model/link[@name='{sensor}_link']/pose").split()]
        assert xyz(joint(root, sensor + '_joint')) == pose[:3]
    assert root.find("link[@name='base_link']/visual/geometry/box").get('size') == sdf.findtext("model/link[@name='base_link']/visual/geometry/box/size")


def test_check_urdf(tmp_path):
    path = tmp_path / 'vehicle.urdf'
    path.write_text(xacro.process_file(str(SOURCE)).toxml())
    result = subprocess.run(['check_urdf', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
