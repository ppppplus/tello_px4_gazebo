# 来源、许可及分发边界

- 本仓库原创控制/裁判/教学代码和程序生成的训练外观：BSD-3-Clause，见 LICENSE。
- 动力学模板 tools/tello/training_dynamics.sdf 衍生自 PX4 v1.14.3 的 Gazebo Classic Iris/GPS SDF，
  插件配置沿用该体系，质量、惯量、电机、碰撞和传感器配置为本项目调整。
  PX4 源码提交锁定于 versions.lock，BSD-3-Clause 通知保留在 licenses/PX4-BSD-3-Clause.txt。
- Gazebo Classic 上游包声明 BSD；具体源码还包含 Apache-2.0 等文件级声明，
  以下载后各文件头为准，不统一重新授权其全部代码。
- MAVROS/MAVLink 不打包进本仓库，通过固定上游提交获取；各自的 GPL/LGPL/BSD 等声明保留在源仓库。
- EGM96-5 地理数据从 GeographicLib 项目数据发布地址下载并校验；不是本仓库原创。
- 历史 albanomarcus/tello_pkg 网格许可证为 TODO，本仓库不提交原始及派生网格，也不自动下载它们。
  相关详细模型视频/截图和教师满分解法也不进入 Git。不要自行强制添加被忽略资源后公开分发。

新训练外观完全由基础几何体构建，无第三方网格/贴图，无官方标志；
Tello/PX4/Gazebo 名称仅用于说明兼容目标，不代表官方出品、授权背书或实机标定。
