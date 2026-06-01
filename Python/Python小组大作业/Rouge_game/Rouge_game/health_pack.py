import pygame
import random
import math
from settings import *

class HealthPack(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.size = HEALTH_PACK_SIZE
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(COLORS['health_pack'])
        
        # 绘制十字标记
        cross_thickness = 3
        cross_length = self.size - 6
        cross_center = self.size // 2
        
        # 水平线
        pygame.draw.rect(self.image, COLORS['health_pack_cross'], 
                        (3, cross_center - cross_thickness//2, cross_length, cross_thickness))
        # 垂直线
        pygame.draw.rect(self.image, COLORS['health_pack_cross'], 
                        (cross_center - cross_thickness//2, 3, cross_thickness, cross_length))
        
        self.rect = self.image.get_rect(center=pos)
        self.heal_amount = HEALTH_PACK_HEAL_AMOUNT
        self.lifetime = HEALTH_PACK_LIFETIME
        self.spawn_time = pygame.time.get_ticks()
        
        # 浮动效果
        self.float_offset = 0
        self.float_speed = 0.1
        self.original_y = pos[1]

    def update(self):
        # 浮动动画
        self.float_offset += self.float_speed
        self.rect.centery = self.original_y + math.sin(self.float_offset) * 3
        
        # 检查生存时间
        current_time = pygame.time.get_ticks()
        if current_time - self.spawn_time > self.lifetime * (1000 / FPS):
            self.kill()
        
        # 闪烁效果（快过期时）
        time_left = self.lifetime * (1000 / FPS) - (current_time - self.spawn_time)
        if time_left < 3000:  # 最后3秒开始闪烁
            if (current_time // 200) % 2:  # 每200ms闪烁一次
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)

class HealthPackGroup:
    def __init__(self):
        self.group = pygame.sprite.Group()
        self.spawn_timer = 0

    def get_spawn_position(self, game_map=None):
        """获取随机生成位置，避免在屏幕边缘"""
        if game_map:
            # 使用地图的有效位置
            return game_map.get_valid_position((HEALTH_PACK_SIZE, HEALTH_PACK_SIZE))
        else:
            # 默认随机位置
            margin = 50
            x = random.randint(margin, SCREEN_WIDTH - margin)
            y = random.randint(margin, SCREEN_HEIGHT - margin)
            return (x, y)

    def update(self, player, game_map=None):
        self.group.update()
        
        # 定期生成血包
        self.spawn_timer += 1
        if self.spawn_timer >= HEALTH_PACK_SPAWN_RATE and len(self.group) < 3:  # 最多3个血包
            pos = self.get_spawn_position(game_map)
            self.group.add(HealthPack(pos))
            self.spawn_timer = 0
        
        # 检查玩家拾取
        collected = pygame.sprite.spritecollide(player, self.group, True)
        for health_pack in collected:
            # 玩家拾取血包
            old_health = player.health
            player.health = min(player.max_health, player.health + health_pack.heal_amount)
            actual_heal = player.health - old_health
            
            # 返回实际回复的血量，用于UI显示
            if actual_heal > 0:
                return actual_heal
        
        return 0

    def draw(self, screen):
        self.group.draw(screen)
        
        # 绘制血包信息
        for health_pack in self.group:
            # 绘制回复量文字
            font = pygame.font.Font(None, 20)
            heal_text = font.render(f"+{health_pack.heal_amount}", True, COLORS['health_pack'])
            text_rect = heal_text.get_rect(center=(health_pack.rect.centerx, health_pack.rect.bottom + 10))
            screen.blit(heal_text, text_rect) 