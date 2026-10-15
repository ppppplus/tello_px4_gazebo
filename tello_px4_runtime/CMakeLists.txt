cmake_minimum_required(VERSION 3.0.2)
project(tello_px4_runtime)
find_package(catkin REQUIRED)
find_package(PythonInterp 3 REQUIRED)
catkin_package()

# Catkin verifies the pinned runtime without downloading into the source tree.
execute_process(COMMAND ${PYTHON_EXECUTABLE}
  ${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_runtime.py --integrity
  RESULT_VARIABLE runtime_status)
if(NOT runtime_status EQUAL 0)
  message(FATAL_ERROR "Tello PX4 runtime validation failed; see the diagnostic above.")
endif()
catkin_install_python(PROGRAMS scripts/px4_node.py scripts/check_runtime.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
install(DIRECTORY runtime airframes licenses patches
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION} USE_SOURCE_PERMISSIONS)
install(FILES versions.lock DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
