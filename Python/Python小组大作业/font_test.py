import pygame
import sys

def test_fonts():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("字体测试")
    
    # 测试字体列表
    font_candidates = [
        'PingFang SC', 'Hiragino Sans GB', 'STHeiti', 'SimHei',
        'Microsoft YaHei', 'SimSun', 'KaiTi', 'FangSong',
        'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'Source Han Sans CN',
        'Arial Unicode MS', 'DejaVu Sans', 'Liberation Sans',
        'Arial', 'Helvetica', 'Verdana', 'Tahoma'
    ]
    
    # 测试文本
    test_texts = [
        "恭喜通关！",
        "生存大师",
        "得分王",
        "完美通关",
        "关卡信息",
        "血量: 100/100",
        "弹药: 30/30",
        "分数: 2500"
    ]
    
    working_fonts = []
    
    print("正在测试字体...")
    for font_name in font_candidates:
        try:
            font = pygame.font.SysFont(font_name, 24)
            # 测试渲染中文
            test_surface = font.render("测试中文", True, (255, 255, 255))
            if test_surface.get_width() > 20:  # 如果能正确渲染
                working_fonts.append((font_name, font))
                print(f"✓ {font_name} - 支持中文")
            else:
                print(f"✗ {font_name} - 不支持中文")
        except Exception as e:
            print(f"✗ {font_name} - 加载失败: {e}")
    
    if not working_fonts:
        print("没有找到支持中文的字体！")
        return
    
    print(f"\n找到 {len(working_fonts)} 个可用字体")
    print("按空格键切换字体，ESC退出")
    
    current_font_index = 0
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    current_font_index = (current_font_index + 1) % len(working_fonts)
        
        screen.fill((30, 30, 30))
        
        if working_fonts:
            font_name, font = working_fonts[current_font_index]
            
            # 显示当前字体名称
            title_text = font.render(f"当前字体: {font_name}", True, (255, 255, 0))
            screen.blit(title_text, (50, 50))
            
            # 显示测试文本
            y_offset = 100
            for i, text in enumerate(test_texts):
                text_surface = font.render(text, True, (255, 255, 255))
                screen.blit(text_surface, (50, y_offset + i * 40))
            
            # 显示操作提示
            help_text = font.render("按空格键切换字体，ESC退出", True, (128, 128, 128))
            screen.blit(help_text, (50, 500))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    test_fonts() 