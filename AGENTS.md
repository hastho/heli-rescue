# AGENTS.md

## Repo overview

Single-file Pygame game (`main.py`, ~1843 lines). No external assets, no build step, Python 3.10+.

## Git workflow

- **`main`** branch is the stable, tested state. Never commit directly to `main`.
- Every new feature or bug fix gets its own **feature branch**:
  ```
  git checkout -b feat/<description>
  ```
- Always run `make test` (or the relevant test command) before merging.
- Only merge when all tests pass:
  ```
  git checkout main
  git merge feat/<description>
  ```
- Merge commits preferred over rebase for traceability.

## Run

```bash
pip install -e .           # install deps (pygame + ymfm-py) in editable mode
# or: pip install pygame ymfm-py
python main.py
```

## Architecture

| Layer | Technique |
|-------|-----------|
| Graphics | All procedurally drawn pixel art via `pygame.Surface` + `draw.rect/ellipse/circle/polygon`. No sprite sheets or image files. |
| Sound FX | Pre-computed waveform arrays (square wave, white noise, sine) fed into `pygame.mixer.Sound`. No audio files. |
| Music | **Primary**: VGZ/VGM playback via `ymfm.YM3812` emulator (`ymfm-py`). **Fallback**: OPL2-style 2-operator FM synthesis generated in code (`fm_note_samples`) — carrier + modulator sine waves with ADSR envelopes. |
| Terrain | Height array (200 segments × 20px = 4000px level). Key points interpolated with noise. |
| Parallax | 3 layers: clouds (0.15×), mountains (0.25×), hills (0.5×). All tiled. |
| Collision | `pygame.Rect.colliderect` AABB checks. |

## Code structure

| Lines | Section |
|-------|---------|
| 1–88 | Imports, constants, GameState enum |
| 99–185 | Sound generation functions |
| 186–255 | VGM/VGZ parser (`_parse_vgm`) |
| 256–345 | VGZ renderer (`_render_vgz`) via ymfm-py |
| 346–583 | OPL2-style FM music generator (fallback) + `init_music()` |
| 584–695 | Pixel-art asset generators |
| 696–840 | Level/terrain generation |
| 841–1212 | Entity classes (Helicopter, Bullet, EnemyBullet, Bomb, Explosion, Civilian, EnemyGun, Particle) |
| 1213–1250 | HUD rendering (`draw_hud`, module-level) |
| 1251–1840 | Main `Game` class (state machine, update, draw) |
| 1841–1843 | Entry point (`run` loop) |

## Key constants (change these to tweak gameplay)

All at the top of `main.py` (lines 23–79). Notable:

- `HELI_SPEED = 5`, `HELI_MAX_HP = 3`, `HELI_MAX_BOMBS = 5`
- `SCROLL_NORMAL = 2`, `SCROLL_BACKTRACK = -1`, `SCROLL_RETURN = -4`
- `GUN_RANGE = 300`, `GUN_FIRE_INTERVAL = 45`, `GUN_MAX_HP = 3`
- `CIVILIAN_RUN_SPEED = 2`, `CIVILIAN_AGGRO_RANGE = 120`
- `LEVEL_WIDTH = 4000`, `TERRAIN_SEGMENT = 20`

## Game state machine

```
TITLE ──SPACE──→ PLAYING ──all rescued at helipad──→ VICTORY
                    │                                  │
                    └──HP=0──→ GAME_OVER ←──SPACE──────┘
                                        ←──SPACE──────┘
                                    (both go back to TITLE)
```

## Controls

- **W/A/S/D** — move helicopter (up/down/left/right)
- **SPACE** — shoot bullet upward (unlimited, 8-frame cooldown)
- **M** — drop bomb (limited to 5, 20-frame cooldown)
- **ESC** — quit anytime
- **SPACE** on title/overlay — start/restart

## Gameplay mechanics

- **Auto-scroll**: Camera moves right at 2px/frame by default. Pauses when helicopter is landed. Backtrack mode (−1px/frame) when heli hits left 120px of viewport. Return mode (−4px/frame) when all civilians onboard.
- **Landing**: Automatic when heli touches ground level (`S` key descends). No landing key needed.
- **Civilian pickup**: Heli must be grounded within 120px of civilian → civilian runs to heli at 2px/frame → boards when overlapping.
- **Enemy guns**: Fixed ground positions. Fire red bullets every 45 frames at heli when distance ≤300px. Don't fire while heli is grounded. 3 HP each, destroyable by 3 bullets or 1 bomb.
- **Victory**: All civilians onboard → return to base → land on helipad (`abs(heli.x - 200) < 60` while grounded) → victory.
- **Game over**: HP reaches 0 → explosion animation → game over screen.
- **Invincibility**: 30 frames after taking damage (helicopter flashes).

## Terrain layout

Segment indices (each = 20px):

| Zone | Segments | x-range | Features |
|------|----------|---------|---------|
| Base | 0–20 | 0–400 | Flat, helipad at x=200, building, trees |
| Plains | 20–100 | 400–2000 | Mostly flat, gentle bumps |
| Hills | 100–140 | 2000–2800 | Rolling hills, higher ground |
| Valley | 140–200 | 2800–4000 | Deep dip then rise |
| Mountains | 200–250 | 4000–5000 | High peaks |
| End plateau | 250–end | 5000+ | Flat, wall barrier |

## Key design decisions (don't break these)

- No enemy respawn — return trip is peaceful
- Landing on helipad without all civilians shows a 3-second hint message (not victory)
- All graphics and sounds are generated in code — no external assets to load
- Helicopter cannot go below ground or above y=80
- Camera clamps to `[0, LEVEL_WIDTH - SCREEN_WIDTH]`

## Common pitfalls for agents

- The `handle_events` method returns `False` to quit (not `running = False` assignment). The `run` loop checks `running = self.handle_events()`.
- `get_ground_y(terrain, x)` uses integer division by 20 — don't pass negative x or values beyond level width without clamping.
- `draw_hud` (line 1213) is a module-level function, not a method on `Game`. All other draw methods are on classes.
- Sound engine loop (`sounds['engine'].play(-1)`) is started in **PLAYING state transition**, not at init. It starts when entering PLAYING and stops on VICTORY/GAME_OVER.
- Explosions and particles update even during GAME_OVER/VICTORY states so the animation plays out.
- Enemy guns check `heli_grounded` to decide whether to fire — they won't shoot while heli is landed.
- Background music (`game.music`) is a `pygame.mixer.Sound` played on loop during TITLE and PLAYING states. It must be stopped manually during VICTORY/GAME_OVER transitions and restarted on return to TITLE.
- `note_to_freq(name, octave)` converts note names ('A', 'C#') + octave to Hz (A4=440). Use octave 2-5 for instruments at game pitch.
- `fm_note_samples` generates 2-operator FM tones: carrier freq = note, modulator freq = carrier × ratio. Key parameters: `ratio` (0.5-4), `index` (1-5), ADSR envelope. Higher index = brighter/more metallic.
- `_parse_vgm` (line 186) parses VGM byte data. It handles v1.50+ headers by scanning from offset 0x40. Only YM3812 writes (0x5A) are captured; all other chips are skipped.
- `_render_vgz` (line 256) renders VGZ/VGM via `ymfm.YM3812`. Uses **precise event-boundary rendering** (not chunk-based). Normalizes 32-bit ymfm output to 16-bit signed. Default volume 0.5, max duration 120s.
