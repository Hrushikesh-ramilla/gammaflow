cmake_minimum_required(VERSION 3.20)
project(GammaFlow
    VERSION 0.1.0
    DESCRIPTION "High-performance financial risk analytics engine"
    LANGUAGES CXX
)

# ── C++20 Standard ───────────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Strict Compiler Warnings ────────────────────────────────────────────────
add_compile_options(-Wall -Wextra -Werror)

# ── Include Paths ────────────────────────────────────────────────────────────
include_directories(${PROJECT_SOURCE_DIR}/include)

# ── Export compile_commands.json for tooling ─────────────────────────────────
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ── Source Files (placeholder) ───────────────────────────────────────────────
# add_executable(gammaflow src/main.cpp)

# ── Tests ────────────────────────────────────────────────────────────────────
enable_testing()

add_executable(test_structures tests/test_structures.cpp)
target_include_directories(test_structures PRIVATE ${PROJECT_SOURCE_DIR}/include)
target_link_libraries(test_structures PRIVATE pthread)

add_test(NAME DataStructureTests COMMAND test_structures)

# ── Benchmarks (placeholder) ────────────────────────────────────────────────
# add_subdirectory(benchmarks)
