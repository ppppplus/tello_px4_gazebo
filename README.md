# Tello 单机决赛课程仿真环境

本目录可以整体放入 ROS 工作空间的 `src/`，使用 `catkin_make` 编译。
包含 Tello 尺寸训练机、PX4 飞控、Gazebo 场景、裁判和学生代码模板。
任务是：**起飞 → 两柜球色识别 → 穿红标窗口 → 依次观察并接近三个红点 → 降落**。

![Gazebo 场地总览：蓝色起飞台、两个球柜、三扇窗口、九宫格白板和绿色降落台](docs/images/overview.png)

上图为本课程场景与模型在 Gazebo 中的实际渲染。蓝色区域是起飞台，绿色区域是目标降落台；
两个球柜位于窗口前，三灯白板位于窗口后。球色、指定窗口和亮灯位置随 `seed` 改变。

## 1. 环境要求

- Ubuntu **20.04 x86_64**、ROS **Noetic**、Gazebo **Classic 11**。
- 已安装 ROS，并配置可用的 ROS 软件源；终端中使用系统 Python 3，退出 Conda。
- 有可用的桌面与 OpenGL。虚拟机请开启 3D 加速；建议至少 4 核 CPU、8 GB 内存。
- 本课程包约 28 MB，包含固定版本的 PX4 v1.14.3 Linux 运行文件、所需的 Gazebo 飞控插件和 EGM96-5 数据。
  **学生不需要另外下载或编译 PX4，也不需要原教师工程。**

课程包内的 PX4 运行文件限定上述平台；不能直接在 Ubuntu 22.04/24.04、ROS 2、ARM、Windows 或 macOS 上运行。
其他系统请使用 Ubuntu 20.04 x86_64 虚拟机或课程镜像。

首次使用时，需要安装 ROS/Gazebo/MAVROS 等系统依赖。已经配置好的课程电脑可跳过：

```bash
cd ~/catkin_ws/src/tello_sim
bash tools/install_dependencies.sh
```

该脚本只通过现有软件源安装依赖，不修改软件源；需要联网及 sudo。
如果提示某个 ROS 包不存在，请先确认系统为 Ubuntu 20.04 且 ROS Noetic 软件源配置正确。
GeographicLib 数据已经随包提供，无需再运行 MAVROS 的全球地理数据下载脚本。

## 2. 放入工作空间并编译

目录结构应当是：

```text
catkin_ws/
└── src/
    └── tello_sim/                 # 整个课程包；这一层不是 ROS 功能包
        ├── README.md
        ├── tello_px4_runtime/     # PX4、飞控插件、运行隔离与数据
        ├── tello_competition/     # 场景、相机、裁判、控制接口和 Action 消息
        ├── tello_control/         # 学生主要修改这里
        │   └── scripts/demo.py   # 最小订阅与飞行控制演示
        ├── docs/                 # 学生接口与验收说明
        └── tools/                # 依赖安装、教师维护工具
```

可以使用已有的 catkin 工作空间；不要在同一工作空间再放一份同名功能包。
从旧版升级时，应替换整份课程目录，并在干净工作空间重新编译，避免旧包和生成消息残留。
当前学生包名为 `tello_control`，场景与裁判包名为 `tello_competition`；
起降 Action 类型使用 `tello_competition` 前缀，`/tello/*` 公共话题名称保持不变。
如果拿到的是 `tello_sim.tar.gz`，可以直接解压：

```bash
mkdir -p ~/catkin_ws/src
tar -xzf ~/Downloads/tello_sim.tar.gz -C ~/catkin_ws/src
```

准备好系统依赖后，编译：

```bash
source /opt/ros/noetic/setup.bash
cd ~/catkin_ws
catkin_make -j2 -DPYTHON_EXECUTABLE=/usr/bin/python3
source devel/setup.bash
```

