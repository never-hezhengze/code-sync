import pygame
import math
import random
import os
from settings import *
from weapons import WeaponType


class UI:
    def __init__(self):
        # 游戏状态数据
        self.score = 0
        self.high_score = 0
        self.heal_message = ""
        self.heal_message_time = 0
        self.level_up_message = ""
        self.level_up_message_time = 0
        self.victory_time = 0
        self.victory_animations = []

        # 字体初始化
        self._init_fonts()

        # 资源预加载
        self._preload_resources()

        # 预渲染静态文本
        self._prerender_static_text()

        # 缓存变量
        self._last_ammo_text = ""
        self._ammo_text_surface = None
        self._last_score_text = ""
        self._score_text_surface = None

    def _init_fonts(self):
        """初始化字体"""
        try:
            self.font_large = pygame.font.SysFont('arial', 32, bold=True)
            self.font_medium = pygame.font.SysFont('arial', 24)
            self.font_small = pygame.font.SysFont('arial', 18)
        except Exception:
            # 备用字体
            self.font_large = pygame.font.Font(None, 36)
            self.font_medium = pygame.font.Font(None, 28)
            self.font_small = pygame.font.Font(None, 22)

    def _preload_resources(self):
        """预加载资源"""
        # 敌人图鉴spritesheet
        self.enemy_spritesheet = None
        SPRITESHEET_PATH = os.path.join(
            os.path.dirname(__file__), 'images', 'enemies', 'kenney_roguelike-characters',
            'Spritesheet', 'roguelikeChar_transparent.png')
        if os.path.exists(SPRITESHEET_PATH):
            try:
                self.enemy_spritesheet = pygame.image.load(SPRITESHEET_PATH).convert_alpha()
            except:
                pass

        # 敌人图鉴坐标
        self.sheet_coords = {
            'fast': (6, 2),
            'tank': (0, 1),
            'sniper': (2, 2),
            'bomber': (4, 2),
            'boss': (7, 0),
            'normal': (1, 0),
        }

    def _prerender_static_text(self):
        """预渲染静态文本"""
        self.static_text = {
            'controls': [
                self.font_small.render("WASD/Arrow Keys: Move", True, COLORS['ui_text']),
                self.font_small.render("Mouse: Aim and Shoot", True, COLORS['ui_text']),
                self.font_small.render("R: Reload Ammo", True, COLORS['ui_text']),
                self.font_small.render("Green Cross: Health Pack (+25 HP)", True, COLORS['ui_text']),
                self.font_small.render("ESC: Exit Game", True, COLORS['ui_text'])
            ],
            'weapon_names': {
                WeaponType.PISTOL: self.font_small.render("Weapon: Pistol", True, COLORS['ui_text']),
            },
            'reloading': self.font_small.render("Reloading...", True, COLORS['ui_text']),
            'enemy_types': self.font_small.render("Enemy Types:", True, COLORS['ui_text'])
        }

    def add_score(self, points):
        """增加分数"""
        self.score += points
        if self.score > self.high_score:
            self.high_score = self.score

    def show_heal_message(self, heal_amount):
        """显示治疗消息"""
        self.heal_message = f"+{heal_amount} Health"
        self.heal_message_time = pygame.time.get_ticks()

    def show_level_up_message(self, level, level_name):
        """显示升级消息"""
        self.level_up_message = f"Level {level}: {level_name}"
        self.level_up_message_time = pygame.time.get_ticks()

    def show_victory(self):
        """显示胜利画面"""
        self.victory_time = pygame.time.get_ticks()
        self.victory_animations = []

        # 初始化烟花效果
        for _ in range(15):  # 减少初始粒子数量
            self._add_victory_particle()

    def _add_victory_particle(self):
        """添加胜利粒子效果"""
        self.victory_animations.append({
            'x': random.randint(100, SCREEN_WIDTH - 100),
            'y': random.randint(100, SCREEN_HEIGHT - 100),
            'color': random.choice([COLORS['victory_gold'], COLORS['victory_silver'], COLORS['victory_bronze']]),
            'size': random.randint(3, 6),  # 减小粒子大小
            'life': random.randint(60, 100),
            'max_life': random.randint(60, 100),
            'surface': None  # 预创建surface
        })

    def draw_health_bar(self, screen, player, x, y, width, height):
        """绘制血条"""
        # 背景
        pygame.draw.rect(screen, COLORS['health_bar_bg'], (x, y, width, height))

        # 血量
        health_ratio = player.health / player.max_health
        health_width = int(width * health_ratio)
        pygame.draw.rect(screen, COLORS['health_bar_fg'], (x, y, health_width, height))

        # 边框
        pygame.draw.rect(screen, COLORS['ui_text'], (x, y, width, height), 2)

        # 血量文本 - 使用缓存
        health_text = f"{player.health}/{player.max_health}"
        if not hasattr(self, '_last_health_text') or self._last_health_text != health_text:
            self._last_health_text = health_text
            self._health_text_surface = self.font_small.render(health_text, True, COLORS['ui_text'])

        text_rect = self._health_text_surface.get_rect(center=(x + width // 2, y + height // 2))
        screen.blit(self._health_text_surface, text_rect)

    def draw_ammo_display(self, screen, player, x, y):
        """绘制弹药显示"""
        if player.is_reloading:
            # 重装进度条
            progress = player.get_reload_progress()
            bar_width = 150

            # 背景
            pygame.draw.rect(screen, COLORS['ammo_bar_bg'], (x, y, bar_width, 20))

            # 进度
            progress_width = int(bar_width * progress)
            pygame.draw.rect(screen, COLORS['ammo_bar_fg'], (x, y, progress_width, 20))

            # 边框
            pygame.draw.rect(screen, COLORS['ui_text'], (x, y, bar_width, 20), 2)

            # 使用预渲染的重装文本
            screen.blit(self.static_text['reloading'], (x, y + 25))
        else:
            # 弹药计数 - 使用缓存
            ammo_text = f"Ammo: {player.ammo}/{player.max_ammo}"
            if not hasattr(self, '_last_ammo_text') or self._last_ammo_text != ammo_text:
                self._last_ammo_text = ammo_text
                self._ammo_text_surface = self.font_medium.render(ammo_text, True, COLORS['ui_text'])

            screen.blit(self._ammo_text_surface, (x, y))

            # 弹药条
            bar_width = 150
            bar_height = 10
            ammo_ratio = player.ammo / player.max_ammo

            # 背景
            pygame.draw.rect(screen, COLORS['ammo_bar_bg'], (x, y + 30, bar_width, bar_height))

            # 弹药
            ammo_width = int(bar_width * ammo_ratio)
            color = COLORS['ammo_bar_fg'] if ammo_ratio > 0.3 else (255, 100, 100)
            pygame.draw.rect(screen, color, (x, y + 30, ammo_width, bar_height))

            # 边框
            pygame.draw.rect(screen, COLORS['ui_text'], (x, y + 30, bar_width, bar_height), 1)

        # 武器类型 - 使用预渲染文本
        weapon_text = self.static_text['weapon_names'].get(
            player.current_weapon,
            self.static_text['weapon_names'][WeaponType.PISTOL])
        screen.blit(weapon_text, (x, y + 50))

    def draw_level_info(self, screen, enemies, x, y):
        """绘制关卡信息"""
        level_config = enemies.get_current_level_config()

        # 关卡名称
        level_text = f"Level {enemies.current_level}: {level_config['name']}"
        if not hasattr(self, '_last_level_text') or self._last_level_text != level_text:
            self._last_level_text = level_text
            self._level_text_surface = self.font_medium.render(level_text, True, COLORS['ui_text'])

        screen.blit(self._level_text_surface, (x, y))

        # 敌人数量
        enemies_text = f"Enemies: {len(enemies.group)}"
        if not hasattr(self, '_last_enemies_text') or self._last_enemies_text != enemies_text:
            self._last_enemies_text = enemies_text
            self._enemies_text_surface = self.font_small.render(enemies_text, True, COLORS['ui_text'])

        screen.blit(self._enemies_text_surface, (x, y + 30))

        # 关卡进度
        progress_text = f"Progress: {enemies.enemies_killed_this_level}/{enemies.enemies_needed_for_next_level}"
        if not hasattr(self, '_last_progress_text') or self._last_progress_text != progress_text:
            self._last_progress_text = progress_text
            self._progress_text_surface = self.font_small.render(progress_text, True, COLORS['ui_text'])

        screen.blit(self._progress_text_surface, (x, y + 50))

        # 进度条
        progress = enemies.enemies_killed_this_level / enemies.enemies_needed_for_next_level
        bar_width = 120
        bar_height = 8

        # 背景
        pygame.draw.rect(screen, (100, 100, 100), (x, y + 70, bar_width, bar_height))
        # 进度
        progress_width = int(bar_width * progress)
        pygame.draw.rect(screen, (0, 255, 255), (x, y + 70, progress_width, bar_height))
        # 边框
        pygame.draw.rect(screen, COLORS['ui_text'], (x, y + 70, bar_width, bar_height), 1)

    def draw_enemy_legend(self, screen, enemies, x, y):
        """绘制敌人图鉴"""
        level_config = enemies.get_current_level_config()
        enemy_types = level_config["enemy_types"]

        # 使用预渲染的标题
        screen.blit(self.static_text['enemy_types'], (x, y))

        y_offset = 20
        icon_size = 20

        for i, enemy_type in enumerate(enemy_types):
            icon_x = x + 10
            icon_y = y + y_offset + i * 28
            name = enemy_type.capitalize()

            # 使用spritesheet绘制图标
            if self.enemy_spritesheet and enemy_type in self.sheet_coords:
                sx, sy = self.sheet_coords[enemy_type]
                rect = pygame.Rect(
                    1 + sx * (16 + 1),
                    1 + sy * (16 + 1),
                    16, 16)
                img = self.enemy_spritesheet.subsurface(rect)
                img = pygame.transform.scale(img, (icon_size, icon_size))
                screen.blit(img, (icon_x, icon_y))
            else:
                # 备用方案
                color = COLORS.get(f'enemy_{enemy_type}', (200, 200, 200))
                pygame.draw.rect(screen, color, (icon_x, icon_y, icon_size, icon_size))

            # 绘制名称 - 使用缓存
            name_text = f"{name}"
            if not hasattr(self, f'_last_{enemy_type}_text') or getattr(self, f'_last_{enemy_type}_text') != name_text:
                setattr(self, f'_last_{enemy_type}_text', name_text)
                setattr(self, f'_{enemy_type}_text_surface',
                        self.font_small.render(name_text, True, COLORS['ui_text']))

            screen.blit(getattr(self, f'_{enemy_type}_text_surface'),
                        (icon_x + icon_size + 5, icon_y + 2))

    def draw_minimap(self, screen, player, enemies, health_packs=None):
        """绘制小地图"""
        minimap_size = 150
        minimap_x = SCREEN_WIDTH - minimap_size - 20
        minimap_y = 20

        # 背景
        pygame.draw.rect(screen, (0, 0, 0, 128), (minimap_x, minimap_y, minimap_size, minimap_size))
        pygame.draw.rect(screen, COLORS['ui_text'], (minimap_x, minimap_y, minimap_size, minimap_size), 2)

        # 玩家位置
        player_x = int(minimap_x + (player.rect.centerx / SCREEN_WIDTH) * minimap_size)
        player_y = int(minimap_y + (player.rect.centery / SCREEN_HEIGHT) * minimap_size)
        pygame.draw.circle(screen, COLORS['player'], (player_x, player_y), 3)

        # 敌人位置 - 只绘制屏幕内的敌人
        screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        for enemy in enemies.group:
            if screen_rect.colliderect(enemy.rect):
                enemy_x = int(minimap_x + (enemy.rect.centerx / SCREEN_WIDTH) * minimap_size)
                enemy_y = int(minimap_y + (enemy.rect.centery / SCREEN_HEIGHT) * minimap_size)
                pygame.draw.circle(screen, COLORS['enemy'], (enemy_x, enemy_y), 2)

        # 血包位置
        if health_packs:
            for health_pack in health_packs.group:
                if screen_rect.colliderect(health_pack.rect):
                    pack_x = int(minimap_x + (health_pack.rect.centerx / SCREEN_WIDTH) * minimap_size)
                    pack_y = int(minimap_y + (health_pack.rect.centery / SCREEN_HEIGHT) * minimap_size)
                    pygame.draw.circle(screen, COLORS['health_pack'], (pack_x, pack_y), 2)

    def draw_game_over(self, screen):
        """绘制游戏结束画面"""
        # 半透明背景
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # 游戏结束文本
        game_over_text = self.font_large.render("GAME OVER", True, (255, 0, 0))
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        screen.blit(game_over_text, game_over_rect)

        # 分数
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, COLORS['ui_text'])
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(score_text, score_rect)

        # 最高分
        high_score_text = self.font_medium.render(f"High Score: {self.high_score}", True, COLORS['ui_text'])
        high_score_rect = high_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(high_score_text, high_score_rect)

        # 重启提示
        restart_text = self.font_small.render("Press R to Restart | Press ESC to Map Select", True, COLORS['ui_text'])
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        screen.blit(restart_text, restart_rect)

    def draw_victory_screen(self, screen, player):
        """绘制胜利画面"""
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.victory_time

        # 半透明背景
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 50))  # 深蓝色背景
        screen.blit(overlay, (0, 0))

        # 更新和绘制动画
        self.update_victory_animations()
        self.draw_victory_animations(screen)

        # 主标题 - 带动画效果
        title_scale = min(1.0, elapsed / 1000.0)  # 1秒内缩放到正常大小
        if title_scale > 0:
            title_text = self.font_large.render("*** VICTORY! ***", True, COLORS['victory_gold'])
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))

            # 缩放效果
            if title_scale < 1.0:
                scaled_width = int(title_rect.width * title_scale)
                scaled_height = int(title_rect.height * title_scale)
                title_text = pygame.transform.scale(title_text, (scaled_width, scaled_height))
                title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))

            screen.blit(title_text, title_rect)

        # 副标题
        if elapsed > 1000:
            subtitle_text = self.font_medium.render("You have conquered all levels!", True, COLORS['victory_silver'])
            subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
            screen.blit(subtitle_text, subtitle_rect)

        # 统计数据
        if elapsed > 2000:
            stats_y = SCREEN_HEIGHT // 2 - 50

            # 最终分数
            final_score = self.score + VICTORY_BONUS_SCORE
            score_text = self.font_medium.render(f"Final Score: {final_score}", True, COLORS['victory_gold'])
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y))
            screen.blit(score_text, score_rect)

            # 胜利奖励
            bonus_text = self.font_small.render(f"Victory Bonus: +{VICTORY_BONUS_SCORE}", True,
                                                COLORS['victory_bronze'])
            bonus_rect = bonus_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y + 30))
            screen.blit(bonus_text, bonus_rect)

            # 玩家状态
            health_text = self.font_small.render(f"Remaining Health: {player.health}/{player.max_health}", True,
                                                 COLORS['health_bar_fg'])
            health_rect = health_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y + 60))
            screen.blit(health_text, health_rect)

        # 成就徽章
        if elapsed > 3000:
            self.draw_achievement_badges(screen, player)

        # 操作提示
        if elapsed > 4000:
            # 闪烁效果
            if (current_time // 500) % 2:
                restart_text = self.font_medium.render("Press R to Start New Challenge", True, COLORS['ui_text'])
                restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120))
                screen.blit(restart_text, restart_rect)

                exit_text = self.font_small.render("Press ESC to Map Select", True, COLORS['ui_text'])
                exit_rect = exit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150))
                screen.blit(exit_text, exit_rect)

    def update_victory_animations(self):
        """更新胜利动画"""
        current_time = pygame.time.get_ticks()

        # 减少随机添加的频率
        if random.random() < 0.05 and current_time - self.victory_time < 10000:
            self._add_victory_particle()

        # 更新现有动画
        for anim in self.victory_animations[:]:
            anim['life'] -= 1
            if anim['life'] <= 0:
                self.victory_animations.remove(anim)
            else:
                # 减少随机移动幅度
                anim['x'] += random.randint(-1, 1)
                anim['y'] += random.randint(-1, 1)

                # 预渲染粒子效果
                if anim['surface'] is None:
                    size = anim['size']
                    anim['surface'] = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(anim['surface'], anim['color'], (size, size), size)

    def draw_victory_animations(self, screen):
        """绘制胜利动画效果"""
        for anim in self.victory_animations:
            alpha = int(255 * (anim['life'] / anim['max_life']))
            anim['surface'].set_alpha(alpha)
            screen.blit(anim['surface'], (anim['x'] - anim['size'], anim['y'] - anim['size']))

    def draw_achievement_badges(self, screen, player):
        """绘制成就徽章"""
        badge_y = SCREEN_HEIGHT // 2 + 20
        badge_size = 40
        badge_spacing = 80

        badges = []

        # 生存徽章
        if player.health > 50:
            badges.append(("S", "Survival Master", COLORS['victory_gold']))
        elif player.health > 20:
            badges.append(("S", "Tough Warrior", COLORS['victory_silver']))
        else:
            badges.append(("S", "Survivor", COLORS['victory_bronze']))

        # 分数徽章
        if self.score > 2000:
            badges.append(("A", "Score King", COLORS['victory_gold']))
        elif self.score > 1000:
            badges.append(("A", "High Scorer", COLORS['victory_silver']))
        else:
            badges.append(("A", "Rookie", COLORS['victory_bronze']))

        # 完美胜利徽章
        if player.health == player.max_health:
            badges.append(("P", "Perfect Victory", COLORS['victory_gold']))

        # 绘制徽章
        start_x = SCREEN_WIDTH // 2 - (len(badges) * badge_spacing) // 2

        for i, (icon, name, color) in enumerate(badges):
            badge_x = start_x + i * badge_spacing

            # 徽章背景
            pygame.draw.circle(screen, color, (badge_x, badge_y), badge_size // 2, 3)

            # 徽章图标
            icon_text = self.font_medium.render(icon, True, color)
            icon_rect = icon_text.get_rect(center=(badge_x, badge_y))
            screen.blit(icon_text, icon_rect)

            # 徽章名称
            name_text = self.font_small.render(name, True, color)
            name_rect = name_text.get_rect(center=(badge_x, badge_y + 30))
            screen.blit(name_text, name_rect)

    def draw_controls_help(self, screen):
        """绘制控制帮助"""
        help_y = SCREEN_HEIGHT - 120

        # 使用预渲染的控制文本
        for i, control_text in enumerate(self.static_text['controls']):
            screen.blit(control_text, (20, help_y + i * 20))

    def draw_heal_message(self, screen):
        """绘制治疗消息"""
        if self.heal_message:
            current_time = pygame.time.get_ticks()
            if current_time - self.heal_message_time < 2000:  # 显示2秒
                # 计算透明度(淡出效果)
                elapsed = current_time - self.heal_message_time
                alpha = max(0, 255 - int(elapsed * 255 / 2000))

                # 创建带透明度的文本
                heal_text = self.font_medium.render(self.heal_message, True, COLORS['health_pack'])
                heal_text.set_alpha(alpha)

                # 显示在屏幕中央上方
                text_rect = heal_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
                screen.blit(heal_text, text_rect)
            else:
                self.heal_message = ""

    def draw_level_up_message(self, screen):
        """绘制升级消息"""
        if self.level_up_message:
            current_time = pygame.time.get_ticks()
            if current_time - self.level_up_message_time < 3000:  # 显示3秒
                # 计算透明度和缩放效果
                elapsed = current_time - self.level_up_message_time
                alpha = max(0, 255 - int(elapsed * 255 / 3000))

                # 创建大文本
                level_text = self.font_large.render(self.level_up_message, True, (0, 255, 255))
                level_text.set_alpha(alpha)

                # 显示在屏幕中央
                text_rect = level_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
                screen.blit(level_text, text_rect)

                # 添加"LEVEL UP!"文本
                upgrade_text = self.font_medium.render("LEVEL UP!", True, (255, 255, 0))
                upgrade_text.set_alpha(alpha)
                upgrade_rect = upgrade_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
                screen.blit(upgrade_text, upgrade_rect)
            else:
                self.level_up_message = ""

    def draw_map_mechanics_info(self, screen, game_map, x, y):
        """绘制地图特殊机制信息"""
        mechanics = game_map.special_mechanics
        if not mechanics:
            return

        # 标题
        title_text = self.font_small.render("Map Effects:", True, COLORS['ui_text'])
        screen.blit(title_text, (x, y))

        # 描述
        desc_text = self.font_small.render(mechanics.get("description", ""), True, (180, 180, 180))
        screen.blit(desc_text, (x, y + 20))

        # 状态指示器
        status_y = y + 45

        if mechanics.get("type") == "speed_boost":
            boost_count = len(game_map.speed_boost_zones)
            status_text = f"Speed Zones: {boost_count}"
            color = (0, 255, 255) if boost_count > 0 else (100, 100, 100)

        elif mechanics.get("type") == "sandstorms":
            status_text = f"Sandstorm: {'Active' if game_map.sandstorm_active else 'Inactive'}"
            color = (255, 165, 0) if game_map.sandstorm_active else (100, 100, 100)

        elif mechanics.get("type") == "defensive_turrets":
            turret_count = sum(1 for obs in game_map.obstacles if obs.obstacle_type == "turret_bunker")
            status_text = f"Turrets: {turret_count} Active"
            color = (0, 255, 0)

        elif mechanics.get("type") == "destructible_walls":
            wall_count = sum(1 for obs in game_map.obstacles
                             if obs.obstacle_type == "destructible_wall" and not obs.destroyed)
            status_text = f"Walls: {wall_count} Remaining"
            color = (150, 150, 150)

        else:
            status_text = "Unknown Effect"
            color = (100, 100, 100)

        status_surface = self.font_small.render(status_text, True, color)
        screen.blit(status_surface, (x, status_y))

    def draw_crosshair(self, screen, visibility=1.0):
        """绘制准星"""
        mouse_pos = pygame.mouse.get_pos()
        crosshair_size = int(10 * visibility)
        alpha = int(255 * visibility)

        if crosshair_size > 2:
            # 十字准星
            color = (*COLORS['ui_text'], alpha) if alpha < 255 else COLORS['ui_text']

            pygame.draw.line(screen, color,
                             (mouse_pos[0] - crosshair_size, mouse_pos[1]),
                             (mouse_pos[0] + crosshair_size, mouse_pos[1]), 2)
            pygame.draw.line(screen, color,
                             (mouse_pos[0], mouse_pos[1] - crosshair_size),
                             (mouse_pos[0], mouse_pos[1] + crosshair_size), 2)

            # 中心点
            pygame.draw.circle(screen, color, mouse_pos, 2)

    def draw(self, screen, player, enemies=None, health_packs=None, game_map=None, game_over=False, victory=False):
        """主绘制方法"""
        if victory:
            self.draw_victory_screen(screen, player)
            return

        if game_over:
            self.draw_game_over(screen)
            return

        # 分数显示 - 使用缓存
        score_text = f"Score: {self.score}"
        if not hasattr(self, '_last_score_text') or self._last_score_text != score_text:
            self._last_score_text = score_text
            self._score_text_surface = self.font_medium.render(score_text, True, COLORS['ui_text'])
        screen.blit(self._score_text_surface, (20, 20))

        # 血条
        self.draw_health_bar(screen, player, 20, 60, 200, 25)

        # 弹药显示
        self.draw_ammo_display(screen, player, 20, 100)

        # 关卡信息
        if enemies:
            self.draw_level_info(screen, enemies, 20, 170)
            # 敌人图鉴
            self.draw_enemy_legend(screen, enemies, 20, 260)
            # 小地图
            self.draw_minimap(screen, player, enemies, health_packs)

        # 地图特殊机制信息
        if game_map:
            self.draw_map_mechanics_info(screen, game_map, 20, 380)

        # 准星(带沙尘暴效果)
        if game_map:
            _, visibility = game_map.get_sandstorm_effect(player.rect.center)
            self.draw_crosshair(screen, visibility)
        else:
            self.draw_crosshair(screen)

        # 控制帮助
        self.draw_controls_help(screen)

        # 治疗消息
        self.draw_heal_message(screen)

        # 升级消息
        self.draw_level_up_message(screen)
