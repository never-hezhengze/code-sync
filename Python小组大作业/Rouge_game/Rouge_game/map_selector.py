import pygame
import math
from settings import *

class MapSelector:
    """
    地图选择器类，用于在游戏开始前选择游戏地图
    提供地图预览、切换和选择功能，支持键盘和鼠标操作
    """
    def __init__(self):
        # 初始化地图选择器的基本属性
        self.selected_map = "classic"  # 当前选中的地图
        self.map_list = list(MAPS.keys())  # 可用地图列表
        self.current_index = 0  # 当前地图在列表中的索引
        self.animation_time = 0  # 用于动画效果的计时器
        self.preview_selected = False  # 地图预览是否被选中
        
        # 显示鼠标光标
        pygame.mouse.set_visible(True)
        
        # 初始化字体，如果系统字体加载失败则使用默认字体
        try:
            self.font_large = pygame.font.SysFont('arial', 36, bold=True)
            self.font_medium = pygame.font.SysFont('arial', 24)
            self.font_small = pygame.font.SysFont('arial', 18)
        except Exception:
            self.font_large = pygame.font.Font(None, 40)
            self.font_medium = pygame.font.Font(None, 28)
            self.font_small = pygame.font.Font(None, 22)
    
    def handle_event(self, event):
        """
        处理用户输入事件
        支持键盘和鼠标操作，包括地图切换和选择
        返回事件处理结果：
        - "map_changed": 地图已切换
        - "map_selected": 地图已选择
        - "exit": 退出选择
        - None: 无特殊事件
        """
        if event.type == pygame.KEYDOWN:
            # 处理键盘输入
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                # 向左切换地图
                self.current_index = (self.current_index - 1) % len(self.map_list)
                self.selected_map = self.map_list[self.current_index]
                self.preview_selected = False
                return "map_changed"
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                # 向右切换地图
                self.current_index = (self.current_index + 1) % len(self.map_list)
                self.selected_map = self.map_list[self.current_index]
                self.preview_selected = False
                return "map_changed"
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # 确认选择地图
                if self.preview_selected:
                    return "map_selected"
            elif event.key == pygame.K_ESCAPE:
                # 退出选择
                return "exit"
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # 处理鼠标点击
            if event.button == 1:  # 左键点击
                mouse_pos = pygame.mouse.get_pos()
                # 检查点击位置并执行相应操作
                if self.is_in_preview_area(mouse_pos):
                    if self.preview_selected:
                        return "map_selected"
                    else:
                        self.preview_selected = True
                        return "map_changed"
                elif self.is_in_left_arrow(mouse_pos):
                    # 点击左箭头切换地图
                    self.current_index = (self.current_index - 1) % len(self.map_list)
                    self.selected_map = self.map_list[self.current_index]
                    self.preview_selected = False
                    return "map_changed"
                elif self.is_in_right_arrow(mouse_pos):
                    # 点击右箭头切换地图
                    self.current_index = (self.current_index + 1) % len(self.map_list)
                    self.selected_map = self.map_list[self.current_index]
                    self.preview_selected = False
                    return "map_changed"
        
        return None
    
    def is_in_preview_area(self, pos):
        """检查鼠标位置是否在地图预览区域内"""
        preview_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, 200, 400, 250)
        return preview_rect.collidepoint(pos)
    
    def is_in_left_arrow(self, pos):
        """检查鼠标位置是否在左箭头区域内"""
        arrow_rect = pygame.Rect(SCREEN_WIDTH//2 - 300, 300, 80, 80)
        return arrow_rect.collidepoint(pos)
    
    def is_in_right_arrow(self, pos):
        """检查鼠标位置是否在右箭头区域内"""
        arrow_rect = pygame.Rect(SCREEN_WIDTH//2 + 220, 300, 80, 80)
        return arrow_rect.collidepoint(pos)
    
    def update(self):
        """更新动画状态"""
        self.animation_time += 1
    
    def draw_map_preview(self, screen, map_name, x, y, width, height):
        """
        绘制地图预览
        包括地图背景、障碍物和选中状态
        """
        map_config = MAPS[map_name]
        
        # 创建预览表面并填充背景色
        preview_surface = pygame.Surface((width, height))
        preview_surface.fill(map_config["bg_color"])
        
        # 计算缩放比例
        scale_x = width / SCREEN_WIDTH
        scale_y = height / SCREEN_HEIGHT
        
        # 绘制所有障碍物
        for obstacle_data in map_config["obstacles"]:
            # 计算障碍物在预览中的位置和大小
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
            else:
                color = (128, 128, 128)
            
            pygame.draw.rect(preview_surface, color, (obs_x, obs_y, obs_w, obs_h))
        
        # 绘制预览边框和选中状态
        if self.preview_selected:
            # 选中状态显示黄色边框和提示文字
            pygame.draw.rect(preview_surface, (255, 255, 0), (0, 0, width, height), 4)
            select_text = self.font_small.render("Selected - Press Enter", True, (255, 255, 0))
            text_rect = select_text.get_rect(center=(width//2, height - 20))
            preview_surface.blit(select_text, text_rect)
        else:
            # 未选中状态显示白色边框
            pygame.draw.rect(preview_surface, (255, 255, 255), (0, 0, width, height), 2)
        
        screen.blit(preview_surface, (x, y))
    
    def draw(self, screen):
        """
        绘制完整的地图选择界面
        包括背景、标题、地图预览、导航箭头和操作提示
        """
        # 绘制动态背景渐变
        for y in range(SCREEN_HEIGHT):
            color_intensity = int(20 + 10 * math.sin(y * 0.01 + self.animation_time * 0.05))
            color = (color_intensity, color_intensity, color_intensity + 10)
            pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))
        
        # 绘制标题和副标题
        title_text = self.font_large.render("SELECT MAP", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 80))
        screen.blit(title_text, title_rect)
        
        subtitle_text = self.font_medium.render("Choose your battlefield", True, (200, 200, 200))
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH//2, 120))
        screen.blit(subtitle_text, subtitle_rect)
        
        # 获取并显示当前地图信息
        current_map = MAPS[self.selected_map]
        
        # 显示地图名称
        map_name_text = self.font_large.render(current_map["name"], True, (255, 215, 0))
        map_name_rect = map_name_text.get_rect(center=(SCREEN_WIDTH//2, 170))
        screen.blit(map_name_text, map_name_rect)
        
        # 显示地图描述
        desc_text = self.font_small.render(current_map["description"], True, (180, 180, 180))
        desc_rect = desc_text.get_rect(center=(SCREEN_WIDTH//2, 480))
        screen.blit(desc_text, desc_rect)
        
        # 绘制地图预览
        preview_x = SCREEN_WIDTH//2 - 200
        preview_y = 200
        preview_width = 400
        preview_height = 250
        self.draw_map_preview(screen, self.selected_map, preview_x, preview_y, preview_width, preview_height)
        
        # 绘制导航箭头
        arrow_y = 300
        mouse_pos = pygame.mouse.get_pos()
        
        # 绘制左箭头
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
        
        # 绘制右箭头
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
        
        # 显示地图导航信息
        nav_y = SCREEN_HEIGHT - 80
        nav_text = self.font_small.render(f"Map {self.current_index + 1}/{len(self.map_list)}", True, (200, 200, 200))
        nav_rect = nav_text.get_rect(center=(SCREEN_WIDTH//2, nav_y))
        screen.blit(nav_text, nav_rect)
        
        # 显示地图特殊机制
        mechanics = MAPS[self.selected_map]["special_mechanics"]
        mech_text = self.font_small.render(f"Special: {mechanics['description']}", True, (0, 200, 200))
        mech_rect = mech_text.get_rect(center=(SCREEN_WIDTH//2, nav_y + 30))
        screen.blit(mech_text, mech_rect)
        
        # 显示操作提示
        controls_text = self.font_small.render("Arrow Keys/WASD: Navigate | Enter/Space: Select | Click: Select | ESC: Exit", True, (150, 150, 150))
        controls_rect = controls_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 30))
        screen.blit(controls_text, controls_rect)
        
        # 显示地图数量指示器
        for i in range(len(self.map_list)):
            dot_x = SCREEN_WIDTH//2 - len(self.map_list) * 10 + i * 20
            dot_y = SCREEN_HEIGHT - 50
            if i == self.current_index:
                pygame.draw.circle(screen, (255, 255, 0), (dot_x, dot_y), 6)
            else:
                pygame.draw.circle(screen, (150, 150, 150), (dot_x, dot_y), 4) 