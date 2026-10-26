# Системы координат ПР06

Все расстояния в метрах, углы в радианах. Оси: x вперёд, y влево, z вверх. Единственный владелец `/tf` и `/tf_static` — `robot_state_publisher`. Он получает модель из `robot_description`, подвижные положения — из `/joint_states`. Других издателей этих связей запускать нельзя.

| Parent | Child | xyz при нулевых сочленениях | rpy | Тип и канал |
|---|---|---|---|---|
| base_link | camera_link | 0.28, 0, 0.38 | 0, 0, 0 | fixed, /tf_static |
| base_link | lidar_link | 0.28, 0, 0.38 | 0, 0, 0 | fixed, /tf_static |
| base_link | imu_link | 0.28, 0, 0.38 | 0, 0, 0 | fixed, /tf_static |
| base_link | front_left_knuckle | 0.4, 0.31, 0 | 0, 0, steering | revolute вокруг z, /tf |
| base_link | front_right_knuckle | 0.4, −0.31, 0 | 0, 0, steering | revolute вокруг z, /tf |
| front_left_knuckle | front_left_wheel | 0, 0, 0 | вращение вокруг y | continuous, /tf |
| front_right_knuckle | front_right_wheel | 0, 0, 0 | вращение вокруг y | continuous, /tf |
| base_link | rear_left_wheel | −0.4, 0.31, 0 | вращение вокруг y | continuous, /tf |
| base_link | rear_right_wheel | −0.4, −0.31, 0 | вращение вокруг y | continuous, /tf |

Корень — `base_link`; 10 звеньев, 9 соединений, циклов и вторых родителей нет. `wheelbase` меняет ±x колёс/кулаков, `track` меняет ±y, `wheel_radius` меняет цилиндры и их инерции. Цилиндры visual/collision повёрнуты на π/2 вокруг x; сами wheel frames сохраняют ориентацию корпуса при нулевом положении. Поэтому ось вращения колеса — y. Передние колёса вращаются относительно кулаков; рулевые сочленения ограничены ±0.55 рад.

Камера, лидар и IMU имеют общий origin, как в SDF kit. Цветные коробки — условная геометрия сенсоров. Для потока изображений в будущем потребуется отдельный camera optical frame с соответствующим поворотом; здесь image data нет. `map` и `odom` не публикуются. Их будущие владельцы — локализация (`map→odom`) и одометрия (`odom→base_link`), не второй `robot_state_publisher`.

## Дефект и доказательство исправления

В коммите из `PRO6/defect-commit.txt` изменён только parent лидара: `camera_link` вместо `base_link`, локальный offset [0.28, 0, 0.38] сохранён. Получается связное и ацикличное, но геометрически неверное дерево: `base_link→camera_link→lidar_link`, суммарный сдвиг [0.56, 0, 0.76].

Сценарий `tools/capture_pr06.py` разворачивает исторический файл во временном каталоге. `check_urdf` успешен; `test_lidar_parent` падает; `tf2_echo` и свежий tf2 Buffer показывают удвоенный offset. После возврата parent=`base_link` тот же тест успешен, Buffer и `tf2_echo` дают [0.28, 0, 0.38]. Команды и результаты обеих стадий — в `model-check.txt`, деревья — `broken-frames.yaml` и `fixed-frames.yaml`.

## Время и QoS

Фиксированные связи публикуются один раз в `/tf_static` с RELIABLE / TRANSIENT_LOCAL. Поздний подписчик с transient_local получает сохранённый пакет; volatile совместим, но старого пакета не запрашивает и ждёт новых публикаций (timeout 124). `/tf` использует RELIABLE / VOLATILE для текущих подвижных позиций по timestamp `/joint_states`. До первого JointState колёс в tf нет — это ожидаемо.

Трансформацию для сенсорного измерения следует запрашивать на timestamp измерения; свежая связь в графе сама по себе не гарантирует наличие данных на нужный момент. При диагностике: status RViz → Fixed Frame=base_link → `tf2_echo` → `view_frames` → timestamp и владелец. Перед сменой модели прежний launch останавливается; capture создаёт новый контекст и буфер для каждой модели.
