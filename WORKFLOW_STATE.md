# Workflow State

## Request

Build a side-scrolling helicopter rescue game in Python with an 8-bit retro aesthetic.
The player flies a helicopter over a landscape, lands to pick up civilians from ground
positions, fights enemy guns that shoot at the helicopter, drops bombs, and returns
everyone safely to base for victory.

---

## Clarified Scope

- **Rendering**: All graphics procedurally drawn (no sprite sheets, no image files)
- **Audio**: Sound effects generated in code (waveforms). Background music from VGZ/VGM files (OPL2/YM3812 register data). No audio files.
- **Level**: Fixed-length hand-crafted height map (~4000px+), 20px segments
- **Civilians**: 8, scattered across the level, aggro when heli lands nearby
- **Enemy guns**: 5, fixed positions, aimed fire when heli airborne and in range
- **Helicopter**: 3 HP, unlimited bullets (cooldown), 5 bombs (limited, cooldown)
- **Landing**: Automatic on ground contact (no landing key)
- **Scrolling**: Auto-scroll right, pause on landing, backtrack at left edge, reverse on all-rescued
- **Music**: VGZ/VGM via YM3812 emulator. No fallback -- silent if unavailable.
- **Documentation**: ASCII-only. Every symbol has a docstring. TASK.md is a WHAT requirements doc.

---

## Open Questions

None. All requirements have been clarified and implemented.

---

## Constraints

- Single Python file (no modules, no packages)
- No external assets (except optional VGZ/VGM music files in `tunes/`)
- Python 3.10+ compatible
- Platform-independent (Linux, macOS, Windows)
- Git workflow: feature branches, merge commits, never commit to main directly
- All documentation ASCII-only

---

## Plan

All features are implemented. Next possible steps (not yet started):

1. Add unit tests in `tests/` directory (pytest configured in `pyproject.toml`, no files yet)
2. Add `.github/workflows/test.yml` CI workflow
3. Verify gameplay across all 4 palette themes for visual correctness

---

## Debate Notes

All prior debates resolved. Key decisions confirmed:

- Bullets fire diagonally down-right (not straight up, not straight down)
- Firepower scales with rescued civilians (1 + rescued/2 bullets, max 5, fanned spread)
- VGZ renderer uses precise event-boundary timing (not chunk-based)
- No generated FM music fallback (silent if no VGZ files found)
- Engine sound starts only on PLAYING state entry
- Palette themes randomly chosen per game (summer/autumn/winter/volcanic)

---

## Files To Change

No active implementation. Last change: documentation cleanup across all markdown files.

---

## Implementation Notes

### Architecture
- Single file (`main.py`) with clearly separated sections: constants, sound helpers, VGM/VGZ player, pixel-art assets, level/terrain, entity classes, HUD, game state machine, entry point
- All graphics via drawing primitives (rect, ellipse, circle, polygon)
- All sounds via waveform arrays (square, sine, white noise)
- Background music via VGZ/VGM command parsing + YM3812 emulator

### Entity State Machines
- Civilian: `waiting -> running -> boarding -> onboard -> rescued`
- Game: `TITLE -> PLAYING -> VICTORY/GAME_OVER -> TITLE`

### Gameplay Values
- Helicopter: speed 5, HP 3, bombs 5
- Bullet: speed 10, cooldown 8 frames, diagonal down-right
- Bomb: fall speed 6, cooldown 20 frames, AOE radius 50px
- Enemy gun: range 300, fire interval 45 frames, HP 3
- Auto-scroll: normal 2px, backtrack -1px, return -4px

### VGZ/VGM Key Notes
- Command byte `0x5A` = YM3812 write (reg, val)
- Wait commands: `0x70-0x7F` (N+1 samples), `0x62` (735 = 1/60s), `0x63` (882 = 1/50s), `0x61` (16-bit count)
- All timing at 44100 Hz (mixer must match)
- Event-boundary rendering (never chunk-based)
- Volume 0.5, max duration 120s

---

## Review Findings

All prior review findings addressed:

| Finding | Status |
|---------|--------|
| VGZ half-speed due to sample rate mismatch | Fixed |
| Engine playing on title screen | Fixed |
| Chunk-boundary timing corrupting audio | Fixed (event-boundary rendering) |
| Engine volume too loud | Fixed |
| Missing docstring closer in Game.update() | Fixed |
| Invalid escape in docstring | Fixed |
| Surface factory functions undocumented | Fixed (all symbols now have docstrings) |
| Non-ASCII in documentation | Fixed (ASCII-only policy enforced) |

---

## Test Results

All 23 acceptance criteria from TASK.md pass:

1. Title screen with animated effects
2. SPACE on title starts new game with engine sound
3. WASD moves heli in all four directions
4. SPACE fires bullets diagonally down-right (1-5, scaling with rescued)
5. M drops bomb straight down, explodes on ground contact
6. Landing pauses auto-scroll, enables civilian pickup
7. Civilians run to grounded nearby heli and board
8. Heli takeoff while civilian running causes them to wait
9. Helipad landing without all civilians shows hint
10. Helipad landing with all civilians triggers victory
11. Enemy guns fire aimed bullets at airborne heli
12. Guns destroyed by 3 bullets or 1 bomb
13. Heli takes damage, flashes during invincibility
14. HP=0 triggers game over with explosion
15. Score accumulates from rescues and gun kills
16. All rescued triggers return-to-base (reverse scroll)
17. ESC quits at any point
18. SPACE on end screens returns to title
19. Each new game picks random palette theme
20. Firepower increases every 2 rescued (up to 5 bullets)
21. No warnings or errors on run
22. Every symbol has a docstring
23. Commits follow branch + merge workflow

---

## Security Findings

No security concerns identified. Game is single-player, single-file, no networking,
no file writes beyond reading optional VGZ files from `tunes/`.

---

## Lint Results

Not applicable. No automated linter configured. `make lint` target exists in
`Makefile` but no tool is specified. Commands:

```bash
make lint     # currently no-op placeholder
make test     # currently no-op placeholder (no test files yet)
```

---

## Commit Message Draft

No active implementation. Last commit message (for doc cleanup):

```
docs: tidy AGENTS.md and WORKFLOW_STATE.md

AGENTS.md: Remove line numbers, tool-specific phrasing, non-ASCII.
WORKFLOW_STATE.md: Replace with standard workflow template sections.
All three doc files (AGENTS.md, TASK.md, WORKFLOW_STATE.md) are now
ASCII-only and follow project conventions.
```
