import pygame
import random
import math
from settings import *
from enum import Enum


class WeaponType(Enum):
    PISTOL = 1


class Bullet(pygame.sprite.Sprite):
    def __init__(self, start_pos, target_pos, weapon_type=WeaponType.PISTOL):
        super().__init__()
        self.weapon_type = weapon_type

        # 设置子弹属性
        self._init_pistol()

        self.rect = self.image.get_rect(center=start_pos)

        # 计算方向
        direction = pygame.math.Vector2(target_pos) - start_pos
        if direction.length() > 0:
            self.direction = direction.normalize()
        else:
            self.direction = pygame.math.Vector2(1, 0)

    def _init_pistol(self):
        """初始化手枪子弹属性"""
        self.image = pygame.Surface((BULLET_SIZE, BULLET_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(self.image, COLORS['bullet'], (BULLET_SIZE // 2, BULLET_SIZE // 2), BULLET_SIZE // 2)
        self.speed = BULLET_SPEED
        self.damage = BULLET_DAMAGE
        self.size = BULLET_SIZE

    def update(self):
        self.rect.center += self.direction * self.speed
        # 移出屏幕后删除
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color=COLORS['explosion']):
        super().__init__()
        self.size = random.randint(2, 6)
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (self.size // 2, self.size // 2), self.size // 2)
        self.rect = self.image.get_rect(center=pos)

        # 随机方向和速度
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        self.velocity = pygame.math.Vector2(
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )
        self.life = random.randint(15, 30)
        self.max_life = self.life

    def update(self):
        self.rect.center += self.velocity
        self.life -= 1

        # 淡出效果
        alpha = int(255 * (self.life / self.max_life))
        self.image.set_alpha(alpha)

        if self.life <= 0:
            self.kill()


class TurretBullet(pygame.sprite.Sprite):
    def __init__(self, start_pos, target_pos):
        super().__init__()
        self.image = pygame.Surface((12, 12), pygame.SRCALPHA)
        # 绘制星形炮弹
        points = []
        for i in range(5):
            angle = 2 * math.pi / 5 * i - math.pi / 2
            outer_x = 6 + math.cos(angle) * 6
            outer_y = 6 + math.sin(angle) * 6
            inner_x = 6 + math.cos(angle + math.pi / 5) * 3
            inner_y = 6 + math.sin(angle + math.pi / 5) * 3
            points.extend([(outer_x, outer_y), (inner_x, inner_y)])
        pygame.draw.polygon(self.image, (255, 50, 50), points)
        self.rect = self.image.get_rect(center=start_pos)
        self.speed = BULLET_SPEED * 0.6  # 稍慢一些
        self.damage = BULLET_DAMAGE * 2.5  # 更高伤害

        direction = pygame.math.Vector2(target_pos) - start_pos
        if direction.length() > 0:
            self.direction = direction.normalize()
        else:
            self.direction = pygame.math.Vector2(1, 0)

    def update(self):
        self.rect.center += self.direction * self.speed
        # 移出屏幕后删除
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class BulletGroup:
    def __init__(self):
        self.group = pygame.sprite.Group()
        self.turret_bullets = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()

    def add_bullet(self, start_pos, target_pos, weapon_type=WeaponType.PISTOL):
        self.group.add(Bullet(start_pos, target_pos, weapon_type))

    def add(self, bullet):
        """添加炮塔子弹"""
        if isinstance(bullet, TurretBullet):
            self.turret_bullets.add(bullet)
        else:
            self.group.add(bullet)

    def create_explosion(self, pos, size=1.0):
        """在指定位置创建爆炸粒子效果"""
        color = COLORS['explosion']
        if size > 1.5:  # 大爆炸使用不同颜色
            color = (255, 150, 50)

        for _ in range(int(PARTICLE_COUNT * size)):
            self.particles.add(Particle(pos, color))

    def update(self):
        self.group.update()
        self.turret_bullets.update()
        self.particles.update()

    def draw(self, screen):
        self.group.draw(screen)
        self.turret_bullets.draw(screen)
        self.particles.draw(screen)