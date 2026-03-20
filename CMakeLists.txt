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

# ── Cross-Platform Compiler Configuration ────────────────────────────────────
if (MSVC)
    # MSVC: /W4 = high warning level, /WX = warnings as errors
    #       /MT = static CRT linkage (no vcredist dependency)
    #       /EHs-c- = disable C++ exceptions on the hot path
    #       /O2 = maximize speed, /arch:AVX2 = use AVX2 intrinsics
    add_compile_options(/W4 /WX /O2 /arch:AVX2 /MT /EHs-c- /DNDEBUG)
else()
    # GCC / Clang: strict warnings + treat as errors
    add_compile_options(-Wall -Wextra -Werror)
endif()

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

if (NOT MSVC)
    target_link_libraries(test_structures PRIVATE pthread)
endif()

add_test(NAME DataStructureTests COMMAND test_structures)

# ── Benchmarks ───────────────────────────────────────────────────────────────
add_executable(latency_bench benchmarks/latency_bench.cpp)
target_include_directories(latency_bench PRIVATE ${PROJECT_SOURCE_DIR}/include)

if (MSVC)
    # HFT Optimization Flags (MSVC):
    # /O2: Maximize speed
    # /arch:AVX2: Use AVX2 SIMD instructions
    # /EHs-c-: Disable exception handling overhead
    # /GL: Whole-program optimization (MSVC equivalent of -flto)
    # /DNDEBUG: Disable assertions
    target_compile_options(latency_bench PRIVATE /O2 /arch:AVX2 /EHs-c- /GL /DNDEBUG)
else()
    # HFT Optimization Flags (GCC/Clang):
    # -O3: Max optimization
    # -march=native: Use local CPU architecture instructions (AVX2/AVX-512)
    # -flto: Link-time optimization across files
    # -fno-exceptions: Remove exception handling overhead from the hot path
    # -DNDEBUG: Disable assertions
    target_compile_options(latency_bench PRIVATE -O3 -march=native -flto -fno-exceptions -DNDEBUG)
    target_link_libraries(latency_bench PRIVATE pthread)
endif()
