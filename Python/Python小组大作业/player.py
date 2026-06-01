'''
本模块实现了一个2D射击游戏中的玩家角色，包含移动、射击、弹药管理等功能。继承自pygame.sprite.Sprite
----------
需要以下的文件
1. settings.py      游戏配置常量（必须包含以下常量：
                    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_SIZE,
                    PLAYER_SPEED, PLAYER_MAX_HEALTH, MAX_AMMO,
                    FIRE_RATE, RELOAD_TIME, HEALTH_REGEN_RATE）
2. weapons.py         # 需实现BulletGroup类及其add_bullet方法
----------
1. 当前使用纯色方块作为角色图像，建议替换为实际素材
   替换时需修改self.image
2. 主循环需以60FPS运行以保证时间计算的准确性
'''
import pygame
from pygame.math import Vector2     # 二维向量处理坐标和方向
from settings import *
import math                      # 三角函数计算

class Player(pygame.sprite.Sprite):
    '''pygame中有sprite(精灵)这一模块，
    是 Pygame 中所有可见游戏对象（比如角色、子弹）的基类，具有图像和位置属性。
    '''
    def __init__(self): #创建Player对象时，自动调用，所有的Player对象都有__init__之中的属性
        super().__init__()  #继承父类(pygame.sprite.Sprite),也就是直接使用其中的属性
        # 角色外观初始化 ------------------------------------------------------
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))   #创建一个 32x32 像素的空白图像
        self.image.fill(COLORS['player'])
        '''
        上一行代码使用的绿色方块，后续可修改这个代码，换成图片
        '''

        self.rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)) #获取图像（角色）的矩形，将中心点设置为屏幕中心
        # 基础属性 ------------------------------------------------------------
        self.speed = PLAYER_SPEED           # 角色速度
        self.health = PLAYER_MAX_HEALTH     # 角色健康值
        self.max_health = PLAYER_MAX_HEALTH # 最大生命值上限
        self.ammo = MAX_AMMO                # 角色的弹药
        self.max_ammo = MAX_AMMO            # 弹药容量上限
        self.current_weapon = "pistol"      # 当前武器类型
        # 射击系统 ------------------------------------------------------------
        self.last_shot = 0                  # 最后射击时间戳（毫秒）
        self.fire_rate = FIRE_RATE          # 射速（帧/发）

        # 换弹系统 ------------------------------------------------------------
        self.is_reloading = False           # 换弹状态标志
        self.reload_start_time = 0          # 换弹开始时间
        self.reload_time = RELOAD_TIME      # 换弹持续时间（帧）

        # 伤害系统 ------------------------------------------------------------
        self.last_damage_time = 0           # 最后受伤时间
        self.damage_cooldown = ENEMY_CONTACT_DAMAGE_COOLDOWN     # 无敌时间（帧）
        self.invulnerable = False           # 无敌状态标志

        # 血量回复------------------------------------------------------------
        self.last_heal_time = 0             # 最后恢复时间
        self.heal_rate = HEALTH_REGEN_RATE  # 生命恢复间隔（帧）
        # 技能系统 ------------------------------------------------------------
        self.e_pressed_last_frame = False   # E键状态跟踪

    def update(self, bullets,game_map=None):      #每帧被调用的方法，用于更新玩家状态
        """
        每帧状态更新（需在主循环中调用）
        """
        self._handle_movement(game_map)     # 处理玩家移动，在下面
        self._handle_shooting(bullets)      # 处理射击，在下面
        self._handle_skill(bullets)         # 技能处理
        self._handle_reload()               # 换弹进度更新
        self._handle_health_regen()         # 自动生命恢复
        self._update_invulnerability()      # 无敌状态更新

    def _handle_movement(self,game_map=None):
        keys = pygame.key.get_pressed() #获取当前所有键盘按键的状态
        move_dir = Vector2(0, 0)    #创建一个二维向量表示移动方向
        
        # 检测WASD按键
        if keys[pygame.K_w]: 
            move_dir.y -= 1
            print("W pressed")  # 调试信息
        if keys[pygame.K_s]: 
            move_dir.y += 1
            print("S pressed")  # 调试信息
        if keys[pygame.K_a]: 
            move_dir.x -= 1
            print("A pressed")  # 调试信息
        if keys[pygame.K_d]: 
            move_dir.x += 1
            print("D pressed")  # 调试信息

        # 如果有移动输入，打印移动方向
        if move_dir.length() > 0:
            print(f"Moving: {move_dir}")  # 调试信息
            move_dir = move_dir.normalize() #将向量长度变为 1，防止斜向移动更快

        # 计算移动距离
        move_distance = move_dir * self.speed
        print(f"Move distance: {move_distance}")  # 调试信息

        # 保存当前位置
        old_x = self.rect.x
        old_y = self.rect.y

        # 应用移动
        self.rect.x += move_distance.x
        self.rect.y += move_distance.y

        # 检查碰撞
        if game_map and game_map.check_collision(self.rect):
            self.rect.x = old_x
            self.rect.y = old_y
            print("Collision detected")  # 调试信息

        # 确保玩家不会移出屏幕
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # 打印最终位置
        print(f"Final position: {self.rect.center}")  # 调试信息

    def _handle_shooting(self, bullets): #处理射击
        current_time = pygame.time.get_ticks()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        # 射击条件判断：左键按下、有弹药、未换弹、射速冷却
        if (mouse_pressed and
                self.ammo > 0 and
                not self.is_reloading and
                current_time - self.last_shot >= self.fire_rate * (1000 / FPS)):

            bullets.add_bullet(self.rect.center, pygame.mouse.get_pos()) #使用了weapons.py里的add_bullet
            self.ammo -= 1
            self.last_shot = current_time

        # 弹药用完自动重装
        if self.ammo == 0:
            self.start_reload() #在下面

    def _handle_skill(self, bullets):
        current_e = pygame.key.get_pressed()[pygame.K_e]

        # 仅在按下E键的瞬间触发（非长按）
        if current_e and not self.e_pressed_last_frame:
            self._fire_circular_bullets(bullets)

        # 更新按键状态记录
        self.e_pressed_last_frame = current_e

    def _fire_circular_bullets(self, bullets):
        directions = 36  # 子弹数量
        bullet_distance = 500  # 子弹目标点距离（像素）

        for i in range(directions):
            angle = math.radians(360 / directions * i)
            direction = Vector2(math.cos(angle), math.sin(angle))
            target_pos = self.rect.center + direction * bullet_distance
            bullets.add_bullet(self.rect.center, target_pos)

    def _handle_reload(self):
        current_time = pygame.time.get_ticks()

        # 检查重装是否完成
        if self.is_reloading:
            if current_time - self.reload_start_time >= self.reload_time * (1000 / FPS):
                self.ammo = self.max_ammo
                self.is_reloading = False

    def _handle_health_regen(self):
        current_time = pygame.time.get_ticks()
        # 满足条件：非满血、恢复间隔到达
        if (self.health < self.max_health and
            current_time - self.last_heal_time >= self.heal_rate * (1000 / FPS)):
            self.health = min(self.max_health, self.health + 5) # 恢复5点
            self.last_heal_time = current_time

    def _update_invulnerability(self):
        current_time = pygame.time.get_ticks()
        # 无敌状态到期检测
        if self.invulnerable and current_time - self.last_damage_time >= self.damage_cooldown * (1000 / FPS):
            self.invulnerable = False

    def start_reload(self):
        """开始装弹"""
        if not self.is_reloading and self.ammo < self.max_ammo:
            self.is_reloading = True
            self.reload_start_time = pygame.time.get_ticks()

    def take_damage(self, damage):
        """受到伤害
            返回：
            bool: 是否实际受到伤害（无敌状态下返回False）
        """
        if not self.invulnerable:
            self.health -= damage
            self.last_damage_time = pygame.time.get_ticks()
            self.invulnerable = True
            return True
        return False

    def get_reload_progress(self):
        """获取换弹进度（0-1）"""
        if not self.is_reloading:
            return 1.0

        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.reload_start_time
        total_time = self.reload_time * (1000 / FPS)
        return min(1.0, elapsed / total_time)

    def draw(self, screen):
        # 受伤时闪烁效果
        if self.invulnerable:
            current_time = pygame.time.get_ticks()
            if (current_time // 100) % 2:  # 每100ms闪烁一次
                return

        screen.blit(self.image, self.rect)