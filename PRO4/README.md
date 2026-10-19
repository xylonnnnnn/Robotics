# ПР04 — параметризуем движение

Продолжение `patrol` из [ПР03](../PRO3/README.md). Подписка на позу и публикация `Twist` сохранены; добавлены параметры `linear_speed` (0–1 м/с), `turn_rate` (−1–1 рад/с), `publish_hz` (1–30 Гц). По умолчанию: 0.5, 0.3, 10.0. До первой позы команда нулевая. Допускаются только конечные числа, включая целые; логические значения и строки отклоняются.

Проверка параметров — чистая функция. Callback проверки не меняет состояние; post-set callback применяет успешно принятый набор. При смене частоты создаётся остановленный таймер, прежний отменяется и уничтожается, затем запускается новый. Невалидный атомарный набор целиком отклоняется. Ошибочные начальные параметры также отклоняются.

Это отдельный workspace: не собирайте `PRO3/src` и `PRO4/src` вместе, поскольку оба содержат пакет `patrol`.

```bash
cd PRO4
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select patrol
source install/setup.bash
colcon test --packages-select patrol --event-handlers console_direct+
colcon test-result --verbose
python3 -m pytest -q src/patrol/test
```

Запустите `ros2 run turtlesim turtlesim_node`, затем в другом терминале:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
ros2 param set /patrol publish_hz 5.0
ros2 param set /patrol publish_hz 0.0
ros2 param get /patrol publish_hz
```

Автоматический опыт с отдельным ROS domain и turtlesim без окна:

```bash
PR04_EVIDENCE_DIR=/tmp/pr04-fixed python3 tools/capture_pr04.py
```

Он проверяет частоту по принятым сообщениям, сохранение 5 Гц после отклонения нуля, изменение обеих скоростей, движение по позе, сервис `/clear` и action поворота. Для повтора исторического дефекта используйте `--expect-defect --defect-commit SHA` с SHA из `evidence/pr04/parameters.md`; исходник дефектного валидатора загружается через `git show` во временный пакет, рабочие файлы не меняются.

Проверка предоставленным course kit из корня репозитория:

```bash
(cd PRO4/course-kit && sha256sum -c SHA256SUMS)
mkdir -p .course-kit/pr04
tar -xzf PRO4/course-kit/pr04-v1-w07.tar.gz -C .course-kit/pr04
(cd .course-kit/pr04/v1 && sha256sum -c MANIFEST.sha256)
python3 .course-kit/pr04/v1/tools/check_practice.py PR04 --submission PRO4
```

Команды и реальные результаты находятся в [evidence/pr04/parameters.md](evidence/pr04/parameters.md). Старая ПР03 сохранена отдельно.
