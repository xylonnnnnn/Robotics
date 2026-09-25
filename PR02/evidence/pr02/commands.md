# ПР02 — команды и опыт с топиком

## Три команды Linux

| Команда | Назначение | Применение и результат |
| --- | --- | --- |
| `pwd` | Выводит абсолютный путь текущего каталога | Перед сборкой подтвердил корень workspace: `/workspace/lab2/solution`. |
| `mkdir -p src evidence/pr02` | Создаёт каталоги, включая вложенные, без ошибки при повторе | Подготовил каталог исходников и evidence; повтор завершился `exit=0`. |
| `cat src/turtle_bringup/package.xml` | Печатает содержимое файла | Позволил проверить имя пакета, зависимость `turtlesim` и тип сборки `ament_python`. |

Сырой вывод этих трёх команд сохранён в [`linux-basics.txt`](linux-basics.txt). Отдельно `colcon build --symlink-install --packages-select turtle_bringup 2>&1 | tee evidence/pr02/build.txt` собрал пакет с результатом `Summary: 1 package finished [0.70s]` ([`build.txt`](build.txt)); `2>&1` объединяет stderr со stdout, а `|` передаёт поток в `tee`.

`>` записывает stdout в файл, заменяя его прежнее содержимое. `|` передаёт stdout одной команды на stdin следующей. `source` выполняет файл в текущем shell и меняет его окружение; запуск отдельного процесса не изменил бы `AMENT_PREFIX_PATH` текущего терминала. Начальный пустой пакет был создан генератором `ros2 pkg create` и отдельно собран; результат сохранён в [`build-empty.txt`](build-empty.txt).

## Сборка и запуск

```bash
source /opt/ros/jazzy/setup.bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup 2>&1 | tee evidence/pr02/build.txt
source install/setup.bash
ros2 pkg prefix turtle_bringup
ros2 launch turtle_bringup sim.launch.py
```

В другом терминале с тем же ROS и доменом 218:

```bash
ros2 node list --no-daemon --spin-time 2
ros2 topic type /turtle1/pose
ros2 topic echo /turtle1/pose --once
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic echo /turtle1/pose --once
```

При запуске [`nodes.txt`](nodes.txt) содержал `/turtlesim`. Установленный `sim.launch.py` найден через `ros2 pkg prefix turtle_bringup`; лог запуска и штатной остановки сохранён в [`launch.txt`](launch.txt). Однократная команда вызывает краткое движение. После неё узел turtlesim может продолжить движение по последней скорости до отправки нулевой команды, поэтому остановите его отдельной публикацией `{}`.

## Воспроизведение ошибки имени

Исходная поза в опыте: **x=5,544445; y=5,544445; theta=0** ([`pose-before.txt`](pose-before.txt)).

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Во время работы издателя [`wrong-topic-info.txt`](wrong-topic-info.txt) показал **1 издателя и 0 подписчиков** у `/cmd_vel`. Одновременно [`expected-topic-info-during-break.txt`](expected-topic-info-during-break.txt) показал **0 издателей и 1 подписчика** у `/turtle1/cmd_vel`. Поза после ошибочной публикации осталась прежней: **x=5,544445; y=5,544445; theta=0** ([`pose-broken.txt`](pose-broken.txt)). Тип `geometry_msgs/msg/Twist` был правильным, а полное имя топика — нет.

## Исправление

Заменено **только** `/cmd_vel` на `/turtle1/cmd_vel`. Та же публикация с той же скоростью дала **1 издателя и 1 подписчика** ([`fixed-topic-info.txt`](fixed-topic-info.txt)). Поза стала **x=7,278801; y=8,526378; theta=2,08** ([`pose-fixed.txt`](pose-fixed.txt)): черепаха прошла вперёд и повернула против часовой стрелки. После остановки издателя отправлена нулевая команда:

```bash
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist '{}'
```

[`stop-command.txt`](stop-command.txt) показывает успешную публикацию нулевого `Twist`. Фактические выводы всех команд сохранены в этой папке; краткая численная сводка находится в [`capture-summary.json`](capture-summary.json).
