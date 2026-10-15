# 来源与许可

- 原创教学、控制、裁判代码及白黑几何训练外观：BSD-3-Clause，见 `LICENSE`。
- PX4：v1.14.3，提交 `1dacb4cdef2d7145754fc788fa8dc482eed74b40`。
  上游为 https://github.com/PX4/PX4-Autopilot 。运行文件包含在
  `tello_px4_runtime/runtime/bin` 和 `runtime/etc`，BSD 通知见该包 `licenses/`。
- PX4 Gazebo Classic 插件：提交 `2e3ed9bfb04d8865e59380afa575dd37b0d6c8e0`，
  上游为 https://github.com/PX4/PX4-SITL_gazebo-classic 。
  所需插件及消息库位于 `runtime/lib`。文件级 BSD/Apache 版权通知保留在
  `runtime/GAZEBO_NOTICES.txt`，Apache 2.0 完整文本位于 `licenses/`。
- 动力学源自该版本 PX4 的 Iris/GPS SDF，并作小型四旋翼质量、惯量、电机和传感器调整。
  自定义机型配置位于 `airframes/10420_gazebo-classic_tello`。
- EGM96-5 数据来自 GeographicLib 的数据发布，位于 `runtime/geographiclib/geoids/egm96-5.pgm`。
  来源：https://downloads.sourceforge.net/project/geographiclib/geoids-distrib/egm96-5.tar.bz2 。
  文件 SHA-256 固定在 `versions.lock`，数据文件原始头部保留。
- ROS、Gazebo、MAVROS 通过系统包管理器安装，遵循各自许可证，不包含在本目录。
- 未打包原详细 Tello 第三方网格、品牌贴图、教师完整比赛解法和历史视频。

为方便课程分发，本包包含 **Ubuntu 20.04 x86_64 的预编译 PX4 运行组件**；
学生使用 catkin 编译的是 ROS 消息和课程功能包。运行组件不是跨平台二进制。
教师可根据固定版本、兼容补丁及 `docs/MAINTENANCE.md` 重新构建。
发布的运行组件去除了调试信息和教师机器的 ELF 库搜索路径，并通过 manifest 逐文件校验。
训练机为约 85 g 的近似模型，不是 Tello 官方固件或经过实机标定的数字孪生。
