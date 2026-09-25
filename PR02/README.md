# ПР02 — терминал, пакет и запуск turtlesim

Работа выполнена в Ubuntu 24.04 / ROS 2 Jazzy внутри Docker. Эта папка — отдельный ROS 2 workspace. Пакет [turtle_bringup](src/turtle_bringup/package.xml) устанавливает [sim.launch.py](src/turtle_bringup/launch/sim.launch.py) и запускает готовую ноду `turtlesim_node`.

Из этой папки:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup
source install/setup.bash
ros2 launch turtle_bringup sim.launch.py
```

Пустой пакет был собран до добавления launch-файла. Логи обеих сборок и результаты опыта находятся в [evidence/pr02](evidence/pr02/). [commands.md](evidence/pr02/commands.md) показывает ошибку публикации в `/cmd_vel` без подписчиков и исправление публикацией в `/turtle1/cmd_vel`, после которого изменилась поза. [types.md](evidence/pr02/types.md) содержит типы сообщений. Воспроизводимый сценарий: [capture_pr02.py](tools/capture_pr02.py), запускать после `source install/setup.bash`.

Проверка отчёта из корня репозитория после распаковки закреплённого course kit в `.course-kit/`:

```bash
python3 .course-kit/v1/tools/check_practice.py PR02 --submission PR02
```
