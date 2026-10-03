cmake_minimum_required(VERSION 3.10)
project(CHLegacyCPUProbe LANGUAGES CXX)
add_executable(cpu_probe cpu_probe.cpp)
target_compile_options(cpu_probe PRIVATE /Od)
