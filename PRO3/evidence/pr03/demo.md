# ПР03: подписка на позу, таймер и исправление топика

## Среда и команды

Ubuntu 24.04 в контейнере `ros:jazzy-ros-base`, ROS 2 Jazzy, `turtlesim`, `Xvfb`, `ROS_DOMAIN_ID=220`. Собраны `turtle_bringup` из ПР02 и новый пакет `patrol`:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --base-paths ../PR02/src src --packages-select turtle_bringup patrol
source install/setup.bash
colcon test --packages-select patrol --event-handlers console_direct+
python3 -m pytest -q src/patrol/test
python3 tools/capture_pr03.py
```

`ros2 topic type /turtle1/pose` вернул `turtlesim/msg/Pose` ([вывод](pose-type.txt)). `turtle_bringup` запустил стандартный `/turtlesim` ([лог](turtlesim-launch.txt)). `patrol` подписывается на эту позу и сохраняет только последнее сообщение в поле `last_pose`. Таймер каждые 0,1 с вызывает чистую функцию `command_for_pose`: пока позы нет, выдаётся нулевой `Twist`; после получения позы — `linear.x=0.5`, `angular.z=0.3`. Проверка обоих случаев записана в [tests.txt](tests.txt).

## Воспроизведение дефекта

Команда без remap:

```bash
ros2 run patrol patrol
```

Нода опубликовала `Twist` в относительный `cmd_vel` (`/cmd_vel`). В [wrong-topic-info.txt](wrong-topic-info.txt) видны 1 издатель и **0 подписчиков**. У `/turtle1/cmd_vel` в [expected-topic-info.txt](expected-topic-info.txt) — 0 издателей и 1 подписчик turtlesim. За 10,001 с в `/cmd_vel` получено 100 сообщений, 9,999 Гц. Поза осталась `(5.544445, 5.544445, 0)` до и после опыта. Тип сообщения совпадает, но имена топиков различаются, поэтому DDS не соединяет издателя с turtlesim.

## Исправление и доказательство

После остановки неправильного запуска команда с remap:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В [fixed-topic-info.txt](fixed-topic-info.txt) у `/turtle1/cmd_vel` уже 1 издатель и 1 подписчик. За 10,001 с получено 100 команд, 9,999 Гц. Поза изменилась с `(6.256371, 5.706039, 0.441600)` на `(4.938362, 8.765225, -2.774385)`. Полные числа и интервалы находятся в [capture-summary.json](capture-summary.json). При проверке сценарий дополнительно утверждает, что до remap координаты неизменны, а после remap `x` меняется более чем на 0,1.

## Роли частей программы и остановка

`rclpy.init()` подготавливает ROS-контекст. `rclpy.spin(node)` обслуживает входящие сообщения и таймер, иначе callback подписки и публикация по таймеру не выполнялись бы. Callback `on_pose` сохраняет последнее сообщение, а `on_timer` только выбирает и публикует команду. `Ctrl+C` завершает spin и ноду. Публикация нулевого `Twist` при закрытии делается, пока ROS-контекст ещё доступен; исчезновение процесса само по себе не является мгновенной командой торможения. В опыте сначала остановлен `patrol`, затем дождались завершения turtlesim.
