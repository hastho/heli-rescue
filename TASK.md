# Heli Rescue -- Requirements Document

## 1. Concept

A side-scrolling helicopter rescue game with an 8-bit retro aesthetic.
The player flies a helicopter over a landscape, lands to pick up civilians,
dodges and destroys ground-based enemy guns, and returns everyone safely to base.

---

## 2. Functional Requirements

### 2.1 Controls

| Input | Action |
|-------|--------|
| W / S | Move helicopter up / down |
| A / D | Move helicopter left / right |
| SPACE | Shoot bullets (unlimited, short cooldown) |
| M | Drop bomb (limited supply, longer cooldown) |
| ESC | Quit game at any time |
| SPACE (on title / end screens) | Start new game / return to title |

### 2.2 Game State Machine

The game has exactly four states with the following transitions:

```
TITLE --SPACE--> PLAYING --all rescued & landed at helipad--> VICTORY
PLAYING --HP=0--> GAME_OVER
VICTORY --SPACE--> TITLE
GAME_OVER --SPACE--> TITLE
```

- **TITLE**: Animated title screen showing game name, controls, and a "Press SPACE to start" prompt.
- **PLAYING**: Main gameplay loop (auto-scroll, enemies, civilians, combat).
- **VICTORY**: Game rendered frozen behind a translucent overlay with "Victory!" message, stats, and restart prompt.
- **GAME_OVER**: Same layout as VICTORY but with "Game Over" message.

### 2.3 Gameplay Mechanics

#### Auto-Scroll & Camera
- The camera auto-scrolls right at a constant speed while the helicopter is airborne.
- Auto-scroll pauses while the helicopter is landed (on the ground).
- If the helicopter falls behind the left 120px of the viewport, the camera backtracks slowly to let the player catch up.
- Once all civilians are onboard, the auto-scroll reverses direction at higher speed (return-to-base mode) so the player flies back left toward the helipad.
- The camera is clamped to the level boundaries.

#### Helicopter
- The helicopter moves freely in all four directions (WASD) within the playable area.
- It cannot fly above a ceiling (roughly y=80) or below ground level.
- Landing happens automatically when the helicopter descends onto the terrain surface -- no separate landing key.
- The helicopter has hit points (HP). Taking damage grants a brief invincibility window (sprite flashes).
- HP reaching zero triggers an explosion animation and transitions to GAME_OVER.

#### Civilians
- 8 civilians are scattered across the level at randomized positions within defined zones.
- Each civilian has a state machine: `waiting -> running -> boarding -> onboard -> rescued`.
- A civilian stays in `waiting` until the helicopter lands within aggro range (~120px).
- Once aggroed, the civilian runs toward the grounded helicopter.
- If the helicopter takes off before the civilian reaches it, the civilian returns to `waiting`.
- When the civilian reaches the helicopter, it boards and is counted as rescued.
- Rescued civilians increase the helicopter's firepower (see Combat section).
- Rescued civilians are delivered by landing on the helipad in the base zone after all are onboard.

#### Enemy Guns
- 5 stationary gun turrets are placed at fixed positions across the level.
- Each gun fires aimed bullets toward the helicopter when it is within range (~300px) and airborne.
- Guns do not fire while the helicopter is grounded (landing is safe).
- Guns have HP and can be destroyed by player bullets or bombs.
- Once destroyed, a gun does not respawn -- the return trip is peaceful.

#### Combat
- **Bullets**: Fire diagonally down-right (toward ground targets ahead of the helicopter).
  Each SPACE press fires 1-5 bullets in a fan spread, depending on firepower level.
- **Bombs**: Drop straight down and explode on ground contact.
  Bombs deal heavy area-of-effect damage (3 HP in a ~50px radius) -- one-hit kill on guns.
- **Firepower Scaling**: Every 2 rescued civilians increases the bullet count by 1 (max 5).
  Additional bullets fan out at different angles, creating a spread shot.
  The HUD displays current firepower level.
- Enemy bullets deal 1 HP damage to the helicopter.
- Bullets that exit the visible area (off-screen bottom or right) are removed.

#### Victory Condition
- All civilians must be onboard the helicopter.
- The helicopter must land on the helipad (x ~200) in the base zone.
- Landing on the helipad without all civilians shows a ~3-second hint message instead of triggering victory.

#### HUD (displayed during PLAYING)
- Hearts: remaining HP (filled/empty heart icons).
- Bombs: remaining bomb count.
- Civilians: count rescued vs total + firepower indicator (filled/empty diamonds).
- Score: accumulated points (civilians = 100 each, guns destroyed = 200 each, victory bonus = 500).
- Message: "RETURN TO BASE!" when all civilians are onboard.

### 2.4 Level & World Design

#### Terrain
A height map covering ~5000px of horizontal space, divided into 20px segments:

| Zone | Position (world-x) | Description |
|------|-------------------|-------------|
| Base | 0-400 | Flat ground. Helipad at x=200, a building, trees. |
| Plains | 400-2000 | Mostly flat with gentle bumps. |
| Hills | 2000-2800 | Rolling hills, higher ground. |
| Valley | 2800-4000 | Deep dip then rise. |
| Mountains | 4000-5000 | High peaks. |
| End plateau | 5000+ | Flat, wall barrier at level end. |

#### Parallax Layers
Three background layers scrolling at different speeds relative to the camera:
- Clouds (slowest, furthest)
- Mountains (medium)
- Hills (fastest, nearest)

All layers tile seamlessly.

#### Palette Themes
The game randomly picks a color theme on each new game, swapping terrain,
vegetation, and building colors without changing the level layout.
Available themes: summer, autumn, winter, volcanic.

