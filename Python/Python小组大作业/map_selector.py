import pygame
import math
from settings import *

class MapSelector:
    def __init__(self):
        self.selected_map = "classic"
        self.map_list = list(MAPS.keys())
        self.current_index = 0
        self.animation_time = 0
        self.preview_selected = False  # 添加预览选中状态
        
        # 显示鼠标光标
        pygame.mouse.set_visible(True)
        
        # 字体
        try:
            self.font_large = pygame.font.SysFont('arial', 36, bold=True)
            self.font_medium = pygame.font.SysFont('arial', 24)
            self.font_small = pygame.font.SysFont('arial', 18)
        except Exception:
            self.font_large = pygame.font.Font(None, 40)
            self.font_medium = pygame.font.Font(None, 28)
            self.font_small = pygame.font.Font(None, 22)
    
    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.current_index = (self.current_index - 1) % len(self.map_list)
                self.selected_map = self.map_list[self.current_index]
                self.preview_selected = False  # 切换地图时取消选中状态
                return "map_changed"
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.current_index = (self.current_index + 1) % len(self.map_list)
                self.selected_map = self.map_list[self.current_index]
                self.preview_selected = False  # 切换地图时取消选中状态
                return "map_changed"
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if self.preview_selected:  # 只有在预览被选中时才返回map_selected
                    return "map_selected"
            elif event.key == pygame.K_ESCAPE:
                return "exit"
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                mouse_pos = pygame.mouse.get_pos()
                # 检查是否点击了地图预览区域
                if self.is_in_preview_area(mouse_pos):
                    if self.preview_selected:  # 如果已经选中，则进入游戏
                        return "map_selected"
                    else:  # 第一次点击，选中预览
                        self.preview_selected = True
                        return "map_changed"
                # 检查是否点击了左右箭头
                elif self.is_in_left_arrow(mouse_pos):
                    self.current_index = (self.current_index - 1) % len(self.map_list)
                    self.selected_map = self.map_list[self.current_index]
                    self.preview_selected = False  # 切换地图时取消选中状态
                    return "map_changed"
                elif self.is_in_right_arrow(mouse_pos):
                    self.current_index = (self.current_index + 1) % len(self.map_list)
                    self.selected_map = self.map_list[self.current_index]
                    self.preview_selected = False  # 切换地图时取消选中状态
                    return "map_changed"
        
        return None
    
    def is_in_preview_area(self, pos):
        """检查是否在预览区域内"""
        preview_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, 200, 400, 250)
        return preview_rect.collidepoint(pos)
    
    def is_in_left_arrow(self, pos):
        """检查是否在左箭头区域"""
        arrow_rect = pygame.Rect(SCREEN_WIDTH//2 - 300, 300, 80, 80)
        return arrow_rect.collidepoint(pos)
    
    def is_in_right_arrow(self, pos):
        """检查是否在右箭头区域"""
        arrow_rect = pygame.Rect(SCREEN_WIDTH//2 + 220, 300, 80, 80)
        return arrow_rect.collidepoint(pos)
    
    def update(self):
        """更新动画"""
        self.animation_time += 1
    
    def draw_map_preview(self, screen, map_name, x, y, width, height):
        """绘制地图预览"""
        map_config = MAPS[map_name]
        
        # 预览背景
        preview_surface = pygame.Surface((width, height))
        preview_surface.fill(map_config["bg_color"])
        
        # 缩放比例
        scale_x = width / SCREEN_WIDTH
        scale_y = height / SCREEN_HEIGHT
        
        # 绘制障碍物预览
        for obstacle_data in map_config["obstacles"]:
            obs_x = int(obstacle_data["pos"][0] * scale_x)
            obs_y = int(obstacle_data["pos"][1] * scale_y)
            obs_w = int(obstacle_data["size"][0] * scale_x)
            obs_h = int(obstacle_data["size"][1] * scale_y)
            
            # 根据障碍物类型选择颜色
            if obstacle_data["type"] == "wall":
                color = (100, 100, 100)
            elif obstacle_data["type"] == "fortress":
                color = (80, 60, 40)
            elif obstacle_data["type"] == "bunker":
                color = (60, 60, 60)
            elif obstacle_data["type"] == "rock":
                color = (90, 80, 70)
            elif obstacle_data["type"] == "building":
                color = (60, 60, 80)
            else:
                color = (128, 128, 128)
            
            pygame.draw.rect(preview_surface, color, (obs_x, obs_y, obs_w, obs_h))
        
        # 添加边框
        if self.preview_selected:
            # 选中状态：黄色边框
            pygame.draw.rect(preview_surface, (255, 255, 0), (0, 0, width, height), 4)
            # 添加选中提示
            select_text = self.font_small.render("Selected - Press Enter", True, (255, 255, 0))
            text_rect = select_text.get_rect(center=(width//2, height - 20))
            preview_surface.blit(select_text, text_rect)
        else:
            # 未选中状态：白色边框
            pygame.draw.rect(preview_surface, (255, 255, 255), (0, 0, width, height), 2)
        
        screen.blit(preview_surface, (x, y))
    
    def draw(self, screen):
        """绘制地图选择界面"""
        # 背景渐变
        for y in range(SCREEN_HEIGHT):
            color_intensity = int(20 + 10 * math.sin(y * 0.01 + self.animation_time * 0.05))
            color = (color_intensity, color_intensity, color_intensity + 10)
            pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))
        
        # 标题
        title_text = self.font_large.render("SELECT MAP", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 80))
        screen.blit(title_text, title_rect)
        
        # 副标题
        subtitle_text = self.font_medium.render("Choose your battlefield", True, (200, 200, 200))
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH//2, 120))
        screen.blit(subtitle_text, subtitle_rect)
        
        # 当前地图信息
        current_map = MAPS[self.selected_map]
        
        # 地图名称
        map_name_text = self.font_large.render(current_map["name"], True, (255, 215, 0))
        map_name_rect = map_name_text.get_rect(center=(SCREEN_WIDTH//2, 170))
        screen.blit(map_name_text, map_name_rect)
        
        # 地图描述
        desc_text = self.font_small.render(current_map["description"], True, (180, 180, 180))
        desc_rect = desc_text.get_rect(center=(SCREEN_WIDTH//2, 480))
        screen.blit(desc_text, desc_rect)
        
        # 地图预览
        preview_x = SCREEN_WIDTH//2 - 200
        preview_y = 200
        preview_width = 400
        preview_height = 250
        
        self.draw_map_preview(screen, self.selected_map, preview_x, preview_y, preview_width, preview_height)
        
        # 左右箭头
        arrow_y = 300
        mouse_pos = pygame.mouse.get_pos()
        
        # 左箭头
        left_arrow_x = SCREEN_WIDTH//2 - 300
        left_points = [
            (left_arrow_x + 40, arrow_y + 10),
            (left_arrow_x + 10, arrow_y + 25),
            (left_arrow_x + 40, arrow_y + 40)
        ]
        if self.is_in_left_arrow(mouse_pos):
            pygame.draw.polygon(screen, (255, 255, 100), left_points)
            pygame.draw.polygon(screen, (255, 255, 255), left_points, 2)
        else:
            pygame.draw.polygon(screen, (255, 255, 255), left_points)
        
        # 右箭头
        right_arrow_x = SCREEN_WIDTH//2 + 250
        right_points = [
            (right_arrow_x + 10, arrow_y + 10),
            (right_arrow_x + 40, arrow_y + 25),
            (right_arrow_x + 10, arrow_y + 40)
        ]
        if self.is_in_right_arrow(mouse_pos):
            pygame.draw.polygon(screen, (255, 255, 100), right_points)
            pygame.draw.polygon(screen, (255, 255, 255), right_points, 2)
        else:
            pygame.draw.polygon(screen, (255, 255, 255), right_points)
        
        # 地图指示器
        indicator_y = 520
        indicator_spacing = 30
        total_width = len(self.map_list) * indicator_spacing
        start_x = SCREEN_WIDTH//2 - total_width//2
        
        for i, map_key in enumerate(self.map_list):
            x = start_x + i * indicator_spacing
            if i == self.current_index:
                # 当前选中的地图
                pygame.draw.circle(screen, (255, 215, 0), (x, indicator_y), 8)
                pygame.draw.circle(screen, (255, 255, 255), (x, indicator_y), 8, 2)
            else:
                # 其他地图
                pygame.draw.circle(screen, (100, 100, 100), (x, indicator_y), 6)
                pygame.draw.circle(screen, (150, 150, 150), (x, indicator_y), 6, 1)
        
        # 控制提示
        controls = [
            "A/D or Arrow Keys: Switch Maps",
            "Click Arrows or Preview: Select Map",
            "Enter/Space: Confirm Selection",
            "ESC: Exit"
        ]
        
        for i, control in enumerate(controls):
            control_text = self.font_small.render(control, True, (150, 150, 150))
            control_rect = control_text.get_rect(center=(SCREEN_WIDTH//2, 580 + i * 25))
            screen.blit(control_text, control_rect)
        
        # 地图统计信息
        stats_y = 460
        obstacle_count = len(current_map["obstacles"])
        stats_text = f"Obstacles: {obstacle_count} | Spawn Type: {current_map['spawn_zones'].replace('_', ' ').title()}"
        stats_surface = self.font_small.render(stats_text, True, (160, 160, 160))
        stats_rect = stats_surface.get_rect(center=(SCREEN_WIDTH//2, stats_y))
        screen.blit(stats_surface, stats_rect) 