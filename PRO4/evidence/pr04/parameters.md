# ПР04: параметры, воспроизводимый дефект и исправление

Среда: Ubuntu 24.04, ROS 2 Jazzy, Python 3.12.3, pytest 7.4.4, Docker на macOS. Симулятор работает с `QT_QPA_PLATFORM=offscreen`; опыт изолирован `ROS_DOMAIN_ID=221`. Исходная подписка и таймер взяты из ПР03. ПР01–ПР03 сохранены без изменений.

Course kit: `v1-w07`, исходный архив из `lab4`, SHA-256 `001f7ec79674d09a0f7eff2ad0935f58c95101b0cf200425c368f41579d6a31c`. Архив и его внутренний MANIFEST проверены без изменений.

## Коммиты

- Версия с отключённой проверкой частоты: `2d810caf454278eadec02af304d2d82eabf04697`.
- Готовая реализация и CI: `8179b328cb37f6bb9125aaf52a1bec80707b56e4`.
- Отчёт и сырые логи фиксируются следующим коммитом. Именно SHA следующего коммита используется для сдачи; `report.commit` указывает реализацию выше.

## Собрать

Из `PRO4`, после подключения `/opt/ros/jazzy/setup.bash`:

```bash
colcon build --symlink-install --packages-select patrol
source install/setup.bash
colcon test --packages-select patrol --event-handlers console_direct+
colcon test-result --verbose
python3 -m pytest -q src/patrol/test
```

Результат: 37 тестов, 0 ошибок, 0 отказов, 0 пропусков. Вывод: [build.txt](build.txt), [colcon-tests.txt](colcon-tests.txt), [colcon-result.txt](colcon-result.txt), [tests.txt](tests.txt). Тесты проверяют конечность и типы, границы всех трёх параметров, 10→5 Гц, ноль/отрицательное/NaN, один активный таймер, неизменность состояния при отклонении атомарного набора или другим callback, скорости и ошибочные стартовые параметры.

## Сломать

В дефектном коммите `validate_settings` пропускает проверку `publish_hz`. До исправления выполнен тест:

```bash
python3 -m pytest -q src/patrol/test/test_parameters.py -k "test_reject_out_of_range and 0.0"
PR04_EVIDENCE_DIR=evidence/pr04/broken python3 tools/capture_pr04.py --expect-defect
```

Первый запуск сохранил ожидаемые отказы в [defect-tests.txt](defect-tests.txt): ноль не вызывает ожидаемый `ValueError`. В реальном ROS-графе после успешной смены 10→5 Гц запрос нуля проходит в post-set callback, деление `1.0 / 0.0` вызывает `ZeroDivisionError`, процесс выходит с кодом 1, CLI не получает ответ (ограничен тайм-аутом), а наблюдатель получает 0 команд за 4.001 с. Полная трассировка — [broken/patrol.txt](broken/patrol.txt), измерения — [broken/capture-summary.json](broken/capture-summary.json).

Повтор из текущей версии без изменения рабочих файлов:

```bash
PR04_EVIDENCE_DIR=/tmp/pr04-broken python3 tools/capture_pr04.py --expect-defect --defect-commit 2d810caf454278eadec02af304d2d82eabf04697
```

Сценарий временно загружает только исторический валидатор через `git show`, используя текущие неизменённые алгоритм таймера и тестовый запрос. Этот повтор также выполняется в CI.

## Доказать исправление

```bash
PR04_EVIDENCE_DIR=evidence/pr04/fixed python3 tools/capture_pr04.py
```

Проверка входных данных выполняется до изменения ROS-параметров, активных настроек и таймера. Callback валидации не имеет побочных эффектов; применение происходит только после успешного принятия параметров. При допустимой частоте старый таймер отменяется и уничтожается, новый запускается один раз. Для невалидного запроса объект таймера и прежние параметры сохраняются.

Реальные измерения за интервалы по 4 секунды:

| Этап | Сообщений | Частота, Гц | linear.x | angular.z |
|---|---:|---:|---:|---:|
| Исходная частота 10 | 40 | 9.992 | 0.5 | 0.3 |
| Допустимая смена на 5 | 20 | 4.996 | 0.5 | 0.3 |
| После отклонения 0 | 20 | 4.998 | 0.5 | 0.3 |
| После смены скоростей | 20 | 4.994 | 0.8 | -0.6 |

