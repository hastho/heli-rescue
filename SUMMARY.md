# Heli Rescue — Project Summary

## Project Stats

| Metric | Value |
|--------|-------|
| **Total code generated** | **2,764 lines** across 4 files |
| `main.py` | 1,844 lines (1,363 non-comment, 27 functions, 10 classes, 50 methods, 43 constants) |
| `AGENTS.md` | 108 lines (architectural documentation for agents) |
| `WORKFLOW_STATE.md` | 548 lines (project state, decisions, bug reports) |
| `TASK.md` | 265 lines (task description + evaluation notes) |
| **External assets** | 0 (all graphics procedurally drawn, all audio synthesized) |
| **Audio files (VGZ)** | 3 files in `tunes/` (~66 KB total, ~168s of OPL2 music) |
| **Python dependencies** | `pygame`, `ymfm-py` (both pip packages) |

## Bugs Found & Fixed

| # | Bug | Root Cause | Fix | Lines Changed | Discovered By |
|---|-----|------------|-----|---------------|---------------|
| 1 | VGZ music plays at **half speed** (octave lower, double duration) | Mixer at 22050 Hz but VGM parser accumulates at 44100 Hz. `pygame.mixer.Sound` plays at mixer rate. | Raised mixer to 44100 Hz, updated all SFX generation to match | 4 lines | Reviewer code review |
| 2 | **Engine drone** plays on title screen, conflicting with VGZ music | `sounds['engine'].play(-1)` called in `init_sounds()` before game starts | Engine starts only when entering PLAYING state; doesn't play during TITLE/GAME_OVER/VICTORY | 3 lines (1 add, 2 remove) | Planner (during playback testing) |
| 3 | VGZ playback **stuttering, wrong tempo, garbled** — "sounds wired" | Chunk-boundary rendering (0.1s chunks) delayed 100% of YM3812 writes by 50-100ms on average | Precise event-boundary rendering: generate audio up to each event's exact sample position | ~25 lines (loop replacement) | Planner diagnostic (0% events at correct position) |
| 4 | Engine sound **too loud** over VGZ music | Volume at 0.08 was still prominent | Halved to 0.04 | 1 line | User feedback |

## Agent Workflow Statistics

| Phase | Agents Involved | Handoffs |
|-------|----------------|----------|
| **Initial build** | planner → debater (×2 rounds) → implementor → reviewer | 4 handoffs |
| **VGZ music feature** | planner → debater → implementor → reviewer | 4 handoffs |
| **Sample rate fix** | reviewer → planner → implementor | 2 handoffs |
| **Engine life cycle fix** | implementor (direct fix) | 1 handoff |
| **Chunk timing fix** | planner (diagnostic) → implementor | 2 handoffs |
| **Engine volume fix** | implementor (direct fix) | 1 handoff |
| **Task/Summary docs** | planner | — |
| **Total** | | **~14 agent handoffs** |

## Main Difficulties Encountered

### 1. GME (libgme) YM3812 emulator produced silence
The first approach to VGZ playback used GME via Python ctypes bindings. GME correctly identified the VGZ files but produced **complete silence** — it misidentified the chip as "Sega SMS/Genesis" despite the VGM header specifying YM3812/OPL2. Switching to `ymfm-py` (MAME-grade emulation via Python bindings) immediately produced audible audio. **Lesson**: MAME's ymfm is the most reliable OPL2 emulator in Python.

### 2. Subtle sample rate interaction
The VGM format specification defines all timing at **44100 Hz** (wait 0x62 = 735 samples = 1/60s). The parser correctly accumulated samples at 44100, but `pygame.mixer.init()` defaults to **22050 Hz**. Since `pygame.mixer.Sound(buffer=...)` determines playback rate from the mixer, all VGZ audio played at half speed. This bug was invisible to code review — the parser returned the correct sample count, the buffer was the right size, but the mixer played it at the wrong rate. **Lesson**: Always verify mixer.sample_rate == parser.sample_rate.

