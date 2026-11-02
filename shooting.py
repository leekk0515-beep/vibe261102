"""
종스크롤 슈팅 게임 (pygame)

공중 적은 레이저(Z), 지상 목표물은 폭탄(X)으로 공격하는 오리지널 종스크롤 슈터.
외부 이미지/사운드 파일 없이 도형으로 그리고, 효과음은 파형을 직접 합성합니다.
P 아이템을 먹을 때마다 레이저가 2 → 4 → 6 → 8발로 강화됩니다.

조작:
    방향키 / WASD : 이동
    Z / J         : 공중 레이저 (누르고 있으면 연사)
    X / K         : 지상 폭탄 (조준점 위치에 낙하)
    P             : 일시정지
    Enter         : 시작 / 다시 시작
    Esc           : 종료
"""

import math
import random
import sys
from array import array

import pygame

WIDTH, HEIGHT = 480, 720
FPS = 60
SCROLL_SPEED = 1.5
scroll_speed = SCROLL_SPEED  # 요새전 중에는 0이 되어 화면이 멈춘다
BOMB_RANGE = 170  # 조준점이 플레이어보다 앞서는 거리

# 색상
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 230, 80)
RED = (240, 70, 70)
ORANGE = (255, 150, 40)
CYAN = (80, 230, 255)
GRASS = (48, 98, 52)
GRASS_DARK = (38, 80, 42)
FOREST = (28, 64, 34)
RIVER = (40, 90, 160)
ROAD = (120, 110, 90)
METAL = (150, 155, 170)
METAL_DARK = (90, 95, 110)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# 음향 효과 (사운드 파일 없이 파형을 직접 합성)
# ---------------------------------------------------------------------------
class SoundBank:
    def __init__(self):
        self.sounds = {}
        init = pygame.mixer.get_init()
        if not init:
            return  # 오디오 장치가 없으면 소리 없이 진행
        self.rate, _, self.channels = init
        self.sounds = {
            "shot": self._make(self._tone(0.07, 1400, 700, "square", 0.12)),
            "bomb": self._make(self._tone(0.25, 900, 250, "sine", 0.3)),
            "explode": self._make(self._noise(0.3, 0.35, hold=3)),
            "ground_explode": self._make(self._noise(0.45, 0.45, hold=6)),
            "big_explode": self._make(self._noise(1.2, 0.6, hold=10)),
            "player_hit": self._make(self._tone(0.6, 600, 60, "saw", 0.35)
                                     + self._noise(0.4, 0.4, hold=8)),
            "powerup": self._make(sum((self._tone(0.07, f, f, "square", 0.2, decay=False)
                                       for f in (523, 659, 784, 1047)), array("h"))),
            "alarm": self._make(sum((self._tone(0.18, f, f, "square", 0.18, decay=False)
                                     for f in (880, 660, 880, 660)), array("h"))),
            "start": self._make(sum((self._tone(0.1, f, f, "sine", 0.3)
                                     for f in (392, 523, 659, 784)), array("h"))),
        }
        self.sounds["shot"].set_volume(0.5)

    def _tone(self, duration, f_start, f_end, wave, volume, decay=True):
        n = int(self.rate * duration)
        buf = array("h")
        phase = 0.0
        for i in range(n):
            t = i / n
            phase += (f_start + (f_end - f_start) * t) / self.rate
            p = phase % 1.0
            if wave == "square":
                v = 1.0 if p < 0.5 else -1.0
            elif wave == "saw":
                v = 2.0 * p - 1.0
            else:
                v = math.sin(phase * math.tau)
            env = (1 - t) ** 2 if decay else 1.0
            buf.append(int(v * env * volume * 32767))
        return buf

    def _noise(self, duration, volume, hold=1):
        """hold 값을 키울수록 같은 샘플을 오래 유지해 낮고 묵직한 폭발음이 된다."""
        n = int(self.rate * duration)
        buf = array("h")
        v = 0.0
        for i in range(n):
            if i % hold == 0:
                v = random.uniform(-1, 1)
            t = i / n
            buf.append(int(v * (1 - t) ** 2 * volume * 32767))
        return buf

    def _make(self, mono):
        if self.channels == 2:
            stereo = array("h")
            for s in mono:
                stereo.append(s)
                stereo.append(s)
            mono = stereo
        return pygame.mixer.Sound(buffer=mono.tobytes())

    def play(self, name):
        snd = self.sounds.get(name)
        if snd:
            snd.play()


