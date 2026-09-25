# ПР02 — типы сообщений и имена топиков

Типы проверены в работающем ROS-графе Jazzy; сырые результаты сохранены в `pose-type.txt`, `command-type.txt` и `twist-interface.txt`:

```bash
ros2 interface show geometry_msgs/msg/Twist
ros2 topic type /turtle1/pose
ros2 topic type /turtle1/cmd_vel
ros2 topic info /turtle1/cmd_vel --verbose
```

| Топик | Тип | Назначение |
| --- | --- | --- |
| `/turtle1/cmd_vel` | `geometry_msgs/msg/Twist` | Команда линейной и угловой скорости для черепахи |
| `/turtle1/pose` | `turtlesim/msg/Pose` (фактический вывод Jazzy) | Координаты `x`, `y`, угол `theta`, линейная и угловая скорость |

`Twist` содержит два вектора: `linear` и `angular`, у каждого поля `x`, `y`, `z`. В опыте используется `linear.x = 1.0` и `angular.z = 0.5`; остальные компоненты равны нулю. Это движение вперёд с поворотом.

Совпадения типа недостаточно для доставки команды: издатель и подписчик должны использовать одно и то же полное имя топика и один ROS-домен. Поэтому команда на `/cmd_vel` не управляет стандартной `turtlesim`, подписанной на `/turtle1/cmd_vel`.
