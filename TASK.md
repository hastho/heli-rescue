# Heli Rescue — Agentic Coding Environment Evaluation Task

## Original Task (verbatim)

Build a side scrolling helicopter rescue game using Python looking like a 8 bit home
computer style. The helicopter should be controalled by the W, A, S and D keys with
space bar to shoot and the m key to drop bombs. The helicopter should take off from
base and fly over the landscape, landing to pickup civilians. The civilians run to the
helicopter when on the ground in their vicinity. When the helicopter returns to base,
it must land to drop off the civilians. There should be enemy guns on the ground
that shoot at the helicopter when flying naer by. The game ends when all the
civiliansare rescued or the helicopter gets shot down. Please make a front screen
for the game with an 80s vibe detailing the controls.

---

## Project Overview

A single-file Python/Pygame side-scrolling helicopter rescue game (~1843 lines).
All graphics are procedurally drawn pixel art (no sprite sheets). All audio is
synthesized (no audio files) — sound effects are pre-computed waveforms, background
music is either OPL2/FM-synthesis via `ymfm-py` VGZ playback or a generated fallback.

The game was built by an agentic coding system (planner → debater → implementor →
reviewer → tester) where each agent has a specific role and follows instructions
from `AGENTS.md`.

---

## Files (all in `/home/thomas/heli2/`)

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 1843 | Single-file game: constants, sound generation, VGM/VGZ parser, OPL2 FM synthesis, pixel-art assets, entity classes, HUD, game state machine, main loop |
| `AGENTS.md` | 108 | Agent instructions detailing architecture, code structure, constants, pitfalls |
| `WORKFLOW_STATE.md` | 548 | Full project state: decisions, plans, bug fixes, review findings, implementation notes |
| `TASK.md` | This file | Task description + evaluation notes |

### `tunes/` directory (optional music files)

| File | Duration | Size |
|------|----------|------|
| `Cheating Engine Tune 1.vgz` | ~31s | 13 KB |
| `Delight Loader.vgz` | ~105s | 43 KB |
| `Old 64-Style.vgz` | ~32s | 9 KB |

These are VGZ (gzip-compressed VGM) files containing YM3812/OPL2 register data.
If they exist, the game plays them as background music. If missing or broken, the
game falls back to a generated OPL2-style FM synthesis loop (~14s, A minor, 140 BPM).

---

## How to Run

```bash
pip install pygame ymfm-py
python main.py
```

Dependencies:
- **pygame** — graphics, sound, input
- **ymfm-py** — MAME-grade YM3812 (OPL2) emulator for VGZ playback (pure Python bindings)

If `ymfm-py` is not installed, the game prints an error and falls back to generated FM music.

On systems with PEP 668 (e.g. Debian/Ubuntu), you may need:
```bash
pip install pygame ymfm-py --break-system-packages
```

---

## Controls

| Key | Action |
|-----|--------|
| W | Move up |
| A | Move left |
| S | Move down (descend to ground = automatic landing) |
| D | Move right |
| SPACE | Shoot bullet (upward, unlimited, 8-frame cooldown) |
| M | Drop bomb (downward, 5 max, 20-frame cooldown) |
| ESC | Quit |
| SPACE (title/game over/victory) | Start / Restart |

---

## Game State Machine

```
TITLE ──SPACE──→ PLAYING ──all rescued at helipad──→ VICTORY
                    │                                  │
                    └──HP=0──→ GAME_OVER ←──SPACE──────┘
                                        ←──SPACE──────┘
                                    (both go back to TITLE)
```

---

## Architecture

### Layer | Technique
|---------|----------|
| Graphics | All procedurally drawn pixel art via `pygame.Surface` + `draw.rect/ellipse/circle/polygon`. No sprite sheets or image files. |
| Sound FX | Pre-computed waveform arrays (square wave, white noise, sine) fed into `pygame.mixer.Sound`. No audio files. |
| Music | **Primary**: VGZ/VGM playback via `ymfm.YM3812` emulator. **Fallback**: OPL2-style 2-operator FM synthesis generated in code — carrier + modulator sine waves with ADSR envelopes. |
| Terrain | Height array (200 segments × 20px = 4000px level). Key points interpolated with noise. |
| Parallax | 3 layers: clouds (0.15×), mountains (0.25×), hills (0.5×). All tiled. |
| Collision | `pygame.Rect.colliderect` AABB checks. |

### Code structure (`main.py`)

| Lines | Section |
|-------|---------|
| 1–88 | Constants and GameState enum |
| 92–175 | Sound generation functions |
| 179–253 | VGM/VGZ parser (`_parse_vgm`) |
| 256–335 | VGZ renderer (`_render_vgz`) via ymfm-py |
| 338–553 | OPL2-style FM music generator (fallback) |
| 404–514 | Pixel-art asset generators |
| 516–658 | Level/terrain generation |
| 661–1032 | Entity classes (Helicopter, Bullet, Bomb, Civilian, EnemyGun, Explosion, Particle) |
| 1035–1070 | HUD rendering (`draw_hud`) |
| 1073–1843 | Main `Game` class (state machine, update, draw) + entry point |

