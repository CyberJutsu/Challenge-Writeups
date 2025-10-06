cmake_minimum_required(VERSION 3.18.1)

project("pixelblackout")

add_library(
        native-lib
        SHARED
        crypto_bridge.cpp
)

find_library(
        log-lib
        log
)

target_link_libraries(
        native-lib
        ${log-lib}
)
