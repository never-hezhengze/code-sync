import pygame
from sys import exit
from settings import *
from player import Player
from enemy import EnemyGroup
from ui import UI
from weapons import BulletGroup
from health_pack import HealthPackGroup
from map_system import GameMap
from map_selector import MapSelector


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("RogueLike Shooter - Ultimate Edition")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.victory = False
        self.state = "map_select"  # 游戏状态：map_select, playing
        
        # 地图选择器
        self.map_selector = MapSelector()
        self.current_map = None
        
        # 根据游戏状态设置鼠标光标
        pygame.mouse.set_visible(True)  # 初始状态为地图选择，显示鼠标

    def reset_game(self, map_name="classic"):
        """重置游戏状态"""
        try:
            # 创建地图
            self.current_map = GameMap(map_name)
            if not self.current_map:
                raise Exception("Failed to create game map")
            
            # 游戏对象
            self.player = Player()
            if not self.player:
                raise Exception("Failed to create player")
            
            # 将地图传递给敌人组，以便使用地图的生成位置
            self.enemies = EnemyGroup(self.current_map)
            if not self.enemies:
                raise Exception("Failed to create enemy group")
            
            self.bullets = BulletGroup()
            if not self.bullets:
                raise Exception("Failed to create bullet group")
            
            self.health_packs = HealthPackGroup()
            if not self.health_packs:
                raise Exception("Failed to create health pack group")
            
            if not hasattr(self, 'ui'):
                self.ui = UI()
                if not self.ui:
                    raise Exception("Failed to create UI")
            
            # 确保玩家在有效位置
            player_pos = self.current_map.get_valid_position((PLAYER_SIZE, PLAYER_SIZE))
            if not player_pos:
                raise Exception("Failed to get valid player position")
            
            self.player.rect.center = player_pos
            
            # 生成初始敌人
            self.enemies.spawn_enemies(3)
            
            # 重置游戏状态（移到最后）
            self.game_over = False
            self.victory = False
            self.state = "playing"
            
            # 游戏进行时隐藏鼠标光标
            pygame.mouse.set_visible(False)
            
            print("Game reset successful")  # 调试信息
            
        except Exception as e:
            print(f"Error in reset_game: {e}")  # 调试信息
            # 如果初始化失败，返回地图选择状态
            self.state = "map_select"
            pygame.mouse.set_visible(True)
            return False
        
        return True

    def run(self):
        while self.running:
            self._handle_events()
            if self.state == "map_select":
                self.map_selector.update()
            elif self.state == "playing" and not self.game_over and not self.victory:
                self._update()
            self._draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        exit()

    def _handle_events(self):
        # 使用 pygame.event.get() 而不是 pygame.event.get()，这样不会清空事件队列
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if self.state == "map_select":
                # 地图选择状态
                result = self.map_selector.handle_event(event)
                if result == "map_selected":
                    # 开始游戏
                    if self.reset_game(self.map_selector.selected_map):
                        # 只有在成功重置游戏后才设置状态
                        self.state = "playing"
                        self.game_over = False
                        self.victory = False
                    else:
                        # 如果重置失败，保持在选择地图状态
                        self.state = "map_select"
                        pygame.mouse.set_visible(True)
                elif result == "exit":
                    self.running = False
            
            elif self.state == "playing":
                # 游戏进行状态
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_over or self.victory:
                            self.running = False
                        else:
                            # 返回地图选择
                            self.state = "map_select"
                            # 返回地图选择时显示鼠标光标
                            pygame.mouse.set_visible(True)
                    if event.key == pygame.K_r:
                        if self.game_over or self.victory:
                            # 重新开始游戏（同一地图）
                            if self.reset_game(self.current_map.map_name):
                                # 只有在成功重置游戏后才设置状态
                                self.state = "playing"
                                self.game_over = False
                                self.victory = False
                            else:
                                # 如果重置失败，保持在当前状态
                                pass
                        else:
                            # 重新装填
                            self.player.start_reload()
        
        # 在游戏进行状态下，检查按键状态
        if self.state == "playing" and not self.game_over and not self.victory:
            # 获取当前按键状态
            keys = pygame.key.get_pressed()
            # 打印按键状态用于调试
            if keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]:
                print("Movement keys detected in main loop")
                # 更新玩家状态
                self.player.update(self.bullets, self.current_map)

    def _update(self):
        # 更新地图状态
        self.current_map.update(self.player, self.enemies, self.bullets)
        
        # 更新游戏对象
        print("Updating player in _update")  # 调试信息
        self.player.update(self.bullets, self.current_map)
        self.enemies.update(self.player, self.current_map)
        self.bullets.update()
        
        # 更新血包并检查拾取
        heal_amount = self.health_packs.update(self.player, self.current_map)
        if heal_amount > 0:
            self.ui.show_heal_message(heal_amount)

        # 玩家子弹与敌人碰撞
        hits = pygame.sprite.groupcollide(
            self.enemies.group, self.bullets.group, False, True
        )
        
        # 炮塔子弹与敌人碰撞
        turret_hits = pygame.sprite.groupcollide(
            self.enemies.group, self.bullets.turret_bullets, False, True
        )
        
        # 处理所有子弹碰撞
        all_hits = {}
        for enemy, bullet_list in hits.items():
            all_hits[enemy] = bullet_list
        for enemy, bullet_list in turret_hits.items():
            if enemy in all_hits:
                all_hits[enemy].extend(bullet_list)
            else:
                all_hits[enemy] = bullet_list
        
        # 玩家子弹与障碍物碰撞
        for bullet in self.bullets.group.copy():
            hit_obstacle = self.current_map.check_bullet_collision(bullet.rect)
            if hit_obstacle:
                self.bullets.create_explosion(bullet.rect.center)
                bullet.kill()
                
                # 如果击中可破坏的障碍物
                if hit_obstacle.take_damage(bullet.damage):
                    # 障碍物被摧毁，创建更大的爆炸
                    self.bullets.create_explosion(hit_obstacle.rect.center)
        
        # 炮塔子弹与障碍物碰撞
        for bullet in self.bullets.turret_bullets.copy():
            if self.current_map.check_collision(bullet.rect):
                self.bullets.create_explosion(bullet.rect.center)
                bullet.kill()
        
        for enemy, bullet_list in all_hits.items():
            for bullet in bullet_list:
                # 创建爆炸效果
                self.bullets.create_explosion(enemy.rect.center)
                
                # 敌人受伤
                if enemy.take_damage(bullet.damage):
                    # 敌人死亡
                    self.ui.add_score(enemy.score_value)
                    result = self.enemies.enemy_killed()  # 检查是否升级或通关
                    if result == "victory":
                        # 通关了！
                        self.victory = True
                        self.ui.add_score(VICTORY_BONUS_SCORE)  # 添加通关奖励分数
                        self.ui.show_victory()
                    elif result:
                        # 升级了
                        level_config = self.enemies.get_current_level_config()
                        self.ui.show_level_up_message(self.enemies.current_level, level_config["name"])
                    enemy.kill()

        # 敌人与玩家碰撞
        colliding_enemies = pygame.sprite.spritecollide(self.player, self.enemies.group, False)
        for enemy in colliding_enemies:
            if self.player.take_damage(ENEMY_DAMAGE):
                # 创建受伤效果
                self.bullets.create_explosion(self.player.rect.center)
        
        # 检查游戏结束
        if self.player.health <= 0:
            self.game_over = True

    def _draw(self):
        if self.state == "map_select":
            # 绘制地图选择界面
            self.map_selector.draw(self.screen)
        
        elif self.state == "playing":
            # 绘制地图背景
            if self.current_map:
                self.current_map.draw(self.screen)
            else:
                self.screen.fill(BG_COLOR)
            
            if not self.game_over and not self.victory:
                # 绘制游戏对象
                self.player.draw(self.screen)
                self.enemies.draw(self.screen)
                self.bullets.draw(self.screen)
                self.health_packs.draw(self.screen)
                
                            # 绘制UI
                self.ui.draw(self.screen, self.player, self.enemies, self.health_packs, self.current_map)
            elif self.victory:
                # 绘制通关界面
                self.ui.draw(self.screen, self.player, self.enemies, self.health_packs, self.current_map, victory=True)
            else:
                # 绘制游戏结束界面
                self.ui.draw(self.screen, self.player, self.enemies, self.health_packs, self.current_map, game_over=True)
        
        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()