### 3. Non-obvious chunk-boundary timing corruption
The original renderer processed YM3812 writes at 0.1s chunk boundaries and generated 0.1s of audio between checks. With ~322 writes/second (one every 3ms), 100% of writes were delayed by 50-100ms. This sounded like "wrong speed" and "stuttering" because note attacks were constantly late. The bug was only revealed when comparing precise (per-event) rendering vs chunked rendering: **only 3.8% of samples matched**. **Lesson**: Chunk-based audio generation is only safe if the chunk size is smaller than the minimum inter-event timing (~3ms = ~132 samples at 44100). Always verify timing assumptions with empirical comparison.

### 4. VGM format edge cases
VGM v1.50+ has a variable-length header where the data section doesn't start at a fixed offset. The parser must scan for the first valid command byte. Additionally, data blocks (0x67), GD3 tags after the end marker (0x66), and multi-chip commands all need handling. The decision to write a ~70-line inline parser instead of using external libraries (which had version incompatibilities) proved correct.

### 5. Sound lifecycle management
Coordinating when sounds start, stop, and restart across state transitions (TITLE → PLAYING → VICTORY/GAME_OVER → TITLE) required careful attention. The engine sound in particular was tricky because `play(-1)` at init time continues across state transitions unless explicitly stopped. The pattern that worked: **start sounds at the transition point where they're needed, stop them at the transition where they're no longer needed**.

### 6. PEP 668 system Python restriction
On Debian/Ubuntu, pip refuses to install packages into the system Python environment unless `--break-system-packages` is passed. This is a minor but consistent friction point for any Python project on modern Linux.

---

## Maintainability Evaluation

This section evaluates how easy this project is to maintain over time, especially
for an AI coding agent that may encounter it fresh.

### Current State (Risks)

| Risk | Severity | Details |
|------|----------|---------|
| **No dependency pins** | High | No `requirements.txt`, `pyproject.toml`, or `setup.cfg`. `pip install pygame ymfm-py` gets whatever is latest. A future `ymfm-py` 0.3.0 could change the YM3812 API and break `_render_vgz()`. `pygame` 2.7 might deprecate `mixer.Sound(buffer=...)` usage. |
| **No tests** | High | Zero tests. A maintainer cannot verify whether a change breaks anything without manually running the game. Critical paths (VGM parser, collision, state machine) have no regression safety net. |
| **Single monolithic file (1844 lines)** | Medium | Everything in one file makes it hard to isolate concerns. A VGM parser bug fix touches the same file as terrain generation. An agent navigating this must scan 1800+ lines to find what it needs. |
| **No type hints** | Medium | 0/27 functions have type annotations. An agent cannot statically verify that `_parse_vgm` returns `list[tuple[int, int, int]]` vs something else. This increases the risk of subtle type mismatches. |
| **No `__future__` annotations** | Low | Not currently a problem (Python 3.12), but if the project is ever auto-formatted or refactored with `from __future__ import annotations`, there could be surprises with `pygame.Surface` type hints (lazy evaluation). |
| **`ymfm-py` is niche** | Medium | Only 0.2.0 on PyPI. Single maintainer risk. If it disappears, the game falls back to generated FM music (which is lower quality but functional). The fallback is adequate but the game would lose its best feature. |
| **`AGENTS.md` line ranges are stale** | Medium | Documents say "lines 661–1032 → Entity classes" but after VGZ additions the actual ranges have shifted. Any agent relying on these ranges will mis-navigate. |
| **Hardcoded tunables scattered** | Low | Most tunables are in the Constants section (lines 23–79), but some are buried in class `__init__` methods (e.g., `invincible_frames=30`, `hint_timer=180`). An agent needs to search the whole file. |

### Make It Maintainable

