# GammaFlow: Ultra-Low Latency C++20 Risk Engine

GammaFlow is a state-of-the-art, deterministic, ultra-low latency C++20 risk evaluation engine tailored for high-frequency trading and quantitative finance environments. It evaluates streaming risk events in raw machine cycles with completely predictable tail latencies.

## Architecture
GammaFlow is built to be 100% wait-free on the hot path. 
* **Zero-Allocation Object Pool**: Reuses pre-allocated slabs of memory to eliminate all `operator new`/`delete` calls during execution.
* **Lock-Free SPSC Ring Buffer**: A Single-Producer Single-Consumer queue utilizing `std::atomic` acquire/release semantics and bitwise mask wrapping to eliminate expensive modulo division, mutexes, and locks.
* **Deterministic Fixed-Point Math**: Replaces floating-point logic across pricing and quantities with perfectly deterministic sub-penny integer representations, ensuring reproducible risk calculations without FPU pipeline overhead.

## Synthesized Ultimate Architecture
To achieve sub-microsecond tick-to-trade, the GammaFlow pipeline targets the bare metal using a simultaneous blend of every extreme historical optimization:
* **Thread-Affinity Core Pinning**: Locks the Producer to Core 2 and the Consumer to Core 3 using Windows `SetThreadAffinityMask` and `SetThreadIdealProcessor` to entirely avoid Core 0 OS interrupt throttling.
* **TIME_CRITICAL Priority**: Disables dynamic thread scheduler boosting and elevates the process to `REALTIME_PRIORITY_CLASS`.
* **Hardware Spin-Waits**: Replaces `yield()` and context switches with the Intel `_mm_pause()` instruction to heavily optimize the CPU spin loops.
* **Cache-Line Padding**: Uses strict `alignas(64)` payload padding to guarantee 64-byte payload offsets, completely destroying false-sharing cache invalidations between cores.
* **Memory Locking**: Uses Windows `VirtualLock()` alongside Working Set expansion to pin the ring buffer and data structures natively into physical RAM, terminating unpredictable disk-based page-faults.
* **Instruction Fencing**: Swaps `__rdtsc()` for strictly serialized `__rdtscp(&aux)` CPU timestamps to protect timestamp metrics against out-of-order execution anomalies.
* **Hybrid Branching Strategy**: Uses predictable `if/else` checks for structural constraints (where the CPU branch predictor excels) and falls back to strictly branchless boolean algebra arrays for randomized, data-dependent risk evaluation. The `RiskEvaluator::evaluate()` method blends both concepts to maximize speed without sacrificing tail determinism.

## Benchmarks
The metrics below were captured on bare metal AC-power against 1,000,000 randomized evaluation bursts. 

### End-to-End Pipeline (Tick-to-Trade)
* **Median (p50)**: `132 ns` (421 cycles)
* **p95**: `152 ns` (485 cycles)
* **p99**: `162 ns` (517 cycles)
* **p99.9**: `14.10 µs` (45,029 cycles)
* **Minimum**: `82 ns` (261 cycles)

*Pipeline averages a sustained throughput in excess of 60.3 Million events/sec.*
