# 学生接口：Tello 尺寸决赛版

## 坐标、控制与相机

- world：X 向右，Y 由起飞区朝白板，Z 向上；单位米、秒、弧度。
- /quadrotor/cmd_vel：linear.x 机体向前、linear.y 机体向左、linear.z 世界向上，angular.z 偏航角速度。
- 限制：水平各轴 0.5 m/s、垂直 0.35 m/s、偏航 0.8 rad/s。至少 10 Hz 发布，建议 20 Hz。
- 0.5 s 没有新速度命令会置零；零速度命令不等于严格位置锁定，观察目标时应主动修正漂移。
- 默认原生 Gazebo 相机：320 × 240，目标 20 Hz，水平视角约 60°，频率受仿真性能影响。
- 相机安装于机体系 (0.036, 0, 0.005) m。内参以 camera_info 为准。
- 可选 software_camera 是简化几何投影，不能用于墙柜遮挡/真实视觉验收。

## 允许使用的接口

| 名称 | 类型 | 用途 |
| --- | --- | --- |
| /quadrotor/cmd_vel | geometry_msgs/Twist | 发布速度 |
| /quadrotor/odom | nav_msgs/Odometry | 公共估计位姿/速度 |
| /quadrotor/state | std_msgs/String（JSON） | ready、connected、armed、mode |
| /front_cam/camera/image | sensor_msgs/Image | 第一视角 |
| /front_cam/camera/camera_info | sensor_msgs/CameraInfo | 相机参数 |
| /quadrotor/takeoff | px4_competition/TakeoffAction | 起飞，height 为相对当前高度的上升量 |
| /quadrotor/land | px4_competition/LandAction | 降落，空 goal |
| /quadrotor/judge | std_msgs/String | 提交颜色和到点结果 |
| /final/status、/final/events | std_msgs/String（JSON） | 公开分数与裁判确认，不含灯位答案 |

学生不得读取 /teacher/*、/gazebo/*、/mavros/* 或任务答案相关参数/服务。
公共静态场地几何可以使用；本地 ROS 无权限隔离，正式比赛须教师环境验收。

Action 接口可接受 0.3～2.0 m 的起飞高度请求，但当前场景不意味着任意高度都安全。
起降自检建议 height=0.48；不要直接照搬原 5 m 场地的航点。
学生模板在 src/student_solution/scripts/student_node.py；默认只监听，--smoke 才实际起降。

## 流程与计分

| 项目 | 分值 | 条件 |
| --- | --- | --- |
| 起飞 | 15 | 起飞台上升超过 0.30 m，保持 0.5 s |
| 旋转柜球色 | 10 | 两字符提交的第一位正确 |
| 固定柜球色 | 10 | 两字符提交的第二位正确 |
| 窗口 | 20 | 完整机体连续穿过红标指定窗，不是质心穿过即可 |
| 三灯 | 30 | 顺序提交，每灯 10 分，中心距亮灯严格小于 0.275 m |
| 降落 | 15 | 目标台内，z ≤ 0.04 m、速度 < 0.10 m/s、倾角 < 10°，保持 1 s |

球色发布如 rg：旋转柜红色、固定柜绿色；只能 r/g/b，整轮只接受首次球色提交。
灯发布 target1、target2、target3；提交成功后下一盏亮起。
每次到达后退回能看清整个白板的位置，再根据图像识别新红点。
“后退观察”是演示与学生任务要求，当前裁判核验顺序和距离，不自动判定是否后退/使用视觉。
起降、穿窗由裁判自动判定。当前水平裁判包络为 0.135 m，上下偏移 ±0.045 m，是小倾角近似。
不要修改裁判、场景、动力学或通过内部话题读取答案来提高分数。
