"""Tests for entity classes in main.py.

Targets: Helicopter, Bullet, EnemyBullet, Bomb, Civilian, EnemyGun.
"""

import math

import pygame
import pytest

import main
from main import (
    LEVEL_WIDTH,
    SCREEN_HEIGHT,
    HELI_SIZE,
    HELI_MAX_HP,
    HELI_MAX_BOMBS,
    SHOOT_COOLDOWN,
    BOMB_COOLDOWN,
    BULLET_SPEED,
    GUN_BULLET_SPEED,
    BOMB_FALL_SPEED,
    GUN_RANGE,
    GUN_FIRE_INTERVAL,
    GUN_MAX_HP,
    CIVILIAN_RUN_SPEED,
    CIVILIAN_AGGRO_RANGE,
    TERRAIN_SEGMENT,
    get_ground_y,
    Helicopter,
    Bullet,
    EnemyBullet,
    Bomb,
    Civilian,
    EnemyGun,
)


# ---------------------------------------------------------------------------
# Helper: build a list of pressed keys (length 512, all False)
# ---------------------------------------------------------------------------
def _pressed(**overrides) -> list[bool]:
    """Return a list of 512 bools (False) with given keys set to True.

    Usage:
        _pressed(K_w=True, K_d=True)
    """
    keys = [False] * 512
    for name, val in overrides.items():
        if val:
            key_const = getattr(pygame, name)
            keys[key_const] = True
    return keys