编译过程会检查 PX4 运行文件的完整性，不联网、不启动仿真。
每次打开新终端，都需要 `source ~/catkin_ws/devel/setup.bash`。
移动整个工作空间后需在新位置重新编译，不要复用其他电脑的 `build/`、`devel/`。

## 3. 启动场景

第一个终端：

```bash
source ~/catkin_ws/devel/setup.bash
roslaunch tello_competition tello.launch
```

Gazebo 中会出现无人机、起降台、两个柜子、三个窗口和白板。
无人机启动后保持未解锁状态，场景不会自动完成比赛。

### 裁判如何启动和查看

上面的 `tello.launch` **已经同时启动裁判节点 `/final_judge`**，无需重复运行。
当前裁判是本机 ROS 节点，没有独立的裁判 GUI，也不需要连接另一台裁判电脑。
场景节点初始化比赛目标，裁判订阅无人机真值与 `/tello/judge` 提交，自动计算得分。

另开终端查看（以下两个 `echo` 分别运行，或 Ctrl+C 停止一个后再运行另一个）：

```bash
source ~/catkin_ws/devel/setup.bash
rosnode info /final_judge      # 确认裁判已启动
rostopic echo /final/status   # 当前阶段、各项成绩与总分
rostopic echo /final/events   # 起飞/穿窗事件、提交是否接受及原因
```

学生程序向 `/tello/judge` 发布 `std_msgs/String`：球色如 `rg`，红点到达为
`target1`、`target2`、`target3`。裁判收到消息不等于一定得分，要看事件中的反馈。
启动例程前先监听 `/final/events`，以免错过瞬时事件；`/final/status` 可随时查看最新状态。

常用参数：

```bash
# 同时打开学生第一视角窗口
roslaunch tello_competition tello.launch camera_preview:=true

# 用不同种子改变球色、指定窗口和三灯位置
roslaunch tello_competition tello.launch seed:=23

# 关闭 Gazebo 主窗口，但仍使用真实渲染相机，需要可用的显示服务
roslaunch tello_competition tello.launch gui:=false
```

相机直接由 Gazebo 渲染，包含墙、柜子及遮挡。图像默认 320×240、目标 20 Hz。
运行下一节 `demo.py` 时，它会自行创建图像窗口，无需额外设置 `camera_preview:=true`。
在无桌面服务器上，可安装 `xvfb` 后使用
`xvfb-run -a roslaunch tello_competition tello.launch gui:=false`；软件渲染速度取决于 CPU。

同一台电脑一次启动一套本课程仿真；停止时在启动终端按 `Ctrl+C`，等待进程退出。
每次启动使用全新的 PX4 参数目录；日志保存在 `~/.ros/tello_sim/run-*` 和 ROS 日志目录中。

## 4. 运行最小控制演示

保持场景运行，打开第二个终端：

```bash
source ~/catkin_ws/devel/setup.bash
rosrun tello_control demo.py
```

**运行后会自动飞行**，请在桌面环境中、场景刚启动且无人机位于起点并未解锁时运行，
不要同时运行其他控制节点。无需 `--smoke` 参数。
旧版脚本入口已替换为 `demo.py`；更新课程包后请重新执行 `catkin_make` 并加载工作空间。

程序打开第一视角窗口，以约 1 Hz 打印 `/tello/pose` 的世界坐标位置和四元数，
等待飞控初始化后起飞约 0.48 m，向机体右侧以 0.10 m/s 飞行 2 个仿真秒，
短暂停顿，再向机体前方以 0.10 m/s 飞行 2 个仿真秒，最后降落。
两段运动的理想位移各约 20 cm，这是定时速度演示，不是精确位置闭环。

