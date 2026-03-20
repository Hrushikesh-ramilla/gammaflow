# 🚀 GammaFlow

### Ultra-Low Latency C++20 Execution Engine

*Deterministic • Cache-Aware • Hardware-Constrained Execution*

---

<p align="center">

![C++20](https://img.shields.io/badge/C%2B%2B-20-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![Architecture](https://img.shields.io/badge/Architecture-SPSC%20Lock--Free-green)
![Latency](https://img.shields.io/badge/Median%20Latency-~92ns--142ns-red)
![Determinism](https://img.shields.io/badge/Deterministic-Yes-brightgreen)
![Allocations](https://img.shields.io/badge/Allocations-Zero%20Hot%20Path-orange)

</p>

---

<p align="center">
  <img src="assets/architecture.png" alt="GammaFlow Architecture" width="100%">
</p>

---

## 🔬 Abstract

GammaFlow is a deterministic, ultra-low latency C++20 execution pipeline designed for high-frequency trading environments. It processes streaming data in **sub-200 nanoseconds**, exploring the practical limits of user-space performance on modern x86 architectures.

The system is engineered by systematically eliminating all avoidable abstraction overhead and aligning execution with:

* CPU cache hierarchy (L1/L2/L3)
* MESI cache coherency protocol
* Inter-core data transfer latency
* OS scheduling and interrupt behavior

> GammaFlow operates at the boundary where latency is no longer a software problem, but a function of cache coherency physics and system-level interruptions.

---

## 🧠 Overview

GammaFlow is not a throughput-optimized system.
It is a **deterministic latency pipeline** designed to answer:

> *What is the minimum achievable latency of a user-space system when all software overhead is removed?*

The result:

* **~92ns lower-bound execution (unfenced pipeline floor)**
* **~142ns median deterministic latency (fully fenced, aligned, measured)**
* **~2–18µs tail latency (OS + hardware interrupt domain)**

Execution is reduced to:

> **cache line ownership transfer + L1-resident computation**

---

## 🧠 Design Philosophy

GammaFlow is built on a hardware-first philosophy:

> Modern latency is dominated by microarchitectural behavior, not algorithmic complexity.

### This enforces strict constraints:

* ❌ No dynamic memory allocation (`new`, `malloc`)

* ❌ No locks, mutexes, or kernel primitives

* ❌ No syscalls in the hot path

* ❌ No scheduler dependence during steady-state

* ✅ Cache-line aligned data structures

* ✅ Explicit memory ordering (`acquire/release`)

* ✅ Core affinity and isolation

* ✅ Branch prediction-aware execution design

---

## 🏗️ System Architecture

<p align="center">
  <img src="assets/architecture.png" alt="GammaFlow System Architecture" width="100%">
</p>

GammaFlow follows a strictly isolated dual-core execution topology:

* **Core 2 → Producer**
* **Core 3 → Consumer**

No syscalls or kernel transitions occur in the hot path.

---

## 🔁 End-to-End Data Flow

```text
Producer (Core 2)
    ↓
Store → Cache Line enters Modified (MESI)
    ↓
SPSC Ring Buffer (Cache-Aligned, Lock-Free)
    ↓
Cache Line Ownership Transfer (MESI, ~50–150 cycles)
    ↓
Consumer (Core 3, Acquire Load)
    ↓
RiskEvaluator::evaluate()
    ↓
Branchless + Predictable Hybrid Compute
```

---

## ⚙️ Core Components

---

### 🧩 1. SPSC Ring Buffer

#### Structural Properties

* Capacity: **65536 (2¹⁶)**
* Strict Single-Producer Single-Consumer model
* Wait-free on the hot path
* No contention, no locking

---

#### Zero-Cost Index Wrapping

```cpp
next = (idx + 1) & mask_;
```

* Eliminates integer division (`idiv`)
* Compiles to single-cycle bitwise AND

---

#### Cache Line Isolation (Critical)

```cpp
struct alignas(64) PaddedEvent {
    gammaflow::RiskEvent event;
    std::uint64_t enqueue_tsc;
    char padding[64 - sizeof(gammaflow::RiskEvent) - sizeof(std::uint64_t)];
};
```

* Exactly **64 bytes per event**
* One event = one physical cache line
* Prevents false sharing completely

---

#### Head / Tail Separation

```cpp
alignas(64) std::atomic<std::size_t> head_{0};
alignas(64) std::atomic<std::size_t> tail_{0};
```

* Eliminates MESI invalidation contention
* Producer and Consumer never fight for the same cache line

---

#### Memory Ordering Model

| Operation      | Ordering               |
| -------------- | ---------------------- |
| Producer write | `memory_order_release` |
| Consumer read  | `memory_order_acquire` |

Guarantee:

> Writes by producer become visible to consumer without full memory fencing overhead.

---

### 🧠 2. Risk Evaluator (Hybrid Compute Pipeline)

GammaFlow deliberately avoids both:

* full branching (misprediction risk)
* fully branchless everywhere (wasteful for predictable cases)

Instead, it uses a hybrid model.

---

#### ✔ Structural Path (Predictable Branching)

```cpp
if (event.quantity.raw() <= 0 || event.price.raw() <= 0) {
    return RiskResult{event.id, 0, RiskTier::LOW};
}
```

* Near-zero misprediction
* Fast-path dominates execution

---

#### ✔ Algorithmic Path (Branchless Arithmetic)

```cpp
std::int32_t price_score =
      (event.price < penny_threshold) * 400
    + (event.price >= penny_threshold && event.price < low_price) * 300;
```

* Deterministic execution
* No pipeline flushes
* Exploits superscalar ALU parallelism

---

### 🔄 3. Inter-Core Communication (MESI Physics)

The dominant cost in GammaFlow:

> Cache line ownership transfer between CPU cores

#### Flow:

1. Producer writes → cache line enters **Modified (M)** state
2. Consumer attempts read → invalidation + transfer triggered
3. Ownership migrates → consumer reads locally

#### Latency:

* ~50–150 cycles depending on topology

This is the **true bottleneck** — not computation.

---

## 🧠 Memory Layout Evolution (Critical Optimization Journey)

---

### ❌ Initial Approach

```cpp
#pragma pack(push, 1)
```

#### Problems:

* Misaligned memory access
* Split loads across cache boundaries
* Undefined behavior risk
* Pipeline penalties on x86

---

### ✅ Final Approach

* Natural alignment restored
* Explicit padding introduced
* Compiler allowed to optimize layout safely

```cpp
static_assert(sizeof(PaddedEvent) == 64, 
              "PaddedEvent must exactly fill one cache line");
```

---

### 📌 Outcome

> Alignment correctness achieved while preserving latency characteristics, eliminating misaligned load penalties and improving architectural validity.

---

## 🧮 Latency Budget Breakdown

**Median Execution (~92ns – 142ns ≈ 300–450 cycles)**

| Component                | Cycles   |
| ------------------------ | -------- |
| `__rdtscp` serialization | ~30–50   |
| Cache coherency transfer | ~50–150  |
| Cache hierarchy movement | ~80–120  |
| Compute (branchless ALU) | ~100–150 |

---

## 📊 Benchmark Results

```text
Median (p50):        ~92 ns – 142 ns
p95:                 ~162 ns
p99:                 ~172 ns
p99.9:               ~2.35 µs
Min:                 ~82 ns
Max:                 ~82.23 µs
```

---

## 📈 Interpretation

* **92ns Floor**
  Lower bound of unfenced pipeline execution (no serialization barriers)

* **142ns Median**
  Fully fenced (`__rdtscp`), cache-aligned, deterministic execution baseline

* **p99 (~172ns)**
  Stable execution under minimal interference

* **p99.9 (~2.35µs – 18µs)**
  Boundary where OS and hardware interrupts dominate

---

## ⚠️ Tail Latency & System Boundary

### Sources of Jitter

* System Management Interrupts (SMI)
* Windows Deferred Procedure Calls (DPC)
* Timer interrupts
* Hypervisor scheduling ticks

---

### Critical Insight

> Tail latency is not caused by GammaFlow — it is imposed by the execution environment.

This represents the **hard boundary of Windows user-space determinism**.

---

## 🧪 OS-Level Optimizations (Windows)

* Thread affinity:

  * Core 2 → Producer
  * Core 3 → Consumer

* `REALTIME_PRIORITY_CLASS`

* `THREAD_PRIORITY_TIME_CRITICAL`

* Disabled priority boosting

* Hardware spin-wait:

```cpp
_mm_pause();
```

* Memory pinning:

  * `VirtualLock()`
  * Expanded working set (≥128MB)

* Pre-warming:

  * Ring buffer
  * TLB
  * Cache lines

---

## ⚖️ Determinism vs Throughput

| Metric              | GammaFlow Choice |
| ------------------- | ---------------- |
| Throughput          | ~50M+ events/sec |
| Determinism         | ✅                |
| Tail Predictability | ✅                |

---

### Tradeoffs

* SPSC instead of MPMC → zero contention
* No batching → minimum latency
* Busy spin → higher CPU usage, zero scheduler involvement

---

## 🚧 System Limits

GammaFlow has reached:

> **Hardware-bound latency regime**

Further improvements are constrained by:

* Cache coherency latency (inter-core fabric)
* OS interrupt model
* CPU microarchitecture

---

## 🚀 Future Work: Linux RT Migration

To break the OS latency barrier:

### Required:

* `PREEMPT_RT`
* `isolcpus`
* `nohz_full`
* `rcu_nocbs`

---

### Expected Results

| Metric | Target   |
| ------ | -------- |
| Median | ~130 ns  |
| p99.9  | < 500 ns |

---

## ▶️ Build & Run

```bash
cmake -B build
cmake --build build --config Release
.\build\Release\latency_bench.exe
```

---

## 📁 Project Structure

```text
gammaflow/
├── include/
│   ├── models.hpp
│   ├── ring_buffer.hpp
│   ├── types.hpp
│   └── evaluator.hpp
├── benchmarks/
│   └── latency_bench.cpp
├── assets/
│   └── architecture.png
├── CMakeLists.txt
└── README.md
```

---

## 🏁 Conclusion

GammaFlow is not simply an optimized program.

It is a **hardware-constrained execution experiment** demonstrating:

* Lock-free, allocation-free design
* Cache-aware memory structuring
* Deterministic execution under real-world system constraints

---

## 📌 Final Statement

> GammaFlow represents the boundary where software optimization ends, and hardware physics begins.

---