# ===================================================================
# Helicopter
# ===================================================================
class TestHelicopter:
    """Tests for the Helicopter entity."""

    def test_constructor_defaults(self):
        """Default helicopter starts at (150, 300) with full HP, bombs, alive."""
        h = Helicopter()
        assert h.x == 150
        assert h.y == 300
        assert h.hp == HELI_MAX_HP
        assert h.bombs == HELI_MAX_BOMBS
        assert h.alive is True
        assert h.grounded is False
        assert h.shoot_cooldown == 0
        assert h.bomb_cooldown == 0
        assert h.passengers == []
        assert h.invincible_timer == 0
        assert h.w == HELI_SIZE[0]
        assert h.h == HELI_SIZE[1]

    def test_rect_property(self, heli):
        """rect property returns correct AABB centred on (x, y)."""
        r = heli.rect
        assert r.x == heli.x - heli.w // 2
        assert r.y == heli.y - heli.h // 2
        assert r.w == heli.w
        assert r.h == heli.h

    def test_bottom_property(self, heli):
        """bottom returns y + h//2."""
        assert heli.bottom == heli.y + heli.h // 2

    def test_update_moves_right_with_d_key(self, sample_terrain, heli):
        """Pressing D moves helicopter right by HELI_SPEED."""
        old_x = heli.x
        heli.update(_pressed(K_d=True), sample_terrain)
        assert heli.x == old_x + main.HELI_SPEED

    def test_update_moves_left_with_a_key(self, sample_terrain, heli):
        """Pressing A moves helicopter left by HELI_SPEED."""
        old_x = heli.x
        heli.update(_pressed(K_a=True), sample_terrain)
        assert heli.x == old_x - main.HELI_SPEED

    def test_update_moves_down_with_s_key(self, sample_terrain, heli):
        """Pressing S moves helicopter down by HELI_SPEED."""
        old_y = heli.y
        heli.update(_pressed(K_s=True), sample_terrain)
        assert heli.y == old_y + main.HELI_SPEED

    def test_update_moves_up_with_w_key(self, sample_terrain, heli):
        """Pressing W moves helicopter up by HELI_SPEED."""
        old_y = heli.y
        heli.update(_pressed(K_w=True), sample_terrain)
        assert heli.y == old_y - main.HELI_SPEED

    def test_update_no_keys_no_movement(self, sample_terrain, heli):
        """Without any key pressed, helicopter stays still."""
        old_x, old_y = heli.x, heli.y
        heli.update(_pressed(), sample_terrain)
        assert heli.x == old_x
        assert heli.y == old_y

    def test_ground_collision_snaps_y(self, sample_terrain):
        """When bottom >= ground_y, helicopter snaps to ground and is grounded."""
        h = Helicopter()
        # Place heli above ground and move it down far enough
        # terrain at x=150 (segment 7) = 500
        h.y = 400  # bottom = 400 + 13 = 413, ground = 500, not touching
        h.update(_pressed(K_s=True), sample_terrain)
        assert h.grounded is False  # still above ground

        # Place heli very low to trigger ground collision
        h.y = 500  # bottom = 500 + 13 = 513 >= 500 (ground_y)
        h.update(_pressed(), sample_terrain)
        assert h.grounded is True
        assert h.y == get_ground_y(sample_terrain, h.x) - h.h // 2

    def test_ceiling_clamp(self, sample_terrain, heli):
        """Helicopter cannot go above y=80 (top edge)."""
        heli.y = 80 + heli.h // 2  # already at ceiling
        heli.update(_pressed(K_w=True), sample_terrain)
        # y should not go above 80 + h//2
        assert heli.y == 80 + heli.h // 2

    def test_left_bound_clamp(self, sample_terrain):
        """Helicopter cannot go past left edge (x - w//2 < 0)."""
        h = Helicopter()
        h.x = h.w // 2  # at left edge
        h.update(_pressed(K_a=True), sample_terrain)
        assert h.x == h.w // 2

    def test_right_bound_clamp(self, sample_terrain):
        """Helicopter cannot go past right edge (x + w//2 > LEVEL_WIDTH)."""
        h = Helicopter()
        h.x = LEVEL_WIDTH - h.w // 2  # at right edge
        h.update(_pressed(K_d=True), sample_terrain)
        assert h.x == LEVEL_WIDTH - h.w // 2

    def test_take_damage_decrements_hp(self, heli):
        """take_damage reduces HP by 1."""
        old_hp = heli.hp
        heli.take_damage()
        assert heli.hp == old_hp - 1

    def test_take_damage_invincibility_prevents_double_hit(self, heli):
        """Second take_damage during invincibility window is blocked."""
        heli.take_damage()  # HP: 3 -> 2, invincible_timer = 30
        result = heli.take_damage()  # blocked
        assert result is False
        assert heli.hp == 2  # unchanged

    def test_take_damage_invincibility_expires(self, heli):
        """After invincibility expires, damage can be applied again."""
        heli.take_damage()  # invincible_timer = 30
        # Simulate 30 frames passing
        heli.invincible_timer = 0
        result = heli.take_damage()
        assert result is True
        assert heli.hp == 1

    def test_take_damage_hp_zero_sets_alive_false(self, heli):
        """When HP reaches 0, alive is set to False."""
        heli.hp = 1
        heli.invincible_timer = 0
        heli.take_damage()
        assert heli.hp == 0
        assert heli.alive is False

    def test_shoot_returns_one_bullet_default(self, heli):
        """shoot() returns a list with one Bullet when no passengers."""
        bullets = heli.shoot()
        assert isinstance(bullets, list)
        assert len(bullets) == 1
        assert isinstance(bullets[0], Bullet)

    def test_shoot_respects_cooldown(self, heli):
        """Second immediate shoot() returns empty list due to cooldown."""
        heli.shoot()  # sets cooldown = SHOOT_COOLDOWN
        bullets = heli.shoot()  # should be blocked
        assert bullets == []

    def test_shoot_scales_with_passengers(self, heli):
        """shoot() returns more bullets as passengers increase."""
        # 0 passengers -> 1 bullet
        heli.shoot_cooldown = 0
        assert len(heli.shoot()) == 1

        # 2 passengers -> 2 bullets
        heli.shoot_cooldown = 0
        heli.passengers = [1, 2]
        assert len(heli.shoot()) == 2

        # 4 passengers -> 3 bullets
        heli.shoot_cooldown = 0
        heli.passengers = [1, 2, 3, 4]
        assert len(heli.shoot()) == 3

        # 8 passengers -> 5 bullets (max)
        heli.shoot_cooldown = 0
        heli.passengers = [1, 2, 3, 4, 5, 6, 7, 8]
        assert len(heli.shoot()) == 5

    def test_drop_bomb_returns_bomb_when_available(self, heli):
        """drop_bomb() returns a Bomb and decrements bomb count."""
        old_bombs = heli.bombs
        bomb = heli.drop_bomb()
        assert isinstance(bomb, Bomb)
        assert heli.bombs == old_bombs - 1
        assert heli.bomb_cooldown == BOMB_COOLDOWN

    def test_drop_bomb_returns_none_when_empty(self, heli):
        """drop_bomb() returns None when out of bombs."""
        heli.bombs = 0
        heli.bomb_cooldown = 0
        assert heli.drop_bomb() is None

    def test_drop_bomb_returns_none_on_cooldown(self, heli):
        """drop_bomb() returns None when on cooldown."""
        heli.bomb_cooldown = 1
        result = heli.drop_bomb()
        assert result is None

    def test_update_decrements_cooldowns(self, sample_terrain, heli):
        """update() decrements shoot_cooldown, bomb_cooldown, invincible_timer."""
        heli.shoot_cooldown = 5
        heli.bomb_cooldown = 5
        heli.invincible_timer = 5
        heli.update(_pressed(), sample_terrain)
        assert heli.shoot_cooldown == 4
        assert heli.bomb_cooldown == 4
        assert heli.invincible_timer == 4

    def test_dead_heli_does_not_move(self, sample_terrain):
        """A dead helicopter ignores update()."""
        h = Helicopter()
        h.alive = False
        old_x, old_y = h.x, h.y
        h.update(_pressed(K_d=True, K_s=True), sample_terrain)
        assert h.x == old_x
        assert h.y == old_y


