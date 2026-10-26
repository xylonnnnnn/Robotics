# ПР06 — Ackermann URDF/Xacro, tf2 и QoS

Самостоятельный workspace ROS 2 Jazzy. `course_description` описывает корпус, два поворотных кулака, четыре колеса и фиксированные camera/lidar/IMU. Размеры взяты из неизменённого SDF в предоставленном course kit, плагины Gazebo не копируются. СИ, оси REP-103: x вперёд, y влево, z вверх. Параметры Xacro: `wheelbase=0.8`, `track=0.62`, `wheel_radius=0.12`; тензоры корпуса и колёс рассчитаны по их геометрии.

```bash
cd PRO6
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
colcon test --packages-select course_description --event-handlers console_direct+
colcon test-result --verbose
ros2 launch course_description display.launch.py
```

Launch разворачивает Xacro, запускает `robot_state_publisher` и RViz с `Fixed Frame=base_link`. Для терминала без графики используйте `rviz:=false`. Аргумент `model:=/absolute/path/model.urdf.xacro` позволяет проверить альтернативную модель. `map` и `odom` на этом этапе отсутствуют. Предупреждение KDL об инерции корневого `base_link` ожидаемо: оно не мешает публикации преобразований, динамика здесь не моделируется.

Фиксированные сенсоры появляются в `/tf_static` без `joint_states`. Для отображения всех колёс и рулевых сочленений можно отдельно публиковать нулевые положения:

```bash
ros2 topic pub -r 10 /joint_states sensor_msgs/msg/JointState \
  "{header: auto, name: [front_left_steering_joint, front_right_steering_joint, front_left_wheel_joint, front_right_wheel_joint, rear_left_wheel_joint, rear_right_wheel_joint], position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"
```

Поздние подписчики при уже работающем publisher:

```bash
ros2 topic info /tf_static --verbose
timeout 4s ros2 topic echo /tf_static --once --qos-reliability reliable --qos-durability transient_local
# exit=0: сохранённые статические преобразования
timeout 4s ros2 topic echo /tf_static --once --qos-reliability reliable --qos-durability volatile
# exit=124: новых публикаций нет
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_tools view_frames
```

Исторический дефект сохранён отдельным коммитом, SHA находится в `defect-commit.txt`: parent лидара заменён на `camera_link`, offset оставлен прежним. `check_urdf` принимает оба дерева, но тест `test_lidar_parent` падает, а настоящий tf показывает [0.56, 0, 0.76] вместо [0.28, 0, 0.38] м. В рабочей модели parent исправлен на `base_link`.

```bash
PR06_EVIDENCE_DIR=/tmp/pr06-new python3 tools/capture_pr06.py
# С Xvfb, ImageMagick и RViz: дополнительно --rviz-screenshot
```

Сценарий берёт дефектный Xacro через `git show`, разворачивает обе версии, выполняет один и тот же тест, проверяет настоящий tf в отдельных свежих буферах, сохраняет `tf2_echo`/`view_frames`, сравнивает late-joiner QoS. Рабочие файлы не меняет. В режиме снимка нулевые `joint_states` публикуются только после обязательного опыта с фиксированными связями.

В [evidence/pr06/frames.md](evidence/pr06/frames.md) описаны связи и единственный владелец каждой публикации. Результат RViz — [evidence/pr06/rviz.png](evidence/pr06/rviz.png). CI повторяет все опыты и сохраняет артефакт `pr06-runtime-evidence`.

```bash
# Из корня репозитория:
(cd PRO6/course-kit && sha256sum -c SHA256SUMS)
mkdir -p .course-kit/pr06
tar -xzf PRO6/course-kit/pr06-v1-w08.tar.gz -C .course-kit/pr06
(cd .course-kit/pr06/v1 && sha256sum -c MANIFEST.sha256)
python3 .course-kit/pr06/v1/tools/check_practice.py PR06 --submission PRO6
```
