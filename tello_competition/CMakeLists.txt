cmake_minimum_required(VERSION 3.0.2)
project(tello_competition)

find_package(catkin REQUIRED COMPONENTS
  actionlib actionlib_msgs gazebo_msgs geometry_msgs message_generation
  nav_msgs rospy sensor_msgs std_msgs std_srvs tf)

catkin_python_setup()
add_action_files(DIRECTORY action FILES Takeoff.action Land.action)
generate_messages(DEPENDENCIES actionlib_msgs std_msgs)
catkin_package(CATKIN_DEPENDS actionlib actionlib_msgs message_runtime)

catkin_install_python(PROGRAMS
  scripts/camera_preview.py
  scripts/final_judge.py
  scripts/final_scene.py
  scripts/gazebo_truth.py
  scripts/student_bridge.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})

install(DIRECTORY action config launch models worlds
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

if(CATKIN_ENABLE_TESTING)
  catkin_add_nosetests(tests)
endif()