# ===================================================================
# Bullet
# ===================================================================
class TestBullet:
    """Tests for the Bullet projectile."""

    def test_constructor_defaults(self):
        """Bullet defaults to vx=vy=BULLET_SPEED (10)."""
        b = Bullet(100, 200)
        assert b.x == 100
        assert b.y == 200
        assert b.vx == BULLET_SPEED
        assert b.vy == BULLET_SPEED
        assert b.alive is True

    def test_constructor_custom_velocity(self):
        """Bullet accepts custom vx, vy."""
        b = Bullet(100, 200, 3, 7)
        assert b.vx == 3
        assert b.vy == 7

    def test_update_moves_by_velocity(self):
        """update() moves bullet by (vx, vy)."""
        b = Bullet(100, 200, 5, 3)
        b.update()
        assert b.x == 105
        assert b.y == 203

    def test_dies_when_below_screen(self):
        """Bullet dies when y > SCREEN_HEIGHT."""
        b = Bullet(100, SCREEN_HEIGHT + 1, 0, 0)
        b.update()
        assert b.alive is False

    def test_dies_when_past_level_width(self):
        """Bullet dies when x > LEVEL_WIDTH."""
        b = Bullet(LEVEL_WIDTH + 1, 100, 0, 0)
        b.update()
        assert b.alive is False

    def test_stays_alive_onscreen(self):
        """Bullet inside screen boundaries stays alive."""
        b = Bullet(100, 100, 1, 1)
        b.update()
        assert b.alive is True

    def test_rect_property(self):
        """Bullet rect is 4x8 at position."""
        b = Bullet(100, 200)
        r = b.rect
        assert r.x == 98  # x - 2
        assert r.y == 200
        assert r.w == 4
        assert r.h == 8


