# Tello 尺寸训练机 + PX4 + Gazebo 决赛（学生版）

支持基线：**Ubuntu 20.04 x86_64 / ROS Noetic / Gazebo Classic 11 / PX4 v1.14.3**。
这是 ROS catkin 工作空间；PX4 与 Gazebo 飞控插件独立构建。
需要可用的桌面/OpenGL，联网获取固定版本依赖，并预留约 10 GB 磁盘空间。
ROS/Gazebo 属于旧版教学环境，不应向公网开放 ROS 端口。

## 首次使用

先按 [安装说明](docs/INSTALL.md) 配置官方 ROS Noetic 软件源，然后：

```bash
git clone <本仓库地址>
cd <仓库目录>
./setup.sh --install-system
./doctor.sh
./run.sh seed:=11
```

安装系统软件时会请求 sudo；源码、Python 构建依赖、编译结果、地理数据和日志均留在本目录。
已装好系统依赖可省略 --install-system。首次会编译 PX4、Gazebo 插件及 ROS 包，耗时取决于机器。
源码锁定在 versions.lock；兼容修改以 patches/ 保存，不依赖教师电脑的构建缓存。
不支持同时启动两个共享默认端口的实例；脚本不会杀掉其他进程。

第二个终端：

```bash
source scripts/env.sh
rosrun student_solution student_node.py
# 确认无人机在起点、未解锁后，测试起飞—悬停—降落：
rosrun student_solution student_node.py --smoke
```

默认学生节点只订阅公开数据，不自动飞行、不包含比赛解法。
在 src/student_solution/ 中实现自己的识别、导航及提交逻辑。
接口参数与计分见 [学生接口](docs/student_api.md)。

## 比赛与外观

场地 2.75 × 2.75 m，窗洞 0.5225 × 0.33 m，白板 3 × 3 灯。
起飞 → 两柜球色识别 → 穿红标窗 → 后退观察、依次接近新亮起的三灯 → 降落。
三灯须依次提交且距离严格小于 0.275 m；满分 100。

学生仓库默认使用本项目程序生成的白黑几何训练外观，不读取或下载授权不明的第三方网格。
原详细 Tello 网格和历史视频仍保留在教师本地，但不进入 Git。
动力学保持 85 g 近似小型四旋翼配置、理想 IMU 和无噪声仿真 GPS；不是 Tello 官方固件或实机数字孪生。
详见 [第三方来源](THIRD_PARTY.md)；不要把旧详细网格视频当作新外观的渲染证据。

## 维护与验证

```bash
./run_tests.sh
./doctor.sh --build-only
./setup.sh --no-fetch              # 已获取源码；仍安装/核对私有 Python 构建依赖并构建
./setup_workspace.sh               # 只重编 ROS 学生代码
python3 tools/tello/build_training_model.py
```

[教师操作](docs/teacher_guide.md) · [验收记录](docs/VALIDATION.md) · [授权](LICENSE)

build*/devel*、vendor/、下载的 MAVROS/MAVLink、日志、视频和虚拟环境均不提交。
不要把工作空间当作可移动的二进制包：移动目录后请保留/重命名旧构建目录并重新构建。
正式评分应在教师环境执行；ROS 1 话题命名和分包不是防作弊或权限隔离机制。