# ---------------------------------------------------------------------------
# 배경 (스크롤되는 지형)
# ---------------------------------------------------------------------------
class Terrain:
    """세로로 이어지는 지형 타일을 절차적으로 만들어 스크롤한다."""

    TILE_H = 120

    def __init__(self):
        self.offset = 0.0
        self.tiles = [self._make_tile() for _ in range(HEIGHT // self.TILE_H + 2)]

    def _make_tile(self):
        surf = pygame.Surface((WIDTH, self.TILE_H))
        surf.fill(GRASS)
        for _ in range(30):
            x, y = random.randrange(WIDTH), random.randrange(self.TILE_H)
            pygame.draw.circle(surf, GRASS_DARK, (x, y), random.randint(2, 5))
        for _ in range(random.randint(2, 6)):
            x, y = random.randrange(WIDTH), random.randrange(self.TILE_H)
            r = random.randint(14, 34)
            pygame.draw.circle(surf, FOREST, (x, y), r)
            pygame.draw.circle(surf, GRASS_DARK, (x - r // 3, y - r // 3), r // 3)
        kind = random.random()
        if kind < 0.25:
            # 가로지르는 강
            y = random.randint(20, self.TILE_H - 40)
            pygame.draw.rect(surf, RIVER, (0, y, WIDTH, 26))
            pygame.draw.line(surf, (90, 140, 210), (0, y + 4), (WIDTH, y + 4), 2)
        elif kind < 0.45:
            # 세로 도로 일부
            x = random.randint(60, WIDTH - 90)
            pygame.draw.rect(surf, ROAD, (x, 0, 30, self.TILE_H))
            for yy in range(0, self.TILE_H, 24):
                pygame.draw.rect(surf, (200, 190, 150), (x + 14, yy, 2, 12))
        return surf

    def update(self):
        self.offset += scroll_speed
        if self.offset >= self.TILE_H:
            self.offset -= self.TILE_H
            self.tiles.pop()
            self.tiles.insert(0, self._make_tile())

    def draw(self, screen):
        for i, tile in enumerate(self.tiles):
            screen.blit(tile, (0, (i - 1) * self.TILE_H + self.offset))


# ---------------------------------------------------------------------------
# 이펙트
# ---------------------------------------------------------------------------
class Explosion:
    def __init__(self, x, y, size=30, ground=False):
        self.x, self.y = x, y
        self.size = size
        self.ground = ground
        self.timer = 0
        self.duration = 28
        self.sparks = [
            [x, y, random.uniform(-3, 3), random.uniform(-3, 3)] for _ in range(12)
        ]

    @property
    def done(self):
        return self.timer >= self.duration

    def update(self):
        self.timer += 1
        if self.ground:
            self.y += scroll_speed
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3] + (scroll_speed if self.ground else 0)

    def draw(self, screen):
        t = self.timer / self.duration
        r = int(self.size * (0.3 + t))
        alpha = int(255 * (1 - t))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*ORANGE, alpha), (r, r), r)
        pygame.draw.circle(surf, (*YELLOW, alpha), (r, r), max(1, r // 2))
        screen.blit(surf, (self.x - r, self.y - r))
        for s in self.sparks:
            pygame.draw.circle(screen, YELLOW, (int(s[0]), int(s[1])), 2)


class Crater:
    """파괴된 지상 목표물 자리에 남는 흔적."""

    def __init__(self, x, y, r):
        self.x, self.y, self.r = x, y, r

    def update(self):
        self.y += scroll_speed

    @property
    def done(self):
        return self.y - self.r > HEIGHT

    def draw(self, screen):
        pygame.draw.circle(screen, (40, 35, 30), (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(screen, (25, 22, 20), (int(self.x), int(self.y)), self.r // 2)


# ---------------------------------------------------------------------------
# 플레이어와 무기
# ---------------------------------------------------------------------------
class Player:
    SPEED = 4.5

    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 100
        self.radius = 10
        self.shot_cooldown = 0
        self.bomb_cooldown = 0
        self.invincible = 120
        self.power = 1  # 1~4 단계 → 레이저 2/4/6/8발

    @property
    def target(self):
        return self.x, self.y - BOMB_RANGE

    def update(self, keys):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = clamp(self.x + dx * self.SPEED, 20, WIDTH - 20)
        self.y = clamp(self.y + dy * self.SPEED, BOMB_RANGE + 20, HEIGHT - 30)
        self.shot_cooldown = max(0, self.shot_cooldown - 1)
        self.bomb_cooldown = max(0, self.bomb_cooldown - 1)
        self.invincible = max(0, self.invincible - 1)

    def draw(self, screen, ground_targets):
        # 폭탄 조준점: 지상 목표물 위에 있으면 빨간색으로 표시
        tx, ty = self.target
        locked = any(math.hypot(g.x - tx, g.y - ty) < g.radius + 8 for g in ground_targets)
        color = RED if locked else WHITE
        pygame.draw.circle(screen, color, (int(tx), int(ty)), 12, 2)
        pygame.draw.line(screen, color, (tx - 18, ty), (tx - 8, ty), 2)
        pygame.draw.line(screen, color, (tx + 8, ty), (tx + 18, ty), 2)
        pygame.draw.line(screen, color, (tx, ty - 18), (tx, ty - 8), 2)
        pygame.draw.line(screen, color, (tx, ty + 8), (tx, ty + 18), 2)

        if self.invincible and (self.invincible // 5) % 2:
            return
        x, y = self.x, self.y
        # 그림자
        shadow = pygame.Surface((40, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 80), (0, 0, 40, 30))
        screen.blit(shadow, (x - 10, y + 10))
        # 기체
        body = [(x, y - 22), (x + 7, y - 4), (x + 22, y + 10), (x + 7, y + 12),
                (x, y + 18), (x - 7, y + 12), (x - 22, y + 10), (x - 7, y - 4)]
        pygame.draw.polygon(screen, (220, 225, 235), body)
        pygame.draw.polygon(screen, METAL_DARK, body, 2)
        pygame.draw.ellipse(screen, CYAN, (x - 4, y - 10, 8, 12))
        flame = random.randint(4, 9)
        pygame.draw.polygon(screen, ORANGE, [(x - 4, y + 16), (x + 4, y + 16), (x, y + 16 + flame)])


class Laser:
    SPEED = 12

    def __init__(self, x, y, vx=0.0):
        self.x, self.y = x, y
        self.vx = vx

    @property
    def done(self):
        return self.y < -20 or not (-20 < self.x < WIDTH + 20)

    def update(self):
        self.x += self.vx
        self.y -= self.SPEED

    def draw(self, screen):
        pygame.draw.rect(screen, YELLOW, (self.x - 2, self.y - 10, 4, 14))
        pygame.draw.rect(screen, WHITE, (self.x - 1, self.y - 8, 2, 10))


class Bomb:
    """플레이어 위치에서 조준점까지 날아가 착탄 시 폭발한다."""

    def __init__(self, x, y, tx, ty):
        self.x, self.y = x, y
        self.sx, self.sy = x, y
        self.tx, self.ty = tx, ty
        self.t = 0
        self.duration = 30
        self.exploded = False

    @property
    def done(self):
        return self.exploded

    def update(self):
        self.t += 1
        self.ty += scroll_speed  # 목표 지점도 지형과 함께 흘러간다
        k = self.t / self.duration
        self.x = self.sx + (self.tx - self.sx) * k
        self.y = self.sy + (self.ty - self.sy) * k

    @property
    def landed(self):
        return self.t >= self.duration

    def draw(self, screen):
        k = self.t / self.duration
        r = int(6 - 3 * k)  # 멀어질수록 작게
        pygame.draw.circle(screen, (60, 60, 60), (int(self.x), int(self.y)), r + 1)
        pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), r)


class EnemyBullet:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.radius = 4

    @property
    def done(self):
        return not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20)

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 2)


class PowerUp:
    """먹으면 레이저가 한 단계(2발씩) 강해지는 아이템."""
    radius = 13

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.age = 0
        self.taken = False

    @property
    def done(self):
        return self.taken or self.y - self.radius > HEIGHT

    def update(self):
        self.age += 1
        self.y += 1.6
        self.x = clamp(self.x + math.sin(self.age * 0.08) * 0.8, 15, WIDTH - 15)

    def draw(self, screen, font):
        x, y = int(self.x), int(self.y)
        glow = 3 + int(math.sin(self.age * 0.2) * 2)
        pygame.draw.circle(screen, CYAN, (x, y), self.radius + glow, 2)
        pygame.draw.circle(screen, (30, 60, 200), (x, y), self.radius)
        img = font.render("P", True, WHITE)
        screen.blit(img, img.get_rect(center=(x, y + 1)))


def aimed_bullet(x, y, px, py, speed):
    angle = math.atan2(py - y, px - x)
    return EnemyBullet(x, y, math.cos(angle) * speed, math.sin(angle) * speed)


# ---------------------------------------------------------------------------
# 공중 적
# ---------------------------------------------------------------------------
class AirEnemy:
    radius = 14
    score = 100
    hp = 1

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.age = 0
        self.fire_timer = random.randint(60, 140)
        self.dead = False

    @property
    def done(self):
        return self.dead or self.y > HEIGHT + 40 or self.y < -200 or not (-80 < self.x < WIDTH + 80)

    def move(self, player):
        pass

    def update(self, player, bullets, level):
        self.age += 1
        self.move(player)
        self.fire_timer -= 1
        if self.fire_timer <= 0 and 0 < self.y < HEIGHT * 0.7:
            bullets.append(aimed_bullet(self.x, self.y, player.x, player.y, 3 + level * 0.3))
            self.fire_timer = max(50, 150 - level * 10)

    def hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.dead = True
            return True
        return False


class Dart(AirEnemy):
    """곧장 내려오다가 플레이어 쪽으로 살짝 꺾는 소형기."""

    def move(self, player):
        self.y += 3
        if self.age > 30:
            self.x += clamp(player.x - self.x, -1.2, 1.2)

    def draw(self, screen):
        x, y = self.x, self.y
        pts = [(x, y + 14), (x + 12, y - 10), (x, y - 4), (x - 12, y - 10)]
        pygame.draw.polygon(screen, (200, 60, 90), pts)
        pygame.draw.polygon(screen, WHITE, pts, 1)
        pygame.draw.circle(screen, YELLOW, (int(x), int(y)), 3)


class Spinner(AirEnemy):
    """사인 곡선을 그리며 내려오는 원반."""
    score = 150

    def __init__(self, x, y):
        super().__init__(x, y)
        self.base_x = x
        self.phase = random.uniform(0, math.tau)

    def move(self, player):
        self.y += 2.2
        self.x = self.base_x + math.sin(self.age * 0.05 + self.phase) * 90

    def draw(self, screen):
        x, y = int(self.x), int(self.y)
        pygame.draw.ellipse(screen, METAL, (x - 15, y - 7, 30, 14))
        pygame.draw.ellipse(screen, METAL_DARK, (x - 15, y - 7, 30, 14), 2)
        a = self.age * 0.3
        for i in range(3):
            ang = a + i * math.tau / 3
            pygame.draw.circle(screen, CYAN, (int(x + math.cos(ang) * 9), int(y + math.sin(ang) * 3)), 2)


class Swooper(AirEnemy):
    """화면 옆에서 들어와 원호를 그리며 빠져나가는 중형기."""
    radius = 16
    score = 200
    hp = 2

    def __init__(self, from_left):
        super().__init__(-30 if from_left else WIDTH + 30, random.randint(60, 200))
        self.dir = 1 if from_left else -1
        self.angle = 0.0

    def move(self, player):
        self.angle += 0.018
        self.x += self.dir * 3.2 * math.cos(self.angle)
        self.y += 2.6 * math.sin(self.angle) + 0.4

    def draw(self, screen):
        x, y = self.x, self.y
        pts = [(x - 16, y - 6), (x + 16, y - 6), (x + 10, y + 10), (x - 10, y + 10)]
        pygame.draw.polygon(screen, (230, 140, 50), pts)
        pygame.draw.polygon(screen, WHITE, pts, 1)
        pygame.draw.rect(screen, BLACK, (x - 8, y - 2, 16, 4))


# ---------------------------------------------------------------------------
# 지상 적 (지형과 함께 스크롤, 폭탄으로만 파괴 가능)
# ---------------------------------------------------------------------------
class GroundTarget:
    radius = 16
    score = 300
    hp = 1

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.age = 0
        self.fire_timer = random.randint(40, 120)
        self.dead = False

    @property
    def done(self):
        return self.dead or self.y - self.radius > HEIGHT

    def update(self, player, bullets, level):
        self.age += 1
        self.y += scroll_speed
        self.fire_timer -= 1
        if self.fire_timer <= 0 and 20 < self.y < player.y - 60:
            self.fire(player, bullets, level)
            self.fire_timer = max(60, 160 - level * 10)

    def fire(self, player, bullets, level):
        bullets.append(aimed_bullet(self.x, self.y, player.x, player.y, 2.8 + level * 0.25))

    def hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.dead = True
            return True
        return False


class Turret(GroundTarget):
    def draw(self, screen, player):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(screen, METAL_DARK, (x, y), 16)
        pygame.draw.circle(screen, METAL, (x, y), 12)
        ang = math.atan2(player.y - y, player.x - x)
        pygame.draw.line(screen, (40, 40, 50), (x, y),
                         (x + math.cos(ang) * 18, y + math.sin(ang) * 18), 5)
        pygame.draw.circle(screen, RED, (x, y), 4)


class Radar(GroundTarget):
    """공격하지 않지만 점수가 높은 레이더 기지."""
    score = 500

    def fire(self, player, bullets, level):
        pass

    def draw(self, screen, player):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(screen, METAL_DARK, (x - 16, y - 16, 32, 32))
        pygame.draw.rect(screen, METAL, (x - 13, y - 13, 26, 26))
        ang = self.age * 0.08
        pygame.draw.line(screen, CYAN, (x, y), (x + math.cos(ang) * 12, y + math.sin(ang) * 12), 3)


class Fortress(GroundTarget):
    """주기적으로 등장하는 대형 지상 요새. 중앙 코어에 폭탄을 여러 번 맞혀야 한다."""
    radius = 26
    score = 3000

    def __init__(self, x, y, level):
        super().__init__(x, y)
        self.hp = 6 + level * 2
        self.max_hp = self.hp
        self.flash = 0

    def update(self, player, bullets, level):
        # 화면 상단 1/3 지점에 오면 스크롤을 멈추고 버틴다
        global scroll_speed
        self.age += 1
        self.y += scroll_speed
        if self.y >= HEIGHT * 0.3:
            scroll_speed = 0
        self.flash = max(0, self.flash - 1)
        self.fire_timer -= 1
        if self.fire_timer <= 0 and self.y > 0:
            n = 8 + level
            base = self.age * 0.05
            for i in range(n):
                a = base + i * math.tau / n
                bullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 2.5, math.sin(a) * 2.5))
            bullets.append(aimed_bullet(self.x, self.y, player.x, player.y, 4))
            self.fire_timer = max(45, 100 - level * 5)

    def hit(self):
        self.flash = 6
        return super().hit()

    def draw(self, screen, player):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(screen, METAL_DARK, [
            (x - 70, y), (x - 40, y - 45), (x + 40, y - 45),
            (x + 70, y), (x + 40, y + 45), (x - 40, y + 45)])
        pygame.draw.polygon(screen, METAL, [
            (x - 58, y), (x - 34, y - 36), (x + 34, y - 36),
            (x + 58, y), (x + 34, y + 36), (x - 34, y + 36)])
        for ox in (-46, 46):
            pygame.draw.circle(screen, METAL_DARK, (x + ox, y), 9)
            pygame.draw.circle(screen, ORANGE, (x + ox, y), 4)
        core_color = WHITE if self.flash else (220, 40, 60)
        pulse = 4 + int(math.sin(self.age * 0.15) * 3)
        pygame.draw.circle(screen, BLACK, (x, y), 22)
        pygame.draw.circle(screen, core_color, (x, y), 14 + pulse // 2)
        # 체력 바
        w = 100
        pygame.draw.rect(screen, BLACK, (x - w // 2, y - 60, w, 6))
        pygame.draw.rect(screen, RED, (x - w // 2, y - 60, int(w * self.hp / self.max_hp), 6))


# ---------------------------------------------------------------------------
# 게임
# ---------------------------------------------------------------------------
class Game:
    FORTRESS_INTERVAL = 60 * 45  # 45초마다 요새 등장

    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.sfx = SoundBank()
        pygame.display.set_caption("Sky Striker - Vertical Shooter")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20, bold=True)
        self.big_font = pygame.font.SysFont("consolas", 46, bold=True)
        self.high_score = 0
        self.state = "title"
        self.reset()

    def reset(self):
        global scroll_speed
        scroll_speed = SCROLL_SPEED
        self.terrain = Terrain()
        self.player = Player()
        self.lasers = []
        self.bombs = []
        self.air = []
        self.ground = []
        self.bullets = []
        self.effects = []
        self.craters = []
        self.items = []
        self.score = 0
        self.lives = 3
        self.frame = 0
        self.level = 1
        self.fortress_timer = self.FORTRESS_INTERVAL
        self.fortress = None
        self.paused = False

    # ----- 스폰 -----
    def spawn(self):
        f = self.frame
        lvl = self.level
        if self.fortress is None:
            if f % max(25, 70 - lvl * 6) == 0:
                kind = random.random()
                if kind < 0.5:
                    self.air.append(Dart(random.randint(30, WIDTH - 30), -20))
                elif kind < 0.8:
                    self.air.append(Spinner(random.randint(100, WIDTH - 100), -20))
                else:
                    left = random.random() < 0.5
                    for i in range(3):
                        e = Swooper(left)
                        e.x -= (1 if left else -1) * i * 45
                        self.air.append(e)
            if f % max(60, 140 - lvl * 10) == 0:
                cls = Radar if random.random() < 0.25 else Turret
                self.ground.append(cls(random.randint(40, WIDTH - 40), -30))
        else:
            # 요새전 중에는 소형기만 가끔 출현
            if f % 120 == 0:
                self.air.append(Dart(random.randint(30, WIDTH - 30), -20))

        self.fortress_timer -= 1
        if self.fortress_timer <= 0 and self.fortress is None:
            self.fortress = Fortress(WIDTH / 2, -60, lvl)
            self.ground.append(self.fortress)
            self.sfx.play("alarm")

    # ----- 업데이트 -----
    def update(self):
        keys = pygame.key.get_pressed()
        p = self.player
        p.update(keys)

        if (keys[pygame.K_z] or keys[pygame.K_j]) and p.shot_cooldown == 0:
            self.fire_lasers()
            p.shot_cooldown = 7
        if (keys[pygame.K_x] or keys[pygame.K_k]) and p.bomb_cooldown == 0 and len(self.bombs) < 2:
            tx, ty = p.target
            self.bombs.append(Bomb(p.x, p.y, tx, ty))
            p.bomb_cooldown = 20
            self.sfx.play("bomb")

        self.frame += 1
        self.level = 1 + self.frame // (60 * 40)
        self.terrain.update()
        self.spawn()

        for obj in self.lasers + self.bombs + self.bullets + self.effects + self.craters + self.items:
            obj.update()
        for e in self.air + self.ground:
            e.update(p, self.bullets, self.level)

        self.handle_collisions()

        self.lasers = [o for o in self.lasers if not o.done]
        self.bombs = [o for o in self.bombs if not o.done]
        self.bullets = [o for o in self.bullets if not o.done]
        self.effects = [o for o in self.effects if not o.done]
        self.craters = [o for o in self.craters if not o.done]
        self.items = [o for o in self.items if not o.done]
        self.air = [o for o in self.air if not o.done]
        self.ground = [o for o in self.ground if not o.done]

    def fire_lasers(self):
        """파워 단계마다 좌우 한 쌍씩, 바깥쪽일수록 넓게 퍼지도록 발사한다."""
        p = self.player
        for i in range(p.power):
            ox = 6 + i * 5
            vx = i * 1.3
            self.lasers.append(Laser(p.x - ox, p.y - 14, -vx))
            self.lasers.append(Laser(p.x + ox, p.y - 14, vx))
        self.sfx.play("shot")

    def drop_item(self, x, y, chance):
        if random.random() < chance:
            self.items.append(PowerUp(x, y))

    def handle_collisions(self):
        p = self.player

        # 레이저 → 공중 적
        for laser in self.lasers:
            for e in self.air:
                if not e.dead and math.hypot(laser.x - e.x, laser.y - e.y) < e.radius + 4:
                    laser.y = -100
                    if e.hit():
                        self.score += e.score
                        self.effects.append(Explosion(e.x, e.y, 26))
                        self.sfx.play("explode")
                        self.drop_item(e.x, e.y, 0.15 if isinstance(e, Swooper) else 0.06)
                    break

        # 폭탄 착탄 → 지상 적
        for bomb in self.bombs:
            if not bomb.landed:
                continue
            bomb.exploded = True
            self.effects.append(Explosion(bomb.x, bomb.y, 18, ground=True))
            self.sfx.play("ground_explode")
            for g in self.ground:
                if not g.dead and math.hypot(bomb.x - g.x, bomb.y - g.y) < g.radius + 10:
                    if g.hit():
                        self.score += g.score
                        big = g is self.fortress
                        self.effects.append(Explosion(g.x, g.y, 80 if big else 32, ground=True))
                        self.craters.append(Crater(g.x, g.y, 40 if big else 14))
                        if isinstance(g, Radar):
                            self.drop_item(g.x, g.y, 1.0)
                        if big:
                            self.sfx.play("big_explode")
                            self.drop_item(g.x - 20, g.y, 1.0)
                            self.drop_item(g.x + 20, g.y, 1.0)
                            global scroll_speed
                            scroll_speed = SCROLL_SPEED
                            self.fortress = None
                            self.fortress_timer = self.FORTRESS_INTERVAL
                            self.bullets.clear()

        # 아이템 획득 (무적 중에도 가능)
        for item in self.items:
            if not item.taken and math.hypot(item.x - p.x, item.y - p.y) < item.radius + p.radius + 6:
                item.taken = True
                if p.power < 4:
                    p.power += 1
                else:
                    self.score += 1000  # 최대 파워에서는 보너스 점수
                self.sfx.play("powerup")

        if p.invincible:
            return

        # 적 탄 / 공중 적 → 플레이어 (지상 적과는 충돌하지 않음)
        for b in self.bullets:
            if math.hypot(b.x - p.x, b.y - p.y) < b.radius + p.radius - 4:
                self.player_hit()
                return
        for e in self.air:
            if not e.dead and math.hypot(e.x - p.x, e.y - p.y) < e.radius + p.radius - 2:
                e.dead = True
                self.effects.append(Explosion(e.x, e.y, 26))
                self.player_hit()
                return

    def player_hit(self):
        p = self.player
        self.effects.append(Explosion(p.x, p.y, 50))
        self.sfx.play("player_hit")
        p.power = max(1, p.power - 1)  # 격추되면 파워 한 단계 감소
        self.lives -= 1
        self.bullets.clear()
        if self.lives <= 0:
            self.high_score = max(self.high_score, self.score)
            self.state = "gameover"
        else:
            p.x, p.y = WIDTH / 2, HEIGHT - 100
            p.invincible = 150

    # ----- 그리기 -----
    def draw_text(self, text, font, color, center):
        img = font.render(text, True, color)
        self.screen.blit(img, img.get_rect(center=center))

    def draw_hud(self):
        self.screen.blit(self.font.render(f"SCORE {self.score:07d}", True, WHITE), (10, 8))
        self.screen.blit(self.font.render(f"HI {max(self.high_score, self.score):07d}", True, YELLOW), (WIDTH - 170, 8))
        self.screen.blit(self.font.render(f"LV {self.level}", True, CYAN), (10, 32))
        self.screen.blit(self.font.render(f"SHOT x{self.player.power * 2}", True, CYAN), (80, 32))
        for i in range(self.lives):
            x = WIDTH - 20 - i * 22
            pygame.draw.polygon(self.screen, WHITE, [(x, 34), (x + 7, 50), (x - 7, 50)])
        if self.fortress:
            self.draw_text("WARNING: FORTRESS - BOMB THE CORE!", self.font, RED, (WIDTH / 2, HEIGHT - 20))

    def draw(self):
        s = self.screen
        self.terrain.draw(s)
        for c in self.craters:
            c.draw(s)
        for g in self.ground:
            g.draw(s, self.player)
        for b in self.bombs:
            b.draw(s)
        for e in self.effects:
            if e.ground:
                e.draw(s)

        for item in self.items:
            item.draw(s, self.font)
        if self.state == "play":
            self.player.draw(s, self.ground)
        for e in self.air:
            e.draw(s)
        for l in self.lasers:
            l.draw(s)
        for b in self.bullets:
            b.draw(s)
        for e in self.effects:
            if not e.ground:
                e.draw(s)

        self.draw_hud()

        if self.state == "title":
            self.overlay()
            self.draw_text("SKY STRIKER", self.big_font, YELLOW, (WIDTH / 2, HEIGHT / 2 - 120))
            lines = [
                "ARROWS / WASD : MOVE",
                "Z : LASER (AIR)",
                "X : BOMB (GROUND)",
                "P : PAUSE",
                "",
                "PRESS ENTER TO START",
            ]
            for i, t in enumerate(lines):
                self.draw_text(t, self.font, WHITE, (WIDTH / 2, HEIGHT / 2 - 40 + i * 30))
        elif self.state == "gameover":
            self.overlay()
            self.draw_text("GAME OVER", self.big_font, RED, (WIDTH / 2, HEIGHT / 2 - 40))
            self.draw_text(f"SCORE {self.score}", self.font, WHITE, (WIDTH / 2, HEIGHT / 2 + 20))
            self.draw_text("PRESS ENTER TO RETRY", self.font, WHITE, (WIDTH / 2, HEIGHT / 2 + 60))
        elif self.paused:
            self.overlay()
            self.draw_text("PAUSED", self.big_font, WHITE, (WIDTH / 2, HEIGHT / 2))

        pygame.display.flip()

    def overlay(self):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.screen.blit(shade, (0, 0))

    # ----- 메인 루프 -----
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_RETURN and self.state in ("title", "gameover"):
                        self.reset()
                        self.state = "play"
                        self.sfx.play("start")
                    if event.key == pygame.K_p and self.state == "play":
                        self.paused = not self.paused

            if self.state == "play" and not self.paused:
                self.update()
            elif self.state != "play":
                # 타이틀/게임오버 화면에서도 배경은 계속 흐르게
                self.terrain.update()
                for e in self.effects:
                    e.update()
                self.effects = [e for e in self.effects if not e.done]

            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