### Key constants (tweak these to adjust gameplay)

All at top of `main.py`, lines 23–79:
- `HELI_SPEED = 5`, `HELI_MAX_HP = 3`, `HELI_MAX_BOMBS = 5`
- `SCROLL_NORMAL = 2`, `SCROLL_BACKTRACK = -1`, `SCROLL_RETURN = -4`
- `GUN_RANGE = 300`, `GUN_FIRE_INTERVAL = 45`, `GUN_MAX_HP = 3`
- `CIVILIAN_RUN_SPEED = 2`, `CIVILIAN_AGGRO_RANGE = 120`
- `LEVEL_WIDTH = 4000`, `TERRAIN_SEGMENT = 20`

### Terrain layout

Segment indices (each = 20px):

| Zone | Segments | x-range | Features |
|------|----------|---------|---------|
| Base | 0–20 | 0–400 | Flat, helipad at x=200, building, trees |
| Plains | 20–100 | 400–2000 | Mostly flat, gentle bumps |
| Hills | 100–140 | 2000–2800 | Rolling hills, higher ground |
| Valley | 140–200 | 2800–4000 | Deep dip then rise |
| Mountains | 200–250 | 4000–5000 | High peaks |
| End plateau | 250–end | 5000+ | Flat, wall barrier |

---

## Implementation History (bugs fixed, decisions made)

### 1. Sample rate mismatch (VGZ half-speed)
- **Problem**: VGM parser accumulated samples at 44100 Hz but `pygame.mixer.init()` was at 22050 Hz. `pygame.mixer.Sound` determines playback rate from the mixer, so VGZ music played at half speed (one octave lower, double duration).
- **Fix**: Changed mixer to 44100 Hz (`pygame.mixer.init(frequency=44100, size=-16, channels=1)`). Updated all sound effect generation (`sr = 44100` in `init_sounds()`) and fallback music generation to match.
- **Files**: main.py lines 134, 555, 556, 1251.

### 2. Engine sound playing on title screen
- **Problem**: `sounds['engine'].play(-1)` was called in `init_sounds()`, before the game starts. This caused the 80 Hz square wave drone to play underneath VGZ music on the title screen.
- **Fix**: Removed `engine.play(-1)` from `init_sounds()`. Engine starts only when entering PLAYING state (in `Game.handle_events()` transition). Engine stops on VICTORY/GAME_OVER. The TITLE→TITLE transition (after VICTORY/GAME_OVER) does NOT restart the engine.
- **Result**: Title screen = pure VGZ music. Gameplay = VGZ music + engine hum. End screens = no engine.

### 3. VGZ playback stuttering/wrong tempo (chunk-boundary timing error)
- **Problem**: `_render_vgz()` processed YM3812 register writes only at chunk boundaries (every 4410 samples = 0.1s). VGM events occur every ~3ms on average. 100% of events were delayed by 50–100ms, corrupting note attacks, phrasing, and tempo.
- **Diagnosis**: Before fixing, the agent was asked to (a) render current output to WAV for analysis, (b) measure event-timing statistics, (c) compare precise vs chunked rendering. The diagnostic showed only 3.8% of samples matched between precise and chunked rendering.
- **Fix**: Replaced chunk-boundary loop with precise event-boundary rendering: generate audio up to each event's exact sample position, apply the YM3812 write, then continue. Performance is ~108× real-time (no perceptible load time increase).
- **Volume**: Increased default VGZ volume from 0.2 to 0.5.

### 4. Engine sound too loud
- **Problem**: 80 Hz square wave drone dominated over VGZ music during gameplay.
- **Fix**: Halved engine volume from 0.08 to 0.04.

---

## Known Design Decisions (don't break these)

- No enemy respawn — return trip is peaceful
- Landing on helipad without all civilians shows a 3-second hint message (not victory)
- All graphics and sounds are generated in code — no external assets
- Helicopter cannot go below ground or above y=80
- Camera clamps to `[0, LEVEL_WIDTH - SCREEN_WIDTH]`
- `handle_events` returns `False` to quit (not `running = False`)
- `get_ground_y(terrain, x)` uses integer division by 20 — don't pass negative x or values beyond level width
- `draw_hud` (line 1035) is a module-level function, not a method on `Game`
- Background music is a `pygame.mixer.Sound` played on loop during PLAYING; must be stopped during VICTORY/GAME_OVER and restarted on return to TITLE
- `note_to_freq(name, octave)` converts note names ('A', 'C#') + octave to Hz (A4=440). Use octave 2–5 for instruments.
- `fm_note_samples` generates 2-operator FM tones: carrier freq = note, modulator freq = carrier × ratio. Key params: `ratio` (0.5–4), `index` (1–5), ADSR envelope.

---

## VGZ/VGM Player Architecture

