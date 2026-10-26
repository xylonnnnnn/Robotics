# ПР05 — Launch, QoS и повтор MCAP

Отдельный ROS 2 Jazzy workspace с продолжением `patrol` из PRO4. Валидатор параметров и управление таймером сохранены; вход `pose` стал относительным. Пакет `course_bringup` запускает глобальный turtlesim, `/robot_a/patrol`, relay и отдельного настраиваемого подписчика. Только launch переназначает `pose` и `cmd_vel` на `/turtle1/pose` и `/turtle1/cmd_vel`. Relay предлагает `/robot_a/sensor_pose` типа `turtlesim/msg/Pose` с BEST_EFFORT / VOLATILE.

Не собирайте несколько папок PRO вместе: они содержат разные версии одноимённых пакетов.

```bash
cd PRO5
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
ros2 launch course_bringup patrol.launch.py namespace:=robot_a \
  subscriber_reliability:=reliable record:=false
```

Во втором терминале с тем же окружением:

```bash
ros2 topic info /robot_a/sensor_pose --verbose
timeout 4s ros2 topic echo /robot_a/sensor_pose --once --qos-reliability reliable
# Ожидается exit=124: топик существует, но BEST_EFFORT не удовлетворяет RELIABLE.
```

Остановите launch через Ctrl+C. Исправленный запуск с записью только одного топика:

```bash
ros2 launch course_bringup patrol.launch.py namespace:=robot_a \
  subscriber_reliability:=best_effort record:=true bag_dir:=/tmp/pr05-demo-bag
```

`record` обработан через `IfCondition`, при `false` recorder не создаётся. Каталог bag должен отсутствовать до запуска. `namespace`, `record`, `bag_dir`, `subscriber_reliability` — аргументы launch, `--show-args` показывает значения. Логи всех процессов идут на экран и в стандартный каталог ROS launch. Используется реальное время.

После нескольких секунд остановите launch через Ctrl+C: recorder закроет MCAP и запишет metadata. Остановите всех живых издателей перед повтором:

```bash
ros2 bag play /tmp/pr05-demo-bag --qos-profile-overrides-path config/qos-overrides.yaml
# В другом терминале: reliable по-прежнему не получает, best_effort получает.
timeout 4s ros2 topic echo /robot_a/sensor_pose --once --qos-reliability best_effort
ros2 bag info /tmp/pr05-demo-bag
```

Автоматическое воспроизведение всех стадий в изолированном домене 225:

```bash
PR05_EVIDENCE_DIR=/tmp/pr05-new python3 tools/capture_pr05.py
```

Сценарий проверяет реальный launch, отсутствие recorder при `false`, оба QoS, namespace `robot_b`, корректную остановку процессов, запись единственного потока MCAP. Затем читает MCAP и сравнивает каждое полученное при replay сообщение с исходной последовательностью; одновременно reliable-подписчик должен получить ноль. Для повторного запуска задайте новый каталог. При другом namespace измените также ключ в YAML replay override.

В [evidence/pr05](evidence/pr05) сохранены реальные логи, MCAP, его metadata и сводка. Один и тот же bag используется для обоих подписчиков при replay; данные «до» и «после» не подменяются двумя записями. CI повторяет эксперимент заново и сохраняет свой bag артефактом `pr05-runtime-evidence`.

Проверка контракта из корня репозитория:

```bash
(cd PRO5/course-kit && sha256sum -c SHA256SUMS)
mkdir -p .course-kit/pr05
tar -xzf PRO5/course-kit/pr05-v1-w08.tar.gz -C .course-kit/pr05
(cd .course-kit/pr05/v1 && sha256sum -c MANIFEST.sha256)
python3 .course-kit/pr05/v1/tools/check_practice.py PR05 --submission PRO5
```