降落成功后向 `/tello/judge` 发送一次示例 `rg`（旋转柜红、固定柜绿），
**不是视觉识别结果，会占用本轮首次球色提交**，正式比赛前请重新启动场景。
可在另一个终端用 `rostopic echo /final/events` 查看裁判反馈。
结束时打印 `Demo finished` 并关闭图像窗口；中途异常或 Ctrl+C 会尝试请求降落，
若 ROS/仿真已停止则无法保证降落，请检查仿真状态。
这不是完整比赛解法，也不包含球色、窗标和红点识别；降落位置不在目标台，不计目标台得分。

可在第三个终端观察接口（每次先加载工作空间）：

```bash
source ~/catkin_ws/devel/setup.bash
rostopic echo /final/events   # 裁判是否收到并接受 rg；Ctrl+C 停止查看
# 也可以分别查看：
rostopic echo /tello/pose     # world 绝对位姿，米 / 四元数
rostopic echo /tello/state   # 最终应为 armed: false、landed_state: 1
```

若图像窗口无法打开，请从已登录的桌面终端运行，并确认 `echo "$DISPLAY"` 非空。
若提示找不到 `mavros` 或 `cv_bridge`，先运行依赖安装脚本；不要仅凭成功编译判断运行依赖齐全。

### 本机实测（2026-10-15）

在实际 PX4 + Gazebo 场景运行 `demo.py`，图像窗口正常打开，绝对位姿持续打印，
起飞和降落 Action 均返回成功，程序打印 `Demo finished` 并正常退出。
监测器收到 570 帧 320×240 图像；最终 `armed=false`、`landed_state=1`。
本轮 `rg` 收到裁判反馈 `accepted=true`、`reason=ball_result_recorded`、`score_delta=0`，
说明消息已接收，但示例颜色并不匹配本轮答案。

实际最高模型原点离地约 44.6 cm（起飞请求是相对上升 48 cm，控制器使用估计高度且有完成容差）。
从运行开始到落地，世界坐标 X 增加约 20.3 cm、Y 增加约 10.0 cm；
出生朝向下分别对应向右和向前。此结果包含起降及停顿时的漂移，不能当作精确航点控制。
若作业需要准确到点，应基于 `/tello/pose` 做位置反馈控制，而非仅按时间发送速度。

本机测试临时加载已有 MAVROS 编译产物，未改动原工程；学生仍应使用依赖安装脚本配置 MAVROS。
更完整的验收范围与历史记录见 [VALIDATION](docs/VALIDATION.md)。

## 5. 编写学生程序

主要修改 `tello_control/scripts/demo.py`，可在 `tello_control` 下继续增加 Python/C++ 节点。
新增依赖或可执行文件时，同步修改该包的 `package.xml` 和 `CMakeLists.txt`，然后重新编译。

| 接口 | 用途 |
| --- | --- |
| `/tello/front_cam/camera/image` | 第一视角图像，`sensor_msgs/Image` |
| `/tello/front_cam/camera/camera_info` | 相机内参 |
| `/tello/pose` | Gazebo 世界坐标绝对位姿（真值），`geometry_msgs/PoseStamped` |
| `/tello/odom` | PX4 估计位姿/速度，`nav_msgs/Odometry` |
| `/tello/state` | 飞控连接、解锁和就绪状态，JSON 字符串 |
| `/tello/cmd_vel` | 速度控制，`geometry_msgs/Twist` |
| `/tello/takeoff`、`/tello/land` | 起降 Action，类型由 `tello_competition` 提供 |
| `/tello/judge` | 球色和红点到达提交，`std_msgs/String` |
| `/final/status`、`/final/events` | 分数和裁判反馈，JSON 字符串 |

无人机公共话题与起降 Action 统一使用 `/tello/` 前缀，不保留旧名称别名。
机体/相机坐标系分别为 `tello/base_link`、`tello/front_camera_optical`；世界坐标系仍为 `world`。
`/final/status`、`/final/events` 等比赛接口及内部 MAVROS/Gazebo/教师命名空间保持不变。