# ===================================================================
# EnemyBullet
# ===================================================================
class TestEnemyBullet:
    """Tests for the EnemyBullet projectile."""

    def test_constructor_aims_at_target(self):
        """EnemyBullet computes velocity toward target."""
        # Gun at (0, 0), target at (300, 300) -> 45 deg
        b = EnemyBullet(0, 0, 300, 300)
        dist = math.hypot(300, 300)
        expected_vx = 300 / dist * GUN_BULLET_SPEED
        expected_vy = 300 / dist * GUN_BULLET_SPEED
        assert abs(b.vx - expected_vx) < 0.001
        assert abs(b.vy - expected_vy) < 0.001

    def test_zero_distance_target_falls_straight_down(self):
        """When target is at same position, bullet falls straight down."""
        b = EnemyBullet(100, 100, 100, 100)
        assert b.vx == 0
        assert b.vy == GUN_BULLET_SPEED

    def test_update_moves_toward_target(self):
        """update() moves bullet by (vx, vy)."""
        b = EnemyBullet(0, 0, 100, 0)  # moving right
        b.update()
        assert b.x == GUN_BULLET_SPEED
        assert b.y == 0

    def test_dies_when_offscreen(self):
        """EnemyBullet dies when outside visible area + 20px margin."""
        # Below screen
        b = EnemyBullet(100, SCREEN_HEIGHT + 21, 100, SCREEN_HEIGHT + 21)
        b.update()
        assert b.alive is False

        # Above screen: spawn far above so after velocity it stays off-screen
        b = EnemyBullet(100, -200, 100, -200)
        b.update()
        assert b.alive is False

        # Left of screen
        b = EnemyBullet(-200, 100, -200, 100)
        b.update()
        assert b.alive is False

        # Right of screen
        b = EnemyBullet(LEVEL_WIDTH + 200, 100, LEVEL_WIDTH + 200, 100)
        b.update()
        assert b.alive is False

    def test_rect_property(self):
        """EnemyBullet rect is 6x6 centred on position."""
        b = EnemyBullet(100, 200, 100, 200)
        r = b.rect
        assert r.x == 97   # 100 - 3
        assert r.y == 197  # 200 - 3
        assert r.w == 6
        assert r.h == 6


# ===================================================================
# Bomb
# ===================================================================
class TestBomb:
    """Tests for the Bomb entity."""

    def test_constructor_defaults(self):
        """Bomb defaults: vy=BOMB_FALL_SPEED, alive=True."""
        b = Bomb(100, 200)
        assert b.x == 100
        assert b.y == 200
        assert b.vy == BOMB_FALL_SPEED
        assert b.alive is True

    def test_update_falls_down(self, sample_terrain):
        """update() moves bomb down by vy each frame."""
        b = Bomb(100, 200)
        b.update(sample_terrain)
        assert b.y == 200 + BOMB_FALL_SPEED

    def test_update_returns_explode_on_ground_contact(self, sample_terrain):
        """update() returns 'explode' when bomb reaches ground."""
        ground_y = get_ground_y(sample_terrain, 100)  # 500
        b = Bomb(100, ground_y - 5)  # close to ground
        result = b.update(sample_terrain)
        # After move: y = ground_y - 5 + 6 = ground_y + 1 >= ground_y
        assert result == 'explode'
        assert b.alive is False

    def test_update_dies_past_bottom(self):
        """update() kills bomb if past bottom of screen (ground below screen)."""
        # Terrain where ground is at y=700 (below visible area)
        deep_terrain = [700] * 200
        b = Bomb(100, SCREEN_HEIGHT + 21)
        result = b.update(deep_terrain)
        # Bomb falls: y = 621 + 6 = 627; 627 + 6 = 633 < 700, so no ground hit
        # But 627 > 620 = SCREEN_HEIGHT + 20, so off-screen death
        assert result is None
        assert b.alive is False

    def test_update_returns_none_while_falling(self, sample_terrain):
        """update() returns None while bomb is still in the air."""
        b = Bomb(100, 100)
        result = b.update(sample_terrain)
        assert result is None
        assert b.alive is True

    def test_rect_property(self):
        """Bomb rect is 8x12 at position."""
        b = Bomb(100, 200)
        r = b.rect
        assert r.x == 96   # x - 4
        assert r.y == 200
        assert r.w == 8
        assert r.h == 12


