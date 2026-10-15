# 教师维护

学生只需要 README 中的依赖安装、catkin 编译和 roslaunch。
本目录没有工作空间级 `src/`、`build/`、`devel/`，也没有根级 `package.xml`，
catkin 会递归发现三个功能包。保持这种层级，便于学生整体放入自己的 `src/`。

## 运行组件的来源

本次发布从原课程已运行的 PX4 v1.14.3 构建中提取 `bin/`、构建后的 `etc/`、
当前 SDF 使用的 Gazebo 插件及其 protobuf 消息库。打包工具复制后再 strip、移除 RPATH，
不会修改原 PX4 源码或编译产物。`runtime/manifest.json` 记录源代码版本和逐文件哈希。
日志、参数、ROS_HOME、用户配置、Gazebo 缓存和原工作空间构建缓存均不进入发布包。

## 从源码重建（仅教师需要）

环境仍为 Ubuntu 20.04 x86_64，需先安装 README 的运行依赖及以下编译依赖：

```bash
sudo apt-get install git ninja-build python3-dev python3-venv python3-pip \
  libgazebo11-dev libeigen3-dev libprotobuf-dev protobuf-compiler \
  libxml2-dev libxml2-utils qtbase5-dev libopencv-dev libtinyxml-dev \
  libtinyxml2-dev libgtest-dev libgmock-dev pkg-config
bash tools/build_runtime.sh
```

脚本会在新临时目录获取 `versions.lock` 固定的 PX4 和子模块，应用 `patches/` 的两项兼容补丁，
创建独立 Python 构建环境，构建 SITL 和插件，再输出一个新的 `runtime` 目录。
它不会覆盖课程包中的运行组件。脚本末尾显示输出位置；替换发布组件前先做完整回归。
该源码重建入口用于后续维护；本次交付的验收范围见 `VALIDATION.md`。

如果已有相同固定版本的 PX4 构建，也可直接提取：

```bash
python3 tools/pack_runtime.py \
  --px4-source /path/to/PX4-Autopilot \
  --geoid tello_px4_runtime/runtime/geographiclib/geoids/egm96-5.pgm \
  --output /path/to/new-runtime
```

输出目录必须不存在或为空。源码版本检查不能证明某个已有二进制对应哪个源码，
维护者仍需确保输入构建的来源，并完成编译后起降验证。

## 发布前验收

1. 把整个 `tello_sim` 复制到全新工作空间的 `src/`，仅加载 ROS Noetic 环境并执行 `catkin_make`。
2. 执行 `catkin_make run_tests` 和 `catkin_test_results`，检查规则与缩放场地回归。
3. 在桌面启动全新场景，检查 `/tello/state`、`/tello/pose`、里程计、相机、裁判，
   运行 `rosrun tello_control demo.py`。它会实际起飞、向右、向前、降落，并提交示例球色 `rg`；
   正式比赛前须重新启动场景，不能复用演示已提交的轮次。
4. 如使用安装空间，执行 `catkin_make install`，在新终端只加载 `install/setup.bash` 再测试。
5. 发布时排除 `__pycache__`、`.pyc`、日志、录像和任何学生/教师答案，不打包工作空间的构建目录。

正式评分要使用教师控制的环境。ROS 1 话题和源码没有访问权限隔离，
当前本地练习包不提供防作弊沙箱。
