# ПР01 — наблюдения графа

Опыт выполнен в Docker с ROS 2 Jazzy, домены 216 и 217. Полный вывод каждой команды сохранён в одноимённых текстовых файлах рядом с этим отчётом. Клавиши стрелок переданы запущенной `turtle_teleop_key` через псевдотерминал; симулятор работал на виртуальном X-дисплее.

## Команды для исправного графа

```bash
ros2 node list --no-daemon --spin-time 2
ros2 topic list -t
ros2 node info /turtlesim
ros2 topic type /turtle1/pose
POSE_TYPE=$(ros2 topic type /turtle1/pose)
ros2 topic echo /turtle1/pose --once
ros2 topic hz /turtle1/pose
```

Фактический граф: [`nodes-before.txt`](nodes-before.txt) показывает `/turtlesim` и `/teleop_turtle`; [`topics-before.txt`](topics-before.txt) показывает `/turtle1/pose` типа `turtlesim/msg/Pose` и `/turtle1/cmd_vel` типа `geometry_msgs/msg/Twist`. В [`node-info.txt`](node-info.txt) видно, что `/turtlesim` публикует позу и подписан на команду. Измерение [`pose-hz.txt`](pose-hz.txt) длилось 12 секунд: последний расчёт дал **62,496 Гц** по окну 694 сообщений. Код 124 у измерения означает штатное ограничение времени, поскольку `ros2 topic hz` сам не завершается. После клавиш вверх поза была `x=8,776444`, `y=5,544445`, `theta=0` ([`pose-before.txt`](pose-before.txt)).

## Сбой области обнаружения

Симулятор остался в домене 216. Teleop был остановлен и перезапущен в домене 217. CLI также запущен в 217:

```bash
ros2 node list --no-daemon --spin-time 2
ros2 topic echo /turtle1/pose turtlesim/msg/Pose --once
```

[`nodes-broken.txt`](nodes-broken.txt) содержит только `/teleop_turtle`. Ожидание позы в соседнем домене прервано через 5 секунд с **exit=124** ([`pose-broken.txt`](pose-broken.txt)). В исходном домене поза всё ещё доступна и не изменилась: `x=8,776444`, `y=5,544445` ([`pose-original-during-break.txt`](pose-original-during-break.txt)).

Причина: издатель `/turtlesim` работает в одной области DDS discovery, а teleop и CLI — в другой. Одинаковые имена топиков не связывают узлы через разные `ROS_DOMAIN_ID`. Код 124 при `timeout` означает истечение пяти секунд без сообщения; другой код требует диагностики.

## Восстановление

Teleop остановлен в 217 и перезапущен в 216; CLI тоже вернулся в 216. Повторены те же команды:

```bash
ros2 node list --no-daemon --spin-time 2
ros2 topic echo /turtle1/pose turtlesim/msg/Pose --once
```

[`nodes-fixed.txt`](nodes-fixed.txt) вновь показывает обе ноды; [`pose-fixed.txt`](pose-fixed.txt) завершился с **exit=0** и позой `x=11,088889`, `y=5,544445`, `theta=0`. Координата `x` выросла после повторного нажатия стрелок, то есть управление восстановлено.

Перезапуск teleop обязателен, потому что `export ROS_DOMAIN_ID` не меняет окружение уже запущенного процесса. Симулятор и установка ROS не меняются.