# ===================================================================
# Civilian
# ===================================================================
class TestCivilian:
    """Tests for the Civilian entity."""

    def test_constructor_defaults(self):
        """Civilian starts in 'waiting' state, not rescued."""
        c = Civilian(cid=0, x=200, ground_y=500)
        assert c.cid == 0
        assert c.x == 200
        assert c.state == 'waiting'
        assert c.rescued is False
        assert c.y == 500 - 14  # standing on ground

    def test_rect_property(self):
        """Civilian rect is 10x14 at position."""
        c = Civilian(0, 200, 500)
        r = c.rect
        assert r.x == 195  # x - 5
        assert r.y == 486  # ground_y - 14
        assert r.w == 10
        assert r.h == 14

    def test_waiting_to_running_when_heli_grounded_and_close(self):
        """Civilian transitions to 'running' when heli is grounded and close."""
        c = Civilian(0, 200, 500)
        heli_rect = pygame.Rect(250, 487, 36, 26)  # centre x=268, dist=68 < 120
        result = c.update(heli_rect=heli_rect, heli_grounded=True)
        assert c.state == 'running'
        assert result is None

    def test_stays_waiting_when_heli_not_grounded(self):
        """Civilian stays 'waiting' when heli is airborne."""
        c = Civilian(0, 200, 500)
        heli_rect = pygame.Rect(250, 300, 36, 26)
        c.update(heli_rect=heli_rect, heli_grounded=False)
        assert c.state == 'waiting'

    def test_stays_waiting_when_heli_too_far(self):
        """Civilian stays 'waiting' when heli is out of aggro range."""
        c = Civilian(0, 200, 500)
        heli_rect = pygame.Rect(400, 487, 36, 26)  # centre x=418, dist=218 > 120
        c.update(heli_rect=heli_rect, heli_grounded=True)
        assert c.state == 'waiting'

    def test_running_to_waiting_when_heli_takes_off(self):
        """Civilian returns to 'waiting' if heli takes off while running."""
        c = Civilian(0, 200, 500)
        heli_rect = pygame.Rect(250, 487, 36, 26)  # within range
        c.update(heli_rect=heli_rect, heli_grounded=True)  # -> running
        assert c.state == 'running'

        # Heli takes off
        c.update(heli_rect=heli_rect, heli_grounded=False)
        assert c.state == 'waiting'

    def test_running_moves_toward_heli(self):
        """Civilian moves toward helicopter when running."""
        c = Civilian(0, 200, 500)
        heli_rect = pygame.Rect(250, 487, 36, 26)  # centre x=268, to the right
        c.update(heli_rect=heli_rect, heli_grounded=True)  # -> running
        old_x = c.x
        c.update(heli_rect=heli_rect, heli_grounded=True)  # move right
        assert c.x > old_x  # moved toward heli

    def test_boarding_transition_when_close_to_target(self):
        """Civilian transitions 'running' -> 'boarding' -> 'onboard'."""
        c = Civilian(0, 200, 500)
        heli_rect = pygame.Rect(202, 487, 36, 26)  # centre x=220, target_x=220
        c.update(heli_rect=heli_rect, heli_grounded=True)  # -> running

        # Move civilian close enough to trigger boarding
        c.x = 218  # dist = |220 - 218| = 2 < 3
        c.update(heli_rect=heli_rect, heli_grounded=True)
        # running -> boarding (returns None)
        assert c.state == 'boarding'

        # Next update: boarding -> onboard -> 'boarded'
        result = c.update(heli_rect=heli_rect, heli_grounded=True)
        assert c.state == 'onboard'
        assert result == 'boarded'

    def test_onboard_returns_none(self):
        """Civilian in 'onboard' state returns None from update()."""
        c = Civilian(0, 200, 500)
        c.state = 'onboard'
        result = c.update(heli_rect=pygame.Rect(0, 0, 36, 26), heli_grounded=True)
        assert result is None


