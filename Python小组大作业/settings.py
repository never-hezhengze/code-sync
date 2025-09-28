# 屏幕设置
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
BG_COLOR = (30, 30, 30)

# 玩家设置
PLAYER_SPEED = 6  # 移动速度
PLAYER_MAX_HEALTH = 100
PLAYER_SIZE = 32

# 敌人设置
ENEMY_SPAWN_RATE = 30  # 每30帧生成一个敌人
ENEMY_SPEED = 3
ENEMY_SIZE = 32
ENEMY_HEALTH = 2  # 敌人血量

# Level System
LEVELS = {
    1: {"name": "Rookie Training", "enemy_types": ["normal"], "spawn_rate": 45, "max_enemies": 8},
    2: {"name": "Basic Combat", "enemy_types": ["normal"], "spawn_rate": 35, "max_enemies": 10},
    3: {"name": "Speed Assault", "enemy_types": ["normal", "fast"], "spawn_rate": 30, "max_enemies": 12},
    4: {"name": "Armor Invasion", "enemy_types": ["normal", "tank"], "spawn_rate": 25, "max_enemies": 10},
    5: {"name": "Mixed Battlefield", "enemy_types": ["normal", "fast", "tank"], "spawn_rate": 20, "max_enemies": 15},
    6: {"name": "Sniper Threat", "enemy_types": ["normal", "fast", "tank", "sniper"], "spawn_rate": 18, "max_enemies": 12},
    7: {"name": "Explosive Expert", "enemy_types": ["normal", "fast", "tank", "bomber"], "spawn_rate": 15, "max_enemies": 14},
    8: {"name": "Elite Forces", "enemy_types": ["fast", "tank", "sniper", "bomber"], "spawn_rate": 12, "max_enemies": 16},
    9: {"name": "Final Challenge", "enemy_types": ["tank", "sniper", "bomber", "boss"], "spawn_rate": 10, "max_enemies": 12},
    10: {"name": "Endless Mode", "enemy_types": ["normal", "fast", "tank", "sniper", "bomber", "boss"], "spawn_rate": 8, "max_enemies": 20}
}

# 武器设置
BULLET_SPEED = 12
BULLET_SIZE = 6
BULLET_DAMAGE = 1
MAX_AMMO = 30
RELOAD_TIME = 60  # 重装时间（帧数）
FIRE_RATE = 5  # 射击间隔（帧数）

# 游戏平衡
SCORE_PER_KILL = 10
HEALTH_REGEN_RATE = 300  # 每300帧回复1点血量
ENEMY_DAMAGE = 10
ENEMY_CONTACT_DAMAGE_COOLDOWN = 60  # 受伤无敌时间

# 视觉效果
PARTICLE_COUNT = 10
EXPLOSION_SIZE = 50

# 血包设置
HEALTH_PACK_SIZE = 20
HEALTH_PACK_HEAL_AMOUNT = 25
HEALTH_PACK_SPAWN_RATE = 600  # 每600帧生成一个血包
HEALTH_PACK_LIFETIME = 900  # 血包存在时间（帧数）

# 通关设置
MAX_LEVEL = 10  # 最大关卡数
VICTORY_BONUS_SCORE = 1000  # 通关奖励分数

