import pygame
import random
import math
from settings import *

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, obstacle_type, pos, size, **kwargs):
        super().__init__()
        self.obstacle_type = obstacle_type
        self.image = pygame.Surface(size)
        self.rect = pygame.Rect(pos, size)
        
        # 特殊属性
        self.health = kwargs.get('health', None)
        self.max_health = self.health
        self.fire_rate = kwargs.get('fire_rate', 120)
        self.last_shot = 0
        self.active = kwargs.get('active', True)
        self.destroyed = False
        
        self.create_appearance()
    
    def create_appearance(self):
        """创建障碍物外观"""
        size = self.image.get_size()
        
        # 根据障碍物类型设置颜色和外观
        if self.obstacle_type == "wall":
            self.image.fill((100, 100, 100))
            # 添加砖块纹理
            for i in range(0, size[0], 20):
                for j in range(0, size[1], 10):
                    pygame.draw.rect(self.image, (120, 120, 120), (i, j, 18, 8), 1)
        
        elif self.obstacle_type == "destructible_wall":
            if self.health and self.health > 0:
                # 根据血量改变颜色
                health_ratio = self.health / self.max_health if self.max_health else 1
                base_color = int(80 + 40 * health_ratio)
                self.image.fill((base_color, base_color + 20, base_color))
                # 裂纹效果
                if health_ratio < 0.7:
                    for _ in range(int((1 - health_ratio) * 10)):
                        x = random.randint(0, size[0])
                        y = random.randint(0, size[1])
                        pygame.draw.line(self.image, (50, 50, 50), 
                                       (x, y), (x + random.randint(-10, 10), y + random.randint(-10, 10)), 2)
            else:
                # 已摧毁，变为碎片
                self.destroyed = True
        
        elif self.obstacle_type == "fortress":
            self.image.fill((80, 60, 40))
            # 城堡纹理
            pygame.draw.rect(self.image, (100, 80, 60), (0, 0, size[0], size[1]), 5)
            # 城垛
            for i in range(0, size[0], 30):
                pygame.draw.rect(self.image, (100, 80, 60), (i, 0, 20, 20))
        
        elif self.obstacle_type == "bunker":
            self.image.fill((60, 60, 60))
            # 掩体纹理
            pygame.draw.circle(self.image, (80, 80, 80), (size[0]//2, size[1]//2), min(size)//2 - 5, 3)
        
        elif self.obstacle_type == "turret_bunker":
            self.image.fill((60, 60, 60))
            # 掩体纹理
            pygame.draw.circle(self.image, (80, 80, 80), (size[0]//2, size[1]//2), min(size)//2 - 5, 3)
            # 炮塔
            center = (size[0]//2, size[1]//2)
            pygame.draw.circle(self.image, (100, 100, 100), center, 15)
            pygame.draw.circle(self.image, (120, 120, 120), center, 15, 2)
            # 炮管
            pygame.draw.rect(self.image, (80, 80, 80), (center[0] - 2, center[1] - 20, 4, 20))
        
        elif self.obstacle_type == "rock":
            self.image.fill((90, 80, 70))
            # 岩石纹理
            pygame.draw.ellipse(self.image, (110, 100, 90), (5, 5, size[0]-10, size[1]-10))
            pygame.draw.ellipse(self.image, (70, 60, 50), (10, 10, size[0]-20, size[1]-20), 2)
        
        elif self.obstacle_type == "sandstorm_generator":
            self.image.fill((120, 100, 60))
            # 沙尘暴发生器
            center = (size[0]//2, size[1]//2)
            pygame.draw.circle(self.image, (150, 130, 80), center, min(size)//2 - 5)
            # 旋转效果
            for i in range(4):
                angle = i * 90 + (pygame.time.get_ticks() * 0.1) % 360
                x = center[0] + math.cos(math.radians(angle)) * 10
                y = center[1] + math.sin(math.radians(angle)) * 10
                pygame.draw.circle(self.image, (200, 180, 120), (int(x), int(y)), 3)
        
        elif self.obstacle_type == "power_station":
            if self.active:
                self.image.fill((40, 40, 80))
                # 电力站
                pygame.draw.rect(self.image, (60, 60, 120), (10, 10, size[0]-20, size[1]-20))
                # 电力效果
                center = (size[0]//2, size[1]//2)
                for i in range(3):
                    radius = 10 + i * 8
                    alpha = int(100 - i * 30)
                    color = (100 + i * 50, 100 + i * 50, 255)
                    pygame.draw.circle(self.image, color, center, radius, 2)
            else:
                self.image.fill((40, 40, 40))
                # 损坏的电力站
                pygame.draw.rect(self.image, (60, 60, 60), (10, 10, size[0]-20, size[1]-20))
                # 火花效果
                for _ in range(5):
                    x = random.randint(10, size[0]-10)
                    y = random.randint(10, size[1]-10)
                    pygame.draw.circle(self.image, (255, 100, 0), (x, y), 2)
        
        elif self.obstacle_type == "building":
            self.image.fill((60, 60, 80))
            # 建筑纹理
            # 窗户
            for i in range(10, size[0]-10, 25):
                for j in range(20, size[1]-10, 30):
                    pygame.draw.rect(self.image, (100, 100, 120), (i, j, 15, 20))
    
    def take_damage(self, damage):
        """受到伤害"""
        if self.health is not None:
            self.health -= damage
            if self.health <= 0:
                if self.obstacle_type == "destructible_wall":
                    self.destroyed = True
                    return True  # 可以被移除
                elif self.obstacle_type == "power_station":
                    self.active = False
                    self.create_appearance()  # 重新绘制外观
            else:
                self.create_appearance()  # 更新外观
        return False
    
    def can_shoot_at_enemy(self, enemy_pos, max_range=150):
        """检查是否可以射击敌人"""
        if self.obstacle_type != "turret_bunker":
            return False
        
        distance = math.sqrt((enemy_pos[0] - self.rect.centerx)**2 + (enemy_pos[1] - self.rect.centery)**2)
        return distance <= max_range
    
    def shoot_at_enemy(self, enemy_pos, bullets_group):
        """向敌人射击"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot >= self.fire_rate:
            # 创建炮塔子弹
            from weapons import TurretBullet
            bullet = TurretBullet(self.rect.center, enemy_pos)
            bullets_group.add(bullet)
            self.last_shot = current_time

class GameMap:
    def __init__(self, map_name="classic"):
        self.map_name = map_name
        self.map_config = MAPS[map_name]
        self.obstacles = pygame.sprite.Group()
        self.bg_color = self.map_config["bg_color"]
        self.special_mechanics = self.map_config.get("special_mechanics", {})
        
        # 特殊机制状态
        self.speed_boost_zones = []
        self.sandstorm_active = False
        self.sandstorm_timer = 0
        self.power_grid_active = True
        
        # 创建障碍物
        for obstacle_data in self.map_config["obstacles"]:
            obstacle = Obstacle(
                obstacle_data["type"],
                obstacle_data["pos"],
                obstacle_data["size"],
                **{k: v for k, v in obstacle_data.items() if k not in ["type", "pos", "size"]}
            )
            self.obstacles.add(obstacle)
        
        # 初始化特殊机制
        self.init_special_mechanics()
    
    def init_special_mechanics(self):
        """初始化特殊机制"""
        if self.special_mechanics.get("type") == "speed_boost":
            # 创建初始速度提升区域
            self.create_speed_boost_zone()
        elif self.special_mechanics.get("type") == "power_grid":
            self.update_power_grid_status()
    
    def create_speed_boost_zone(self):
        """创建速度提升区域"""
        if len(self.speed_boost_zones) < 2:  # 最多2个区域
            pos = self.get_valid_position((80, 80))
            self.speed_boost_zones.append({
                'pos': pos,
                'size': (80, 80),
                'lifetime': 300,  # 5秒
                'created_time': pygame.time.get_ticks()
            })
    
    def update_power_grid_status(self):
        """更新电力网状态"""
        active_stations = sum(1 for obs in self.obstacles if obs.obstacle_type == "power_station" and obs.active)
        self.power_grid_active = active_stations > 0
    
    def get_spawn_position(self):
        """根据地图类型获取生成位置"""
        spawn_type = self.map_config["spawn_zones"]
        
        if spawn_type == "edges":
            # 经典模式：从边缘生成
            side = random.randint(0, 3)
            if side == 0:  # 上边
                return (random.randint(0, SCREEN_WIDTH), -50)
            elif side == 1:  # 右边
                return (SCREEN_WIDTH + 50, random.randint(0, SCREEN_HEIGHT))
            elif side == 2:  # 下边
                return (random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 50)
            else:  # 左边
                return (-50, random.randint(0, SCREEN_HEIGHT))
        
        elif spawn_type == "safe_areas":
            # 迷宫模式：在安全区域生成
            safe_areas = [
                (50, 50, 100, 100),
                (350, 50, 100, 100),
                (750, 50, 100, 100),
                (50, 550, 100, 100),
                (350, 550, 100, 100),
                (750, 550, 100, 100),
            ]
            area = random.choice(safe_areas)
            return (random.randint(area[0], area[0] + area[2]),
                   random.randint(area[1], area[1] + area[3]))
        
        elif spawn_type == "fortress_perimeter":
            # 要塞模式：在要塞周围生成
            center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.randint(250, 400)
            x = center_x + distance * math.cos(angle)
            y = center_y + distance * math.sin(angle)
            return (max(0, min(SCREEN_WIDTH, x)), max(0, min(SCREEN_HEIGHT, y)))
        
        elif spawn_type == "streets":
            # 城市模式：在街道上生成
            street_areas = [
                (0, 0, 150, SCREEN_HEIGHT),  # 左街道
                (250, 0, 150, SCREEN_HEIGHT),  # 中左街道
                (550, 0, 150, SCREEN_HEIGHT),  # 中右街道
                (850, 0, 150, SCREEN_HEIGHT),  # 右街道
                (0, 0, SCREEN_WIDTH, 150),    # 上街道
                (0, 350, SCREEN_WIDTH, 150),  # 中街道
                (0, 550, SCREEN_WIDTH, 150),  # 下街道
            ]
            area = random.choice(street_areas)
            return (random.randint(area[0], area[0] + area[2]),
                   random.randint(area[1], area[1] + area[3]))
        
        else:  # random
            # 随机生成
            return (random.randint(50, SCREEN_WIDTH - 50),
                   random.randint(50, SCREEN_HEIGHT - 50))
    
    def update(self, player, enemies, bullets_group):
        """更新地图状态"""
        current_time = pygame.time.get_ticks()
        
        # 更新特殊机制
        if self.special_mechanics.get("type") == "speed_boost":
            self.update_speed_boost_zones(current_time)
        elif self.special_mechanics.get("type") == "sandstorms":
            self.update_sandstorms(current_time)
        elif self.special_mechanics.get("type") == "defensive_turrets":
            self.update_turrets(enemies, bullets_group)
        elif self.special_mechanics.get("type") == "power_grid":
            self.update_power_grid_status()
        
        # 移除被摧毁的障碍物
        for obstacle in self.obstacles.copy():
            if hasattr(obstacle, 'destroyed') and obstacle.destroyed:
                obstacle.kill()
    
    def update_speed_boost_zones(self, current_time):
        """更新速度提升区域"""
        # 移除过期的区域
        self.speed_boost_zones = [zone for zone in self.speed_boost_zones 
                                 if current_time - zone['created_time'] < zone['lifetime'] * (1000/60)]
        
        # 随机创建新区域
        if random.random() < 0.01:  # 1%概率每帧
            self.create_speed_boost_zone()
    
    def update_sandstorms(self, current_time):
        """更新沙尘暴"""
        self.sandstorm_timer += 1
        if self.sandstorm_timer >= 300:  # 每5秒切换状态
            self.sandstorm_active = not self.sandstorm_active
            self.sandstorm_timer = 0
    
    def update_turrets(self, enemies, bullets_group):
        """更新炮塔"""
        for obstacle in self.obstacles:
            if obstacle.obstacle_type == "turret_bunker":
                # 寻找最近的敌人
                closest_enemy = None
                min_distance = float('inf')
                
                for enemy in enemies.group:
                    if obstacle.can_shoot_at_enemy(enemy.rect.center):
                        distance = math.sqrt((enemy.rect.centerx - obstacle.rect.centerx)**2 + 
                                           (enemy.rect.centery - obstacle.rect.centery)**2)
                        if distance < min_distance:
                            min_distance = distance
                            closest_enemy = enemy
                
                if closest_enemy:
                    obstacle.shoot_at_enemy(closest_enemy.rect.center, bullets_group)
    
    def check_collision(self, rect):
        """检查与障碍物的碰撞"""
        for obstacle in self.obstacles:
            # 只有未被摧毁的障碍物才会阻挡移动
            if not (hasattr(obstacle, 'destroyed') and obstacle.destroyed):
                if rect.colliderect(obstacle.rect):
                    return True
        return False
    
    def check_bullet_collision(self, bullet_rect):
        """检查子弹与障碍物的碰撞，返回被击中的障碍物"""
        for obstacle in self.obstacles:
            if not (hasattr(obstacle, 'destroyed') and obstacle.destroyed):
                if bullet_rect.colliderect(obstacle.rect):
                    return obstacle
        return None
    
    def check_player_in_speed_zone(self, player_rect):
        """检查玩家是否在速度提升区域"""
        for zone in self.speed_boost_zones:
            zone_rect = pygame.Rect(zone['pos'], zone['size'])
            if player_rect.colliderect(zone_rect):
                return True
        return False
    
    def get_sandstorm_effect(self, player_pos):
        """获取沙尘暴对玩家的影响"""
        if not self.sandstorm_active:
            return 1.0, 1.0  # 正常速度，正常视野
        
        # 检查玩家是否靠近沙尘暴发生器
        for obstacle in self.obstacles:
            if obstacle.obstacle_type == "sandstorm_generator":
                distance = math.sqrt((player_pos[0] - obstacle.rect.centerx)**2 + 
                                   (player_pos[1] - obstacle.rect.centery)**2)
                if distance < 200:  # 影响范围
                    effect_strength = 1.0 - (distance / 200)
                    speed_multiplier = 1.0 - effect_strength * 0.5  # 最多减速50%
                    visibility = 1.0 - effect_strength * 0.7  # 最多减少70%视野
                    return speed_multiplier, visibility
        
        return 1.0, 1.0
    
    def is_power_grid_active(self):
        """检查电力网是否激活"""
        return self.power_grid_active
    
    def get_valid_position(self, size):
        """获取不与障碍物碰撞的有效位置"""
        max_attempts = 50
        for _ in range(max_attempts):
            x = random.randint(0, SCREEN_WIDTH - size[0])
            y = random.randint(0, SCREEN_HEIGHT - size[1])
            test_rect = pygame.Rect(x, y, size[0], size[1])
            
            if not self.check_collision(test_rect):
                return (x, y)
        
        # 如果找不到有效位置，返回屏幕中央
        return (SCREEN_WIDTH // 2 - size[0] // 2, SCREEN_HEIGHT // 2 - size[1] // 2)
    
    def draw(self, screen):
        """绘制地图"""
        # 绘制背景
        screen.fill(self.bg_color)
        
        # 绘制障碍物
        self.obstacles.draw(screen)
        
        # 绘制特殊机制效果
        self.draw_special_effects(screen)
    
    def draw_special_effects(self, screen):
        """绘制特殊效果"""
        if self.special_mechanics.get("type") == "speed_boost":
            # 绘制速度提升区域
            for zone in self.speed_boost_zones:
                current_time = pygame.time.get_ticks()
                elapsed = current_time - zone['created_time']
                lifetime_ms = zone['lifetime'] * (1000/60)
                
                if elapsed < lifetime_ms:
                    # 计算透明度（随时间淡出）
                    alpha = int(255 * (1 - elapsed / lifetime_ms))
                    
                    # 创建带透明度的表面
                    zone_surface = pygame.Surface(zone['size'])
                    zone_surface.set_alpha(alpha)
                    zone_surface.fill((0, 255, 255))  # 青色
                    
                    # 绘制边框
                    pygame.draw.rect(zone_surface, (255, 255, 255), (0, 0, zone['size'][0], zone['size'][1]), 3)
                    
                    screen.blit(zone_surface, zone['pos'])
                    
                    # 绘制箭头指示
                    center_x = zone['pos'][0] + zone['size'][0] // 2
                    center_y = zone['pos'][1] + zone['size'][1] // 2
                    for i in range(3):
                        y_offset = -15 + i * 15
                        pygame.draw.polygon(screen, (255, 255, 255), [
                            (center_x - 5, center_y + y_offset),
                            (center_x + 5, center_y + y_offset),
                            (center_x, center_y + y_offset - 10)
                        ])
        
        elif self.special_mechanics.get("type") == "sandstorms":
            if self.sandstorm_active:
                # 绘制沙尘暴效果
                for obstacle in self.obstacles:
                    if obstacle.obstacle_type == "sandstorm_generator":
                        # 绘制沙尘暴范围
                        center = obstacle.rect.center
                        for radius in range(50, 200, 30):
                            alpha = int(50 - (radius - 50) * 0.3)
                            if alpha > 0:
                                storm_surface = pygame.Surface((radius * 2, radius * 2))
                                storm_surface.set_alpha(alpha)
                                storm_surface.fill((150, 130, 80))
                                storm_rect = storm_surface.get_rect(center=center)
                                screen.blit(storm_surface, storm_rect)
                        
                        # 绘制沙粒效果
                        for _ in range(30):
                            angle = random.uniform(0, 2 * math.pi)
                            distance = random.uniform(0, 180)
                            x = center[0] + math.cos(angle) * distance
                            y = center[1] + math.sin(angle) * distance
                            if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                                pygame.draw.circle(screen, (200, 180, 120), (int(x), int(y)), 2)
        
        elif self.special_mechanics.get("type") == "defensive_turrets":
            # 绘制炮塔射击线
            for obstacle in self.obstacles:
                if obstacle.obstacle_type == "turret_bunker":
                    # 绘制射程圈
                    pygame.draw.circle(screen, (100, 255, 100, 50), obstacle.rect.center, 150, 2)
        
        elif self.special_mechanics.get("type") == "power_grid":
            # 绘制电力网连接线
            power_stations = [obs for obs in self.obstacles if obs.obstacle_type == "power_station" and obs.active]
            if len(power_stations) >= 2:
                for i in range(len(power_stations)):
                    for j in range(i + 1, len(power_stations)):
                        start_pos = power_stations[i].rect.center
                        end_pos = power_stations[j].rect.center
                        # 绘制电力连接线
                        pygame.draw.line(screen, (100, 100, 255), start_pos, end_pos, 3)
                        # 绘制电流效果
                        mid_x = (start_pos[0] + end_pos[0]) // 2
                        mid_y = (start_pos[1] + end_pos[1]) // 2
                        pygame.draw.circle(screen, (150, 150, 255), (mid_x, mid_y), 5)
        
        # 添加原有的地图特效
        if self.map_name == "desert":
            # 沙漠效果：随机沙粒
            for _ in range(20):
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(0, SCREEN_HEIGHT)
                pygame.draw.circle(screen, (80, 70, 50), (x, y), 1)
        
        elif self.map_name == "urban":
            # 城市效果：路灯
            lamp_positions = [(100, 100), (300, 300), (600, 200), (900, 400)]
            for pos in lamp_positions:
                pygame.draw.circle(screen, (255, 255, 200), pos, 30, 2)
                pygame.draw.circle(screen, (255, 255, 150), pos, 15)

import math 