После запроса 0.0 получено `Setting parameter failed: publish_hz must be in [1.0, 30.0]`, а `ros2 param get /patrol publish_hz` вернул `Double value is: 5.0`. Отрицательное значение и NaN также отклонены. Изменение `linear_speed=0.8`, `turn_rate=-0.6` подтверждено полученными Twist и изменением координат, частота сохранилась около 5 Гц.

### Реальные команды и полный вывод: исправленная версия

```text
$ ros2 run turtlesim turtlesim_node

$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel

initial 10 Hz: {"messages": 40, "seconds": 4.003057127000034, "hz": 9.992363019304886, "last_twist": [0.5, 0.3]}

$ ros2 topic type /turtle1/pose
exit=0
turtlesim/msg/Pose


$ ros2 param set /patrol publish_hz 5.0
exit=0
Set parameter successful


changed 5 Hz: {"messages": 20, "seconds": 4.0028415839999525, "hz": 4.996450541521165, "last_twist": [0.5, 0.3]}

$ ros2 param set /patrol publish_hz 0.0
exit=0
Setting parameter failed: publish_hz must be in [1.0, 30.0]


$ ros2 param get /patrol publish_hz
exit=0
Double value is: 5.0


preserved 5 Hz after zero: {"messages": 20, "seconds": 4.001385793999987, "hz": 4.9982683574249895, "last_twist": [0.5, 0.3]}

$ ros2 param set /patrol publish_hz -1.0
exit=0
Setting parameter failed: publish_hz must be in [1.0, 30.0]


$ ros2 param set /patrol publish_hz .nan
exit=0
Setting parameter failed: publish_hz must be a finite number


$ ros2 param set /patrol linear_speed 0.8
exit=0
Set parameter successful


$ ros2 param set /patrol turn_rate -0.6
exit=0
Set parameter successful


new speeds, still 5 Hz: {"messages": 20, "seconds": 4.005061461000025, "hz": 4.993681169378657, "last_twist": [0.8, -0.6]}

$ ros2 service call /clear std_srvs/srv/Empty {}
exit=0
waiting for service to become available...
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()



$ ros2 action list -t
exit=0
/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]

```

### Реальные команды и полный вывод: дефектная версия

```text
$ ros2 run turtlesim turtlesim_node

$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel

initial 10 Hz: {"messages": 40, "seconds": 4.001948459999994, "hz": 9.995131221654978, "last_twist": [0.5, 0.3]}

$ ros2 topic type /turtle1/pose
exit=0
turtlesim/msg/Pose


$ ros2 param set /patrol publish_hz 5.0
exit=0
Set parameter successful


changed 5 Hz: {"messages": 20, "seconds": 4.000233252000044, "hz": 4.999708452000984, "last_twist": [0.5, 0.3]}

$ ros2 param set /patrol publish_hz 0.0
exit=124
CLI timeout


broken stream: {"messages": 0, "seconds": 4.001028667000014, "hz": 0.0, "last_twist": null}
```

## Service и action

Сервис `/clear` выполняет короткий запрос и возвращает один ответ; запрос не имеет жизненного цикла цели и потока обратной связи. Action `/turtle1/rotate_absolute` принимает длительную цель поворота, поддерживает обратную связь, получение результата и отмену цели.

`/clear` реально вызван, ответ получен; `/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]` найден через `ros2 action list -t`. Собственный IDL и action-сервер в обязательную часть не входят. Необязательный контроллер маршрута не добавлялся: в ПР03 реализована обязательная нода `patrol`.

## CI

Job `pr04` в `.github/workflows/ci.yml` отдельно собирает пакет ПР04, выполняет все тесты, повторяет дефект из истории, запускает исправленный опыт и проверяет контракт course kit. Логи каждого запуска загружаются артефактом `pr04-runtime-evidence` даже при ошибке. Job предыдущих лабораторных сохранён. Трудоёмкость в `report.json` — плановая из задания: одна лабораторная пара (2 академических часа) и около 2 часов самостоятельной работы.
