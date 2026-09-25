# ПР01 — окружение и граф ROS 2

Опыт выполнен в Ubuntu 24.04 / ROS 2 Jazzy внутри Docker. `turtlesim_node` и `turtle_teleop_key` запускались в виртуальном X-дисплее; клавиши стрелок передавались в псевдотерминал teleop. Исходный `ROS_DOMAIN_ID` — 216, соседний — 217. На занятии значения заменяются на выделенную пару.

Из этой папки с установленными ROS 2, `turtlesim` и `Xvfb`:

```bash
source /opt/ros/jazzy/setup.bash
PR01_DOMAIN_ID=216 python3 tools/capture_pr01.py
```

Команды опыта и результаты записаны в [graph.md](evidence/pr01/graph.md). Данные среды — в [environment.json](evidence/pr01/environment.json), полный вывод `ros2 doctor --report` — в [doctor.txt](evidence/pr01/doctor.txt). В домене 216 измерена частота `/turtle1/pose` 62,496 Гц. В домене 217 CLI не обнаружил симулятор; после возврата в 216 снова получил позу. Движение teleop подтверждено изменением координаты `x`.

Проверка отчёта из корня репозитория после распаковки закреплённого course kit в `.course-kit/`:

```bash
python3 .course-kit/v1/tools/check_practice.py PR01 --submission PR01
```