### 2.5 Title Screen
- Dark gradient background with twinkling stars (sinusoidal brightness).
- Game title with cycling hue (colour rotation).
- Glint sweep effect: a white highlight band slides across the title.
- Subtitle, controls list, animated "SPACE TO START" prompt.
- Preview helicopter graphic.

### 2.6 Audio

#### Sound Effects (generated in code)
All sound effects are synthesized at runtime -- no audio files are loaded.
Required sounds:
- Engine hum (low square wave, loops during PLAYING)
- Shoot (short noise burst)
- Bomb drop (descending tone)
- Explosion (white noise burst)
- Civilian pickup (ascending beep)
- Damage (low buzz)
- Victory jingle (short melody)

#### Background Music (loaded from files)
The game plays background music from external music files.
Music format: VGZ (gzip-compressed VGM) or raw VGM files containing
YM3812/OPL2 FM synthesis register data.
- If music files exist in a `tunes/` directory, the game plays one as background music.
- Playback must be sample-accurate -- register writes in VGM occur every ~3ms
  and must be processed at the correct sample position (event-boundary rendering,
  not chunk-based).
- If no playable files are found or the music library is unavailable,
  the game proceeds silently (no background music -- not a crash).
- Music plays on the title screen and during PLAYING.
- Music stops during VICTORY/GAME_OVER and restarts when returning to the title.

#### Audio Lifecycle Rules
- Engine sound starts only when entering PLAYING state (not during title screen).
- Engine sound stops on transition to VICTORY or GAME_OVER.
- All sounds stop when returning from VICTORY/GAME_OVER to TITLE.
- Background music restarts on return to TITLE.

---

## 3. Non-Functional Requirements

### 3.1 Code Architecture
- **Single-file application**: The entire game lives in one source file (no modules, no packages).
- **No external assets**: All graphics are procedurally drawn pixel art. All sounds are synthesized.
  No sprite sheets, image files, audio files, or data files (except optional VGZ music files in `tunes/`).
- **Self-contained dependencies**: Minimise external libraries. Prefer standard library where possible.
- **Platform independence**: Must run on Linux, macOS, and Windows without platform-specific code.
- **Configurable constants**: All gameplay tuning values (speeds, ranges, counts, cooldowns)
  are defined as module-level constants at the top of the file, with clear names and comments.

### 3.2 Code Quality & Documentation
- **Every function, class, and method must have a docstring** describing what it does,
  its parameters, and return value. Use a consistent style (e.g. Google-style Args/Returns).
- **Docstrings must use only ASCII characters** -- no non-ASCII symbols, emoji, or special
  Unicode characters. This avoids encoding issues across editors and Python versions.
- **Complex code blocks must have inline comments** explaining the intent, not just the mechanics.
- **Code must be self-explaining**: use descriptive variable/function names, avoid clever one-liners.
- **All comments and docstrings must use ASCII only** (no `->`, `x` for dimensions, `deg` for degrees, `--` for dashes).

### 3.3 Maintainability
- **Separation of concerns**: Graphics generation, sound generation, entity logic, game state,
  and rendering should be clearly separated within the file (functions grouped by concern,
  classes for entities).
- **No magic numbers**: All literal values that affect gameplay or rendering behaviour
  should be named constants.
- **No dead code**: Generated FM fallback music was removed when it was never heard (VGZ files
  are always present). Keep the codebase minimal.
- **One source of truth**: WORKFLOW_STATE.md tracks the current state, decisions, and plans.
  AGENTS.md describes the architecture and common pitfalls.

### 3.4 Git Workflow
- `main` branch is stable and tested. Never commit directly to `main`.
- Every change gets its own feature branch (`feat/<description>`).
- Merge commits are preferred over rebase for traceability.
- Commit messages describe WHAT and WHY, not just the diff.

### 3.5 Error Handling
- Missing music files or library: graceful degradation to silence, not a crash.
- Invalid VGZ/VGM data: log the error and skip to the next file, do not crash.
- Missing `tunes/` directory: play without background music.

---

## 4. Acceptance Criteria

The game meets these tests of correctness:

1. Game starts on title screen with animated effects.
2. SPACE on title starts a new game with engine sound.
3. WASD moves the helicopter in all four directions.
4. SPACE during gameplay fires 1+ bullets diagonally down-right.
5. M drops a bomb straight down; bomb explodes on ground contact.
6. Landing on the ground pauses auto-scroll and allows civilian pickup.
7. Civilians run toward a grounded, nearby helicopter and board it.
8. Helicopter takes off while civilian is running causes them to wait.
9. Landing on helipad without all civilians shows hint message.
10. Landing on helipad with all civilians triggers victory.
11. Enemy guns fire aimed bullets at the airborne helicopter.
12. Guns are destroyed by 3 bullets or 1 bomb.
13. Helicopter takes damage from enemy bullets and flashes when invincible.
14. HP reaching 0 triggers game over with explosion.
15. Destroying guns and rescuing civilians accumulates score.
16. All civilians rescued triggers return-to-base mode (reverse scroll).
17. ESC quits the game at any point.
18. SPACE on victory/game-over returns to title screen.
19. Every new game picks a random palette theme.
20. Rescuing 2 civilians increases bullet count by 1 (up to 5).
21. No warnings or errors when running the game.
22. Every symbol in the source has a docstring.
23. Commits follow the branch + merge workflow.

---

## 5. Project Files

| File | Purpose |
|------|---------|
| `main.py` | Single source file containing all game code |
| `AGENTS.md` | Architecture overview, code map, common pitfalls |
| `WORKFLOW_STATE.md` | Current project state, decisions, bug history |
| `TASK.md` | This file -- requirements and acceptance criteria |
| `tunes/*.vgz` | Optional background music files (YM3812/OPL2 register data) |
