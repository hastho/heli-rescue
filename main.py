# Heli Rescue -- 8-bit side-scrolling helicopter rescue game
# Copyright (C) 2026  Thomas Hass
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

"""
Heli Rescue -- 8-bit side-scrolling helicopter rescue game

Controls:
  W A S D  -- Move helicopter
  SPACE    -- Shoot (bullets go upward)
  M        -- Drop bomb (falls straight down)
  SPACE    -- Start / Restart

Objective:
  Pick up all civilians, return to base, avoid enemy guns.
"""

from __future__ import annotations

import pygame
import math
import random
import sys
from enum import Enum
import gzip
import struct
import array
import os
import glob
import json
from typing import Any
import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

LEVEL_WIDTH = 4000

# Colours (8-bit retro palette)
SKY_BLUE = (100, 180, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 40, 40)
DARK_RED = (160, 20, 20)
GREEN = (60, 180, 60)
DARK_GREEN = (20, 120, 20)
OLIVE = (100, 130, 40)
BROWN = (140, 80, 30)
DARK_BROWN = (100, 55, 15)
GRAY = (140, 140, 140)
DARK_GRAY = (80, 80, 80)
YELLOW = (240, 220, 40)
ORANGE = (240, 140, 20)
PURPLE = (140, 60, 180)
BEIGE = (210, 180, 140)

# Theme palettes (swap these to change level appearance without changing layout)
THEMES = {
    'summer': {
        'dirt': (140, 80, 30),
        'dirt_dark': (100, 55, 15),
        'grass': (60, 180, 60),
        'grass_dark': (20, 120, 20),
        'mountain': (60, 70, 100),
        'mountain_outline': (50, 60, 90),
        'hill': (40, 80, 40, 160),
        'hill_dark': (30, 70, 30, 160),
        'trunk': (100, 55, 15),
        'foliage': (60, 180, 60),
        'foliage_dark': (20, 120, 20),
        'building': (100, 55, 15),
        'roof': (220, 40, 40),
    },
    'autumn': {
        'dirt': (140, 80, 30),
        'dirt_dark': (100, 55, 15),
        'grass': (180, 160, 40),
        'grass_dark': (140, 120, 20),
        'mountain': (80, 70, 90),
        'mountain_outline': (70, 60, 80),
        'hill': (160, 100, 40, 160),
        'hill_dark': (130, 80, 30, 160),
        'trunk': (100, 55, 15),
        'foliage': (180, 120, 20),
        'foliage_dark': (140, 80, 10),
        'building': (100, 55, 15),
        'roof': (180, 60, 20),
    },
    'winter': {
        'dirt': (150, 150, 160),
        'dirt_dark': (120, 120, 130),
        'grass': (200, 210, 220),
        'grass_dark': (170, 180, 190),
        'mountain': (100, 110, 140),
        'mountain_outline': (80, 90, 120),
        'hill': (130, 150, 170, 160),
        'hill_dark': (110, 130, 150, 160),
        'trunk': (80, 50, 30),
        'foliage': (100, 140, 100),
        'foliage_dark': (60, 100, 60),
        'building': (80, 60, 40),
        'roof': (140, 40, 40),
    },
    'volcanic': {
        'dirt': (80, 50, 50),
        'dirt_dark': (50, 30, 30),
        'grass': (60, 40, 40),
        'grass_dark': (80, 30, 30),
        'mountain': (50, 30, 40),
        'mountain_outline': (40, 20, 30),
        'hill': (80, 40, 40, 160),
        'hill_dark': (60, 30, 30, 160),
        'trunk': (60, 40, 20),
        'foliage': (40, 30, 20),
        'foliage_dark': (30, 20, 10),
        'building': (60, 40, 20),
        'roof': (200, 40, 20),
    },
}

# Helicopter
HELI_SPEED = 5
HELI_SIZE = (36, 26)
HELI_MAX_HP = 3
HELI_MAX_BOMBS = 5
SHOOT_COOLDOWN = 8  # frames
BOMB_COOLDOWN = 20

# Auto-scroll
SCROLL_NORMAL = 2        # px / frame right
SCROLL_BACKTRACK = -1    # px / frame left  (backtrack)
SCROLL_RETURN = -4       # px / frame left  (return to base)
BACKTRACK_ZONE = 120     # px from left edge

# Bullets & bombs
BULLET_SPEED = 10
ENEMY_BULLET_SPEED = 4
BOMB_FALL_SPEED = 6
EXPLOSION_DURATION = 15  # frames
FIRE_SPREAD_DEG = 25     # total spread arc for multi-bullet fan (degrees)

# Civilians
CIVILIAN_RUN_SPEED = 2
CIVILIAN_AGGRO_RANGE = 120

# Enemy guns
GUN_RANGE = 300
GUN_FIRE_INTERVAL = 45   # frames
GUN_MAX_HP = 3
GUN_BULLET_SPEED = 4

# High scores
HIGHSCORES_FILE = "highscores.json"
MAX_HIGHSCORES = 10

# Terrain
TERRAIN_SEGMENT = 20     # px per height entry
NUM_SEGMENTS = LEVEL_WIDTH // TERRAIN_SEGMENT  # 200

# ---------------------------------------------------------------------------
# Game states
# ---------------------------------------------------------------------------
class GameState(Enum):
    """Game state machine.

    Transitions:
        TITLE --SPACE--> PLAYING --all rescued--> VICTORY
        PLAYING --HP=0--> GAME_OVER
        VICTORY --SPACE--> PLAYING (NG+) / --ESC--> TITLE
        GAME_OVER --SPACE--> TITLE
        TITLE --TAB--> HIGH_SCORES --SPACE/ESC--> TITLE
    """
    TITLE = 0
    PLAYING = 1
    VICTORY = 2
    GAME_OVER = 3
    HIGH_SCORES = 4


# ---------------------------------------------------------------------------
# Sound helpers
# ---------------------------------------------------------------------------
def _make_sound(samples: list[int], sample_rate: int = 22050, volume: float = 0.3) -> pygame.mixer.Sound:
    """Create a pygame Sound from a list of 16-bit integer samples."""
    buf = array.array('h', samples)
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    snd.set_volume(volume)
    return snd


