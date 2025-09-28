import pygame
import random
import math
from pygame import Vector2
import settings

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, enemy_type="normal"):
        super().__init__()
        self.enemy_type = enemy_type
        self.setup_enemy_stats()
        
        # 创建敌人外观
        self.create_enemy_appearance()
        self.rect = self.image.get_rect(center=pos)
        
        self.max_health = self.health
        self.last_damage_time = 0
        self.last_attack_time = 0
        
        # 添加路径记忆系统
        self.stuck_timer = 0
        self.last_position = pos
        self.bad_directions = set()  # 记录导致卡住的方向
        self.path_memory = []  # 记录最近的位置
        self.path_memory_size = 10  # 记忆最近10个位置
        self.stuck_threshold = 30  # 30帧没有移动就认为被卡住
        
        # 沿墙走系统
        self.wall_following = False  # 是否正在沿墙走
        self.wall_direction = None  # 沿墙走的方向
        self.wall_follow_timer = 0  # 沿墙走计时器
        self.wall_follow_max_time = 60  # 最大沿墙走时间
        self.wall_memory = []  # 记录最近的墙壁位置
        self.wall_memory_size = 5  # 记忆最近5个墙壁位置
        self.safe_distance = 50  # 安全距离，超过这个距离才考虑改变方向
        self.last_wall_position = None  # 最后遇到的墙壁位置

    def setup_enemy_stats(self):
        """根据敌人类型设置属性"""
        if self.enemy_type == "fast":
            self.speed = settings.ENEMY_SPEED * 1.8
            self.health = 1
            self.size = 24
            self.color = settings.COLORS['enemy_fast']
            self.score_value = 15
            self.attack_damage = 8
        elif self.enemy_type == "tank":
            self.speed = settings.ENEMY_SPEED * 0.6
            self.health = 5
            self.size = 44
            self.color = settings.COLORS['enemy_tank']
            self.score_value = 30
            self.attack_damage = 15
        else:  # normal
            self.speed = settings.ENEMY_SPEED
            self.health = settings.ENEMY_HEALTH
            self.size = settings.ENEMY_SIZE
            self.color = settings.COLORS['enemy_normal']
            self.score_value = settings.SCORE_PER_KILL
            self.attack_damage = 10

    def create_enemy_appearance(self):
        """创建敌人的独特外观"""
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(self.color)
        
        if self.enemy_type == "fast":
            # 快速敌人：三角形形状
            points = [
                (self.size // 2, 2),
                (2, self.size - 2),
                (self.size - 2, self.size - 2)
            ]
            pygame.draw.polygon(self.image, self.color, points)
            # 添加速度线条
            for i in range(3):
                y = 6 + i * 6
                pygame.draw.line(self.image, (255, 255, 255), (4, y), (self.size - 4, y), 1)
                
        elif self.enemy_type == "tank":
            # 坦克敌人：厚重的方形带装甲线条
            pygame.draw.rect(self.image, self.color, (0, 0, self.size, self.size))
            # 装甲线条
            for i in range(0, self.size, 8):
                pygame.draw.line(self.image, (200, 200, 200), (i, 0), (i, self.size), 2)
                pygame.draw.line(self.image, (200, 200, 200), (0, i), (self.size, i), 2)
            # 中心炮塔
            center = self.size // 2
            pygame.draw.circle(self.image, (100, 100, 100), (center, center), 8)

    def take_damage(self, damage):
        """受到伤害"""
        self.health -= damage
        self.last_damage_time = pygame.time.get_ticks()
        
        # 受伤闪烁效果
        if self.health > 0:
            self.image.fill((255, 255, 255))  # 白色闪烁
            # 重新绘制外观（下一帧会恢复）
        
        return self.health <= 0

    def update(self, player, game_map=None):
        # 保存地图引用用于碰撞检测
        self.game_map = game_map
        
        # 恢复正常外观
        current_time = pygame.time.get_ticks()
        if current_time - self.last_damage_time > 100:
            self.create_enemy_appearance()
        
        # 应用地图效果
        speed_modifier = 1.0
        if game_map:
            # 沙尘暴效果
            if game_map.special_mechanics.get("type") == "sandstorms":
                storm_speed_modifier, _ = game_map.get_sandstorm_effect(self.rect.center)
                speed_modifier *= storm_speed_modifier
        
        # 根据敌人类型执行不同的行为
        self.normal_movement(player, speed_modifier)
    
    def try_move(self, movement_vector):
        """尝试移动，如果碰撞则尝试其他方向"""
        if not hasattr(self, 'game_map') or not self.game_map:
            # 如果没有地图，直接移动
            self.rect.center += movement_vector
            return
        
        # 保存当前位置
        old_center = self.rect.center
        
        # 检查是否被卡住
        if self.rect.center == self.last_position:
            self.stuck_timer += 1
        else:
            self.stuck_timer = 0
            # 更新路径记忆
            self.path_memory.append(self.rect.center)
            if len(self.path_memory) > self.path_memory_size:
                self.path_memory.pop(0)
        
        # 如果被卡住，开始沿墙走
        if self.stuck_timer > self.stuck_threshold:
            if not self.wall_following:
                self.start_wall_following(movement_vector)
            self.stuck_timer = 0
        
        # 如果正在沿墙走
        if self.wall_following:
            return self.wall_follow_move(old_center, movement_vector)
        
        # 计算到目标的方向
        target_direction = Vector2(movement_vector).normalize()
        
        # 尝试主要方向
        self.rect.center += movement_vector
        if not self.game_map.check_collision(self.rect):
            # 检查是否在安全距离内
            if self.last_wall_position:
                distance_to_wall = Vector2(self.rect.center).distance_to(Vector2(self.last_wall_position))
                if distance_to_wall < self.safe_distance:
                    # 如果太靠近墙壁，继续沿墙走
                    self.rect.center = old_center
                    self.start_wall_following(movement_vector)
                    return self.wall_follow_move(old_center, movement_vector)
            
            self.last_position = self.rect.center
            return  # 如果主要方向可行，直接移动
        
        # 如果主要方向不可行，开始沿墙走
        self.rect.center = old_center  # 恢复位置
        self.last_wall_position = self.rect.center  # 记录墙壁位置
        self.wall_memory.append(self.rect.center)
        if len(self.wall_memory) > self.wall_memory_size:
            self.wall_memory.pop(0)
        
        self.start_wall_following(movement_vector)
        return self.wall_follow_move(old_center, movement_vector)

    def start_wall_following(self, movement_vector):
        """开始沿墙走"""
        self.wall_following = True
        self.wall_follow_timer = 0
        
        # 确定初始沿墙方向（顺时针或逆时针）
        # 根据目标方向选择最合适的初始方向
        target_direction = Vector2(movement_vector).normalize()
        
        # 尝试四个基本方向
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        best_direction = None
        best_angle = float('inf')
        
        for dx, dy in directions:
            test_vector = Vector2(dx, dy)
            angle = abs(test_vector.angle_to(target_direction))
            if angle < best_angle:
                best_angle = angle
                best_direction = (dx, dy)
        
        self.wall_direction = best_direction

    def wall_follow_move(self, old_center, target_vector):
        """执行沿墙走移动"""
        self.wall_follow_timer += 1
        
        # 如果沿墙走时间过长，重置状态
        if self.wall_follow_timer > self.wall_follow_max_time:
            self.wall_following = False
            self.rect.center = old_center
            return
        
        # 尝试当前方向
        dx, dy = self.wall_direction
        test_vector = Vector2(dx, dy) * self.speed
        self.rect.center = old_center + test_vector
        
        if not self.game_map.check_collision(self.rect):
            # 检查是否可以安全地回到目标方向
            target_direction = Vector2(target_vector).normalize()
            
            # 检查多个点以确保完全脱离墙壁
            check_points = [
                self.rect.center,  # 中心点
                (self.rect.centerx + self.size//2, self.rect.centery),  # 右边缘
                (self.rect.centerx - self.size//2, self.rect.centery),  # 左边缘
                (self.rect.centerx, self.rect.centery + self.size//2),  # 下边缘
                (self.rect.centerx, self.rect.centery - self.size//2),  # 上边缘
            ]
            
            # 检查所有点是否都可以安全移动
            can_move_safely = True
            for point in check_points:
                test_target = Vector2(point) + target_direction * self.speed
                test_rect = pygame.Rect(
                    test_target.x - self.size//2,
                    test_target.y - self.size//2,
                    self.size,
                    self.size
                )
                if self.game_map.check_collision(test_rect):
                    can_move_safely = False
                    break
            
            # 如果所有点都可以安全移动且距离墙壁足够远，结束沿墙走
            if can_move_safely:
                if self.last_wall_position:
                    distance_to_wall = Vector2(self.rect.center).distance_to(Vector2(self.last_wall_position))
                    if distance_to_wall > self.safe_distance:
                        self.wall_following = False
                        self.last_wall_position = None
                        self.wall_memory.clear()
            
            self.last_position = self.rect.center
            return
        
        # 如果当前方向不可行，尝试顺时针旋转
        self.rect.center = old_center
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        current_index = directions.index(self.wall_direction)
        next_index = (current_index + 1) % 4
        self.wall_direction = directions[next_index]
        
        # 尝试新方向
        dx, dy = self.wall_direction
        test_vector = Vector2(dx, dy) * self.speed
        self.rect.center = old_center + test_vector
        
        if not self.game_map.check_collision(self.rect):
            self.last_position = self.rect.center
            return
        
        # 如果新方向也不可行，重置状态
        self.wall_following = False
        self.rect.center = old_center
        self.last_position = old_center

    def normal_movement(self, player, speed_modifier=1.0):
        """普通移动行为"""
        direction = Vector2(player.rect.center) - Vector2(self.rect.center)
        distance = direction.length()
        
        if distance > 0:
            direction = direction.normalize()
            
            # 添加一些随机移动
            if random.random() < 0.1:
                random_angle = random.uniform(-0.5, 0.5)
                direction = direction.rotate(math.degrees(random_angle))
            
            # 尝试移动并检查碰撞
            self.try_move(direction * self.speed * speed_modifier)

class EnemyGroup:
    def __init__(self, game_map=None):
        self.group = pygame.sprite.Group()
        self.spawn_timer = 0
        self.current_level = 1
        self.enemies_killed_this_level = 0
        self.enemies_needed_for_next_level = 10
        self.game_map = game_map

    def get_spawn_position(self):
        """获取生成位置"""
        if self.game_map:
            return self.game_map.get_spawn_position()
        else:
            # 默认边缘生成
            side = random.randint(0, 3)
            if side == 0:  # 上边
                return (random.randint(0, settings.SCREEN_WIDTH), -50)
            elif side == 1:  # 右边
                return (settings.SCREEN_WIDTH + 50, random.randint(0, settings.SCREEN_HEIGHT))
            elif side == 2:  # 下边
                return (random.randint(0, settings.SCREEN_WIDTH), settings.SCREEN_HEIGHT + 50)
            else:  # 左边
                return (-50, random.randint(0, settings.SCREEN_HEIGHT))

    def get_current_level_config(self):
        """获取当前关卡配置"""
        if self.current_level in settings.LEVELS:
            return settings.LEVELS[self.current_level]
        else:
            # 无尽模式
            return settings.LEVELS[10]

    def spawn_enemies(self, num):
        level_config = self.get_current_level_config()
        
        for _ in range(num):
            # 尝试多次找到有效的生成位置
            for attempt in range(10):
                pos = self.get_spawn_position()
                
                # 根据关卡配置选择敌人类型
                enemy_type = random.choice(level_config["enemy_types"])
                
                # 创建临时敌人来检查碰撞
                temp_enemy = Enemy(pos, enemy_type)
                
                # 检查是否与障碍物碰撞
                if not self.game_map or not self.game_map.check_collision(temp_enemy.rect):
                    self.group.add(temp_enemy)
                    break  # 找到有效位置，退出尝试循环
                # 如果碰撞，继续尝试下一个位置

    def update(self, player, game_map=None):
        self.group.update(player, game_map)
        
        level_config = self.get_current_level_config()
        
        # 动态生成敌人
        self.spawn_timer += 1
        if (self.spawn_timer >= level_config["spawn_rate"] and 
            len(self.group) < level_config["max_enemies"]):
            self.spawn_enemies(1)
            self.spawn_timer = 0

    def enemy_killed(self):
        """敌人被击杀时调用"""
        self.enemies_killed_this_level += 1
        
        # 检查是否可以进入下一关
        if self.enemies_killed_this_level >= self.enemies_needed_for_next_level:
            result = self.advance_to_next_level()
            if result == "victory":
                return "victory"  # 返回通关标志
            elif result:
                return True  # 返回True表示升级了
        return False

    def advance_to_next_level(self):
        """进入下一关"""
        self.current_level += 1
        self.enemies_killed_this_level = 0
        self.enemies_needed_for_next_level += 5  # 每关需要击杀的敌人数量增加
        
        # 检查是否通关
        if self.current_level > settings.MAX_LEVEL:
            return "victory"  # 返回通关标志
        return True  # 返回True表示升级了

    def draw(self, screen):
        self.group.draw(screen)
        
        # 绘制敌人血条和特殊标识
        for enemy in self.group:
            self.draw_enemy_ui(screen, enemy)

    def draw_enemy_ui(self, screen, enemy):
        """绘制敌人的UI元素"""
        # 血条
        if enemy.health < enemy.max_health:
            bar_width = enemy.size
            bar_height = 4
            bar_x = enemy.rect.centerx - bar_width // 2
            bar_y = enemy.rect.top - 8
            
            # 背景
            pygame.draw.rect(screen, (255, 0, 0), 
                           (bar_x, bar_y, bar_width, bar_height))
            # 血量
            health_width = int(bar_width * (enemy.health / enemy.max_health))
            pygame.draw.rect(screen, (0, 255, 0), 
                           (bar_x, bar_y, health_width, bar_height))