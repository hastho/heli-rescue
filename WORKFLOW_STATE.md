# WORKFLOW_STATE

## Project Status (2026-05-25)

All phases complete. The game is fully functional with all 23 acceptance criteria passing.

## Current State

### Completed Features

| Feature | Status | Details |
|---------|--------|---------|
| Core gameplay | Done | Helicopter movement, auto-scroll, landing, civilian pickup/delivery |
| Combat | Done | Bullets (down-right diagonal, firepower scaling), bombs (straight down, AOE), enemy guns (aimed fire) |
| State machine | Done | TITLE -> PLAYING -> VICTORY/GAME_OVER -> TITLE |
| HUD | Done | HP hearts, bomb count, civilians + firepower, score, return/base hint messages |
| Title screen | Done | Animated (twinkling stars, hue cycling, glint sweep), controls listing |
| Sound effects | Done | Engine, shoot, bomb, explosion, pickup, damage, victory jingle |
| VGZ/VGM music | Done | Sample-accurate playback via YM3812 emulator. Event-boundary rendering (not chunk-based). No fallback -- silent if no files found. |
| Terrain + parallax | Done | Height map (6 zones, 4000px+), 3-layer parallax (clouds/mountains/hills) |
| Palette themes | Done | Summer, autumn, winter, volcanic -- randomly chosen per game |
| Firepower scaling | Done | 1 + (rescued // 2) bullets, up to 5, fanned spread |
| Documentation | Done | All symbols docstringed, ASCII-only docs, TASK.md as requirements doc, AGENTS.md updated, WORKFLOW_STATE.md current |
| Git workflow | Done | Feature branches, merge commits, no direct pushes to main |

### Known Resolved Issues

| Issue | Root Cause | Fix |
|-------|------------|-----|
| VGZ half-speed | Mixer at 22050 Hz, VGM parser at 44100 Hz | Mixer changed to 44100 Hz |
| Engine on title | `play(-1)` called at init | Engine starts only on PLAYING entry |
| Chunk-boundary timing | Events processed at 0.1s chunks (100% delayed, avg 54ms) | Precise event-boundary rendering |
| Engine too loud | Volume 0.08 vs music at 0.5 | Engine halved to 0.04 |
| Unclosed docstring | Missing `"""` in `Game.update()` | Added closing quote |
| `\-` escape warning | Non-ASCII in docstring | Replaced with ASCII |

### Open / Not Yet Implemented

- Unit tests (`tests/` directory configured in `pyproject.toml` but no files)
- CI workflow (no `.github/workflows/`)

## Key Design Decisions (preserve these)

- No enemy respawn -- return trip is always peaceful
- Landing on helipad without all civilians shows ~3-second hint (not victory)
- All graphics and sounds generated in code -- no external assets (except VGZ files)
- Helicopter ceiling at y=80, ground-clamped below
- Camera clamps to `[0, LEVEL_WIDTH - SCREEN_WIDTH]`
- Bullets fire diagonally down-right at 45-degree angle (vx=vy=10 baseline)
- Bombs drop straight down at BOMB_FALL_SPEED, explode on ground contact
- Firepower: 1 base bullet + 1 per 2 rescued civilians, max 5, fanned across 25-degree arc
- Engine sound lifecycle: start on PLAYING entry, stop on VICTORY/GAME_OVER
- Music lifecycle: play on TITLE and PLAYING, stop on VICTORY/GAME_OVER, restart on return to TITLE
- VGZ renderer uses precise event-boundary timing (never chunk-based)
- No generated FM fallback -- if no VGZ files found or ymfm-py unavailable, game plays silently
- All documentation ASCII-only (no Unicode in docstrings, comments, or markdown)

## Audio Requirements Summary

| Sound | Type | Lifecycle |
|-------|------|-----------|
| Engine | Square wave, loops | PLAYING only |
| Shoot | White noise burst | On SPACE |
| Bomb | Descending tone | On M |
| Explosion | White noise burst | On bomb/bullet kill |
| Pickup | Ascending beep | On civilian boarding |
| Damage | Low buzz | On hit |
| Victory | Sine melody | On VICTORY state |
| Music | VGZ/VGM via emulator | TITLE + PLAYING, stop on end states |

## VGZ/VGM Player Notes

- VGM commands: `0x5A` = YM3812 write (reg, val). Wait commands: `0x70-0x7F` (short, N+1 samples), `0x62` (735 = 1/60s), `0x63` (882 = 1/50s), `0x61` (16-bit count). All timing at 44100 Hz.
- YM3812 emulator API: `chip = YM3812(clock=3579545)`, `chip.write(port, val)`, `chip.generate(n)` returns memoryview of int32.
- Render volume 0.5, max duration 120s.
- No fallback if no files or emulator missing -- game proceeds silently.

## Next Steps (if continuing)

1. Add unit tests in `tests/` directory (pytest configured in `pyproject.toml`)
2. Add `.github/workflows/test.yml` for CI
3. Verify gameplay across all 4 palette themes for visual correctness

## Git History

Branch-per-feature workflow. Notable merges on main (most recent first):

```
Merge feat/ascii-only-docs          -- Replace non-ASCII in docs
Merge feat/docstrings-all           -- All symbols documented
Merge feat/firepower-levels         -- Firepower scales with rescued
Merge feat/bullets-diagonal         -- Bullets fire down-right
Merge feat/bullets-downward         -- Bullets fire downward (interim)
Merge feat/remove-fm-fallback       -- VGZ-only music
Merge feat/level-palette-themes     -- Palette themes
Merge feat/title-palette-tricks     -- Title screen animations
Merge feat/engine-lifecycle-fix     -- Fix engine audio lifecycle
Merge feat/sample-rate-fix          -- Fix VGZ half-speed
Merge feat/precise-rendering        -- Fix chunk-boundary timing
... (earlier: initial features)
```