def _square_wave(freq: float, duration_ms: float, sample_rate: int = 22050) -> list[int]:
    """Generate square wave samples."""
    n_samples = int(sample_rate * duration_ms / 1000)
    period = sample_rate // max(freq, 1)
    return [
        int(16000 if (i % period) < period // 2 else -16000)
        for i in range(n_samples)
    ]


def _white_noise(duration_ms: float, sample_rate: int = 22050) -> list[int]:
    """Generate white noise samples for explosion/sfx.

    Each sample is a random value in [-16000, 16000]. Used to create
    explosion, shoot, and damage sound effects.

    Args:
        duration_ms: Length of the noise burst in milliseconds.
        sample_rate: Samples per second (default 22050, overridden to 44100 by init_sounds).

    Returns:
        list[int]: List of 16-bit PCM samples.
    """
    n_samples = int(sample_rate * duration_ms / 1000)
    return [random.randint(-16000, 16000) for _ in range(n_samples)]


def _sine_wave(freq: float, duration_ms: float, sample_rate: int = 22050) -> list[int]:
    """Generate sine wave samples for musical tones/pickup sounds.

    Used for the victory jingle and civilian pickup beep.

    Args:
        freq: Frequency in Hz (e.g. 440 for A4).
        duration_ms: Length of the tone in milliseconds.
        sample_rate: Samples per second (default 22050).

    Returns:
        list[int]: List of 16-bit PCM samples.
    """
    n_samples = int(sample_rate * duration_ms / 1000)
    return [
        int(16000 * math.sin(2 * math.pi * freq * i / sample_rate))
        for i in range(n_samples)
    ]


def init_sounds() -> dict[str, pygame.mixer.Sound]:
    """Pre-compute and return dict of sound effects."""
    sounds = {}
    sr = 44100

    # Engine hum -- low square wave (looping, started when entering PLAYING state)
    eng = _square_wave(80, 200, sr)
    sounds['engine'] = _make_sound(eng, sr, 0.04)

    # Shoot -- short noise
    sounds['shoot'] = _make_sound(_white_noise(40, sr), sr, 0.15)

    # Bomb drop -- descending tone
    bomb_s = []
    for i in range(int(sr * 200 / 1000)):
        t = i / sr
        freq = 600 - (600 - 80) * (t / 0.2)
        val = int(12000 * math.sin(2 * math.pi * freq * t))
        bomb_s.append(val)
    sounds['bomb_drop'] = _make_sound(bomb_s, sr, 0.2)

    # Explosion -- white noise burst
    sounds['explosion'] = _make_sound(_white_noise(200, sr), sr, 0.3)

    # Civilian pickup -- ascending beep
    pickup_s = []
    for i in range(int(sr * 120 / 1000)):
        t = i / sr
        freq = 500 + 1000 * (t / 0.12)
        val = int(14000 * math.sin(2 * math.pi * freq * t))
        pickup_s.append(val)
    sounds['pickup'] = _make_sound(pickup_s, sr, 0.2)

    # Damage -- low buzz
    sounds['damage'] = _make_sound(_square_wave(80, 150, sr), sr, 0.2)

    # Victory jingle
    jingle_s = []
    notes = [523, 659, 784, 1047]  # C5 E5 G5 C6
    for freq in notes:
        for i in range(int(sr * 100 / 1000)):
            t = i / sr
            val = int(14000 * math.sin(2 * math.pi * freq * t))
            # fade out
            env = 1.0 - i / (sr * 0.1)
            jingle_s.append(int(val * env))
    sounds['victory'] = _make_sound(jingle_s, sr, 0.3)

    return sounds


# ---------------------------------------------------------------------------
# VGM/VGZ parser for YM3812 (OPL2) music playback via ymfm-py
# ---------------------------------------------------------------------------

def _parse_vgm(raw_bytes: bytes) -> tuple[int, list[tuple[int, int, int]]]:
    """Parse VGM command stream from raw bytes (decompressed VGZ or raw VGM).

    Returns (total_samples, event_list) where:
    - total_samples: number of samples at 44100 Hz
    - event_list: [(sample_pos_44100, reg, val), ...] for YM3812 writes
    """
    assert raw_bytes[0:4] == b'Vgm ', "Not a VGM file"

    # Scan forward from offset 0x40 to find first real command byte,
    # handling v1.50+ where the data offset field may point inside the header.
    data_offset = 0x40
    for scan in range(0x40, min(len(raw_bytes), 0x200)):
        b = raw_bytes[scan]
        if b in (0x5A, 0x5B, 0x52, 0x53, 0x80, 0x50, 0x61, 0x62, 0x63, 0x66) or (0x70 <= b <= 0x7F):
            data_offset = scan
            break

    events = []
    pos = data_offset
    sample = 0  # sample counter at 44100 Hz

    while pos < len(raw_bytes) - 2:
        byte = raw_bytes[pos]

        if 0x70 <= byte <= 0x7F:
            # Wait (byte & 0x0F) + 1 samples
            sample += (byte & 0x0F) + 1
            pos += 1
        elif byte == 0x61:
            # Wait 16-bit sample count
            sample += struct.unpack_from('<H', raw_bytes, pos + 1)[0]
            pos += 3
        elif byte == 0x62:
            sample += 735   # 1/60 sec at 44100 Hz
            pos += 1
        elif byte == 0x63:
            sample += 882   # 1/50 sec at 44100 Hz
            pos += 1
        elif byte == 0x5A:
            # YM3812 register write: reg, val
            reg = raw_bytes[pos + 1]
            val = raw_bytes[pos + 2]
            events.append((sample, reg, val))
            pos += 3
        elif byte == 0x66:
            # End of stream
            break
        elif byte == 0x67:
            # Data block: type(1) + size(4) + data(size)
            blk_size = struct.unpack_from('<I', raw_bytes, pos + 2)[0]
            pos += 6 + blk_size
        elif byte == 0x68:
            sz = struct.unpack_from('<H', raw_bytes, pos + 4)[0]
            pos += 6 + sz
        elif byte in (0x80, 0x50):
            pos += 2  # SN76489 / PSG
        elif byte in (0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5B, 0x5C, 0x5D):
            pos += 3  # Other chip writes (YM2612, YM2151, etc.)
        elif byte in (0x90, 0x91):
            pos += 9  # DAC stream
        elif byte == 0x92:
            pos += 5
        elif byte in (0x00, 0x30):
            pos += 1  # NOP / YM2612 DAC
        else:
            pos += 1  # Skip unknown, keep parsing

    return sample, events


def _render_vgz(filepath: str, volume: float = 0.5, max_duration: int = 120) -> pygame.mixer.Sound | None:
    """Render a VGZ or VGM file to a pygame.mixer.Sound using ymfm-py.

    Returns a pygame.mixer.Sound or None on any error.
    """
    try:
        import ymfm
    except ImportError:
        print("ymfm-py not installed. Install with: pip install ymfm-py")
        return None

    try:
        with open(filepath, 'rb') as f:
            raw = f.read()

        # Decompress VGZ (gzip) if needed; VGM passes through
        if filepath.lower().endswith('.vgz'):
            try:
                vgm_data = gzip.decompress(raw)
            except Exception:
                print(f"  Not a valid gzip file: {filepath}")
                return None
        else:
            vgm_data = raw

        total_samples, events = _parse_vgm(vgm_data)
        if total_samples <= 0 and events:
            total_samples = events[-1][0] + 44100  # 1s after last event

        # Cap duration
        sample_count = min(total_samples, max_duration * 44100)
        if sample_count <= 0:
            return None

        # Create YM3812 chip and render
        chip = ymfm.YM3812(clock=3579545)
        chip.reset()

        # Render with precise event-boundary timing
        output = []
        event_idx = 0
        pos = 0

        while pos < sample_count:
            # Process all events at or before this exact position
            while event_idx < len(events) and events[event_idx][0] <= pos:
                _, reg, val = events[event_idx]
                chip.write(0, reg)
                chip.write(1, val)
                event_idx += 1

            # Find the next event position (or end of audio)
            next_event = events[event_idx][0] if event_idx < len(events) else sample_count
            chunk_end = min(next_event, sample_count)

            if chunk_end > pos:
                # Generate samples up to the next event boundary
                chunk_samples = chip.generate(chunk_end - pos)
                for i in range(chunk_end - pos):
                    output.append(chunk_samples[i, 0])
                pos = chunk_end
            else:
                pos += 1  # safety: avoid infinite loop if events align

        # Normalize to 16-bit
        if not output:
            return None
        max_val = max(abs(s) for s in output)
        if max_val == 0:
            return None

        scale = min(32000.0 / max_val, 1.0)
        s16 = array.array('h', [int(s * scale) for s in output])

        snd = pygame.mixer.Sound(buffer=s16.tobytes())
        snd.set_volume(volume)
        return snd

    except Exception as e:
        print(f"  Error rendering {filepath}: {e}")
        return None


# ---------------------------------------------------------------------------
# VGZ/VGM music loader (returns None if no valid file or ymfm-py unavailable)
# ---------------------------------------------------------------------------
def init_music() -> pygame.mixer.Sound | None:
    """Try to load VGZ/VGM music from tunes/ directory.
    Returns a pygame.mixer.Sound or None if no playable file is found.
    """
    tunes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tunes')
    if os.path.isdir(tunes_dir):
        for ext in ('*.vgz', '*.vgm'):
            pattern = os.path.join(tunes_dir, ext)
            for path in sorted(glob.glob(pattern)):
                print(f"Loading VGZ/VGM: {path}")
                snd = _render_vgz(path)
                if snd is not None:
                    print(f"  Successfully loaded ({snd.get_length():.1f}s)")
                    return snd
                print(f"  Failed, trying next...")
    print("No playable VGZ/VGM music found -- game will play without background music")
    return None


# ---------------------------------------------------------------------------
# Pixel-art asset generation
# ---------------------------------------------------------------------------
def make_helicopter_surface() -> pygame.Surface:
    """Draw a side-view pixel-art helicopter."""
    w, h = HELI_SIZE
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Main body (olive)
    body_rect = pygame.Rect(4, 8, 28, 12)
    pygame.draw.ellipse(surf, OLIVE, body_rect)
    # Tail
    pygame.draw.rect(surf, OLIVE, (28, 10, 8, 6))
    # Tail fin
    pts = [(36, 10), (36, 16), (32, 13)]
    pygame.draw.polygon(surf, DARK_GREEN, pts)
    # Cockpit window
    pygame.draw.ellipse(surf, SKY_BLUE, (8, 10, 10, 7))
    # Rotor shaft
    pygame.draw.rect(surf, DARK_GRAY, (14, 3, 2, 5))
    # Rotor blades
    pygame.draw.rect(surf, GRAY, (4, 1, 22, 3))
    pygame.draw.rect(surf, DARK_GRAY, (4, 2, 22, 1))
    # Skids
    pygame.draw.rect(surf, DARK_GRAY, (6, 20, 20, 2))
    pygame.draw.rect(surf, DARK_GRAY, (8, 22, 16, 2))
    return pygame.transform.flip(surf, True, False)


def make_civilian_surface() -> pygame.Surface:
    """Draw a tiny pixel person."""
    surf = pygame.Surface((10, 14), pygame.SRCALPHA)
    # Head
    surf.set_at((4, 0), BEIGE)
    surf.set_at((5, 0), BEIGE)
    surf.set_at((4, 1), BEIGE)
    surf.set_at((5, 1), BEIGE)
    # Body
    pygame.draw.rect(surf, BLUE := (60, 60, 200), (3, 3, 4, 5))
    # Legs
    pygame.draw.rect(surf, DARK_GRAY, (3, 8, 2, 5))
    pygame.draw.rect(surf, DARK_GRAY, (5, 8, 2, 5))
    # Arms
    pygame.draw.rect(surf, BEIGE, (1, 3, 2, 4))
    pygame.draw.rect(surf, BEIGE, (7, 3, 2, 4))
    return surf


def make_enemy_gun_surface() -> pygame.Surface:
    """Draw a stationary enemy gun turret."""
    surf = pygame.Surface((24, 20), pygame.SRCALPHA)
    # Base
    pygame.draw.rect(surf, DARK_GRAY, (4, 12, 16, 8))
    # Swivel
    pygame.draw.circle(surf, GRAY, (12, 12), 5)
    # Barrel
    pygame.draw.rect(surf, DARK_RED, (8, 2, 4, 12))
    # Muzzle
    pygame.draw.rect(surf, YELLOW, (8, 0, 4, 3))
    return surf


def make_bullet_surface() -> pygame.Surface:
    """4x8 pixel yellow bullet sprite (player projectile)."""
    surf = pygame.Surface((4, 8), pygame.SRCALPHA)
    pygame.draw.rect(surf, YELLOW, (0, 0, 4, 8))
    pygame.draw.rect(surf, ORANGE, (1, 1, 2, 6))
    return surf


def make_enemy_bullet_surface() -> pygame.Surface:
    """6x6 pixel red/yellow bullet sprite (enemy projectile)."""
    surf = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(surf, RED, (3, 3), 3)
    pygame.draw.circle(surf, YELLOW, (3, 3), 1)
    return surf


def make_bomb_surface() -> pygame.Surface:
    """8x12 pixel bomb sprite with fins."""
    surf = pygame.Surface((8, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, DARK_GRAY, (0, 2, 8, 10))
    pygame.draw.rect(surf, GRAY, (2, 0, 4, 3))
    # Fins
    pygame.draw.rect(surf, DARK_GRAY, (0, 2, 2, 2))
    pygame.draw.rect(surf, DARK_GRAY, (6, 2, 2, 2))
    return surf


def make_explosion_surfaces() -> list[pygame.Surface]:
    """Return list of frames for explosion animation."""
    frames = []
    for i in range(5):
        r = 4 + i * 4
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        colors = [YELLOW, ORANGE, RED]
        col = colors[min(i, len(colors) - 1)]
        pygame.draw.circle(surf, col, (r, r), r)
        if i > 1:
            pygame.draw.circle(surf, ORANGE, (r, r), r - 2)
        if i > 3:
            pygame.draw.circle(surf, YELLOW, (r, r), r - 4)
        frames.append(surf)
    return frames


def make_cloud_surface(w: int, h: int) -> pygame.Surface:
    """Simple cloud shape."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    pygame.draw.ellipse(surf, (255, 255, 255, 200), (cx - 20, cy - 8, 40, 16))
    pygame.draw.ellipse(surf, (255, 255, 255, 200), (cx - 12, cy - 14, 24, 20))
    pygame.draw.ellipse(surf, (255, 255, 255, 200), (cx + 4, cy - 12, 20, 18))
    return surf


# ---------------------------------------------------------------------------
# Level / Terrain
# ---------------------------------------------------------------------------
def build_terrain() -> list[int]:
    """Return a list of ground heights (one per 20px segment, 200 entries)."""
    seg = TERRAIN_SEGMENT
    heights = []

    # Define key points (segment_index, height)
    # Height is y-coordinate of ground surface (higher = lower on screen)
    base_h = 460
    flat_h = 440
    hill_peak = 360
    valley_bottom = 480
    mountain_peak = 300

    key_points = [
        (0, base_h),           # base
        (20, base_h),          # end base flat
        (30, flat_h - 10),     # transition
        (45, flat_h),          # plains
        (60, flat_h),          # plains end
        (65, flat_h - 20),     # gentle bump
        (75, flat_h),          # back to plains
        (90, flat_h + 10),     #
        (100, hill_peak + 20), # hills start
        (110, hill_peak),      # hill peak
        (120, hill_peak + 30), # valley
        (130, hill_peak + 10), # hill
        (140, flat_h + 10),    # transition
        (150, flat_h),         #
        (160, flat_h - 20),    # valley start
        (170, valley_bottom),  # valley bottom
        (180, valley_bottom),  # valley floor
        (190, flat_h),         # rise
        (200, flat_h),         #
        (210, mountain_peak + 40),  # mountain start
        (220, mountain_peak),       # peak
        (230, mountain_peak + 30),  # saddle
        (240, mountain_peak + 10),  # peak
        (250, flat_h + 10),         # end mountains
        (260, flat_h + 20),         # transition to end
        (270, base_h),              # end plateau
        (NUM_SEGMENTS - 1, base_h),
    ]

    # Interpolate between key points
    for seg_idx in range(NUM_SEGMENTS):
        # Find surrounding key points
        prev_k, next_k = None, None
        for k in key_points:
            if k[0] <= seg_idx:
                prev_k = k
            if k[0] >= seg_idx and next_k is None:
                next_k = k
        if prev_k is None or next_k is None:
            heights.append(base_h)
            continue

        if prev_k[0] == next_k[0]:
            h = prev_k[1]
        else:
            t = (seg_idx - prev_k[0]) / (next_k[0] - prev_k[0])
            h = prev_k[1] + (next_k[1] - prev_k[1]) * t
        # Add small noise for organic feel
        noise = random.randint(-3, 3)
        heights.append(int(h) + noise)

    return heights


def get_ground_y(terrain: list[int], x: float) -> int:
    """Return ground surface y-coordinate at world x."""
    seg_idx = int(x / TERRAIN_SEGMENT)
    seg_idx = max(0, min(seg_idx, len(terrain) - 1))
    return terrain[seg_idx]


def make_terrain_surface(terrain: list[int], level_width: int,
                         palette: dict | None = None) -> pygame.Surface:
    """Draw the full terrain surface (dirt + grass top).
    If palette is None, uses the 'summer' theme.
    """
    if palette is None:
        palette = THEMES['summer']
    surf = pygame.Surface((level_width, SCREEN_HEIGHT), pygame.SRCALPHA)
    seg_w = TERRAIN_SEGMENT
    for i, h in enumerate(terrain):
        x = i * seg_w
        # Dirt column
        dirt_h = SCREEN_HEIGHT - h
        rect = pygame.Rect(x, h, seg_w, dirt_h)
        # Alternate shades for pixel effect
        col = palette['dirt'] if (i // 2) % 2 == 0 else palette['dirt_dark']
        pygame.draw.rect(surf, col, rect)
        # Grass line on top
        grass_col = palette['grass'] if (i // 3) % 2 == 0 else palette['grass_dark']
        pygame.draw.rect(surf, grass_col, (x, h - 2, seg_w, 4))
    return surf


def make_mountains_surface(level_width: int,
                           palette: dict | None = None) -> pygame.Surface:
    """Far background mountains.
    If palette is None, uses the 'summer' theme.
    """
    if palette is None:
        palette = THEMES['summer']
    mtn_col = palette['mountain']
    mtn_out = palette['mountain_outline']
    surf = pygame.Surface((level_width, SCREEN_HEIGHT), pygame.SRCALPHA)
    # Draw a few mountain shapes
    peaks = [
        (0, 50, 200),
        (300, 35, 180),
        (700, 45, 220),
        (1200, 30, 160),
        (1700, 40, 200),
        (2200, 25, 150),
        (2700, 50, 190),
        (3200, 35, 170),
        (3700, 45, 210),
    ]
    for px, py, pw in peaks:
        pts = [(px, SCREEN_HEIGHT), (px + pw // 2, py), (px + pw, SCREEN_HEIGHT)]
        pygame.draw.polygon(surf, mtn_col, pts)
        pygame.draw.polygon(surf, mtn_out, pts, 1)
    return surf


def make_hills_surface(level_width: int,
                       palette: dict | None = None) -> pygame.Surface:
    """Mid-ground hills.
    If palette is None, uses the 'summer' theme.
    """
    if palette is None:
        palette = THEMES['summer']
    surf = pygame.Surface((level_width, SCREEN_HEIGHT), pygame.SRCALPHA)
    # Rolling hills
    for x in range(0, level_width, 4):
        h_val = 480 + int(30 * math.sin(x * 0.003)) + int(20 * math.sin(x * 0.007))
        col = palette['hill'] if (x // 8) % 2 == 0 else palette['hill_dark']
        pygame.draw.line(surf, col, (x, h_val), (x, SCREEN_HEIGHT))
    return surf


def make_clouds_surface(level_width: int) -> pygame.Surface:
    """Static cloud layer for parallax."""
    surf = pygame.Surface((level_width, SCREEN_HEIGHT // 2), pygame.SRCALPHA)
    random.seed(42)
    for _ in range(12):
        cx = random.randint(0, level_width)
        cy = random.randint(20, 180)
        cw = random.randint(50, 90)
        ch = random.randint(16, 28)
        alpha = random.randint(140, 220)
        col = (255, 255, 255, alpha)
        pygame.draw.ellipse(surf, col, (cx, cy, cw, ch))
        pygame.draw.ellipse(surf, col, (cx - 10, cy - 6, cw - 10, ch + 4))
    return surf


# ---------------------------------------------------------------------------
# Entity classes
# ---------------------------------------------------------------------------
class Helicopter:
    """Player-controlled helicopter.

    Manages position, velocity, HP, bombs, grounded state, invincibility,
    rescued passenger list, and firing cooldowns. Updated each frame by
    Game.update(). Rendered by Game._draw_game().

    Movement is WASD with HELI_SPEED px/frame. Ground collision snaps the
    heli to the terrain surface; ceiling clamped to y=80. Level edges are
    also clamped. Bomb capacity is configurable via max_bombs (default
    HELI_MAX_BOMBS, lowered in NG+ for higher difficulty).
    """

    def __init__(self, max_bombs: int = HELI_MAX_BOMBS):
        """Initialise helicopter at default spawn position (150, 300).

        State: full HP, full bombs, no passengers, no cooldowns, alive.

        Args:
            max_bombs: Maximum bomb capacity (default HELI_MAX_BOMBS,
                       lowered in NG+ for higher difficulty).
        """
        self.x = 150
        self.y = 300
        self.vx = 0
        self.vy = 0
        self.w, self.h = HELI_SIZE
        self.hp = HELI_MAX_HP
        self.max_hp = HELI_MAX_HP
        self.max_bombs = max_bombs
        self.bombs = max_bombs
        self.grounded = False
        self.shoot_cooldown = 0
        self.bomb_cooldown = 0
        self.passengers = []  # list of rescued civilian ids
        self.invincible_timer = 0  # flash after hit
        self.surface = make_helicopter_surface()
        self.facing_right = True
        self.alive = True

    @property
    def rect(self) -> pygame.Rect:
        """AABB collision rectangle centred on (x, y) with (w, h)."""
        return pygame.Rect(self.x - self.w // 2, self.y - self.h // 2, self.w, self.h)

    @property
    def bottom(self) -> float:
        """Y-coordinate of the helicopter's bottom edge."""
        return self.y + self.h // 2

    def update(self, keys: list[bool], terrain: list[int], scroll_speed: int = SCROLL_NORMAL) -> None:
        """Advance helicopter one frame: handle input, movement, collisions.

        Reads WASD from the pressed-keys array, applies velocity, then
        resolves ground collision (snap to terrain surface), ceiling clamp
        (y >= 80), and level-boundary clamps. Decrements all cooldowns.

        Sets facing_right based on horizontal direction (player input takes
        priority; if stationary, follows auto-scroll direction).

        Args:
            keys: Boolean array from pygame.key.get_pressed().
            terrain: Height array from build_terrain().
            scroll_speed: Current auto-scroll speed (default SCROLL_NORMAL).
        """
        if not self.alive:
            return

        self.vx = 0
        self.vy = 0

        if keys[pygame.K_w]:
            self.vy = -HELI_SPEED
        if keys[pygame.K_s]:
            self.vy = HELI_SPEED
        if keys[pygame.K_a]:
            self.vx = -HELI_SPEED
        if keys[pygame.K_d]:
            self.vx = HELI_SPEED

        # Determine facing direction based on movement or scroll
        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False
        else:
            self.facing_right = scroll_speed >= 0

        # Apply velocity
        self.x += self.vx
        self.y += self.vy

        # Ground collision
        ground_y = get_ground_y(terrain, self.x)
        if self.bottom >= ground_y:
            self.y = ground_y - self.h // 2
            self.grounded = True
            self.vy = 0
        else:
            self.grounded = False

        # Ceiling
        if self.y - self.h // 2 < 80:
            self.y = 80 + self.h // 2

        # Left / right level bounds
        if self.x - self.w // 2 < 0:
            self.x = self.w // 2
        if self.x + self.w // 2 > LEVEL_WIDTH:
            self.x = LEVEL_WIDTH - self.w // 2

        # Cooldowns
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def shoot(self):
        """Fire one or more bullets downward-forward at the helicopter's current position.

        Firepower scales with rescued civilians:
            num_bullets = 1 + (passengers // 2), clamped to [1, 5].

        When num_bullets == 1, fires a single center bullet. Direction depends
        on self.facing_right: down-right when facing right, down-left when facing left.
        When num_bullets > 1, fires a symmetric fan spread across FIRE_SPREAD_DEG degrees
        centered on 45-degree down-right (or down-left when facing left). Each bullet
        gets its own (vx, vy) via trig so that all bullets travel at the same speed
        but different trajectories.

        Returns:
            list[Bullet]: Empty list if on cooldown, otherwise 1-5 Bullet objects.
        """
        if self.shoot_cooldown > 0:
            return []
        self.shoot_cooldown = SHOOT_COOLDOWN

        num = min(5, 1 + len(self.passengers) // 2)
        cx, cy = self.x, self.bottom

        if num == 1:
            if self.facing_right:
                return [Bullet(cx, cy)]
            else:
                return [Bullet(cx, cy, -BULLET_SPEED, BULLET_SPEED)]

        spread = math.radians(FIRE_SPREAD_DEG)
        step = spread / (num - 1)
        base_angle = math.pi / 4 if self.facing_right else 3 * math.pi / 4
        start = base_angle - spread / 2
        # Speed magnitude matching the current vx=vy=10 baseline
        mag = math.sqrt(BULLET_SPEED * BULLET_SPEED * 2)

        bullets = []
        for i in range(num):
            angle = start + step * i
            vx = mag * math.cos(angle)
            vy = mag * math.sin(angle)
            bullets.append(Bullet(cx, cy, vx, vy))
        return bullets

    def drop_bomb(self) -> Bomb | None:
        """Drop a single bomb below the helicopter if available and off cooldown.

        Bombs are limited (self.max_bombs) and have a cooldown (BOMB_COOLDOWN
        frames). Each bomb falls straight down and explodes on ground contact.

        Returns:
            Bomb | None: A new Bomb object, or None if out of bombs or on cooldown.
        """
        if self.bombs <= 0 or self.bomb_cooldown > 0:
            return None
        self.bombs -= 1
        self.bomb_cooldown = BOMB_COOLDOWN
        return Bomb(self.x, self.bottom)

    def take_damage(self) -> bool:
        """Inflict one point of damage. No-op during invincibility window.

        On HP reaching 0, sets alive=False. Invincibility lasts 30 frames
        and is indicated by the helicopter sprite flashing.

        Returns:
            bool: True if damage was applied, False if invincible.
        """
        if self.invincible_timer > 0:
            return False
        self.hp -= 1
        self.invincible_timer = 30  # half second invincibility
        if self.hp <= 0:
            self.alive = False
        return True

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render the helicopter at its world position, offset by camera scroll.

        Flashes (skips every other 4-frame interval) while invincible.

        Args:
            screen: The pygame display surface.
            offset_x: Camera scroll offset (self.scroll_x).
        """
        if not self.alive:
            return
        sx = int(self.x - offset_x - self.w // 2)
        sy = int(self.y - self.h // 2)
        # Flash when invincible
        if self.invincible_timer > 0 and (self.invincible_timer // 4) % 2 == 0:
            return
        surf = self.surface if self.facing_right else pygame.transform.flip(self.surface, True, False)
        screen.blit(surf, (sx, sy))


class Bullet:
    """A player-fired projectile that travels diagonally (down-right or down-left).

    Direction depends on the helicopter's facing: right when facing right,
    left when facing left. Spawned by Helicopter.shoot(). Moves at a fixed
    velocity (vx, vy) each frame. Dies when it exits the visible area
    (bottom, right edge, or left edge).
    Collision with enemy guns is handled externally in Game.update().
    """

    def __init__(self, x: float, y: float, vx: float | None = None, vy: float | None = None):
        """Initialise bullet at world position (x, y) with given velocity.

        If vx or vy is None, defaults to BULLET_SPEED (10), giving a
        45-degree down-right trajectory (standard for right-facing heli).
        When the helicopter faces left, shoot() passes explicit negative
        vx for down-left trajectory.

        Args:
            x: World x position (pixels).
            y: World y position (pixels).
            vx: Horizontal velocity (px/frame). Positive = right.
            vy: Vertical velocity (px/frame). Positive = down.
        """
        self.x = x
        self.y = y
        self.vx = BULLET_SPEED if vx is None else vx
        self.vy = BULLET_SPEED if vy is None else vy
        self.alive = True
        self.surface = make_bullet_surface()

    def update(self) -> None:
        """Advance bullet one frame: move by (vx, vy), kill if off-screen."""
        if not self.alive:
            return
        self.x += self.vx
        self.y += self.vy
        if self.y > SCREEN_HEIGHT or self.x > LEVEL_WIDTH or self.x < 0:
            self.alive = False

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render bullet at its world position, offset by camera scroll."""
        if not self.alive:
            return
        sx = int(self.x - offset_x - 2)
        sy = int(self.y)
        screen.blit(self.surface, (sx, sy))

    @property
    def rect(self) -> pygame.Rect:
        """4x8 collision rectangle at the bullet's current position."""
        return pygame.Rect(self.x - 2, self.y, 4, 8)


class EnemyBullet:
    """A bullet fired by an EnemyGun, aimed at the helicopter's current position.

    Moves at the configured speed (default GUN_BULLET_SPEED, increased in NG+)
    in the direction of the target. Dies when it exits the visible area
    (any edge +20px margin).
    """

    def __init__(self, x: float, y: float, target_x: float, target_y: float,
                 speed: float = GUN_BULLET_SPEED):
        """Initialise bullet at (x, y) heading toward (target_x, target_y).

        Velocity is computed by normalising the aim vector and scaling to
        the given speed (default GUN_BULLET_SPEED, increased in NG+).
        If the target is at the same position (dist < 1px), falls straight
        down as a fallback.

        Args:
            x: Spawn world-x (gun muzzle position).
            y: Spawn world-y (gun muzzle position).
            target_x: Target world-x (helicopter centre).
            target_y: Target world-y (helicopter centre).
            speed: Bullet speed in px/frame (default GUN_BULLET_SPEED).
        """
        self.x = x
        self.y = y
        self.alive = True
        self.surface = make_enemy_bullet_surface()
        # Aim at helicopter
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        if dist < 1:
            self.vx, self.vy = 0, speed
        else:
            self.vx = dx / dist * speed
            self.vy = dy / dist * speed

    def update(self) -> None:
        """Advance bullet one frame: move, kill if off-screen."""
        if not self.alive:
            return
        self.x += self.vx
        self.y += self.vy
        if self.y > SCREEN_HEIGHT + 20 or self.y < -20 or self.x < -20 or self.x > LEVEL_WIDTH + 20:
            self.alive = False

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render enemy bullet at its world position, offset by camera scroll."""
        if not self.alive:
            return
        sx = int(self.x - offset_x - 3)
        sy = int(self.y - 3)
        screen.blit(self.surface, (sx, sy))

    @property
    def rect(self) -> pygame.Rect:
        """6x6 collision square centred on the bullet."""
        return pygame.Rect(self.x - 3, self.y - 3, 6, 6)


class Bomb:
    """A bomb dropped by the helicopter that falls straight down.

    Explodes on ground contact, damaging nearby enemy guns (3 HP damage
    in a 50px radius). Returns 'explode' from update() when it hits the
    ground so the Game loop can spawn the explosion and check damage.
    """

    def __init__(self, x: float, y: float):
        """Initialise bomb at (x, y) falling at BOMB_FALL_SPEED.

        Args:
            x: World-x position (helicopter centre).
            y: World-y position (helicopter bottom).
        """
        self.x = x
        self.y = y
        self.vy = BOMB_FALL_SPEED
        self.alive = True
        self.surface = make_bomb_surface()

    def update(self, terrain: list[int]) -> str | None:
        """Advance bomb one frame: fall, check ground/offscreen.

        Args:
            terrain: Height array from build_terrain().

        Returns:
            str | None: 'explode' if bomb hit the ground, None otherwise.
        """
        if not self.alive:
            return None
        self.y += self.vy
        ground_y = get_ground_y(terrain, self.x)
        if self.y + 6 >= ground_y:
            self.alive = False
            return 'explode'
        if self.y > SCREEN_HEIGHT + 20:
            self.alive = False
        return None

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render bomb at its world position, offset by camera scroll."""
        if not self.alive:
            return
        sx = int(self.x - offset_x - 4)
        sy = int(self.y)
        screen.blit(self.surface, (sx, sy))

    @property
    def rect(self) -> pygame.Rect:
        """8x12 collision rectangle at the bomb's current position."""
        return pygame.Rect(self.x - 4, self.y, 8, 12)


class Explosion:
    """Animated explosion effect: expanding circle that fades through YELLOW->ORANGE->RED.

    Each frame of the animation is drawn from a pre-rendered frame list.
    Each frame is shown for 3 ticks, so total duration = len(frames) x 3.
    """

    def __init__(self, x: float, y: float, frames: list[pygame.Surface]):
        """Initialise explosion at (x, y) with pre-rendered frame list.

        Args:
            x: World-x position (pixels).
            y: World-y position (pixels).
            frames: List of expanding circle surfaces from make_explosion_surfaces().
        """
        self.x = x
        self.y = y
        self.frames = frames
        self.frame = 0
        self.alive = True

    def update(self) -> None:
        """Advance animation: increment frame counter, kill when complete."""
        if not self.alive:
            return
        self.frame += 1
        if self.frame >= len(self.frames) * 3:  # each frame shown for 3 ticks
            self.alive = False

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render the current explosion frame, offset by camera scroll."""
        if not self.alive:
            return
        idx = min(self.frame // 3, len(self.frames) - 1)
        surf = self.frames[idx]
        sx = int(self.x - offset_x - surf.get_width() // 2)
        sy = int(self.y - surf.get_height() // 2)
        screen.blit(surf, (sx, sy))


class Civilian:
    """A civilian on the ground that can be rescued.

    State machine:
        waiting -> running -> boarding -> onboard -> rescued

    - waiting:  Standing still, watching for a grounded heli nearby.
    - running:  Moving toward the grounded helicopter at self.run_speed.
    - boarding: Reached the helicopter -- triggers onboard.
    - onboard:  Passenger inside the helicopter (hidden from world).
    - rescued:  Final state after victory (HUD counts these).
    - aggro_range: Distance to trigger run (default CIVILIAN_AGGRO_RANGE).

    If the helicopter takes off while a civilian is running, they return
    to waiting state.
    """

    def __init__(self, cid: int, x: float, ground_y: float,
                 aggro_range: float = CIVILIAN_AGGRO_RANGE,
                 run_speed: float = CIVILIAN_RUN_SPEED):
        """Initialise civilian at (x, ground_y), standing on the terrain.

        Args:
            cid: Unique civilian ID (index into generation order).
            x: World-x position.
            ground_y: Y-coordinate of the terrain surface at x.
            aggro_range: Distance at which civilian starts running toward
                a grounded heli (default CIVILIAN_AGGRO_RANGE).
            run_speed: Movement speed toward heli in px/frame
                (default CIVILIAN_RUN_SPEED).
        """
        self.cid = cid
        self.x = x
        self.y = ground_y - 14  # standing on ground
        self.ground_y = ground_y
        self.aggro_range = aggro_range
        self.run_speed = run_speed
        self.state = 'waiting'  # waiting -> running -> boarding -> onboard -> rescued
        self.surface = make_civilian_surface()
        self.target_x = 0
        self.rescued = False

    def update(self, heli_rect: pygame.Rect, heli_grounded: bool) -> str | None:
        """Advance civilian state machine one frame.

        Args:
            heli_rect: Helicopter AABB rect for distance checks.
            heli_grounded: Whether the helicopter is currently on the ground.

        Returns:
            str | None: 'boarded' if the civilian just boarded, None otherwise.
        """
        if self.state == 'onboard' or self.state == 'rescued':
            return None

        if self.state == 'waiting':
            # Check if heli is nearby and grounded
            if heli_grounded:
                dist = abs(self.x - heli_rect.centerx)
                if dist < self.aggro_range:
                    self.state = 'running'

        elif self.state == 'running':
            # If heli takes off, civilians stop and wait
            if not heli_grounded:
                self.state = 'waiting'
                return None

            # Track helicopter position each frame
            self.target_x = heli_rect.centerx
            dx = self.target_x - self.x
            if abs(dx) < 3:
                self.state = 'boarding'
            else:
                self.x += self.run_speed if dx > 0 else -self.run_speed

        elif self.state == 'boarding':
            self.state = 'onboard'
            return 'boarded'

        return None

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render civilian if not already onboard/rescued."""
        if self.state == 'onboard' or self.state == 'rescued':
            return
        sx = int(self.x - offset_x - 5)
        sy = int(self.y)
        screen.blit(self.surface, (sx, sy))

    @property
    def rect(self) -> pygame.Rect:
        """10x14 collision rectangle at the civilian's position."""
        return pygame.Rect(self.x - 5, self.y, 10, 14)


class EnemyGun:
    """A stationary ground turret that fires aimed bullets at the helicopter.

    Fires only when the helicopter is within self.gun_range, is not grounded,
    and has not yet scrolled past the gun (off-camera left). Each gun has
    GUN_MAX_HP health and can be destroyed by 3 bullets or 1 bomb.
    Uses stored fire_interval, bullet_speed, and gun_range (set in constructor,
    allowing NG+ scaling). Draws a green/red HP bar above itself.
    """

    def __init__(self, gid: int, x: float, ground_y: float,
                 fire_interval: int = GUN_FIRE_INTERVAL,
                 bullet_speed: float = GUN_BULLET_SPEED,
                 gun_range: float = GUN_RANGE):
        """Initialise gun at (x, ground_y) with full HP.

        Args:
            gid: Unique gun ID (index into generation order).
            x: World-x position.
            ground_y: Y-coordinate of the terrain surface at x.
            fire_interval: Frames between shots (default GUN_FIRE_INTERVAL,
                decreased in NG+ for faster fire rate).
            bullet_speed: Speed of enemy bullets in px/frame
                (default GUN_BULLET_SPEED, increased in NG+).
            gun_range: Maximum firing range in px
                (default GUN_RANGE, decreased in NG+).
        """
        self.gid = gid
        self.x = x
        self.y = ground_y - 20  # sits on ground
        self.hp = GUN_MAX_HP
        self.max_hp = GUN_MAX_HP
        self.alive = True
        self.fire_cooldown = 0
        self.fire_interval = fire_interval
        self.bullet_speed = bullet_speed
        self.gun_range = gun_range
        self.surface = make_enemy_gun_surface()

    def update(self, heli_x: float, heli_y: float, heli_grounded: bool,
               scroll_x: float) -> EnemyBullet | None:
        """Advance gun logic: decrement cooldown, maybe fire.

        Fires an EnemyBullet aimed at (heli_x, heli_y) if all conditions met:
            - Alive
            - Helicopter within self.gun_range
            - Helicopter not grounded
            - Gun not scrolled past (self.x < scroll_x - 50)
            - Cooldown elapsed (self.fire_interval frames)

        Args:
            heli_x: Helicopter world-x.
            heli_y: Helicopter world-y.
            heli_grounded: Whether the helicopter is grounded.
            scroll_x: Current camera scroll offset.

        Returns:
            EnemyBullet | None: New bullet if fired, None otherwise.
        """
        if not self.alive:
            return None
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Don't fire if helicopter is behind camera left edge (already passed)
        if self.x < scroll_x - 50:
            return None

        dist = abs(self.x - heli_x)
        if dist <= self.gun_range and not heli_grounded:
            if self.fire_cooldown == 0:
                self.fire_cooldown = self.fire_interval
                # Fire toward helicopter
                return EnemyBullet(self.x, self.y - 10, heli_x, heli_y, self.bullet_speed)
        return None

    def take_damage(self, amount: int = 1) -> bool:
        """Reduce HP by amount. Returns True if destroyed."""
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False
            return True  # destroyed
        return False

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render gun sprite and HP bar, offset by camera scroll."""
        if not self.alive:
            return
        sx = int(self.x - offset_x - 12)
        sy = int(self.y)
        screen.blit(self.surface, (sx, sy))
        # HP bar
        bar_w = 20
        bar_h = 3
        bx = int(self.x - offset_x - bar_w // 2)
        by = sy - 6
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, DARK_RED, (bx, by, bar_w, bar_h))
        pygame.draw.rect(screen, GREEN, (bx, by, int(bar_w * hp_ratio), bar_h))

    @property
    def rect(self) -> pygame.Rect:
        """24x20 collision rectangle at the gun's position."""
        return pygame.Rect(self.x - 12, self.y, 24, 20)


class Particle:
    """Simple pixel particle for engine exhaust, etc."""
    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: tuple[int, int, int], life: int = 20, size: int = 2):
        """Initialise particle with position, velocity, colour, and lifetime.

        Args:
            x: World-x position.
            y: World-y position.
            vx: Horizontal velocity (px/frame).
            vy: Vertical velocity (px/frame).
            color: RGB tuple for particle colour.
            life: Frames until the particle expires (default 20).
            size: Pixel size (width/height, default 2).
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.alive = True

    def update(self) -> None:
        """Advance particle: move, decrement life, kill when expired."""
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, screen: pygame.Surface, offset_x: float) -> None:
        """Render particle as a small square that fades with remaining life."""
        if not self.alive:
            return
        alpha = int(255 * self.life / self.max_life)
        sx = int(self.x - offset_x)
        sy = int(self.y)
        # Approximate alpha with color brightness
        r, g, b = self.color
        factor = self.life / self.max_life
        col = (int(r * factor), int(g * factor), int(b * factor))
        pygame.draw.rect(screen, col, (sx, sy, self.size, self.size))


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def draw_hud(screen: pygame.Surface, heli: Helicopter, civilians: list[Any],
             score: int, font: pygame.font.Font, rank: int = 1) -> None:
    """Render the HUD overlay: hearts, bombs, civilian/firepower status, score.

    Layout (left-aligned at x=10):
        Line 1 (y=10):  Hearts (heart symbol) -- red filled / white outline.
        Line 2 (y=32):  Bombs remaining (B: N/MAX).
        Line 3 (y=54):  Civilians rescued (Civ: N/TOTAL) + firepower diamonds (PWR: filled/empty diamonds).
        Top-right:      Score (y=10, right-aligned) + Rank (below score).

    If all civilians are onboard, a centred "RETURN TO BASE!" message
    appears at y=80.

    Args:
        screen: The pygame display surface.
        heli: The helicopter instance (gives HP, bombs, passenger count).
        civilians: List of all Civilian objects in the level.
        score: Current player score.
        font: Monospace-style pygame Font for rendering text.
        rank: Current difficulty rank (default 1, shown below score).
    """
    # Hearts
    heart_str = ""
    for i in range(heli.max_hp):
        if i < heli.hp:
            heart_str += "\u2665 "  # filled heart
        else:
            heart_str += "\u2661 "  # empty heart
    heart_surf = font.render(heart_str, True, RED)
    screen.blit(heart_surf, (10, 10))

    # Bombs
    bomb_str = f"B: {heli.bombs}/{heli.max_bombs}"
    bomb_surf = font.render(bomb_str, True, WHITE)
    screen.blit(bomb_surf, (10, 32))

    # Civilians rescued / total + firepower
    rescued = sum(1 for c in civilians if c.state == 'onboard' or c.state == 'rescued')
    total = len(civilians)
    pwr = min(5, 1 + len(heli.passengers) // 2)
    pwr_str = '♦' * pwr + '◇' * (5 - pwr)
    civ_str = f"Civ: {rescued}/{total}  PWR: {pwr_str}"
    civ_surf = font.render(civ_str, True, WHITE)
    screen.blit(civ_surf, (10, 54))

    # Score
    score_str = f"Score: {score}"
    score_surf = font.render(score_str, True, YELLOW)
    screen.blit(score_surf, (SCREEN_WIDTH - 150, 10))

    # Rank (NG+)
    if rank > 1:
        rank_str = f"Rank {rank}"
        rank_surf = font.render(rank_str, True, ORANGE)
        screen.blit(rank_surf, (SCREEN_WIDTH - 150, 34))

    # Message when all onboard
    if heli.alive and rescued == total and total > 0:
        msg = "RETURN TO BASE!"
        msg_surf = font.render(msg, True, YELLOW)
        screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, 80))


# ---------------------------------------------------------------------------
# High score helpers
# ---------------------------------------------------------------------------
def load_highscores() -> list[dict]:
    """Load high scores from the JSON file.

    Handles FileNotFoundError (missing file = first play), JSONDecodeError
    (corrupted file), and invalid schema (not a list, missing keys) by
    returning an empty list.

    Returns:
        list[dict]: List of score records, each with keys:
            score, rank, rescued, destroyed, date.
            Empty list on any error.
    """
    if not os.path.exists(HIGHSCORES_FILE):
        return []
    try:
        with open(HIGHSCORES_FILE, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []
    # Validate schema
    if not isinstance(data, list):
        return []
    required_keys = {'score', 'rank', 'rescued', 'destroyed', 'date'}
    for entry in data:
        if not isinstance(entry, dict):
            return []
        if not required_keys.issubset(entry.keys()):
            return []
    return data


def save_highscores(scores: list[dict]) -> None:
    """Save high scores list to the JSON file.

    Args:
        scores: List of score record dicts to persist.
    """
    with open(HIGHSCORES_FILE, 'w') as f:
        json.dump(scores, f, indent=2)


def is_highscore(score: int, scores: list[dict]) -> int | None:
    """Check if a score qualifies for the high score list.

    Args:
        score: The player's final score.
        scores: Current high score list (sorted descending by score).

    Returns:
        int | None: The rank index (0-9) where this score would be
        inserted, or None if it does not qualify.
    """
    for i, entry in enumerate(scores):
        if score > entry['score']:
            return i
    if len(scores) < MAX_HIGHSCORES:
        return len(scores)
    return None


def add_highscore(score: int, rank: int, rescued: int, destroyed: int,
                  scores: list[dict]) -> list[dict]:
    """Insert a new high score record in sorted order.

    Args:
        score: The player's final score.
        rank: The difficulty rank at time of scoring.
        rescued: Number of civilians rescued.
        destroyed: Number of enemy guns destroyed.
        scores: Current high score list (modified in place).

    Returns:
        list[dict]: Updated high score list, sorted descending by score,
        truncated to MAX_HIGHSCORES entries.
    """
    new_entry = {
        'score': score,
        'rank': rank,
        'rescued': rescued,
        'destroyed': destroyed,
        'date': datetime.date.today().isoformat(),
    }
    scores.append(new_entry)
    scores.sort(key=lambda e: e['score'], reverse=True)
    return scores[:MAX_HIGHSCORES]


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
class Game:
    """Main game class -- state machine, update loop, rendering.

    Owns all game entities (helicopter, civilians, enemy guns, projectiles,
    particles, explosions) and coordinates their update/draw. Runs the
    event loop and manages the state machine (TITLE -> PLAYING -> VICTORY/GAME_OVER).

    All procedural art surfaces are pre-computed once; per-frame rendering
    scrolls them according to the camera position.
    """

    def __init__(self):
        """Initialise Pygame, mixer, fonts, pre-compute assets, set initial state.

        Loads VGZ background music (silent if no playable file found),
        builds terrain, generates tree decoration positions, and starts
        the title screen with music playing. Entities are created by
        new_game() when the player presses SPACE.
        """
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=1)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Heli Rescue")
        self.clock = pygame.time.Clock()
        self.frame_count = 0
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 52)
        self.small_font = pygame.font.Font(None, 18)

        # Pre-compute assets
        random.seed(123)
        self.terrain = build_terrain()
        self.explosion_frames = make_explosion_surfaces()

        # Sounds
        self.sounds = init_sounds()

        # VGZ/VGM background music (may be None if no playable file found)
        self.music = init_music()
        if self.music:
            self.music.play(-1)  # start immediately on title screen
        self.music_playing = bool(self.music)

        # Decoration trees
        self.tree_positions = self._generate_trees()

        # Game state
        self.state = GameState.TITLE
        self.score = 0

        # High scores + NG+ state
        self.highscores = load_highscores()
        self.difficulty_rank = 1
        self.score_multiplier = 1.0

        # Entities (set up by new_game)
        self.heli = None
        self.civilians = []
        self.enemy_guns = []
        self.bullets = []
        self.enemy_bullets = []
        self.bombs = []
        self.explosions = []
        self.particles = []
        self.scroll_x = 0
        self.auto_scroll_speed = SCROLL_NORMAL

        # Base helipad position
        self.helipad_x = 200

        # Score tracking
        self.guns_destroyed = 0

        # Helipad hint timer (frames remaining to show "return here with civilians" message)
        self.helipad_hint_timer = 0

    def _generate_trees(self):
        """Generate tree decoration positions."""
        trees = []
        random.seed(456)
        # Scatter trees across the level, avoiding base area (0-400) and very steep terrain
        for x in range(0, LEVEL_WIDTH, random.randint(60, 150)):
            gnd = get_ground_y(self.terrain, x)
            if gnd < 300 or gnd > 500:
                continue
            if x < 400:
                continue  # no trees in base
            trees.append(x)
        return trees

    def new_game(self):
        """Reset all game entities and pick a random level theme.

        Called when the player presses SPACE on the title screen (rank 1)
        or continues in New Game+ (rank > 1). Re-renders terrain, mountains,
        hills, and clouds with the chosen theme palette. Applies NG+ scaling
        based on self.difficulty_rank.
        """
        random.seed()
        # Pick a random theme and regenerate rendered surfaces
        self.theme = random.choice(list(THEMES.keys()))
        pal = THEMES[self.theme]
        self.terrain_surf = make_terrain_surface(self.terrain, LEVEL_WIDTH, pal)
        self.mountain_surf = make_mountains_surface(LEVEL_WIDTH, pal)
        self.hills_surf = make_hills_surface(LEVEL_WIDTH, pal)
        self.clouds_surf = make_clouds_surface(LEVEL_WIDTH)  # clouds stay white
        random.seed()  # re-seed after make_clouds_surface() seeds to 42 internally

        # NG+ scaling
        rank = self.difficulty_rank
        num_guns = min(15, 5 + 2 * (rank - 1))
        num_civilians = min(16, 8 + 2 * (rank - 1))
        fire_interval = max(15, GUN_FIRE_INTERVAL - 5 * (rank - 1))
        bullet_speed = min(10, GUN_BULLET_SPEED + (rank - 1))
        gun_range = max(150, GUN_RANGE - 20 * (rank - 1))
        aggro_range = max(60, CIVILIAN_AGGRO_RANGE - 10 * (rank - 1))
        start_bombs = max(1, HELI_MAX_BOMBS - (rank - 1))
        self.score_multiplier = 1.0 + 0.5 * (rank - 1)

        self.heli = Helicopter(max_bombs=start_bombs)
        self.scroll_x = 0
        self.auto_scroll_speed = SCROLL_NORMAL
        self.score = 0
        self.guns_destroyed = 0
        self.helipad_hint_timer = 0

        # Clear entities
        self.bullets.clear()
        self.enemy_bullets.clear()
        self.bombs.clear()
        self.explosions.clear()
        self.particles.clear()

        # Generate civilians with NG+ scaling
        self.civilians.clear()
        civ_available = LEVEL_WIDTH - 900  # positions from 600 to 3700
        civ_step = max(30, civ_available // max(1, num_civilians + 2))
        civ_x_positions = random.sample(range(600, LEVEL_WIDTH - 300, civ_step), num_civilians)
        for i, cx in enumerate(civ_x_positions):
            gy = get_ground_y(self.terrain, cx)
            self.civilians.append(Civilian(i, cx, gy, aggro_range=aggro_range))

        # Generate enemy guns with NG+ scaling
        self.enemy_guns.clear()
        gun_step = max(50, civ_available // max(1, num_guns + 2))
        gun_x_positions = random.sample(range(600, LEVEL_WIDTH - 300, gun_step), num_guns)
        for i, gx in enumerate(gun_x_positions):
            gy = get_ground_y(self.terrain, gx)
            self.enemy_guns.append(EnemyGun(i, gx, gy, fire_interval, bullet_speed, gun_range))

    def handle_events(self) -> bool:
        """Process the Pygame event queue for one frame.

        Dispatches based on self.state:
            TITLE:      SPACE -> new_game(), PLAYING state, start engine.
                        TAB -> HIGH_SCORES state.
            PLAYING:    SPACE -> shoot bullet(s); M -> drop bomb.
            VICTORY:    SPACE -> NG+ continue (rank++), new_game, PLAYING.
                        ESC -> reset rank, return to TITLE.
            GAME_OVER:  SPACE -> return to TITLE.
            HIGH_SCORES: SPACE or ESC -> return to TITLE.

        ESC behaviour is state-sensitive: VICTORY and HIGH_SCORES transition
        to TITLE; all other states quit the game.

        Returns:
            bool: False if the game should quit, True otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    pygame.image.save(self.screen, "screenshot.png")
                    print("Screenshot saved: screenshot.png")

                if event.key == pygame.K_ESCAPE:
                    # State-sensitive exit behaviour
                    if self.state == GameState.VICTORY:
                        # ESC from victory: reset rank, return to title
                        self.difficulty_rank = 1
                        self.score_multiplier = 1.0
                        self.state = GameState.TITLE
                        if self.music:
                            self.music.stop()
                        self.music_playing = False
                        for s in self.sounds.values():
                            s.stop()
                        if self.music:
                            self.music.play(-1)
                        self.music_playing = bool(self.music)
                        continue
                    elif self.state == GameState.HIGH_SCORES:
                        self.state = GameState.TITLE
                        continue
                    else:
                        # TITLE, PLAYING, GAME_OVER -> quit
                        return False

                if self.state == GameState.TITLE:
                    if event.key == pygame.K_SPACE:
                        self.new_game()
                        self.state = GameState.PLAYING
                        self.sounds['engine'].play(-1)  # start engine when gameplay begins
                    elif event.key == pygame.K_TAB:
                        self.state = GameState.HIGH_SCORES
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_SPACE:
                        bullets = self.heli.shoot()
                        if bullets:
                            self.bullets.extend(bullets)
                            self.sounds['shoot'].play()
                    if event.key == pygame.K_m:
                        b = self.heli.drop_bomb()
                        if b:
                            self.bombs.append(b)
                            self.sounds['bomb_drop'].play()
                elif self.state == GameState.VICTORY:
                    if event.key == pygame.K_SPACE:
                        self.difficulty_rank += 1
                        self.new_game()
                        self.state = GameState.PLAYING
                        self.sounds['engine'].play(-1)
                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_SPACE:
                        self.difficulty_rank = 1
                        self.score_multiplier = 1.0
                        self.state = GameState.TITLE
                        if self.music:
                            self.music.stop()
                        self.music_playing = False
                        for s in self.sounds.values():
                            s.stop()
                        if self.music:
                            self.music.play(-1)
                        self.music_playing = bool(self.music)
                elif self.state == GameState.HIGH_SCORES:
                    if event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                        self.state = GameState.TITLE

        return True

    def update(self) -> None:
        """Advance the game simulation by one frame.

        Always updates explosions and particles (so death/victory animations
        play out), then if PLAYING:
            1. Helicopter movement + cooldowns
            2. Engine exhaust particles
            3. Camera auto-scroll
            4. Bullet/enemy-bullet/bomb updates
            5. Bomb -> explosion + AOE damage
            6. Enemy guns fire toward helicopter
            7. Bullet <-> enemy-gun collisions
            8. Enemy-bullet <-> helicopter collisions
            9. Civilian AI (waiting -> running -> boarding)
            10. Helicopter death check -> GAME_OVER
            11. All-onboard victory check -> return + helipad landing
             12. Helipad hint timer
        """
        # Always update explosions and particles (for game over / victory animations)
        for exp in self.explosions[:]:
            exp.update()
            if not exp.alive:
                self.explosions.remove(exp)
        for p in self.particles[:]:
            p.update()
            if not p.alive:
                self.particles.remove(p)

        if self.state != GameState.PLAYING:
            return

        keys = pygame.key.get_pressed()
        heli = self.heli
        terrain = self.terrain

        # --- Update helicopter ---
        heli.update(keys, terrain, self.auto_scroll_speed)

        # --- Engine particles (exhaust) ---
        if heli.alive and not heli.grounded and random.random() < 0.6:
            px = (heli.x - heli.w // 2 - 3) if heli.facing_right else (heli.x + heli.w // 2 + 3)
            py = heli.y + heli.h // 4
            self.particles.append(Particle(
                px, py,
                random.uniform(-0.5, 0.5),
                random.uniform(0.5, 1.5),
                GRAY, random.randint(10, 20), 2
            ))

        # --- Update camera ---
        self._update_camera()

        # --- Update bullets ---
        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        # --- Update enemy bullets ---
        for b in self.enemy_bullets:
            b.update()
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

        # --- Update bombs ---
        for bomb in self.bombs[:]:
            result = bomb.update(terrain)
            if result == 'explode':
                self._spawn_explosion(bomb.x, get_ground_y(terrain, bomb.x) - 4)
                self.sounds['explosion'].play()
                # Damage nearby enemies
                for gun in self.enemy_guns:
                    if gun.alive and abs(gun.x - bomb.x) < 50:
                        destroyed = gun.take_damage(3)  # bomb kills in 1 hit
                        if destroyed:
                            self.guns_destroyed += 1
                            self.score += int(200 * self.score_multiplier)
                            self._spawn_explosion(gun.x, gun.y + 10)
                self.bombs.remove(bomb)
            elif not bomb.alive:
                self.bombs.remove(bomb)

        # --- Enemy guns fire ---
        for gun in self.enemy_guns:
            bullet = gun.update(heli.x, heli.y, heli.grounded, self.scroll_x)
            if bullet:
                self.enemy_bullets.append(bullet)

        # --- Bullet vs enemy gun collisions ---
        for b in self.bullets[:]:
            for gun in self.enemy_guns:
                if gun.alive and b.alive and b.rect.colliderect(gun.rect):
                    b.alive = False
                    destroyed = gun.take_damage(1)
                    if destroyed:
                        self.guns_destroyed += 1
                        self.score += int(200 * self.score_multiplier)
                        self._spawn_explosion(gun.x, gun.y + 10)
                        self.sounds['explosion'].play()
                    else:
                        self._spawn_explosion(b.x, b.y)
                    break

        # --- Enemy bullet vs helicopter collisions ---
        for b in self.enemy_bullets[:]:
            if b.alive and heli.alive and b.rect.colliderect(heli.rect):
                b.alive = False
                if heli.take_damage():
                    self.sounds['damage'].play()
                    self._spawn_explosion(heli.x, heli.y)
                self.enemy_bullets.remove(b)

        # --- Update civilians ---
        for civ in self.civilians:
            result = civ.update(heli.rect, heli.grounded)
            if result == 'boarded':
                heli.passengers.append(civ.cid)
                self.sounds['pickup'].play()
                self.score += int(100 * self.score_multiplier)

        # --- Check helicopter death ---
        if not heli.alive:
            self.state = GameState.GAME_OVER
            # Auto-record high score on death
            rescued = sum(1 for c in self.civilians if c.state == 'onboard' or c.state == 'rescued')
            rank_idx = is_highscore(self.score, self.highscores)
            if rank_idx is not None:
                self.highscores = add_highscore(
                    self.score, self.difficulty_rank, rescued,
                    self.guns_destroyed, self.highscores)
                save_highscores(self.highscores)
            if self.music:
                self.music.stop()
            self.music_playing = False
            self.sounds['engine'].stop()
            self._spawn_explosion(heli.x, heli.y)
            return

        # --- Check victory condition ---
        all_onboard = all(c.state == 'onboard' or c.state == 'rescued' for c in self.civilians)
        if all_onboard and len(self.civilians) > 0:
            # Return to base mode
            self.auto_scroll_speed = SCROLL_RETURN

            # Check if landed on helipad
            if heli.grounded and abs(heli.x - self.helipad_x) < 60:
                # Victory!
                for civ in self.civilians:
                    civ.state = 'rescued'
                self.score += int(500 * self.score_multiplier)
                self.state = GameState.VICTORY
                # Auto-record high score on victory
                rescued = sum(1 for c in self.civilians if c.state == 'onboard' or c.state == 'rescued')
                rank_idx = is_highscore(self.score, self.highscores)
                if rank_idx is not None:
                    self.highscores = add_highscore(
                        self.score, self.difficulty_rank, rescued,
                        self.guns_destroyed, self.highscores)
                    save_highscores(self.highscores)
                if self.music:
                    self.music.stop()
                self.music_playing = False
                self.sounds['engine'].stop()
                self.sounds['victory'].play()
                # Celebration particles
                for _ in range(30):
                    angle = random.uniform(0, math.pi * 2)
                    speed = random.uniform(1, 4)
                    self.particles.append(Particle(
                        heli.x, heli.y,
                        math.cos(angle) * speed,
                        math.sin(angle) * speed - 2,
                        random.choice([YELLOW, ORANGE, RED, WHITE]),
                        random.randint(30, 60), 3
                    ))
                return

        # Hint when landing on helipad without all civilians rescued
        if heli.grounded and abs(heli.x - self.helipad_x) < 60:
            if not (all_onboard and len(self.civilians) > 0):
                self.helipad_hint_timer = 180  # show for ~3 seconds
        # Count down the hint timer
        if self.helipad_hint_timer > 0:
            self.helipad_hint_timer -= 1

    def _update_camera(self):
        """Update camera position with auto-scroll, backtrack, and return logic."""
        heli = self.heli

        # Determine effective scroll speed for this frame
        scroll_speed = self.auto_scroll_speed
        # Pause auto-scroll while landed (normal mode only)
        if scroll_speed > 0 and heli.grounded:
            scroll_speed = 0

        # Apply auto-scroll
        self.scroll_x += scroll_speed

        # --- Keep helicopter in a reasonable screen region ---
        heli_screen_x = heli.x - self.scroll_x

        # Backtrack: if heli is too far left (normal forward-scroll mode),
        # scroll left at a fixed rate (slower than auto-scroll).
        if heli_screen_x < BACKTRACK_ZONE and self.auto_scroll_speed > 0:
            self.scroll_x += SCROLL_BACKTRACK  # -1 px/frame

        # During return mode, if heli falls behind (right side of screen),
        # push the camera right to keep it visible.
        if heli_screen_x > SCREEN_WIDTH - 120 and self.auto_scroll_speed < 0:
            correction = (heli_screen_x - (SCREEN_WIDTH - 120)) * 0.5
            self.scroll_x += correction

        # --- Clamp to level bounds ---
        max_scroll = LEVEL_WIDTH - SCREEN_WIDTH
        self.scroll_x = max(0, min(self.scroll_x, max_scroll))

        # --- Safety clamp: never let heli go completely off-screen ---
        heli_screen_x = heli.x - self.scroll_x
        if heli_screen_x < 5:
            self.scroll_x = max(0, heli.x - 5)
        elif heli_screen_x > SCREEN_WIDTH - 5:
            self.scroll_x = min(max_scroll, heli.x - (SCREEN_WIDTH - 5))

    def _spawn_explosion(self, x: float, y: float) -> None:
        """Create an explosion animation at world coordinates (x, y)."""
        self.explosions.append(Explosion(x, y, self.explosion_frames))

    def draw(self) -> None:
        """Render the entire current frame based on state.

        Clears the screen (SKY_BLUE), then dispatches to:
            TITLE:      _draw_title()
            PLAYING:    _draw_game() + HUD + optional helipad hint
            VICTORY:    _draw_game() + HUD + _draw_overlay("VICTORY!")
            GAME_OVER:  _draw_game() + HUD + _draw_overlay("GAME OVER")
        """
        self.screen.fill(SKY_BLUE)

        if self.state == GameState.TITLE:
            self._draw_title()
        elif self.state == GameState.PLAYING:
            self._draw_game()
            draw_hud(self.screen, self.heli, self.civilians, self.score, self.font,
                     rank=self.difficulty_rank)
            # Helipad hint message
            if self.helipad_hint_timer > 0:
                hint = self.font.render("Return here with all civilians to rescue them!", True, YELLOW)
                self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 110))
        elif self.state == GameState.VICTORY:
            self._draw_game()
            draw_hud(self.screen, self.heli, self.civilians, self.score, self.font,
                     rank=self.difficulty_rank)
            self._draw_overlay("VICTORY!", "All civilians rescued!", YELLOW)
        elif self.state == GameState.GAME_OVER:
            self._draw_game()
            draw_hud(self.screen, self.heli, self.civilians, self.score, self.font,
                     rank=self.difficulty_rank)
            self._draw_overlay("GAME OVER", "Press SPACE to restart", RED)
        elif self.state == GameState.HIGH_SCORES:
            self._draw_highscores()

        pygame.display.flip()

    def _draw_title(self) -> None:
        """Render the animated title screen.

        Elements:
            - Dark gradient background
            - 80 twinkling stars (sinusoidal brightness with per-star phase)
            - "HELI RESCUE" title with cycling hue (RGB sine waves)
            - Glint sweep: a white highlight band sliding across the title
            - Subtitle, controls list, blinking "SPACE TO START"
        """
        # Background
        for y in range(0, SCREEN_HEIGHT, 4):
            shade = max(10, 40 - y // 20)
            pygame.draw.rect(self.screen, (shade, shade, shade + 10),
                             (0, y, SCREEN_WIDTH, 4))

        # Stars (twinkling via palette-style brightness animation)
        if not hasattr(self, '_stars'):
            random.seed(789)
            self._stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, 300),
                            random.uniform(0, math.pi * 2)) for _ in range(80)]
        for sx, sy, phase in self._stars:
            bright = int(100 + 155 * (0.5 + 0.5 * math.sin(self.frame_count * 0.03 + phase)))
            self.screen.set_at((sx, sy), (bright, bright, bright))

        # Title (palette rotation: colour cycles through hues)
        t = self.frame_count * 0.025
        title_col = (int(128 + 127 * math.sin(t)),
                     int(128 + 127 * math.sin(t + 2.094)),
                     int(128 + 127 * math.sin(t + 4.188)))
        title = self.big_font.render("HELI RESCUE", True, title_col)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        # Glint sweep: bright band sliding across the title
        tw = title.get_width()
        glint_phase = (self.frame_count * 2) % (tw + 60) - 30
        glint_x = SCREEN_WIDTH // 2 - tw // 2 + glint_phase
        glint = pygame.Surface((30, title.get_height()), pygame.SRCALPHA)
        for gx in range(30):
            alpha = int(200 * max(0, 1 - abs(gx - 15) / 20))
            pygame.draw.line(glint, (255, 255, 255, alpha), (gx, 0), (gx, title.get_height()))
        self.screen.blit(glint, (glint_x, 100))

        # Subtitle
        sub = self.small_font.render("~ 8-Bit Retro ~", True, WHITE)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 160))

        # Draw a small helicopter
        heli_surf = make_helicopter_surface()
        heli_surf = pygame.transform.scale2x(heli_surf)
        self.screen.blit(heli_surf, (SCREEN_WIDTH // 2 - heli_surf.get_width() // 2, 200))

        # Controls
        controls = [
            "CONTROLS",
            "",
            "W A S D  -- Move helicopter",
            "SPACE    -- Shoot bullets",
            "M        -- Drop bomb",
            "TAB      -- High Scores",
            "",
            "Press SPACE to start",
        ]
        y = 300
        for line in controls:
            col = YELLOW if line == "Press SPACE to start" else (200, 200, 200)
            if line == "CONTROLS":
                surf = self.font.render(line, True, WHITE)
            elif line == "":
                y += 10
                continue
            else:
                surf = self.small_font.render(line, True, col)
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, y))
            y += 28

        # Blinking start text
        if pygame.time.get_ticks() % 1000 < 500:
            start_text = self.font.render("SPACE TO START", True, YELLOW)
            self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 480))

    def _draw_game(self) -> None:
        """Render the playing field: parallax layers, terrain, entities.

        Draw order (back to front):
            1. Clouds (0.15x scroll, tiled)
            2. Mountains (0.25x scroll, tiled)
            3. Hills (0.5x scroll, tiled)
            4. Terrain surface (1x scroll, clipped to visible area)
            5. Base helipad + building (if visible)
            6. Decoration trees
            7. Enemy guns
            8. Civilians
            9. Helicopter
            10. Player bullets
            11. Enemy bullets
            12. Bombs
            13. Explosions
            14. Particles
        """
        scroll = self.scroll_x

        # --- Draw parallax layers ---
        # Far: clouds at 0.15x
        cloud_offset = scroll * 0.15
        # Tile clouds
        cw = self.clouds_surf.get_width()
        for cx in range(-cw, cw * 2, cw):
            sx = cx - int(cloud_offset % cw)
            self.screen.blit(self.clouds_surf, (sx, 0))

        # Far: mountains at 0.25x
        mtn_offset = scroll * 0.25
        mtn_w = self.mountain_surf.get_width()
        for mx in range(-mtn_w, mtn_w * 2, mtn_w):
            sx = mx - int(mtn_offset % mtn_w)
            self.screen.blit(self.mountain_surf, (sx, 0))

        # Mid: hills at 0.5x
        hill_offset = scroll * 0.5
        hill_w = self.hills_surf.get_width()
        for hx in range(-hill_w, hill_w * 2, hill_w):
            sx = hx - int(hill_offset % hill_w)
            self.screen.blit(self.hills_surf, (sx, 0))

        # --- Draw terrain (near layer, 1x) ---
        # Clip to visible area
        visible_rect = pygame.Rect(scroll, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.screen.blit(self.terrain_surf, (0, 0), visible_rect)

        # --- Draw base helipad ---
        self._draw_base(scroll)

        # --- Draw trees ---
        self._draw_trees(scroll)

        # --- Draw enemy guns ---
        for gun in self.enemy_guns:
            gun.draw(self.screen, scroll)

        # --- Draw civilians ---
        for civ in self.civilians:
            civ.draw(self.screen, scroll)

        # --- Draw helicopter ---
        self.heli.draw(self.screen, scroll)

        # --- Draw bullets ---
        for b in self.bullets:
            b.draw(self.screen, scroll)

        # --- Draw enemy bullets ---
        for b in self.enemy_bullets:
            b.draw(self.screen, scroll)

        # --- Draw bombs ---
        for bomb in self.bombs:
            bomb.draw(self.screen, scroll)

        # --- Draw explosions ---
        for exp in self.explosions:
            exp.draw(self.screen, scroll)

        # --- Draw particles ---
        for p in self.particles:
            p.draw(self.screen, scroll)

    def _draw_base(self, scroll):
        """Draw the base area with helipad and building."""
        # Only draw if visible
        if scroll > 500:
            return
        pal = THEMES.get(self.theme, THEMES['summer'])

        # Helipad
        pad_x = self.helipad_x - scroll
        pad_y = get_ground_y(self.terrain, self.helipad_x) - 4

        # Concrete pad
        pygame.draw.ellipse(self.screen, DARK_GRAY,
                           (pad_x - 30, pad_y - 8, 60, 16))
        pygame.draw.ellipse(self.screen, GRAY,
                           (pad_x - 26, pad_y - 6, 52, 12))
        # H marking
        h_surf = self.small_font.render("H", True, WHITE)
        self.screen.blit(h_surf, (pad_x - h_surf.get_width() // 2, pad_y - 6))

        # Small building (theme-colored)
        build_x = 50 - scroll
        build_y = get_ground_y(self.terrain, 50) - 50
        pygame.draw.rect(self.screen, pal['building'],
                        (build_x, build_y, 40, 50))
        # Roof
        pygame.draw.rect(self.screen, pal['roof'],
                        (build_x - 4, build_y - 6, 48, 8))
        # Door
        pygame.draw.rect(self.screen, DARK_GRAY,
                        (build_x + 14, build_y + 28, 12, 22))
        # Window
        pygame.draw.rect(self.screen, YELLOW,
                        (build_x + 6, build_y + 10, 10, 10))
        pygame.draw.rect(self.screen, YELLOW,
                        (build_x + 24, build_y + 10, 10, 10))

    def _draw_trees(self, scroll):
        """Draw decorative trees."""
        pal = THEMES.get(self.theme, THEMES['summer'])
        for tx in self.tree_positions:
            sx = int(tx - scroll)
            if sx < -30 or sx > SCREEN_WIDTH + 30:
                continue
            gy = get_ground_y(self.terrain, tx)
            # Trunk
            pygame.draw.rect(self.screen, pal['trunk'],
                            (sx - 3, gy - 30, 6, 30))
            # Foliage (triangular)
            pts = [(sx, gy - 50), (sx - 15, gy - 28), (sx + 15, gy - 28)]
            col = pal['foliage_dark'] if (tx // 100) % 2 == 0 else pal['foliage']
            pygame.draw.polygon(self.screen, col, pts)
            # Second layer (swap shading)
            pts2 = [(sx, gy - 42), (sx - 12, gy - 24), (sx + 12, gy - 24)]
            pygame.draw.polygon(self.screen, pal['foliage'] if col == pal['foliage_dark'] else pal['foliage_dark'], pts2)

    def _draw_overlay(self, title_text, subtitle_text, title_color):
        """Draw a translucent overlay with game result."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(160)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        # Title
        title = self.big_font.render(title_text, True, title_color)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))

        # Subtitle
        sub = self.font.render(subtitle_text, True, WHITE)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 260))

        # Stats
        stats = [
            f"Score: {self.score}",
            f"Civilians: {sum(1 for c in self.civilians if c.state == 'rescued')}/{len(self.civilians)}",
            f"Guns destroyed: {self.guns_destroyed}",
        ]
        y = 310
        for s in stats:
            surf = self.small_font.render(s, True, (200, 200, 200))
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, y))
            y += 24

        # Restart prompt (different for victory vs game over)
        if self.state == GameState.VICTORY:
            if pygame.time.get_ticks() % 1000 < 500:
                cont = self.font.render(f"SPACE - Continue (Rank {self.difficulty_rank + 1})", True, YELLOW)
                self.screen.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, 390))
                esc_text = self.small_font.render("ESC - Return to title", True, (180, 180, 180))
                self.screen.blit(esc_text, (SCREEN_WIDTH // 2 - esc_text.get_width() // 2, 420))
        else:
            if pygame.time.get_ticks() % 1000 < 500:
                restart = self.font.render("Press SPACE to continue", True, YELLOW)
                self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 400))

    def _draw_highscores(self) -> None:
        """Render the high score table screen.

        Shows the title "HIGH SCORES" and a table with columns:
        Rank, Score, Civilians, Guns, Rank Lvl, Date.
        If no scores recorded, shows a 'No scores yet' message.
        SPACE returns to title.
        """
        # Background
        for y in range(0, SCREEN_HEIGHT, 4):
            shade = max(10, 40 - y // 20)
            pygame.draw.rect(self.screen, (shade, shade, shade + 10),
                             (0, y, SCREEN_WIDTH, 4))

        # Title
        title = self.big_font.render("HIGH SCORES", True, YELLOW)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        if not self.highscores:
            msg = self.font.render("No scores yet!", True, WHITE)
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 200))
        else:
            # Column headers
            headers = ["#", "Score", "Civ", "Guns", "Rank", "Date"]
            col_x = [SCREEN_WIDTH // 2 - 220, SCREEN_WIDTH // 2 - 160,
                     SCREEN_WIDTH // 2 - 60, SCREEN_WIDTH // 2 - 10,
                     SCREEN_WIDTH // 2 + 50, SCREEN_WIDTH // 2 + 120]
            for h, cx in zip(headers, col_x):
                hdr = self.small_font.render(h, True, WHITE)
                self.screen.blit(hdr, (cx, 80))

            # Score rows
            for i, entry in enumerate(self.highscores[:MAX_HIGHSCORES]):
                y = 115 + i * 28
                col = ORANGE if i == 0 else (200, 200, 200)
                vals = [str(i + 1), str(entry['score']), str(entry['rescued']),
                        str(entry['destroyed']), str(entry['rank']), entry['date']]
                for val, cx in zip(vals, col_x):
                    vs = self.small_font.render(val, True, col)
                    self.screen.blit(vs, (cx, y))

        # Return prompt
        if pygame.time.get_ticks() % 1000 < 500:
            ret = self.font.render("Press SPACE to return", True, YELLOW)
            self.screen.blit(ret, (SCREEN_WIDTH // 2 - ret.get_width() // 2, 540))

    def run(self) -> None:
        """Main game loop: process events, update state, render frame.

        Runs at FPS frames per second. Increments frame_count each tick.
        Exits when handle_events() returns False (ESC or window close).
        """
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.frame_count += 1
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()
