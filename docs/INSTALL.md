# 安装与可复现构建

## 支持范围

Ubuntu 20.04 x86_64，系统 Python 3.8、ROS Noetic、Gazebo Classic 11。
原生 GUI/相机依赖桌面和 OpenGL；只检测到 DISPLAY 并不能证明渲染可用。
本项目保留旧版教学栈，不自动升级为 ROS 2 或新版 Gazebo。
PX4 版本兼容参考：https://docs.px4.io/v1.14/en/dev_setup/dev_env_linux_ubuntu

## 全新系统

1. 先安装 Git，并按官方 Noetic 安装文档配置 Ubuntu universe 与 ROS apt 软件源：
   https://wiki.ros.org/noetic/Installation/Ubuntu
2. 拉取本仓库，运行 ./setup.sh --install-system。
3. 切入桌面，运行 ./doctor.sh，再运行 ./run.sh seed:=11。
4. 第二终端 source scripts/env.sh，执行学生 --smoke 起降检查，确认有原生相机图像。

安装脚本不擅自改软件源、添加信任密钥、移除现有软件或升级操作系统。
config/system-packages.txt 列出需要的系统包；源不可用时应修复软件源或使用经学校验证的镜像。
没有 ROS 软件源时安装脚本会明确停止，不会给出成功提示。

## 构建过程

setup.sh 获取固定源码 → 应用两项兼容补丁 → 下载并校验 EGM96-5 数据 →
创建项目私有 .venv-build → 安装 requirements-build.txt → 编译 PX4 和 Gazebo 插件 →
使用系统 Python 编译 ROS/MAVROS/学生包 → 单元测试与环境检查。

环境无编译产物时仍可完整构建，不依赖教师机器的路径、原网格或历史视频。
下载脚本遇到已存在但版本错误的依赖会停止，不 reset/覆盖用户修改。
重复运行补丁检测是幂等的。--no-fetch 不下载源码，但 Python 依赖若缺失仍可能需要网络。
上游源码提交、Python直接依赖和地理数据校验值固定；系统 apt 库仍随配置的软件源变化，
这不等于逐位一致的操作系统镜像。

## 常见问题

- ROS/PX4 已运行：正常关闭旧实例再启动；脚本不自动终止其他实例。
- 原生相机崩溃或黑屏：确认已进入桌面、DISPLAY/XAUTHORITY 正确，检查 OpenGL。
  gui:=false software_camera:=true 只用于无图形接口冒烟测试，不能验证真实视觉。
- 构建缓存路径冲突：保留/重命名对应 build/devel 目录，再构建；脚本不会递归删除文件。
- 不要激活 PX4 的 .venv-build 去运行 ROS 节点；使用 source scripts/env.sh。
- 学生起降测试停住：查看 /quadrotor/state，等待定位和 action 就绪；不要反复解锁。
- apt 报依赖冲突：先由机器管理员解决已有软件包状态；安装器带 --no-remove，
  不会为安装仿真自动删除其他软件。本机安装模拟发现既有非本项目软件及调试包冲突，
  本轮没有自动修复系统包管理器。

## 干净环境自动验收

.github/workflows/ci.yml 提供无本机构建缓存的容器构建任务，
包括完整依赖获取、PX4/插件/ROS 构建及静态测试。
CI 无桌面，不宣称验证原生相机或完整决赛。推送仓库前该远端任务尚未执行。
本地实际验收范围见 docs/VALIDATION.md。