### Components
1. **`_parse_vgm(raw_bytes)`** (~70 lines) — Minimal VGM command parser:
   - Supports v1.50+ headers (scans from offset 0x40 for first valid command byte)
   - Processes YM3812 writes (0x5A: reg, val)
   - Handles all wait commands: 0x70–0x7F (short waits), 0x61 (16-bit sample count), 0x62 (735 samples = 1/60s), 0x63 (882 samples = 1/50s)
   - Skips non-YM3812 chips (0x52–0x59, 0x5B–0x5D), data blocks (0x67/0x68), DAC (0x90–0x92), NOP (0x00, 0x30)
   - Returns `(total_samples_44100, event_list)` where event = `(sample_pos, reg, val)`

2. **`_render_vgz(filepath, volume=0.5, max_duration=120)`** (~65 lines):
   - Decompresses VGZ (gzip) or passes VGM through
   - Creates `ymfm.YM3812(clock=3579545)` chip
   - Renders with precise event-boundary timing (not chunk-based)
   - Normalizes to 16-bit signed: `scale = min(32000.0 / max_val, 1.0)`
   - Returns `pygame.mixer.Sound` or None on error

3. **`init_music()`** (~20 lines):
   - Scans `tunes/` for `.vgz` and `.vgm` files (alphabetically sorted)
   - Tries each with `_render_vgz()`, returns first successful Sound
   - Falls back to `_generate_fallback_music()` if none work

4. **`_generate_fallback_music()`** (~5 lines):
   - Calls `generate_music_loop(bpm=140, sr=44100)` which produces ~14s loop
   - A minor heroic theme: bass (80 BPM root-5th), pad (sustained chords), lead (melody), arpeggio

### Timing rules (critical)
- **YM3812 register write in VGM**: command byte `0x5A` followed by register byte and value byte. The write takes effect at the current accumulated sample position.
- **VGM timing at 44100 Hz**: wait `0x62` = 735 samples (1/60s), `0x63` = 882 samples (1/50s), `0x70–0x7F` = `(n & 0x0F) + 1` samples, `0x61` = 16-bit sample count
- **`ymfm.YM3812` API**: `chip = ymfm.YM3812(clock=3579545)`, `chip.reset()`, `chip.write(0, reg)` + `chip.write(1, val)`, `chip.generate(n)` → memoryview[N, 1] of 32-bit ints
- **Mixer must be at 44100 Hz** — the VGM parser accumulates sample counts assuming 44100 Hz rate. If mixer is at any other rate, playback speed is wrong.

---

## Agent Workflow Used

The project was built using a structured multi-agent workflow:

1. **planner** — Reads task, asks clarifying questions, confirms understanding, writes implementation plan, hands off to debater
2. **debater** — Reviews plan for flaws, suggests alternatives. Planner and debater iterate until plan is solid.
3. **implementor** — Implements the approved plan, makes code changes, records changes in WORKFLOW_STATE.md
4. **reviewer** — Reviews implementation for correctness, maintainability, and adherence to plan
5. (optional) **linter** — Runs linting/formatting checks
6. (optional) **tester** — Runs relevant tests

Each agent follows `AGENTS.md` for context about the codebase. `WORKFLOW_STATE.md` is the shared state file that tracks current status, plans, decisions, and bugs.

---

## Evaluation Notes (for repeating this exercise)

### What worked well
- VGZ playback via `ymfm-py` (MAME-grade OPL2 emulation) works reliably
- Minimal inline VGM parser (~70 lines) is simpler and more maintainable than external libraries
- Precise event-boundary rendering fixed the timing bug completely (108× real-time performance is fine)
- Gameplay code was never broken by any of the audio fixes — clean separation

### What was tricky
- **Sample rate mismatch**: Easiest mistake — VGM spec uses 44100 Hz timing, but pygame defaults to 22050 Hz. The bug manifests as half-speed audio, easy to miss.
- **Engine sound lifecycle**: Subtle bug — `play(-1)` at init vs only during PLAYING state. Easy to overlook because the engine is quiet and blends in.
- **Chunk-boundary rendering**: Non-obvious bug — rendering in 0.1s chunks seems reasonable until you measure: 100% of events delayed, average 54ms. Always verify by comparing precise vs chunked output.
- **GME (libgme) produced silence**: Was the first approach tried but GME misidentified YM3812 files as Sega SMS/Genesis. Abandoned in favor of `ymfm-py` which works correctly.
- **PEP 668 restriction**: On modern Debian/Ubuntu, system Python requires `--break-system-packages` for pip installs.

### Key files to read for a new LLM
- `AGENTS.md` — Architecture overview, code structure, pitfalls
- `WORKFLOW_STATE.md` — Full project state including all bug fixes and decisions
- `main.py` lines 179–335 — VGM parser and VGZ renderer (the most complex audio code)
- `main.py` lines 1073–1660 — Game class (state machine, update, draw loops)

### Typical bugs to watch for
1. Mixer sample rate ≠ VGM parser sample rate → half/double speed audio
2. Sounds starting at wrong lifecycle point (title vs gameplay)
3. Chunk-based rendering instead of event-boundary → timing errors
4. Not normalizing ymfm output to 16-bit → silent or distorted audio
5. Not handling VGM data block (0x67) or GD3 tag at end of file → parse errors
