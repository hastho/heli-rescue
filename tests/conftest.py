"""Shared test fixtures for the Heli Rescue test suite.

Sets SDL_VIDEODRIVER=dummy before pygame.init() for headless operation.
Provides sample_terrain and heli fixtures for entity tests.
"""

import os
# Must set before importing pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import pygame
import pytest

from main import Helicopter, TERRAIN_SEGMENT, LEVEL_WIDTH


@pytest.fixture(scope='session', autouse=True)
def pygame_init():
    """Initialise pygame once for the entire test session.

    Uses dummy video driver (set above) so no display is needed.
    """
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1)
    yield
    pygame.quit()


@pytest.fixture
def sample_terrain():
    """Return a flat terrain list with a bump at segment 50.

    All 200 segments are y=500 except segment 50 which is y=400.
    Useful for ground-collision and get_ground_y tests.
    """
    num = LEVEL_WIDTH // TERRAIN_SEGMENT  # 200
    terrain = [500] * num
    terrain[50] = 400
    return terrain


@pytest.fixture
def heli():
    """Return a default Helicopter instance (x=150, y=300, 3 HP, 5 bombs)."""
    return Helicopter()