# ===================================================================
# EnemyGun
# ===================================================================
class TestEnemyGun:
    """Tests for the EnemyGun entity."""

    def test_constructor_defaults(self):
        """EnemyGun starts alive with full HP and zero cooldown."""
        g = EnemyGun(gid=0, x=300, ground_y=500)
        assert g.gid == 0
        assert g.x == 300
        assert g.y == 500 - 20  # sits on ground
        assert g.hp == GUN_MAX_HP
        assert g.alive is True
        assert g.fire_cooldown == 0

    def test_fires_when_heli_in_range_and_airborne(self):
        """Gun fires an EnemyBullet when heli is in range and not grounded."""
        g = EnemyGun(0, 300, 500)
        # Heli at (100, 200), dist=200 <= 300, not grounded
        result = g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=0)
        assert isinstance(result, EnemyBullet)
        assert g.fire_cooldown == GUN_FIRE_INTERVAL

    def test_does_not_fire_when_heli_grounded(self):
        """Gun does not fire when helicopter is grounded."""
        g = EnemyGun(0, 300, 500)
        result = g.update(heli_x=100, heli_y=500, heli_grounded=True, scroll_x=0)
        assert result is None

    def test_does_not_fire_when_heli_out_of_range(self):
        """Gun does not fire when helicopter is out of range."""
        g = EnemyGun(0, 300, 500)
        result = g.update(heli_x=1000, heli_y=200, heli_grounded=False, scroll_x=0)
        assert result is None

    def test_does_not_fire_when_scrolled_past(self):
        """Gun does not fire when scrolled past (x < scroll_x - 50)."""
        g = EnemyGun(0, 300, 500)
        result = g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=400)
        # 300 < 400 - 50 = 350 -> scrolled past
        assert result is None

    def test_does_not_fire_on_cooldown(self):
        """Gun does not fire while on cooldown."""
        g = EnemyGun(0, 300, 500)
        # First shot fires
        g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=0)
        # Second shot blocked by cooldown
        result = g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=0)
        assert result is None

    def test_fires_after_cooldown_expires(self):
        """Gun fires again after cooldown expires."""
        g = EnemyGun(0, 300, 500)
        g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=0)  # fires, cooldown=45

        # Advance cooldown to 0
        g.fire_cooldown = 0
        result = g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=0)
        assert isinstance(result, EnemyBullet)

    def test_take_damage_decrements_hp(self):
        """take_damage(1) reduces HP by 1."""
        g = EnemyGun(0, 300, 500)
        old_hp = g.hp
        g.take_damage(1)
        assert g.hp == old_hp - 1

    def test_take_damage_destroyed_returns_true(self):
        """take_damage returns True when gun is destroyed."""
        g = EnemyGun(0, 300, 500)
        g.hp = 1
        destroyed = g.take_damage(1)
        assert destroyed is True
        assert g.alive is False

    def test_take_damage_not_destroyed_returns_false(self):
        """take_damage returns False when gun is damaged but still alive."""
        g = EnemyGun(0, 300, 500)
        destroyed = g.take_damage(1)
        assert destroyed is False
        assert g.alive is True

    def test_rect_property(self):
        """EnemyGun rect is 24x20 at position."""
        g = EnemyGun(0, 300, 500)
        r = g.rect
        assert r.x == 288  # 300 - 12
        assert r.y == 480  # 500 - 20
        assert r.w == 24
        assert r.h == 20

    def test_dead_gun_returns_none(self):
        """Dead gun returns None from update()."""
        g = EnemyGun(0, 300, 500)
        g.alive = False
        result = g.update(heli_x=100, heli_y=200, heli_grounded=False, scroll_x=0)
        assert result is None