#### 1. Add a `pyproject.toml` (5 minutes, high value)

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "heli-rescue"
version = "1.0.0"
description = "8-bit side-scrolling helicopter rescue game"
requires-python = ">=3.10"
dependencies = [
    "pygame>=2.5,<3",
    "ymfm-py>=0.2,<0.3",
]
```

This pins dependencies with version bounds and gives pip a single entry point:
`pip install -e .` or `pip install -r <(pip freeze | grep -E '^(pygame|ymfm-py)')`.

#### 2. Add test stubs for critical paths (medium effort, high value)

The most fragile code that an agent is likely to break:

| Priority | What to test | Example |
|----------|-------------|---------|
| P0 | VGM parser (`_parse_vgm`) | Feed a known VGM byte stream, assert correct event list and sample count |
| P0 | VGZ renderer (`_render_vgz`) | Assert output Sound duration matches expected, assert no exception |
| P1 | Collision detection | Feed known `pygame.Rect` pairs, assert `colliderect` outcomes |
| P1 | State machine transitions | Call `handle_events` with SPACE in TITLE, assert state → PLAYING |
| P2 | Helicopter movement | Call `update` with known key states, assert position changes correctly |

Add a `tests/` directory with `pytest` tests. A minimal `.github/workflows/test.yml`
would run them on every push.

#### 3. Add type hints (medium effort, high value)

Adding type hints to the 27 functions helps agents (and humans) understand data flow
without reading the full implementation. Example for the most critical functions:

```python
def _parse_vgm(raw_bytes: bytes) -> tuple[int, list[tuple[int, int, int]]]:
    ...
def _render_vgz(filepath: str, volume: float = 0.5, max_duration: int = 120) -> pygame.mixer.Sound | None:
    ...
def get_ground_y(terrain: list[int], x: int) -> int:
    ...
```

A single session adding type hints (without changing behavior) would cut future
agent navigation time significantly.

#### 4. Add a `Makefile` or `Justfile` (low effort, medium value)

```makefile
.PHONY: run test lint

run:
	python main.py

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check main.py
```

This gives agents a standard entry point regardless of which LLM or toolchain
they use.

#### 5. Refresh `AGENTS.md` line ranges (5 minutes, high value)

The current AGENTS.md has stale line ranges. An agent relying on "lines 661–1032 →
Entity classes" would land in the wrong section. Update to current line numbers
after any significant change.

### Dependency Upgrade Plan (when ymfm-py 0.3 drops)

If `ymfm-py` releases a breaking change:

1. Pin the old version: `pip install "ymfm-py<0.3"` — this buys time
2. Read the new API changelog
3. Search `main.py` for `ymfm.` calls (there are 5: `import ymfm`, `YM3812(clock=...)`,
   `chip.reset()`, `chip.write()`, `chip.generate()`)
4. Update those calls to match the new API
5. Run the test suite (if it exists) or manually verify with `timeout 5 python3 main.py`

If `ymfm-py` is abandoned:

1. The fallback (`_generate_fallback_music()`) activates automatically — the game
   still runs, just with the ~14s OPL2-style loop instead of 30-105s VGZ tunes
2. If VGZ playback is required, alternatives are:
   - **`adlmidi-py`** (if it exists by then) — another MAME-derived OPL3 player
   - **Inline Cython OPL2 emulator** — port a minimal OPL2 emulator (e.g. Nuked OPL3)
   - **Pre-rendered WAV files** — render VGZ to WAV offline, bundle WAV as game asset

### What an Agent Needs Most (Priority Order)

1. **`pyproject.toml`** + **`requirements.txt`** — so it knows what to `pip install`
2. **Tests** — so it can safely refactor without breaking the game
3. **Type hints** — so it can reason about data flow without reading every function body
4. **Current `AGENTS.md`** — so it can navigate the codebase quickly
5. **A `Makefile`** — so it can `make run` / `make test` without guessing

None of these are blockers — the game runs today with just `pip install pygame ymfm-py`.
But each missing piece adds friction and risk for a future maintainer (human or agent).