速度命令中的 `linear.x` 为机体向前、`linear.y` 为机体向左、`linear.z` 为世界向上，
`angular.z` 为偏航角速度。单位是 m/s、rad/s，建议 20 Hz 连续发布；0.5 s 未收到新指令会置零。
世界坐标 X 向右、Y 从起点朝白板、Z 向上。公共里程计与控制坐标的使用详见接口文档。

`/tello/pose` 可供学生定位，直接给出 Gazebo 中无人机模型原点的位置（米）和姿态（四元数），
`header.frame_id=world`，无需再加出生点偏移。学生模板通过 `self.pose` 保存最新消息。
查看方法：`rostopic echo /tello/pose`。此接口不改变 PX4 内部估计或起降控制。

学生需要实现视觉识别、导航、后退观察和结果提交；不得通过内部话题读取答案。
完整消息类型、速度限制、提交格式和裁判条件见 [学生接口](docs/student_api.md)。

### 学生分发包范围

分发整个 `tello_sim` 目录或对应压缩包即可；它包含三个功能包、课程文档及配图、
依赖安装/维护工具和回归测试。不包含本机验收日志、录屏、接口采样、临时工作空间或构建缓存，
也不包含旧地图、旧比赛解法和教师录像脚本。
`tello_px4_runtime/runtime/` 中的 PX4 可执行文件、共享库和地理数据是必要的运行组件，
不是应删除的调试产物。学生仍需按第 1 节安装系统依赖。

## 6. 任务流程与计分

场地 2.75×2.75 m，三扇窗口的净尺寸均为 **宽 0.35 m × 高 0.25 m**，
窗洞中心离地 **0.82 m**，下沿离地 0.695 m、上沿离地 0.945 m；白板灯位为 3×3 布局。
裁判保留原有保守机体包络：穿窗期间横向中心误差需严格小于 3.5 cm，
高度偏差需严格小于 7 cm。这是计分限制，不等同于机体刚好不碰窗框的几何余量。

场地独立尺寸和位置以整厘米设置，半厘米按绝对值向上取整；窗洞中心高度按指定值设为 82 cm。
由中心和尺寸推导的边缘、几何体半高仍保留小数，以免改变净尺寸。
机体尺寸、装配/渲染间隙、飞控参数和裁判安全阈值不按厘米取整。

| 场地参数 | 当前值（cm） |
| --- | --- |
| 场地边长 | 275 |
| 外围墙高 / 厚 | 138 / 6 |
| 窗墙长 / 高 / 厚 | 165 / 110 / 3 |
| 窗洞宽 / 高 / 中心离地 | 35 / 25 / 82 |
| 窗口红标半径 / 中心离地 | 6 / 104 |
| 柜体宽 / 深 / 高 | 22 / 15 / 55 |
| 柜口宽 / 高 / 中心离地 | 14 / 15 / 43 |
| 柜板厚 / 球半径 | 2 / 6 |
| 两柜中心 X；Y | −42、42；−72 |
| 白板宽 / 高 / 顶端离地；Y | 110 / 55 / 90；136 |
| 红灯半径 | 1 |
| 白板灯位横坐标 / 纵坐标（从左上角） | 14、55、96 / 7、28、48 |
| 起降台边长 | 33 |

教师修改场地参数后，执行 `python3 tools/sync_world.py` 同步静态地图；
可用 `python3 tools/sync_world.py --check` 检查配置与地图是否一致。
修改出生位置时，还需同步 `tello.launch` 中的出生参数。学生直接使用已生成的地图即可。

| 顺序 | 任务 | 分数 |
| --- | --- | --- |
| 1 | 从起飞台上升超过 0.30 m，并保持 0.5 s | 15 |
| 2 | 识别旋转柜、固定柜的球色，按此顺序一次提交两字符 | 10+10 |
| 3 | 完整机体连续穿过红标指定窗口 | 20 |
| 4 | 识别当前亮起的红点，飞到跟前并提交；后退观察，再完成下一盏，共三次 | 10×3 |
| 5 | 在目标降落台内平稳降落，满足高度、速度和倾角条件并保持 1 s | 15 |