# 地图系统
MAPS = {
    "classic": {
        "name": "Classic Arena",
        "description": "Traditional battlefield with open space",
        "bg_color": (30, 30, 30),
        "obstacles": [],
        "spawn_zones": "edges",
        "special_mechanics": {
            "type": "speed_boost",
            "description": "Speed boost zones appear randomly"
        }
    },
    "maze": {
        "name": "Maze Complex",
        "description": "Navigate through narrow corridors",
        "bg_color": (20, 40, 20),
        "obstacles": [
            # Maze walls
            {"type": "wall", "pos": (200, 100), "size": (20, 200)},
            {"type": "wall", "pos": (400, 200), "size": (20, 300)},
            {"type": "wall", "pos": (600, 100), "size": (20, 200)},
            {"type": "wall", "pos": (800, 200), "size": (20, 300)},
            {"type": "wall", "pos": (1000, 100), "size": (20, 200)},
            # Horizontal walls
            {"type": "wall", "pos": (100, 300), "size": (200, 20)},
            {"type": "wall", "pos": (500, 400), "size": (200, 20)},
            {"type": "wall", "pos": (900, 300), "size": (200, 20)},
            # Destructible walls
            {"type": "destructible_wall", "pos": (300, 250), "size": (20, 100), "health": 3},
            {"type": "destructible_wall", "pos": (700, 350), "size": (20, 100), "health": 3},
        ],
        "spawn_zones": "safe_areas",
        "special_mechanics": {
            "type": "destructible_walls",
            "description": "Shoot walls to create new paths"
        }
    },
    "fortress": {
        "name": "Fortress Siege",
        "description": "Defend the central fortress",
        "bg_color": (40, 30, 20),
        "obstacles": [
            # Central fortress
            {"type": "fortress", "pos": (SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 - 100), "size": (200, 200)},
            # Corner bunkers with turrets
            {"type": "turret_bunker", "pos": (100, 100), "size": (80, 80), "fire_rate": 120},
            {"type": "turret_bunker", "pos": (SCREEN_WIDTH - 180, 100), "size": (80, 80), "fire_rate": 120},
            {"type": "turret_bunker", "pos": (100, SCREEN_HEIGHT - 180), "size": (80, 80), "fire_rate": 120},
            {"type": "turret_bunker", "pos": (SCREEN_WIDTH - 180, SCREEN_HEIGHT - 180), "size": (80, 80), "fire_rate": 120},
        ],
        "spawn_zones": "fortress_perimeter",
        "special_mechanics": {
            "type": "defensive_turrets",
            "description": "Turrets automatically shoot nearby enemies"
        }
    },
    "desert": {
        "name": "Desert Storm",
        "description": "Sandy battlefield with scattered rocks",
        "bg_color": (60, 50, 30),
        "obstacles": [
            # Scattered rocks
            {"type": "rock", "pos": (300, 200), "size": (60, 60)},
            {"type": "rock", "pos": (700, 150), "size": (80, 80)},
            {"type": "rock", "pos": (500, 400), "size": (70, 70)},
            {"type": "rock", "pos": (900, 350), "size": (90, 90)},
            {"type": "rock", "pos": (200, 500), "size": (50, 50)},
            {"type": "rock", "pos": (1000, 200), "size": (60, 60)},
            # Sandstorm generators
            {"type": "sandstorm_generator", "pos": (150, 300), "size": (40, 40)},
            {"type": "sandstorm_generator", "pos": (800, 500), "size": (40, 40)},
        ],
        "spawn_zones": "random",
        "special_mechanics": {
            "type": "sandstorms",
            "description": "Sandstorms reduce visibility and slow movement"
        }
    },
    "urban": {
        "name": "Urban Warfare",
        "description": "Fight through city streets",
        "bg_color": (25, 25, 35),
        "obstacles": [
            # Buildings
            {"type": "building", "pos": (150, 150), "size": (100, 150)},
            {"type": "building", "pos": (400, 100), "size": (120, 200)},
            {"type": "building", "pos": (700, 200), "size": (100, 100)},
            {"type": "building", "pos": (950, 150), "size": (80, 180)},
            {"type": "building", "pos": (300, 450), "size": (150, 100)},
            {"type": "building", "pos": (800, 500), "size": (100, 120)},
            # Power stations
            {"type": "power_station", "pos": (50, 50), "size": (60, 60), "active": True},
            {"type": "power_station", "pos": (1100, 600), "size": (60, 60), "active": True},
        ],
        "spawn_zones": "streets",
        "special_mechanics": {
            "type": "power_grid",
            "description": "Destroy power stations to disable enemy electronics"
        }
    }
}

# 颜色定义
COLORS = {
    'player': (0, 255, 0),
    'enemy': (255, 0, 0),
    'bullet': (255, 255, 0),
    'ui_text': (255, 255, 255),
    'health_bar_bg': (255, 0, 0),
    'health_bar_fg': (0, 255, 0),
    'ammo_bar_bg': (100, 100, 100),
    'ammo_bar_fg': (255, 215, 0),
    'explosion': (255, 165, 0),
    'health_pack': (0, 255, 0),
    'health_pack_cross': (255, 255, 255),
    # 敌人颜色
    'enemy_normal': (255, 0, 0),
    'enemy_fast': (255, 100, 100),
    'enemy_tank': (150, 0, 0),
    'enemy_sniper': (128, 0, 128),
    'enemy_bomber': (255, 165, 0),
    'enemy_boss': (100, 0, 100),
    # 通关界面颜色
    'victory_gold': (255, 215, 0),
    'victory_silver': (192, 192, 192),
    'victory_bronze': (205, 127, 50)
}

