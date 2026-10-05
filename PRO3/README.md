# ПР03 — первая нода: поза и команда

`patrol` получает `turtlesim/msg/Pose` из `/turtle1/pose`, хранит последнюю позу и раз в 0,1 с публикует `geometry_msgs/msg/Twist`. До первой позы команда нулевая, после неё `linear.x=0.5`, `angular.z=0.3`. Остальные поля остаются нулевыми.

Эта папка — отдельный workspace ROS 2 Jazzy. Пакет запуска `turtle_bringup` берётся из соседней ПР02, без копирования исходников:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --base-paths ../PR02/src src --packages-select turtle_bringup patrol
source install/setup.bash
colcon test --packages-select patrol --event-handlers console_direct+
python3 -m pytest -q src/patrol/test
```

В первом терминале запустите `ros2 launch turtle_bringup sim.launch.py`. Во втором выполните `ros2 run patrol patrol`: сообщения идут в относительный `cmd_vel`, у которого нет подписчиков turtlesim. Остановите ноду и запустите исправленный вариант:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Данные реального опыта в контейнере ROS Jazzy записаны в [evidence/pr03](evidence/pr03/). Сценарий повторения: `python3 tools/capture_pr03.py` после сборки и установки `xvfb` и `turtlesim`. Он измеряет частоту команд в течение 10 секунд до и после remap и проверяет движение по позе. Описание эксперимента и роли `init`, `spin`, callback, `Ctrl+C` — в [demo.md](evidence/pr03/demo.md).

Из корня репозитория, после распаковки course kit `v1-w05` в `.course-kit/`:

```bash
python3 .course-kit/v1/tools/check_practice.py PR03 --submission PRO3
```
