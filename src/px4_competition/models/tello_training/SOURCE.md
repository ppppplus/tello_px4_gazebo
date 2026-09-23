# 学生版训练外观

外观由 tools/tello/build_training_model.py 使用盒、圆柱和分段护罩直接生成。
未读取、转换或分发原 albanomarcus/tello_pkg 的任何网格；无品牌标识、无贴图。
它是白黑配色的小型四旋翼训练替代外观，不是 Tello 官方或精确外形。
外观代码与原始几何采用本仓库 BSD-3-Clause 许可。

动力学模板衍生自 PX4 v1.14.3 Gazebo Classic Iris/GPS SDF，保持本项目已验证的
85 g 质量、惯量、电机、碰撞及理想传感器配置；许可证说明见 THIRD_PARTY.md。
新外观不改变碰撞或动力学，但历史详细网格视频不能作为本外观的渲染证明。
