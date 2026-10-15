if(NOT DEFINED BINARY)
  message(FATAL_ERROR "Pass -DBINARY=<copied runtime binary>")
endif()
file(RPATH_REMOVE FILE "${BINARY}")