球色只接受整轮第一次提交，例如 `rg` 表示旋转柜红球、固定柜绿球。
颜色编码为 `r/g/b`，不含空格。
红点依次提交 `target1`、`target2`、`target3`；每次无人机中心距亮灯中心必须严格小于 **0.275 m**。
裁判确认成功后才会熄灭当前灯并点亮下一盏。
“后退观察”是课程任务要求；当前裁判核验顺序和距离，不自动证明是否后退或使用视觉。

### 子任务示意

以下图片使用本课程场景与模型，由 Gazebo 原生相机采集，展示场景和任务目标。
起飞图拍摄于实际起降自检过程，其余为场地局部视图；图片不代表自动完成比赛。

**① 起飞：从蓝色起飞台上升。** 裁判确认上升高度和保持时间后计分。

![起飞任务：Tello 训练机实际飞离蓝色起飞台](docs/images/takeoff.png)

**② 识别球色：依次观察旋转柜和固定柜。** 等待球进入视野，再按“旋转柜、固定柜”的顺序
向 `/tello/judge` 提交两个颜色字符，例如 `gb`。示例图中的颜色仅对应本次场景。

![球色识别任务：旋转柜和固定柜中的彩色球](docs/images/ball_recognition.png)

**③ 穿窗：寻找上方带红色标记的窗口。** 调整位置和高度，让完整机体连续穿过指定窗洞；
此项由裁判自动判定，无需发送到点消息。

![穿窗任务：三个窗洞及指定窗口上方的红色标记](docs/images/window.png)

**④ 三灯任务：观察当前亮起的红点，接近后提交。** 白板为 3×3 灯位，每次只亮一盏。
靠近至距离小于 0.275 m 后，依次提交 `target1`、`target2`、`target3`；
每次确认成功后先后退，重新观察下一盏灯的位置，再接近。

![三灯任务：九宫格白板与当前亮起的一盏红灯](docs/images/red_lamps.png)

**⑤ 降落：完成三灯后飞向绿色目标台。** 在台内平稳落地，满足高度、速度、倾角和保持时间要求。

![降落任务：场地另一角的绿色目标降落台](docs/images/landing.png)

查看裁判反馈：

```bash
rostopic echo /final/status
rostopic echo /final/events
```

需要重来时，先停止学生控制程序，再停止并重新启动仿真。
`/final/reset` 和 `/final/randomize` 留作教师调试接口，学生日常练习建议完整重启以重新初始化飞控。

## 7. 常见问题

- **找不到功能包**：确认目录层级正确，并执行 `source ~/catkin_ws/devel/setup.bash`。
  使用 `rospack find tello_competition` 检查当前解析到的路径，避免加载旧课程工作空间。
- **找不到 MAVROS、Gazebo 插件或共享库**：执行依赖安装脚本；可用
  `rosrun tello_px4_runtime check_runtime.py --integrity --libraries` 检查 PX4 运行文件。
- **相机无图、图形初始化失败**：确认当前桌面可用；`gui:=false` 仍然需要图形渲染支持。
  先检查 `rostopic hz /tello/front_cam/camera/image`，再检查 Gazebo 的报错。
- **刚启动不能起飞**：等待 `/tello/state` 中 `ready` 为真，并再留几秒给飞控估计器初始化。
- **端口占用**：退出之前的 PX4/Gazebo 仿真。程序不会自动结束其他仿真进程。
- **编译时 Python 包找不到**：退出 Conda，使用上面的 `/usr/bin/python3` 编译命令。

课程代码及模型来源见 [THIRD_PARTY.md](THIRD_PARTY.md)，本机验收记录见 [docs/VALIDATION.md](docs/VALIDATION.md)。
教师重新构建 PX4 运行组件的方法见 [docs/MAINTENANCE.md](docs/MAINTENANCE.md)。
