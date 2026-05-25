# AGENTS.md

## Repo overview

Single-file game (`main.py`). No external assets, no build step, Python 3.10+.
Uses a graphics/multimedia library for rendering, input, and audio output.

## Git workflow

- **`main`** branch is the stable, tested state. Never commit directly to `main`.
- Every new feature or bug fix gets its own **feature branch**:
  ```
  git checkout -b feat/<description>
  ```
- Always run tests before merging.
- Only merge when all tests pass:
  ```
  git checkout main
  git merge feat/<description>
  ```
- Merge commits preferred over rebase for traceability.

## Run

```bash
pip install -e .           # install deps
python main.py
```

## Architecture

| Layer | Technique |
|-------|-----------|
| Graphics | All procedurally drawn pixel art via drawing primitives (rect, ellipse, circle, polygon). No sprite sheets or image files. |
| Sound FX | Pre-computed waveform arrays (square wave, white noise, sine). No audio files. |
| Music | **Primary**: VGZ/VGM playback via a YM3812/OPL2 emulator. **Fallback**: no music (silent) if no playable file found. |
| Terrain | Height array (200 segments x 20px = 4000px level). Key points interpolated with noise. |
| Parallax | 3 layers: clouds (0.15x), mountains (0.25x), hills (0.5x). All tiled. |
| Collision | Axis-aligned bounding box (AABB) checks. |

## Code structure

| Section | Contents |
|---------|----------|
| Constants | Module-level tuning values (speeds, ranges, counts, colours) |
| Sound helpers | Waveform generation and sound-effect synthesis |
| VGM/VGZ player | Minimal VGM command parser + YM3812 emulator rendering |
| Pixel-art assets | Functions that generate entity sprites as surfaces |
| Level/terrain | Height-map generation and rendering |
| Entity classes | Helicopter, Bullet, EnemyBullet, Bomb, Explosion, Civilian, EnemyGun, Particle |
| HUD | Module-level function drawing HP, bombs, civilians, score, firepower |
| Game class | State machine, update loop, draw loop, event handling |
| Entry point | Run loop |

## Key constants (change these to tweak gameplay)

All at the top of `main.py`. Notable:

- `HELI_SPEED = 5`, `HELI_MAX_HP = 3`, `HELI_MAX_BOMBS = 5`
- `SCROLL_NORMAL = 2`, `SCROLL_BACKTRACK = -1`, `SCROLL_RETURN = -4`
- `GUN_RANGE = 300`, `GUN_FIRE_INTERVAL = 45`, `GUN_MAX_HP = 3`
- `CIVILIAN_RUN_SPEED = 2`, `CIVILIAN_AGGRO_RANGE = 120`
- `LEVEL_WIDTH = 4000`, `TERRAIN_SEGMENT = 20`

## Game state machine

```
TITLE --SPACE--> PLAYING --all rescued at helipad--> VICTORY
PLAYING --HP=0--> GAME_OVER
VICTORY --SPACE--> TITLE
GAME_OVER --SPACE--> TITLE
```

## Controls

- **W/A/S/D** -- move helicopter (up/down/left/right)
- **SPACE** -- shoot bullet (unlimited, cooldown)
- **M** -- drop bomb (limited supply, cooldown)
- **ESC** -- quit anytime
- **SPACE** on title/overlay -- start/restart

## Gameplay mechanics

- **Auto-scroll**: Camera moves right by default. Pauses when helicopter is landed. Backtrack mode when heli hits left edge of viewport. Return mode (reversed, faster) when all civilians onboard.
- **Landing**: Automatic when heli touches ground level. No landing key needed.
- **Civilian pickup**: Heli must be grounded near civilian -> civilian runs to heli -> boards when overlapping.
- **Enemy guns**: Fixed ground positions. Fire aimed bullets at heli when in range. Don't fire while heli is grounded. Destroyable by bullets (3 hits) or bombs (1 hit).
- **Victory**: All civilians onboard -> return to base -> land on helipad -> victory.
- **Game over**: HP reaches 0 -> explosion animation -> game over screen.
- **Invincibility**: Brief window after taking damage (sprite flashes).

## Terrain layout

Segment indices (each = 20px):

| Zone | Segments | x-range | Features |
|------|----------|---------|---------|
| Base | 0-20 | 0-400 | Flat, helipad at x=200, building, trees |
| Plains | 20-100 | 400-2000 | Mostly flat, gentle bumps |
| Hills | 100-140 | 2000-2800 | Rolling hills, higher ground |
| Valley | 140-200 | 2800-4000 | Deep dip then rise |
| Mountains | 200-250 | 4000-5000 | High peaks |
| End plateau | 250-end | 5000+ | Flat, wall barrier |

## Key design decisions (don't break these)

- No enemy respawn -- return trip is peaceful
- Landing on helipad without all civilians shows a ~3-second hint message (not victory)
- All graphics and sounds are generated in code -- no external assets to load
- Helicopter cannot go below ground or above y=80
- Camera clamps to level bounds `[0, LEVEL_WIDTH - SCREEN_WIDTH]`
- `draw_hud` is a module-level function, not a method on the Game class

## Common pitfalls for agents

- The event handler returns `False` to quit (not assigning `running = False`). The run loop checks `running = self.handle_events()`.
- `get_ground_y(terrain, x)` uses integer division by 20 -- clamp x to valid range before calling.
- Engine sound (`play(-1)`) is started in the PLAYING state transition, not at init. It starts when entering PLAYING and stops on VICTORY/GAME_OVER.
- Explosions and particles update even during GAME_OVER/VICTORY states so animations play out.
- Enemy guns check `heli_grounded` to decide whether to fire -- they won't shoot while heli is landed.
- Background music must be stopped during VICTORY/GAME_OVER transitions and restarted on return to TITLE.
- The VGM parser handles v1.50+ headers by scanning from offset 0x40 for the first valid command byte. Only YM3812 writes (0x5A) are captured; all other chips are skipped.
- The VGZ renderer uses **precise event-boundary rendering** (not chunk-based) to avoid corrupting note timing. It normalises 32-bit emulator output to 16-bit signed samples. Default volume 0.5, max duration 120s.
