import pygame, sys
import os
from os import walk
import random
from math import sin
from random import choice, randint
import json

def save_play_data(player, level_num, enemies, bushes):
    data = {
        'player': {
            'x': player.rect.x,
            'y': player.rect.y,
            'health': player.health,
            'energy': player.energy,
            'exp': player.exp,
            'stats': player.stats,
            'upgrade_cost': player.upgrade_cost,
            'weapon_index': player.weapon_index,
            'magic_index': player.magic_index,
        },
        'level': level_num,
        'enemies': [
            {
                'type': e.monster_name,
                'x': e.rect.x,
                'y': e.rect.y,
                'health': e.health
            }
            for e in enemies if hasattr(e, 'monster_name') and e.alive()
        ],
        'bushes': [
            {
                'x': b.rect.x,
                'y': b.rect.y,
                'image_path': getattr(b, 'image_path', 'Ashen Legacy - Vine.png')
            }
            for b in bushes if b.alive()
        ]
    }

    if level_num == 3:
        for enemy in enemies:
            if hasattr(enemy, 'sprite_type') and enemy.sprite_type == 'boss':
                if not enemy.alive():
                    data['boss_defeated'] = True
                else:
                    data['boss_defeated'] = False
                break

    with open(f"save_data_level_{level_num}.json", "w") as f:
        json.dump(data, f)

# loads saved player/enemy/bush state from JSON
# merges in transferred exp and stats if moving from previous level
def load_player_data(level_num):
    transferred_exp = 0
    transferred_stats = None
    transferred_cost = None

    try:
        with open("exp_transfer.json", "r") as f:
            temp_data = json.load(f)
            transferred_exp = temp_data.get('exp', 0)
            transferred_stats = temp_data.get('stats')
            transferred_cost = temp_data.get('upgrade_cost')
    except FileNotFoundError:
        pass

    saved_data = {}
    try:
        with open(f"save_data_level_{level_num}.json", "r") as f:
            saved_data = json.load(f)
    except FileNotFoundError:
        pass

    if 'player' not in saved_data:
        saved_data['player'] = {}

    # Merge in transferred values
    if transferred_exp > 0:
        saved_data['player']['exp'] = saved_data['player'].get('exp', 0) + transferred_exp

    if transferred_stats:
        saved_data['player']['stats'] = transferred_stats

    if transferred_cost:
        saved_data['player']['upgrade_cost'] = transferred_cost
        if transferred_stats:
            saved_data['player']['stats'] = transferred_stats
        if transferred_cost:
            saved_data['player']['upgrade_cost'] = transferred_cost

        os.remove("exp_transfer.json")

    return saved_data if saved_data else None

def reset_save_data():
    deleted = False
    for level_num in [0, 1, 2, 3]:
        path = f'save_data_level_{level_num}.json'
        if os.path.exists(path):
            os.remove(path)
            deleted = True
    if os.path.exists("exp_transfer.json"):
        os.remove("exp_transfer.json")
        deleted = True

    if os.path.exists("persistent_exp.json"):
        os.remove("persistent_exp.json")

def update_highscore(exp):
    highscore_path = "highscore.json"
    try:
        with open(highscore_path, "r") as f:
            data = json.load(f)
            if exp > data.get("highscore", 0):
                data["highscore"] = exp
                with open(highscore_path, "w") as fw:
                    json.dump(data, fw)
    except FileNotFoundError:
        with open(highscore_path, "w") as fw:
            json.dump({"highscore": exp}, fw)

def get_highscore():
    try:
        with open("highscore.json", "r") as f:
            data = json.load(f)
            return data.get("highscore", 0)
    except FileNotFoundError:
        return 0

pygame.init()

pygame.mixer.init()
pygame.init()

# Global volumes
music_volume = 0.25
sfx_volume = 0.25

font = pygame.font.Font(None, 30)

def debug(info,y = 10, x = 10):
    display_surface = pygame.display.get_surface()
    debug_surf = font.render(str(info), True, 'White')
    debug_rect = debug_surf.get_rect(topleft = (x,y))
    pygame.draw.rect(display_surface, 'Black', debug_rect)
    display_surface.blit(debug_surf, debug_rect)

WIDTH = 1280
HEIGHT = 720
FPS = 60
TILESIZE = 64
HITBOX_OFFSET = {
    'player': -26,
    'object': -40,
    'grass': -10,
    'invisible': 0}

# ui
BAR_HEIGHT = 20
HEALTH_BAR_WIDTH = 200
ENERGY_BAR_WIDTH = 140
ITEM_BOX_SIZE = 80
UI_FONT = 'Ashen Legacy - Font.ttf'
UI_FONT_SIZE = 18

# general colours
WATER_COLOUR = '#71ddee'
UI_BG_COLOUR = '#222222'
UI_BORDER_COLOUR = '#111111'
TEXT_COLOUR = '#EEEEEE'

# ui colours
HEALTH_COLOUR = 'red'
ENERGY_COLOUR = 'blue'
UI_BORDER_COLOUR_ACTIVE = 'gold'

# upgrade menu
TEXT_COLOUR_SELECTED = '#111111'
BAR_COLOUR = '#EEEEEE'
BAR_COLOUR_SELECTED = '#111111'
UPGRADE_BG_COLOUR_SELECTED = '#EEEEEE'

# weapons
weapon_data = {
    'sword': {'cooldown': 100, 'damage': 15,'graphic':'Ashen Legacy - Weapons/sword/full.png'},
    'lance': {'cooldown': 400, 'damage': 30,'graphic':'Ashen Legacy - Weapons/lance/full.png'},
    'axe': {'cooldown': 300, 'damage': 20, 'graphic':'Ashen Legacy - Weapons/axe/full.png'},
    'rapier':{'cooldown': 50, 'damage': 8, 'graphic':'Ashen Legacy - Weapons/rapier/full.png'},
    'sai':{'cooldown': 80, 'damage': 10, 'graphic':'Ashen Legacy - Weapons/sai/full.png'}}

# magic
magic_data = {
    'flame': {'strength': 5, 'cost': 20, 'graphic': 'Ashen Legacy - Particles/flame/fire.png'},
    'heal': {'strength': 20, 'cost': 10, 'graphic': 'Ashen Legacy - Particles/heal/heal.png'}}

# enemy
monster_data = {
    'skeleton': {'health': 100,'exp':100,'damage':20,'attack_type': 'slash', 'attack_sound': 'Ashen Legacy - SFX/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 80, 'notice_radius': 300},
    'goblin': {'health': 90,'exp':75, 'damage':12,'attack_type': 'claw', 'attack_sound': 'Ashen Legacy - SFX/attack/claw.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 50, 'notice_radius': 300},
    'ghost': {'health': 100,'exp':110,'damage':8,'attack_type': 'thunder', 'attack_sound': 'Ashen Legacy - SFX/attack/fireball.wav', 'speed': 4, 'resistance': 3, 'attack_radius': 60, 'notice_radius': 300}}

# boss
boss_data = {'ancient_skeleton': {'health': 2500, 'exp': 2500, 'damage': 35, 'attack_type': 'slash', 'attack_sound': 'Ashen Legacy - SFX/attack/slash.wav', 'speed': 2, 'resistance': 5, 'attack_radius': 200, 'notice_radius': 350}}

# Legend:
# 'p' = player spawn
# 'e' = enemy
# 'a' = boss
# 'x' = wall
# 'b' = bush
# 'v' = vine
# 'f' = portal

WORLD_MAP_0 = [
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
['x','1','1','1',' ',' ','2',' ',' ',' ',' ',' ','3',' ',' ',' ',' ',' ',' ','x'],
['x','1','p','1',' ',' ','2',' ',' ',' ',' ',' ','3',' ',' ',' ',' ',' ',' ','x'],
['x','1','1','1',' ',' ','2',' ',' ',' ',' ',' ','3',' ',' ',' ',' ',' ',' ','x'],
['x','x','x','x','x',' ','2',' ',' ',' ',' ',' ','3',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ','x',' ','2',' ',' ',' ',' ',' ','3',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ','x','x','x','x','x','x','x','x','x','x','x','x','5','5','5','x'],
['x',' ',' ',' ',' ','6',' ',' ',' ',' ',' ','4',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ','6',' ',' ',' ',' ',' ','4',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ','6',' ',' ',' ',' ',' ','4',' ',' ',' ',' ',' ',' ',' ','x'],
['x','b','b','b','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
['x','7','7','7','7',' ',' ',' ',' ',' ',' ',' ','e',' ',' ','8',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','e',' ',' ','8',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','e',' ',' ','8',' ',' ',' ','x'],
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x',' ',' ',' ','x'],
['x','f',' ',' ',' ',' ','0',' ',' ',' ',' ',' ',' ',' ','9',' ',' ',' ',' ','x'],
['x','f',' ',' ',' ',' ','0',' ',' ',' ',' ',' ',' ',' ','9',' ',' ',' ',' ','x'],
['x','f',' ',' ',' ',' ','0',' ',' ',' ',' ',' ',' ',' ','9',' ',' ',' ',' ','x'],
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
]

WORLD_MAP_1 = [
  ['x'] * 38,
  ['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
  ['x',' ','p',' ',' ',' ',' ',' ',' ','e',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','e',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
  ['x','x','x','x','x','x','x','x','x','x','x','x','x','b','b','b','x','x','x','x','x','x','x','x','x','x','x','x','x','x',' ',' ',' ','x','x','x','x','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','e',' ',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','e',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ','e',' ','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ','x','x','x','x','x','x','x','x','x','x','x',' ',' ',' ','x'],
  ['x',' ',' ','x','x','x','x','x','x',' ','e',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ','b',' ',' ','x',' ',' ',' ','e',' ',' ',' ',' ',' ',' ','x'],
  ['x',' ',' ','b',' ',' ','x',' ',' ',' ',' ',' ','x',' ','e',' ','x',' ',' ',' ','x',' ',' ','b',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
  ['x',' ',' ','b',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ',' ','x',' ','e',' ','x',' ',' ','b',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x','x','x','x',' ',' ','x','x','x','x','x',' ',' ',' ','x',' ',' ','x','e',' ','x',' ',' ',' ','x','x','x','x','x','x','x','x'],
  ['x',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ','b',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','e',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ','b',' ',' ',' ','x'],
  ['x',' ',' ','x','x','x','x','x','x','x',' ',' ','x',' ',' ',' ','x','x','x','x','x',' ',' ','x',' ',' ','x','x','x','x','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ','b',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','e',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ','b',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ',' ',' ',' ','x',' ',' ','x','x','x','x','x','x','x','x',' ',' ',' ','x',' ',' ','x','x','x','x',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x','x','x','x',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','b',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ',' ','x',' ',' ','x',' ','e',' ','x'],
  ['x',' ',' ','b',' ',' ','x',' ',' ','x','x','x','x',' ',' ',' ','x','x','x','x','x',' ',' ','x','x','x','x',' ','e',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','b',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ','x',' ',' ','x',' ','e',' ','x'],
  ['x',' ','e','x',' ',' ','x',' ',' ',' ',' ',' ','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x','x','x','x','b','b','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ','x','x','x','x','x','x','x','x','x','b','b','x','x','x','x','x','x','x','x','x','x','x'],
  ['x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ','x',' ',' ',' ','b',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ','x',' ',' ',' ','x',' ',' ',' ','b',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ','e',' ',' ',' ','x'],
  ['x',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ','x',' ','e',' ','x',' ',' ',' ','x',' ','e',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','e',' ','x'],
  ['x',' ',' ','x',' ',' ',' ',' ',' ','x',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x',' ',' ',' ','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
  ['x',' ',' ','x','x','x','x','x','x','x',' ',' ','x','x','x','x','x',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','f','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ','e',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','f','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','e',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','f','x'],
  ['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','f','x'],
  ['x'] * 38,
]

WORLD_MAP_2 = [
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
['x',' ',' ',' ','v','v','v','v','v','v',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ','p',' ','v','v','v','v','v','v',' ',' ','e',' ',' ','e',' ',' ','e',' ',' ',' ','x'],
['x',' ',' ',' ','v','v','v','v','v','v',' ',' ',' ',' ',' ',' ','v',' ',' ','v',' ',' ','x'],
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x',' ',' ','x'],
['x',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ','v',' ','e',' ',' ','v',' ',' ','e',' ','e',' ',' ',' ','e','v',' ',' ','x'],
['x',' ',' ',' ','v',' ',' ',' ','e',' ','e',' ',' ','v',' ',' ','e',' ',' ','e',' ',' ','x'],
['x',' ','e',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ','x'],
['x',' ',' ','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ','e',' ',' ','v',' ',' ','e',' ',' ',' ',' ',' ','v',' ',' ','x'],
['x',' ','e',' ','v','e',' ',' ',' ',' ','v',' ',' ',' ',' ','v',' ',' ','e',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ','v',' ','e',' ',' ',' ',' ',' ',' ',' ','v',' ',' ','e',' ',' ','v',' ','x'],
['x',' ',' ','e',' ',' ',' ',' ','v',' ','e',' ','e',' ','v',' ',' ',' ',' ','e',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ','f','x'],
['x',' ','v',' ',' ','e',' ',' ',' ',' ',' ','e',' ',' ','v',' ','v',' ',' ',' ',' ','f','x'],
['x',' ',' ','e',' ',' ','v',' ','e',' ','v',' ',' ','e',' ',' ','v',' ','e',' ',' ','f','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ','f','x'],
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
]

WORLD_MAP_3 = [
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ','p',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ','x',' ','e',' ',' ',' ',' ',' ','e',' ',' ','v',' ','x'],
['x',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ','x',' ',' ','v',' ',' ','x','x','x','x',' ',' ',' ','x'],
['x',' ',' ','e',' ',' ','x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ','v',' ',' ',' ',' ',' ','a',' ',' ',' ','v',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ','e',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ','x','x','x',' ',' ',' ',' ',' ',' ','x','x','x',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ','e',' ',' ',' ',' ',' ',' ','e',' ','x',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ','v',' ',' ',' ',' ',' ',' ',' ','v',' ',' ',' ','x'],
['x',' ',' ','v',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ','x'],
['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
]

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ashen Legacy - Splash Screen")

# load splash image
background_image = pygame.image.load("Ashen Legacy - Splash Screen.png").convert()
background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))  # Scale to fit the screen

font_path = 'Ashen Legacy - Font.ttf'
font_size = 80
font = pygame.font.Font(font_path, font_size)

def show_splash_screen():
    # Main title
    text = font.render("ASHEN LEGACY", True, "Gold")
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    # Bottom text
    font_small = pygame.font.Font(font_path, 24)
    text_continue = font_small.render("Press Any Key to Continue", True, "White")
    text_continue_rect = text_continue.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 40)

    while True:
        screen.fill("black")

        # Draw background
        screen.blit(background_image, (0, 0))

        # Draw text
        screen.blit(text, text_rect)
        screen.blit(text_continue, text_continue_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Any key OR mouse button ends splash
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return

        pygame.display.update()

# Call the splash screen before the main game/menu
show_splash_screen()

def import_folder(path, scale_factor=1):
    surface_list = []

    for _,__,img_files in walk(path):
        for image in img_files:
            full_path = path + '/' + image
            image_surf = pygame.image.load(full_path).convert_alpha()
            if scale_factor != 1:
                width = int(image_surf.get_width() * scale_factor)
                height = int(image_surf.get_height() * scale_factor)
                image_surf = pygame.transform.scale(image_surf, (width, height))
            surface_list.append(image_surf)

    return surface_list

def load_portal_frames(path):
    frames = []
    for i in range(41):
        image_path = f"{path}/{i}.png"
        image = pygame.image.load(image_path).convert_alpha()
        frames.append(image)
    return frames

# displays final score and highscore after completing Level 3
def show_end_screen(final_score, highscore):
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ashen Legacy - End Screen")

    bg_image = pygame.image.load("Ashen Legacy - Menu Background.png")

    font_title = pygame.font.Font("Ashen Legacy - Font.ttf", 100)
    font_score = pygame.font.Font("Ashen Legacy - Font.ttf", 60)
    font_prompt = pygame.font.Font("Ashen Legacy - Font.ttf", 24)  # Match splash screen text

    clock = pygame.time.Clock()
    waiting = True

    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                waiting = False  # Exit loop on any input

        screen.blit(bg_image, (0, 0))

        # Render text
        title = font_title.render("GAME COMPLETE", True, "#b68f40")
        final_score_text = font_score.render(f"FINAL EXP: {int(final_score)}", True, "#d7fcd4")
        highscore_text = font_score.render(f"HIGHSCORE: {int(highscore)}", True, "white")
        prompt_text = font_prompt.render("Press any key to return to menu", True, "white")

        # Draw text
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 150)))
        screen.blit(final_score_text, final_score_text.get_rect(center=(WIDTH // 2, 300)))
        screen.blit(highscore_text, highscore_text.get_rect(center=(WIDTH // 2, 380)))
        screen.blit(prompt_text, prompt_text.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 40))  # Just like splash

        pygame.display.flip()
        clock.tick(60)

    reset_save_data()
    main_menu()

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprite_type, image_path):
        super().__init__(groups)
        self.sprite_type = sprite_type
        y_offset = HITBOX_OFFSET[sprite_type]
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, y_offset)

class Portal(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups):
        super().__init__(groups)
        self.frames = frames
        self.index = 0
        self.image = self.frames[int(self.index)]
        self.rect = self.image.get_rect(topleft=pos)
        self.animation_speed = 0.25  # Adjust for speed

    def update(self):
        self.index += self.animation_speed
        if self.index >= len(self.frames):
            self.index = 0
        self.image = self.frames[int(self.index)]

class AnimationPlayer:
    def __init__(self):
        self.frames = {
            # magic
            'flame': import_folder('Ashen Legacy - Particles/flame/frames'),
            'aura': import_folder('Ashen Legacy - Particles/aura'),
            'heal': import_folder('Ashen Legacy - Particles/heal/frames'),

            # attacks
            'claw': import_folder('Ashen Legacy - Particles/claw'),
            'slash': import_folder('Ashen Legacy - Particles/slash'),
            'sparkle': import_folder('Ashen Legacy - Particles/sparkle'),
            'thunder': import_folder('Ashen Legacy - Particles/thunder'),

            # player death
            'lone_warrior_death': import_folder('Ashen Legacy - Particles/Lone Warrior Death'),

            # monster deaths
            'skeleton': import_folder('Ashen Legacy - Particles/Skeleton Death'),
            'goblin': import_folder('Ashen Legacy - Particles/Goblin Death'),
            'ghost': import_folder('Ashen Legacy - Particles/Ghost Death'),

            # boss deaths
            'ancient_skeleton': import_folder('Ashen Legacy - Particles/Ancient_Skeleton Death', scale_factor = 3),

            # leafs
            'leaf': (
                import_folder('Ashen Legacy - Particles/leaf1'),
                import_folder('Ashen Legacy - Particles/leaf2'),
                import_folder('Ashen Legacy - Particles/leaf3'),
                import_folder('Ashen Legacy - Particles/leaf4'),
                import_folder('Ashen Legacy - Particles/leaf5'),
                import_folder('Ashen Legacy - Particles/leaf6'),
                self.reflect_images(import_folder('Ashen Legacy - Particles/leaf1')),
                self.reflect_images(import_folder('Ashen Legacy - Particles/leaf2')),
                self.reflect_images(import_folder('Ashen Legacy - Particles/leaf3')),
                self.reflect_images(import_folder('Ashen Legacy - Particles/leaf4')),
                self.reflect_images(import_folder('Ashen Legacy - Particles/leaf5')),
                self.reflect_images(import_folder('Ashen Legacy - Particles/leaf6'))
            )
        }

    def reflect_images(self, frames):
        new_frames = []

        for frame in frames:
            flipped_frame = pygame.transform.flip(frame, True, False)
            new_frames.append(flipped_frame)
        return new_frames

    def create_grass_particles(self, pos, groups):
        animation_frames = choice(self.frames['leaf'])
        ParticleEffect(pos, animation_frames, groups)

    def create_particles(self, animation_type, pos, groups):
        animation_frames = self.frames[animation_type]
        ParticleEffect(pos, animation_frames, groups)

class ParticleEffect(pygame.sprite.Sprite):
    def __init__(self, pos, animation_frames, groups):
        super().__init__(groups)
        self.sprite_type = 'magic'
        self.frame_index = 0
        self.animation_speed = 0.15
        self.frames = animation_frames
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=pos)

    def animate(self):
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.frames):
            self.kill()
        else:
            self.image = self.frames[int(self.frame_index)]

    def update(self):
        self.animate()

class Entity(pygame.sprite.Sprite):
	def __init__(self,groups):
		super().__init__(groups)
		self.frame_index = 0
		self.animation_speed = 0.15
		self.direction = pygame.math.Vector2()

	def move(self,speed):
		if self.direction.magnitude() != 0:
			self.direction = self.direction.normalize()

		self.hitbox.x += self.direction.x * speed
		self.collision('horizontal')
		self.hitbox.y += self.direction.y * speed
		self.collision('vertical')
		self.rect.center = self.hitbox.center

	def collision(self,direction):
		if direction == 'horizontal':
			for sprite in self.obstacle_sprites:
				if sprite.hitbox.colliderect(self.hitbox):
					if self.direction.x > 0: # moving right
						self.hitbox.right = sprite.hitbox.left
					if self.direction.x < 0: # moving left
						self.hitbox.left = sprite.hitbox.right

		if direction == 'vertical':
			for sprite in self.obstacle_sprites:
				if sprite.hitbox.colliderect(self.hitbox):
					if self.direction.y > 0: # moving down
						self.hitbox.bottom = sprite.hitbox.top
					if self.direction.y < 0: # moving up
						self.hitbox.top = sprite.hitbox.bottom

	def wave_value(self):
		value = sin(pygame.time.get_ticks())
		if value >= 0:
			return 255
		else:
			return 0

class Player(Entity):
    def __init__(self, pos, groups, obstacle_sprites, create_attack, destroy_attack, create_magic, saved_data,
                 animation_player, initial_stats=None, initial_exp=None, initial_upgrade_cost=None):
        super().__init__(groups)
        self.image = pygame.image.load('Ashen Legacy - Lone Warrior/warrior.png').convert_alpha()
        if saved_data and 'x' in saved_data and 'y' in saved_data:
            self.rect = self.image.get_rect(topleft=(saved_data['x'], saved_data['y']))
        else:
            self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-6, HITBOX_OFFSET['player'])

        self.initial_stats = initial_stats
        self.initial_exp = initial_exp
        self.initial_upgrade_cost = initial_upgrade_cost

        # graphics setup
        self.import_player_assets()
        self.status = 'down'

        self.animation_player = animation_player

        # movement
        self.attacking = False
        self.attack_cooldown = 400
        self.attack_time = None
        self.obstacle_sprites = obstacle_sprites

        # weapon
        self.create_attack = create_attack
        self.destroy_attack = destroy_attack
        self.weapon_index = 0
        self.weapon = list(weapon_data.keys())[self.weapon_index]
        self.can_switch_weapon = True
        self.weapon_switch_time = None
        self.switch_duration_cooldown = 200

        # magic
        self.create_magic = create_magic
        self.magic_index = 0
        self.magic = list(magic_data.keys())[self.magic_index]
        self.can_switch_magic = True
        self.magic_switch_time = None

        # stats
        default_stats = {'health': 100, 'energy': 60, 'attack': 10, 'magic': 4, 'speed': 5}
        self.stats = saved_data.get('stats', default_stats) if saved_data else default_stats

        default_upgrade_cost = {'health': 100, 'energy': 100, 'attack': 100, 'magic': 100, 'speed': 100}
        self.upgrade_cost = saved_data.get('upgrade_cost', default_upgrade_cost) if saved_data else default_upgrade_cost

        self.health = saved_data.get('health', self.stats['health']) if saved_data else self.stats['health']
        self.energy = saved_data.get('energy', self.stats['energy']) if saved_data else self.stats['energy']

        # Experience points handling
        if saved_data:
            self.exp = saved_data.get('exp', 0)
        else:
            self.exp = 0

        self.weapon_index = saved_data.get('weapon_index', 0) if saved_data else 0
        self.weapon = list(weapon_data.keys())[self.weapon_index]

        self.magic_index = saved_data.get('magic_index', 0) if saved_data else 0
        self.magic = list(magic_data.keys())[self.magic_index]

        self.max_stats = {'health': 300, 'energy': 140, 'attack': 20, 'magic': 10, 'speed': 12}

        # damage timer
        self.vulnerable = True
        self.hurt_time = None
        self.invulnerability_duration = 500

        # import a sound
        self.weapon_attack_sound = pygame.mixer.Sound('Ashen Legacy - SFX/sword.wav')
        self.weapon_attack_sound.set_volume(sfx_volume)

    def import_player_assets(self):
        character_path = 'Ashen Legacy - Lone Warrior'
        self.animations = {'up': [], 'down': [], 'left': [], 'right': [],
            'right_idle': [], 'left_idle': [], 'up_idle': [], 'down_idle': [],
            'right_attack': [], 'left_attack': [], 'up_attack': [], 'down_attack': []}

        for animation in self.animations.keys():
            full_path = os.path.join(character_path, animation)
            self.animations[animation] = import_folder(full_path)

    def input(self):
        if not self.attacking:
            keys = pygame.key.get_pressed()

            # movement input
            if keys[pygame.K_UP]:
                self.direction.y = -1
                self.status = 'up'
            elif keys[pygame.K_DOWN]:
                self.direction.y = 1
                self.status = 'down'
            else:
                self.direction.y = 0

            if keys[pygame.K_RIGHT]:
                self.direction.x = 1
                self.status = 'right'
            elif keys[pygame.K_LEFT]:
                self.direction.x = -1
                self.status = 'left'
            else:
                self.direction.x = 0

            # attack input
            if keys[pygame.K_SPACE]:
                self.attacking = True
                self.attack_time = pygame.time.get_ticks()
                self.create_attack()
                self.weapon_attack_sound.play()

            # magic input
            if keys[pygame.K_LCTRL]:
                self.attacking = True
                self.attack_time = pygame.time.get_ticks()
                style = list(magic_data.keys())[self.magic_index]
                strength = list(magic_data.values())[self.magic_index]['strength'] + self.stats['magic']
                cost = list(magic_data.values())[self.magic_index]['cost']
                self.create_magic(style, strength, cost)

            if keys[pygame.K_q] and self.can_switch_weapon:
                self.can_switch_weapon = False
                self.weapon_switch_time = pygame.time.get_ticks()

                if self.weapon_index < len(list(weapon_data.keys())) - 1:
                    self.weapon_index += 1
                else:
                    self.weapon_index = 0

                self.weapon = list(weapon_data.keys())[self.weapon_index]

            if keys[pygame.K_e] and self.can_switch_magic:
                self.can_switch_magic = False
                self.magic_switch_time = pygame.time.get_ticks()

                if self.magic_index < len(list(magic_data.keys())) - 1:
                    self.magic_index += 1
                else:
                    self.magic_index = 0

                self.magic = list(magic_data.keys())[self.magic_index]

    def get_status(self):

        # idle status
        if self.direction.x == 0 and self.direction.y == 0:
            if not 'idle' in self.status and not 'attack' in self.status:
                self.status = self.status + '_idle'

        if self.attacking:
            self.direction.x = 0
            self.direction.y = 0
            if not 'attack' in self.status:
                if 'idle' in self.status:
                    self.status = self.status.replace('_idle', '_attack')
                else:
                    self.status = self.status + '_attack'
        else:
            if 'attack' in self.status:
                self.status = self.status.replace('_attack', '')

    def cooldowns(self):
        current_time = pygame.time.get_ticks()

        if self.attacking:
            if current_time - self.attack_time >= self.attack_cooldown + weapon_data[self.weapon]['cooldown']:
                self.attacking = False
                self.destroy_attack()

        if not self.can_switch_weapon:
            if current_time - self.weapon_switch_time >= self.switch_duration_cooldown:
                self.can_switch_weapon = True

        if not self.can_switch_magic:
            if current_time - self.magic_switch_time >= self.switch_duration_cooldown:
                self.can_switch_magic = True

        if not self.vulnerable:
            if current_time - self.hurt_time >= self.invulnerability_duration:
                self.vulnerable = True

    def animate(self):
        animation = self.animations[self.status]

        # loop over the frame index
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0

        # set the image
        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center = self.hitbox.center)

        # flicker
        if not self.vulnerable:
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def get_full_weapon_damage(self):
        base_damage = self.stats['attack']
        weapon_damage = weapon_data[self.weapon]['damage']
        return base_damage + weapon_damage

    def get_full_magic_damage(self):
        base_damage = self.stats['magic']
        spell_damage = magic_data[self.magic]['strength']
        return base_damage + spell_damage

    def get_value_by_index(self, index):
        return list(self.stats.values())[index]

    def get_cost_by_index(self, index):
        return list(self.upgrade_cost.values())[index]

    def energy_recovery(self):
        if self.energy < self.stats['energy']:
            self.energy += 0.01 * self.stats['magic']
        else:
            self.energy = self.stats['energy']

    def die(self, groups):
        self.vulnerable = False  # Prevent further hits
        self.direction = pygame.math.Vector2()  # Stop movement
        death_animation = self.animation_player.frames['lone_warrior_death']
        ParticleEffect(self.rect.center, death_animation, groups)
        self.kill()

    def update(self):
        self.input()
        self.cooldowns()
        self.get_status()
        self.animate()
        self.move(self.stats['speed'])

class Enemy(Entity):
    def __init__(self, monster_name, pos, groups, obstacle_sprites, damage_player, trigger_death_particles, add_exp):

        # general setup
        super().__init__(groups)
        self.sprite_type = 'enemy'

        # graphics setup
        self.import_graphics(monster_name)
        self.status = 'down_idle'
        # Fallback-safe animation selection
        if self.status in self.animations and self.animations[self.status]:
            self.image = self.animations[self.status][self.frame_index]
        else:
            # Fallback to any available animation
            for anim in self.animations.values():
                if anim:
                    self.image = anim[0]
                    break
            else:
                raise ValueError(f"No animation frames found for enemy '{monster_name}' with status '{self.status}'")

        # movement
        self.rect = self.image.get_rect(topleft = pos)
        self.hitbox = self.rect.inflate(0, -10)
        self.obstacle_sprites = obstacle_sprites

        # stats
        self.monster_name = monster_name
        monster_info = monster_data[self.monster_name]
        self.health = monster_info['health']
        self.exp = monster_info['exp']
        self.speed = monster_info['speed']
        self.attack_damage = monster_info['damage']
        self.resistance = monster_info['resistance']
        self.attack_radius = monster_info['attack_radius']
        self.notice_radius = monster_info['notice_radius']
        self.attack_type = monster_info['attack_type']

        # player interaction
        self.can_attack = True
        self.attack_time = None
        self.attack_cooldown = 400
        self.damage_player = damage_player
        self.trigger_death_particles = trigger_death_particles
        self.add_exp = add_exp

        # invincibility timer
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 300

        # sounds
        self.death_sound = pygame.mixer.Sound('Ashen Legacy - SFX/death.wav')
        self.hit_sound = pygame.mixer.Sound('Ashen Legacy - SFX/hit.wav')
        self.attack_sound = pygame.mixer.Sound(monster_info['attack_sound'])
        self.death_sound.set_volume(sfx_volume)
        self.hit_sound.set_volume(sfx_volume)
        self.attack_sound.set_volume(sfx_volume)

    def import_graphics(self, name):
        character_path = f'Ashen Legacy - Enemies/{name}'
        self.animations = {'up': [], 'down': [], 'left': [], 'right': [],
            'right_idle': [], 'left_idle': [], 'up_idle': [], 'down_idle': [],
            'right_attack': [], 'left_attack': [], 'up_attack': [], 'down_attack': []}

        for animation in self.animations.keys():
            full_path = os.path.join(character_path, animation)
            self.animations[animation] = import_folder(full_path)

    def get_player_distance_direction(self, player):
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(player.rect.center)
        distance = (player_vec - enemy_vec).magnitude()

        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()

        return distance, direction

    def get_direction_status(self, player):
        direction_vector = pygame.math.Vector2(player.rect.center) - pygame.math.Vector2(self.rect.center)
        abs_x = abs(direction_vector.x)
        abs_y = abs(direction_vector.y)

        if abs_x > abs_y:
            return 'right' if direction_vector.x > 0 else 'left'
        else:
            return 'down' if direction_vector.y > 0 else 'up'

    def get_player_distance_direction(self, player):
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(player.rect.center)
        distance = (player_vec - enemy_vec).magnitude()

        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()

        return distance, direction

    def get_direction_status(self, player):
        direction_vector = pygame.math.Vector2(player.rect.center) - pygame.math.Vector2(self.rect.center)
        abs_x = abs(direction_vector.x)
        abs_y = abs(direction_vector.y)

        if abs_x > abs_y:
            return 'right' if direction_vector.x > 0 else 'left'
        else:
            return 'down' if direction_vector.y > 0 else 'up'

    def get_status(self, player):
        distance = self.get_player_distance_direction(player)[0]
        direction_status = self.get_direction_status(player)

        if distance <= self.attack_radius and self.can_attack:
            if self.status != direction_status + '_attack':
                self.frame_index = 0
            self.status = direction_status + '_attack'
        elif distance <= self.notice_radius:
            self.status = direction_status
        else:
            self.status = direction_status + '_idle'

    def actions(self, player):
        distance, direction = self.get_player_distance_direction(player)

        if 'attack' in self.status:
            if self.can_attack:
                self.attack_time = pygame.time.get_ticks()
                self.damage_player(self.attack_damage, self.attack_type)
                self.attack_sound.play()

        elif 'idle' not in self.status and distance <= self.notice_radius:
            self.direction = direction  # only move if within notice radius
        else:
            self.direction = pygame.math.Vector2()  # stop moving

    def animate(self):
        animation = self.animations.get(self.status, [])

        # Fallback if animation list is empty
        if not animation:
            for fallback in self.animations.values():
                if fallback:
                    animation = fallback
                    break
            else:
                return  # nothing to animate

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.status == 'down_attack':
                self.can_attack = False
            self.frame_index = 0

        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center = self.hitbox.center)

        if not self.vulnerable:
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if not self.can_attack:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

        if not self.vulnerable:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def get_damage(self, player, attack_type):
        if self.vulnerable:
            self.hit_sound.play()
            self.direction = self.get_player_distance_direction(player)[1]
            if attack_type == 'weapon':
                self.health -= player.get_full_weapon_damage()
            else:
                self.health -= player.get_full_magic_damage()
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False

    def check_death(self):
        if self.health <= 0:
            self.kill()
            self.trigger_death_particles(self.rect.center, self.monster_name)
            self.add_exp(self.exp)
            self.death_sound.play()

    def hit_reaction(self):
        if not self.vulnerable:
            self.direction *= -self.resistance

    def update(self):
        self.hit_reaction()
        self.move(self.speed)
        self.animate()
        self.cooldowns()
        self.check_death()

    def enemy_update(self, player):
        self.get_status(player)
        self.actions(player)

class Bush(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacle_sprites, image_path='Ashen Legacy - Bush.png'):
        super().__init__(groups)
        self.sprite_type = 'bush'
        self.image_path = image_path
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)

        self.obstacle_sprites = obstacle_sprites
        self.obstacle_sprites.add(self)

    def get_damage(self, player, attack_type):
        self.kill()

class Boss(Entity):
    def __init__(self, boss_name, pos, groups, obstacle_sprites, damage_player, trigger_death_particles, add_exp):

        # general setup
        super().__init__(groups)
        self.sprite_type = 'boss'

        # graphics setup
        self.import_graphics(boss_name)
        self.status = 'down_idle'

        # Fallback safe image selection
        if self.status in self.animations and len(self.animations[self.status]) > 0:
            self.image = self.animations[self.status][self.frame_index]
        else:
            # Look for any non-empty animation list
            for frames in self.animations.values():
                if frames:
                    self.image = frames[0]
                    break
            else:
                raise ValueError(f"No valid animation frames found for boss '{boss_name}'")

        # movement
        self.rect = self.image.get_rect(topleft = pos)
        self.hitbox = self.rect.inflate(0, -10)
        self.obstacle_sprites = obstacle_sprites

        # stats
        self.boss_name = boss_name
        monster_info = boss_data[self.boss_name]
        self.health = monster_info['health']
        self.exp = monster_info['exp']
        self.speed = monster_info['speed']
        self.attack_damage = monster_info['damage']
        self.resistance = monster_info['resistance']
        self.attack_radius = monster_info['attack_radius']
        self.notice_radius = monster_info['notice_radius']
        self.attack_type = monster_info['attack_type']

        # player interaction
        self.can_attack = True
        self.attack_time = None
        self.attack_cooldown = 2000
        self.damage_player = damage_player
        self.trigger_death_particles = trigger_death_particles
        self.add_exp = add_exp

        # invincibility timer
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 300

        # sounds
        self.death_sound = pygame.mixer.Sound('Ashen Legacy - SFX/death.wav')
        self.hit_sound = pygame.mixer.Sound('Ashen Legacy - SFX/hit.wav')
        self.attack_sound = pygame.mixer.Sound(monster_info['attack_sound'])
        self.death_sound.set_volume(sfx_volume)
        self.hit_sound.set_volume(sfx_volume)
        self.attack_sound.set_volume(sfx_volume)

    def import_graphics(self, name):
        character_path = f'Ashen Legacy - Boss/{name}'
        self.animations = {
            'up': [], 'down': [], 'left': [], 'right': [],
            'up_idle': [], 'down_idle': [], 'left_idle': [], 'right_idle': [],
            'up_attack': [], 'down_attack': [], 'left_attack': [], 'right_attack': []
        }

        for key in list(self.animations.keys()):
            standard_path = os.path.join(character_path, key)
            if os.path.exists(standard_path):
                self.animations[key] = import_folder(standard_path, scale_factor=3)

            # attack0, attack1, attack2
            if 'attack' in key:
                for i in range(3):
                    variant_path = f"{character_path}/{key}{i}"
                    if os.path.exists(variant_path):
                        self.animations[f"{key}{i}"] = import_folder(variant_path, scale_factor=3)

    def get_player_distance_direction(self, player):
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(player.rect.center)
        distance = (player_vec - enemy_vec).magnitude()

        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()

        return distance, direction

    def get_direction_status(self, player):
        direction_vector = pygame.math.Vector2(player.rect.center) - pygame.math.Vector2(self.rect.center)
        abs_x = abs(direction_vector.x)
        abs_y = abs(direction_vector.y)

        if abs_x > abs_y:
            return 'right' if direction_vector.x > 0 else 'left'
        else:
            return 'down' if direction_vector.y > 0 else 'up'

    # selects a random attack animation variant when close enough to the player
    def get_status(self, player):
        distance = self.get_player_distance_direction(player)[0]
        direction_status = self.get_direction_status(player)

        if distance <= self.attack_radius and self.can_attack:
            if not self.status.startswith(direction_status + '_attack'):
                self.current_attack_variant = random.randint(0, 2)  # pick 0, 1, or 2
                self.frame_index = 0
            self.status = f"{direction_status}_attack{self.current_attack_variant}"
        elif distance <= self.notice_radius:
            self.status = direction_status
        else:
            self.status = direction_status + '_idle'

    def actions(self, player):
        distance, direction = self.get_player_distance_direction(player)

        if 'attack' in self.status and self.can_attack:
            if self.frame_index == 0:
                self.attack_time = pygame.time.get_ticks()
                self.damage_player(self.attack_damage, self.attack_type)
                self.attack_sound.play()

        elif 'idle' not in self.status and distance <= self.notice_radius:
            self.direction = direction  # only move if within notice radius
        else:
            self.direction = pygame.math.Vector2()  # stop moving

    # handles animation variant switching and fallback if frame list is missing
    def animate(self):
        base_status = self.status

        # Handle attack variant (e.g., 'down_attack1')
        if 'attack' in self.status and not self.status in self.animations:
            base_status = self.status[:-1]  # remove the variant number
            variant_index = self.status[-1]  # last character (0, 1, or 2)
            combined_key = base_status + variant_index
            animation = self.animations.get(combined_key, [])
        else:
            animation = self.animations.get(base_status, [])

        if not animation:
            return  # skip animation if list is empty to avoid crash

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if 'attack' in base_status:
                self.can_attack = False
            self.frame_index = 0

        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.hitbox.center)

        if not self.vulnerable:
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if not self.can_attack:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

        if not self.vulnerable:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def get_damage(self, player, attack_type):
        if self.vulnerable:
            self.hit_sound.play()
            self.direction = self.get_player_distance_direction(player)[1]
            if attack_type == 'weapon':
                self.health -= player.get_full_weapon_damage()
            else:
                self.health -= player.get_full_magic_damage()
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False

    def check_death(self):
        if self.health <= 0:
            self.kill()
            self.trigger_death_particles(self.rect.center, self.boss_name)
            self.add_exp(self.exp)
            self.death_sound.play()

    def hit_reaction(self):
        if not self.vulnerable:
            self.direction *= -self.resistance

    def update(self):
        self.hit_reaction()
        self.move(self.speed)
        self.animate()
        self.cooldowns()
        self.check_death()

    def enemy_update(self, player):
        self.get_status(player)
        self.actions(player)

class UI:
    def __init__(self):

        # general
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)

        # bar setup
        self.health_bar_rect = pygame.Rect(10, 10, HEALTH_BAR_WIDTH, BAR_HEIGHT)
        self.energy_bar_rect = pygame.Rect(10, 34, ENERGY_BAR_WIDTH,BAR_HEIGHT)

        # convert weapon dictionary
        self.weapon_graphics = []
        for weapon in weapon_data.values():
            path = weapon['graphic']
            weapon = pygame.image.load(path).convert_alpha()
            self.weapon_graphics.append(weapon)

        # convert magic dictionary
        self.magic_graphics = []
        for magic in magic_data.values():
            magic = pygame.image.load(magic['graphic']).convert_alpha()
            self.magic_graphics.append(magic)

    def show_bar(self, current, max_amount, bg_rect, colour):
        # draw bg
        pygame.draw.rect(self.display_surface, UI_BG_COLOUR, bg_rect)

        # converting stat to pixel
        ratio = current / max_amount
        current_width = bg_rect.width * ratio
        current_rect = bg_rect.copy()
        current_rect.width = current_width

        # drawing the bar
        pygame.draw.rect(self.display_surface, colour, current_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOUR, bg_rect, 3)

    def show_exp(self, exp):
        text_surf = self.font.render(str(int(exp)), False, TEXT_COLOUR)
        x = self.display_surface.get_size()[0] - 20
        y = self.display_surface.get_size()[1] - 20
        text_rect = text_surf.get_rect(bottomright = (x, y))

        pygame.draw.rect(self.display_surface, UI_BG_COLOUR, text_rect.inflate(20, 20))
        self.display_surface.blit(text_surf, text_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOUR, text_rect.inflate(20, 20), 3)

    def selection_box(self, left, top, has_switched):
        bg_rect = pygame.Rect(left, top, ITEM_BOX_SIZE, ITEM_BOX_SIZE)
        pygame.draw.rect(self.display_surface, UI_BG_COLOUR, bg_rect)
        if has_switched:
            pygame.draw.rect(self.display_surface, UI_BORDER_COLOUR_ACTIVE, bg_rect, 3)
        else:
            pygame.draw.rect(self.display_surface, UI_BORDER_COLOUR, bg_rect, 3)
        return bg_rect

    def weapon_overlay(self, weapon_index, has_switched):
        bg_rect = self.selection_box(10, 630, has_switched)
        weapon_surf = self.weapon_graphics[weapon_index]
        weapon_rect = weapon_surf.get_rect(center = bg_rect.center)

        self.display_surface.blit(weapon_surf, weapon_rect)

    def magic_overlay(self, magic_index, has_switched):
        bg_rect = self.selection_box(80, 635, has_switched)
        magic_surf = self.magic_graphics[magic_index]
        magic_rect = magic_surf.get_rect(center=bg_rect.center)

        self.display_surface.blit(magic_surf, magic_rect)

    def display(self, player):
        self.show_bar(player.health, player.stats['health'], self.health_bar_rect, HEALTH_COLOUR)
        self.show_bar(player.energy, player.stats['energy'], self.energy_bar_rect, ENERGY_COLOUR)

        self.show_exp(player.exp)

        self.weapon_overlay(player.weapon_index, not player.can_switch_weapon)
        self.magic_overlay(player.magic_index, not player.can_switch_magic)

class Weapon(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        super().__init__(groups)
        self.sprite_type = 'weapon'
        direction = player.status.split('_')[0]

        # graphic
        full_path = f'Ashen Legacy - Weapons/{player.weapon}/{direction}.png'
        self.image = pygame.image.load(full_path).convert_alpha()

        # placement
        if direction == 'right':
            self.rect = self.image.get_rect(midleft = player.rect.midright + pygame.math.Vector2(-10, 16))
        elif direction == 'left':
            self.rect = self.image.get_rect(midright=player.rect.midleft + pygame.math.Vector2(10, 16))
        elif direction == 'down':
            self.rect = self.image.get_rect(midtop=player.rect.midbottom + pygame.math.Vector2(-10, -20))
        else:
            self.rect = self.image.get_rect(midbottom = player.rect.midtop + pygame.math.Vector2(-10, 20))

class MagicPlayer:
    def __init__(self,animation_player):
        self.animation_player = animation_player
        self.sounds = {
        'heal': pygame.mixer.Sound('Ashen Legacy - SFX/heal.wav'),
        'flame': pygame.mixer.Sound('Ashen Legacy - SFX/Fire.wav')
        }

    def heal(self,player,strength,cost,groups):
        if player.energy >= cost:
            self.sounds['heal'].play()
            player.health += strength
            player.energy -= cost
            if player.health >= player.stats['health']:
                player.health = player.stats['health']
            self.animation_player.create_particles('aura',player.rect.center,groups)
            self.animation_player.create_particles('heal',player.rect.center,groups)

    def flame(self, player, cost, groups):
        if player.energy >= cost:
            player.energy -= cost
            self.sounds['flame'].play()

            if player.status.split('_')[0] == 'right': direction = pygame.math.Vector2(1,0)
            elif player.status.split('_')[0] == 'left': direction = pygame.math.Vector2(-1,0)
            elif player.status.split('_')[0] == 'up': direction = pygame.math.Vector2(0,-1)
            else: direction = pygame.math.Vector2(0,1)

            for i in range(1,6):
                if direction.x: #horizontal
                    offset_x = (direction.x * i) * TILESIZE
                    x = player.rect.centerx + offset_x + randint(-TILESIZE // 3, TILESIZE // 3)
                    y = player.rect.centery + randint(-TILESIZE // 3, TILESIZE // 3)
                    self.animation_player.create_particles('flame',(x,y),groups)
                else: # vertical
                    offset_y = (direction.y * i) * TILESIZE
                    x = player.rect.centerx + randint(-TILESIZE // 3, TILESIZE // 3)
                    y = player.rect.centery + offset_y + randint(-TILESIZE // 3, TILESIZE // 3)
                    self.animation_player.create_particles('flame',(x,y),groups)

class Upgrade:
    def __init__(self, player):

        # general setup
        self.display_surface = pygame.display.get_surface()
        self.player = player
        self.attribute_nr = len(player.stats)
        self.attribute_names = list(player.stats.keys())
        self.max_values = list(player.max_stats.values())
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)

        # item creation
        self.height = self.display_surface.get_size()[1] * 0.8
        self.width = self.display_surface.get_size()[0] // 6
        self.create_items()

        # selection system
        self.selection_index = 0
        self.selection_time = None
        self.can_move = True

    def input(self):
        keys = pygame.key.get_pressed()

        if self.can_move:
            if keys[pygame.K_RIGHT] and self.selection_index < self.attribute_nr - 1:
                self.selection_index += 1
                self.can_move = False
                self.selection_time = pygame.time.get_ticks()
            elif keys[pygame.K_LEFT] and self.selection_index >= 1:
                self.selection_index -= 1
                self.can_move = False
                self.selection_time = pygame.time.get_ticks()

            if keys[pygame.K_SPACE]:
                self.can_move = False
                self.selection_time = pygame.time.get_ticks()
                self.item_list[self.selection_index].trigger(self.player)

    def selection_cooldown(self):
        if not self.can_move:
            current_time = pygame.time.get_ticks()
            if current_time - self.selection_time >= 300:
                self.can_move = True

    def create_items(self):
        self.item_list = []

        for item, index in enumerate(range(self.attribute_nr)):
            # horizontal position
            full_width = self.display_surface.get_size()[0]
            increment = full_width // self.attribute_nr
            left = (item * increment) + (increment - self.width) // 2

            # vertical position
            top = self.display_surface.get_size()[1] * 0.1

            # create the object
            item = Item(left, top, self.width, self.height, index, self.font)
            self.item_list.append(item)

    def display(self):
        self.input()
        self.selection_cooldown()

        for index, item in enumerate(self.item_list):
            # get attributes
            name = self.attribute_names[index]
            value = self.player.get_value_by_index(index)
            max_value = self.max_values[index]
            cost = self.player.get_cost_by_index(index)
            item.display(self.display_surface, self.selection_index, name, value, max_value, cost)

class Item:
    def __init__(self, l, t, w, h, index, font):
        self.rect = pygame.Rect(l, t, w, h)
        self.index = index
        self.font = font

    def display_names(self, surface, name, cost, selected):
        colour = TEXT_COLOUR_SELECTED if selected else TEXT_COLOUR

        # title
        title_surf = self.font.render(name, False, colour)
        title_rect = title_surf.get_rect(midtop=self.rect.midtop + pygame.math.Vector2(0, 20))

        # cost
        cost_surf = self.font.render(f'{int(cost)}', False, colour)
        cost_rect = cost_surf.get_rect(midbottom=self.rect.midbottom - pygame.math.Vector2(0, 20))

        # draw
        surface.blit(title_surf, title_rect)
        surface.blit(cost_surf, cost_rect)

    def display_bar(self, surface, value, max_value, selected):

        # drawing setup
        top = self.rect.midtop + pygame.math.Vector2(0, 60)
        bottom = self.rect.midbottom - pygame.math.Vector2(0, 60)
        colour = BAR_COLOUR_SELECTED if selected else BAR_COLOUR

        # bar setup
        full_height = bottom[1] - top[1]
        relative_number = (value / max_value) * full_height
        value_rect = pygame.Rect(top[0] - 15, bottom[1] - relative_number, 30, 10)

        # draw elements
        pygame.draw.line(surface, colour, top, bottom, 5)
        pygame.draw.rect(surface, colour, value_rect)

    def trigger(self, player):
        upgrade_attribute = list(player.stats.keys())[self.index]

        if player.exp >= player.upgrade_cost[upgrade_attribute] and player.stats[upgrade_attribute] < player.max_stats[
            upgrade_attribute]:
            player.exp -= player.upgrade_cost[upgrade_attribute]
            player.stats[upgrade_attribute] *= 1.2
            player.upgrade_cost[upgrade_attribute] *= 1.4

        if player.stats[upgrade_attribute] > player.max_stats[upgrade_attribute]:
            player.stats[upgrade_attribute] = player.max_stats[upgrade_attribute]

        save_play_data(player, player.level.level_num, player.level.enemies, player.level.bushes)

    def display(self, surface, selection_num, name, value, max_value, cost):
        if self.index == selection_num:
            pygame.draw.rect(surface, UPGRADE_BG_COLOUR_SELECTED, self.rect)
            pygame.draw.rect(surface, UI_BORDER_COLOUR, self.rect, 4)
        else:
            pygame.draw.rect(surface, UI_BG_COLOUR, self.rect)
            pygame.draw.rect(surface, UI_BORDER_COLOUR, self.rect, 4)

        self.display_names(surface, name, cost, self.index == selection_num)
        self.display_bar(surface, value, max_value, self.index == selection_num)

# handles the tutorial level: teaches player controls and starts the game
class Level_0:
    def __init__(self, level, restore_exp=None, restore_stats=None, restore_upgrade_cost=None, load_saved_data=True):
        self.player_death_triggered = False
        self.player_death_time = 0

        self.session_exp = 0  # EXP earned this life only

        self.saved_data = load_player_data(level) if load_saved_data else {}

        # Default fallbacks
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        default_stats = {'health': 100, 'energy': 60, 'attack': 10, 'magic': 4, 'speed': 5}
        default_upgrade_cost = {'health': 100, 'energy': 100, 'attack': 100, 'magic': 100, 'speed': 100}

        self.initial_exp = (
            restore_exp if restore_exp is not None else transfer_data.get('exp', 0)
        )
        self.initial_stats = restore_stats if restore_stats is not None else transfer_data.get('stats', default_stats)
        self.initial_upgrade_cost = restore_upgrade_cost if restore_upgrade_cost is not None else transfer_data.get(
            'upgrade_cost', default_upgrade_cost)

        self.enemies = []
        self.bushes = []
        self.level_num = level
        # get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        # sprite group setup
        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        # attack sprites
        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()

        # particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        # sprite setup
        self.create_map()

        # user interface
        self.ui = UI()
        self.upgrade = Upgrade(self.player)

        self.tutorial_text = "Use arrow keys to move!"
        self.tutorial_font = pygame.font.Font(UI_FONT, 24)
        self.tutorial_timer = pygame.time.get_ticks()

    def get_tutorial_message(self, x, y, tile):
        if tile == '1':
            return "Use arrow keys to move!"
        elif tile == '2':
            return "Press Q to switch weapons!"
        elif tile == '3':
            return "Press E to switch magic!"
        elif tile == '4':
            return "Hold CTRL to use your equipped magic spell!"
        elif tile == '5':
            return "Press SPACE to attack with your weapon!"
        elif tile == '6':
            return "You can destroy obstacles with your attacks!"
        elif tile == '7':
            return "Now fight your first enemies!"
        elif tile == '8':
            return "Press M to level up!"
        elif tile == '9':
            return "Press Esc to save your progress!"
        elif tile == '0':
            return "Walk into the portal to begin your adventure!"
        return None

    def create_map(self):
         world_map = WORLD_MAP_0
         for row_index, row in enumerate(world_map):
             for col_index, col in enumerate(row):
                 x = col_index * TILESIZE
                 y = row_index * TILESIZE

                 if col == 'x':
                     Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object',
                          'Ashen Legacy - Tree Border.png')

                 elif col == 'p':
                     # Default position based on 'p' tile
                     start_pos = (x, y)

                     # Override with saved position if available
                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']
                         if 'x' in pdata and 'y' in pdata:
                             start_pos = (pdata['x'], pdata['y'])

                     self.player = Player(
                         start_pos,
                         [self.visible_sprites],
                         self.obstacle_sprites,
                         self.create_attack,
                         self.destroy_attack,
                         self.create_magic,
                         self.saved_data,
                         self.animation_player,
                         initial_stats=self.initial_stats,
                         initial_exp=self.initial_exp,
                         initial_upgrade_cost=self.initial_upgrade_cost
                     )

                     self.player.level = self

                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']

                         self.player.health = pdata.get('health', self.player.health)
                         self.player.energy = pdata.get('energy', self.player.energy)
                         # Only override EXP if it's actually in the saved data
                         if 'exp' in pdata:
                             self.player.exp = pdata['exp']
                         else:
                             self.player.exp = self.initial_exp
                         self.player.stats = pdata.get('stats', self.player.stats)
                         self.player.upgrade_cost = pdata.get('upgrade_cost', self.player.upgrade_cost)
                         self.player.weapon_index = pdata.get('weapon_index', self.player.weapon_index)
                         self.player.magic_index = pdata.get('magic_index', self.player.magic_index)

                 elif col == 'f':
                     portal_frames = load_portal_frames("Ashen Legacy - Portal")
                     self.portal = Portal((x, y), portal_frames, [self.visible_sprites])

         # Load saved enemies if any
         if self.saved_data and 'enemies' in self.saved_data:
             for enemy_data in self.saved_data['enemies']:
                 enemy = Enemy(
                     enemy_data['type'],
                     (enemy_data['x'], enemy_data['y']),
                     [self.visible_sprites, self.attackable_sprites],
                     self.obstacle_sprites,
                     self.damage_player,
                     self.trigger_death_particles,
                     self.add_exp
                 )
                 enemy.health = enemy_data['health']
                 self.enemies.append(enemy)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'e':
                         enemy_type = random.choice(['skeleton', 'goblin', 'ghost'])
                         enemy = Enemy(
                             enemy_type,
                             (x, y),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             self.damage_player,
                             self.trigger_death_particles,
                             self.add_exp
                         )
                         self.enemies.append(enemy)

         # Load saved bushes
         if self.saved_data and 'bushes' in self.saved_data:
             for bush_data in self.saved_data['bushes']:
                 bush = Bush((bush_data['x'], bush_data['y']),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             bush_data.get('image_path', 'Ashen Legacy - Vine.png'))
                 self.bushes.append(bush)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'b':
                         bush = Bush((x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites)
                         self.bushes.append(bush)

         save_play_data(self.player, self.level_num, self.enemies, self.bushes)

    def create_attack(self):
        self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, strength, cost):
        if style == 'heal':
            self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])

        if style == 'flame':
            self.magic_player.flame(self.player, cost, [self.visible_sprites, self.attack_sprites])

    def destroy_attack(self):
        if self.current_attack:
            self.current_attack.kill()
        self.current_attack = None

    def player_attack_logic(self):
        if self.attack_sprites:
            for attack_sprite in self.attack_sprites:
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'bush':
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2(0, 75)
                            for leaf in range(randint(3, 6)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                            target_sprite.kill()
                        elif target_sprite.sprite_type in ['enemy', 'boss']:
                            target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.health -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

    def add_exp(self, amount):
        self.player.exp += amount
        self.session_exp += amount

    def toggle_menu(self):

        self.game_paused = not self.game_paused

    def trigger_death_particles(self, pos, particle_type):

        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    # checks if player is on a portal tile ('f')
    # if so saves game data and transfers exp/stats to the next level
    def check_exit_tile(self):
        player_tile_x = self.player.rect.centerx // TILESIZE
        player_tile_y = self.player.rect.centery // TILESIZE

        # Choose the correct map for the current level
        if self.level_num == 0:
            world_map = WORLD_MAP_0
        elif self.level_num == 1:
            world_map = WORLD_MAP_1
        elif self.level_num == 2:
            world_map = WORLD_MAP_2
        elif self.level_num == 3:
            world_map = WORLD_MAP_3
        else:
            return

        if 0 <= player_tile_y < len(world_map) and 0 <= player_tile_x < len(world_map[0]):
            current_tile = world_map[player_tile_y][player_tile_x]
            if current_tile == 'f':
                # Always show this message near 'f' tiles
                self.tutorial_text = "Press R to proceed to the next level"
                self.tutorial_timer = pygame.time.get_ticks()

                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    save_play_data(self.player, self.level_num, self.enemies, self.bushes)

                    # Update persistent EXP before moving to next level
                    if os.path.exists("persistent_exp.json"):
                        with open("persistent_exp.json", "r") as f:
                            data = json.load(f)
                            previous_total = data.get("earned_exp", 0)
                    else:
                        previous_total = 0

                    with open("persistent_exp.json", "w") as f:
                        json.dump({"earned_exp": self.player.exp}, f)

                    # Save exp/stats for next level
                    with open("exp_transfer.json", "w") as f:
                        json.dump({
                            'exp': self.player.exp,
                            'stats': self.player.stats,
                            'upgrade_cost': self.player.upgrade_cost,
                            'total_exp': self.player.exp
                        }, f)

                    self.session_exp = 0  # Reset session EXP after committing

                    next_level = self.level_num + 1 if self.level_num < 3 else 1
                    new_game = Game(level=next_level)
                    new_game.run()
                    pygame.quit()
                    sys.exit()

    def draw_tutorial_text(self):
        if self.tutorial_text and pygame.time.get_ticks() - self.tutorial_timer < 5000:
            text_surface = self.tutorial_font.render(self.tutorial_text, True, 'white')
            bg_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
            pygame.draw.rect(self.display_surface, (0, 0, 0), bg_rect.inflate(20, 10))
            self.display_surface.blit(text_surface, bg_rect)
        else:
            self.tutorial_text = None

    def check_tutorial_trigger(self):
        player_tile_x = self.player.rect.centerx // TILESIZE
        player_tile_y = self.player.rect.centery // TILESIZE

        if 0 <= player_tile_y < len(WORLD_MAP_0) and 0 <= player_tile_x < len(WORLD_MAP_0[0]):
            current_tile = WORLD_MAP_0[player_tile_y][player_tile_x]

            # Only show a message if on a tutorial tile
            if current_tile in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
                self.tutorial_text = self.get_tutorial_message(player_tile_x, player_tile_y, current_tile)
                self.tutorial_timer = pygame.time.get_ticks()

    def restart_level(self):
        # Load fallback values from exp_transfer.json
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        new_game = Game(
            level=self.level_num,
            restore_exp=transfer_data.get('exp', 0),
            restore_stats=transfer_data.get('stats'),
            restore_upgrade_cost=transfer_data.get('upgrade_cost')
        )
        new_game.run()
        pygame.quit()
        sys.exit()

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.enemy_update(self.player)
            self.visible_sprites.update()
            self.player_attack_logic()
            self.player.energy_recovery()
        self.check_tutorial_trigger()
        self.draw_tutorial_text()
        self.check_exit_tile()

        if self.player.health <= 0 and not self.player_death_triggered:
            self.player.die(self.visible_sprites)  # Trigger death animation
            self.player_death_triggered = True
            self.player_death_time = pygame.time.get_ticks()

        # If already dead, wait for animation to finish before restart
        if self.player_death_triggered:
            if pygame.time.get_ticks() - self.player_death_time >= 2000:  # wait 2 seconds
                self.restart_level()
                return

# first combat focused level
class Level_1:
    def __init__(self, level, restore_exp=None, restore_stats=None, restore_upgrade_cost=None, load_saved_data=True):
        self.saved_data = load_player_data(level) if load_saved_data else {}

        self.player_death_triggered = False
        self.player_death_time = 0

        self.session_exp = 0  # EXP earned this life only

        # Default fallbacks
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        default_stats = {'health': 100, 'energy': 60, 'attack': 10, 'magic': 4, 'speed': 5}
        default_upgrade_cost = {'health': 100, 'energy': 100, 'attack': 100, 'magic': 100, 'speed': 100}

        self.initial_exp = (
            restore_exp if restore_exp is not None else transfer_data.get('exp', 0)
        )
        self.initial_stats = restore_stats if restore_stats is not None else transfer_data.get('stats', default_stats)
        self.initial_upgrade_cost = restore_upgrade_cost if restore_upgrade_cost is not None else transfer_data.get(
            'upgrade_cost', default_upgrade_cost)

        self.enemies = []
        self.bushes = []
        self.level_num = level
        # get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        # sprite group setup
        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        # attack sprites
        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()

        # particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        # sprite setup
        self.create_map()

        # user interface
        self.ui = UI()
        self.upgrade = Upgrade(self.player)

        self.tutorial_text = None
        self.tutorial_font = pygame.font.Font(UI_FONT, 24)
        self.tutorial_timer = 0

    def draw_tutorial_text(self):
        if self.tutorial_text and pygame.time.get_ticks() - self.tutorial_timer < 5000:
            text_surface = self.tutorial_font.render(self.tutorial_text, True, 'white')
            bg_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
            pygame.draw.rect(self.display_surface, (0, 0, 0), bg_rect.inflate(20, 10))
            self.display_surface.blit(text_surface, bg_rect)
        else:
            self.tutorial_text = None

    def create_map(self):
         world_map = WORLD_MAP_1
         for row_index, row in enumerate(world_map):
             for col_index, col in enumerate(row):
                 x = col_index * TILESIZE
                 y = row_index * TILESIZE

                 if col == 'x':
                     Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object',
                          'Ashen Legacy - Tree Border.png')

                 elif col == 'p':
                     # Default position based on 'p' tile
                     start_pos = (x, y)

                     # Override with saved position if available
                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']
                         if 'x' in pdata and 'y' in pdata:
                             start_pos = (pdata['x'], pdata['y'])

                     self.player = Player(
                         start_pos,
                         [self.visible_sprites],
                         self.obstacle_sprites,
                         self.create_attack,
                         self.destroy_attack,
                         self.create_magic,
                         self.saved_data,
                         self.animation_player,
                         initial_stats=self.initial_stats,
                         initial_exp=self.initial_exp,
                         initial_upgrade_cost=self.initial_upgrade_cost
                     )

                     self.player.level = self

                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']

                         self.player.health = pdata.get('health', self.player.health)
                         self.player.energy = pdata.get('energy', self.player.energy)
                         # Only override EXP if it's actually in the saved data
                         if 'exp' in pdata:
                             self.player.exp = pdata['exp']
                         else:
                             self.player.exp = self.initial_exp
                         self.player.stats = pdata.get('stats', self.player.stats)
                         self.player.upgrade_cost = pdata.get('upgrade_cost', self.player.upgrade_cost)
                         self.player.weapon_index = pdata.get('weapon_index', self.player.weapon_index)
                         self.player.magic_index = pdata.get('magic_index', self.player.magic_index)

                 elif col == 'f':
                     portal_frames = load_portal_frames("Ashen Legacy - Portal")
                     self.portal = Portal((x, y), portal_frames, [self.visible_sprites])

         # Load saved enemies if any
         if self.saved_data and 'enemies' in self.saved_data:
             for enemy_data in self.saved_data['enemies']:
                 enemy = Enemy(
                     enemy_data['type'],
                     (enemy_data['x'], enemy_data['y']),
                     [self.visible_sprites, self.attackable_sprites],
                     self.obstacle_sprites,
                     self.damage_player,
                     self.trigger_death_particles,
                     self.add_exp
                 )
                 enemy.health = enemy_data['health']
                 self.enemies.append(enemy)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'e':
                         enemy_type = random.choice(['skeleton', 'goblin', 'ghost'])
                         enemy = Enemy(
                             enemy_type,
                             (x, y),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             self.damage_player,
                             self.trigger_death_particles,
                             self.add_exp
                         )
                         self.enemies.append(enemy)

         # Load saved bushes
         if self.saved_data and 'bushes' in self.saved_data:
             for bush_data in self.saved_data['bushes']:
                 bush = Bush((bush_data['x'], bush_data['y']),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             bush_data.get('image_path', 'Ashen Legacy - Vine.png'))  # <-- Use saved or default to vine
                 self.bushes.append(bush)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'b':
                         bush = Bush((x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites)
                         self.bushes.append(bush)

         save_play_data(self.player, self.level_num, self.enemies, self.bushes)

    def create_attack(self):
        self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, strength, cost):
        if style == 'heal':
            self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])

        if style == 'flame':
            self.magic_player.flame(self.player, cost, [self.visible_sprites, self.attack_sprites])

    def destroy_attack(self):
        if self.current_attack:
            self.current_attack.kill()
        self.current_attack = None

    def player_attack_logic(self):
        if self.attack_sprites:
            for attack_sprite in self.attack_sprites:
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'bush':
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2(0, 75)
                            for leaf in range(randint(3, 6)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                            target_sprite.kill()
                        elif target_sprite.sprite_type in ['enemy', 'boss']:
                            target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.health -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

    def add_exp(self, amount):
        self.player.exp += amount
        self.session_exp += amount

    def toggle_menu(self):

        self.game_paused = not self.game_paused

    def trigger_death_particles(self, pos, particle_type):

        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    # checks if player is on a portal tile ('f')
    # if so saves game data and transfers exp/stats to the next level
    def check_exit_tile(self):
        player_tile_x = self.player.rect.centerx // TILESIZE
        player_tile_y = self.player.rect.centery // TILESIZE

        # Choose the correct map for the current level
        if self.level_num == 0:
            world_map = WORLD_MAP_0
        elif self.level_num == 1:
            world_map = WORLD_MAP_1
        elif self.level_num == 2:
            world_map = WORLD_MAP_2
        elif self.level_num == 3:
            world_map = WORLD_MAP_3
        else:
            return

        if 0 <= player_tile_y < len(world_map) and 0 <= player_tile_x < len(world_map[0]):
            current_tile = world_map[player_tile_y][player_tile_x]
            if current_tile == 'f':
                # Always show this message near 'f' tiles
                self.tutorial_text = "Press R to proceed to the next level"
                self.tutorial_timer = pygame.time.get_ticks()

                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    save_play_data(self.player, self.level_num, self.enemies, self.bushes)

                    # Update persistent EXP before moving to next level
                    if os.path.exists("persistent_exp.json"):
                        with open("persistent_exp.json", "r") as f:
                            data = json.load(f)
                            previous_total = data.get("earned_exp", 0)
                    else:
                        previous_total = 0

                    with open("persistent_exp.json", "w") as f:
                        json.dump({"earned_exp": self.player.exp}, f)

                    # Save exp/stats for next level
                    with open("exp_transfer.json", "w") as f:
                        json.dump({
                            'exp': self.player.exp,
                            'stats': self.player.stats,
                            'upgrade_cost': self.player.upgrade_cost,
                            'total_exp': self.player.exp
                        }, f)

                    self.session_exp = 0  # Reset session EXP after committing

                    next_level = self.level_num + 1 if self.level_num < 3 else 1
                    new_game = Game(level=next_level)
                    new_game.run()
                    pygame.quit()
                    sys.exit()

    def restart_level(self):
        # Load fallback values from exp_transfer.json
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        new_game = Game(
            level=self.level_num,
            restore_exp=transfer_data.get('exp', 0),
            restore_stats=transfer_data.get('stats'),
            restore_upgrade_cost=transfer_data.get('upgrade_cost')
        )
        new_game.run()
        pygame.quit()
        sys.exit()

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.enemy_update(self.player)
            self.visible_sprites.update()
            self.player_attack_logic()
            self.player.energy_recovery()
        self.check_exit_tile()
        self.draw_tutorial_text()

        if self.player.health <= 0 and not self.player_death_triggered:
            self.player.die(self.visible_sprites)  # Trigger death animation
            self.player_death_triggered = True
            self.player_death_time = pygame.time.get_ticks()

        # If already dead, wait for animation to finish before restart
        if self.player_death_triggered:
            if pygame.time.get_ticks() - self.player_death_time >= 2000:  # wait 2 seconds
                self.restart_level()
                return

# cave level with vines as obstacles
class Level_2:
    def __init__(self, level, restore_exp=None, restore_stats=None, restore_upgrade_cost=None, load_saved_data=True):
        self.saved_data = load_player_data(level) if load_saved_data else {}

        self.player_death_triggered = False
        self.player_death_time = 0

        self.session_exp = 0  # EXP earned this life only

        # Default fallbacks
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        default_stats = {'health': 100, 'energy': 60, 'attack': 10, 'magic': 4, 'speed': 5}
        default_upgrade_cost = {'health': 100, 'energy': 100, 'attack': 100, 'magic': 100, 'speed': 100}

        self.initial_exp = (
            restore_exp if restore_exp is not None else transfer_data.get('exp', 0)
        )
        self.initial_stats = restore_stats if restore_stats is not None else transfer_data.get('stats', default_stats)
        self.initial_upgrade_cost = restore_upgrade_cost if restore_upgrade_cost is not None else transfer_data.get(
            'upgrade_cost', default_upgrade_cost)

        self.enemies = []
        self.bushes = []
        self.level_num = level
        # get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        # sprite group setup
        self.visible_sprites = YSortCameraGroup('Ashen Legacy - Cave Background.png')
        self.obstacle_sprites = pygame.sprite.Group()

        # attack sprites
        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()

        # particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        # sprite setup
        self.create_map()

        # user interface
        self.ui = UI()
        self.upgrade = Upgrade(self.player)

        self.tutorial_text = None
        self.tutorial_font = pygame.font.Font(UI_FONT, 24)
        self.tutorial_timer = 0

    def draw_tutorial_text(self):
        if self.tutorial_text and pygame.time.get_ticks() - self.tutorial_timer < 5000:
            text_surface = self.tutorial_font.render(self.tutorial_text, True, 'white')
            bg_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
            pygame.draw.rect(self.display_surface, (0, 0, 0), bg_rect.inflate(20, 10))
            self.display_surface.blit(text_surface, bg_rect)
        else:
            self.tutorial_text = None

    def create_map(self):
         world_map = WORLD_MAP_2
         for row_index, row in enumerate(world_map):
             for col_index, col in enumerate(row):
                 x = col_index * TILESIZE
                 y = row_index * TILESIZE

                 if col == 'x':
                     Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object', 'Ashen Legacy - Cave Wall.png')

                 elif col == 'p':
                     # Default position based on 'p' tile
                     start_pos = (x, y)

                     # Override with saved position if available
                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']
                         if 'x' in pdata and 'y' in pdata:
                             start_pos = (pdata['x'], pdata['y'])

                     self.player = Player(
                         start_pos,
                         [self.visible_sprites],
                         self.obstacle_sprites,
                         self.create_attack,
                         self.destroy_attack,
                         self.create_magic,
                         self.saved_data,
                         self.animation_player,
                         initial_stats=self.initial_stats,
                         initial_exp=self.initial_exp,
                         initial_upgrade_cost=self.initial_upgrade_cost
                     )

                     self.player.level = self

                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']

                         self.player.health = pdata.get('health', self.player.health)
                         self.player.energy = pdata.get('energy', self.player.energy)
                         # Only override EXP if it's actually in the saved data
                         if 'exp' in pdata:
                             self.player.exp = pdata['exp']
                         else:
                             self.player.exp = self.initial_exp
                         self.player.stats = pdata.get('stats', self.player.stats)
                         self.player.upgrade_cost = pdata.get('upgrade_cost', self.player.upgrade_cost)
                         self.player.weapon_index = pdata.get('weapon_index', self.player.weapon_index)
                         self.player.magic_index = pdata.get('magic_index', self.player.magic_index)

                 elif col == 'f':
                     portal_frames = load_portal_frames("Ashen Legacy - Portal")
                     self.portal = Portal((x, y), portal_frames, [self.visible_sprites])


         # Load saved enemies if any
         if self.saved_data and 'enemies' in self.saved_data:
             for enemy_data in self.saved_data['enemies']:
                 enemy = Enemy(
                     enemy_data['type'],
                     (enemy_data['x'], enemy_data['y']),
                     [self.visible_sprites, self.attackable_sprites],
                     self.obstacle_sprites,
                     self.damage_player,
                     self.trigger_death_particles,
                     self.add_exp
                 )
                 enemy.health = enemy_data['health']
                 self.enemies.append(enemy)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'e':
                         enemy_type = random.choice(['skeleton', 'goblin', 'ghost'])
                         enemy = Enemy(
                             enemy_type,
                             (x, y),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             self.damage_player,
                             self.trigger_death_particles,
                             self.add_exp
                         )
                         self.enemies.append(enemy)

         # Load saved bushes
         if self.saved_data and 'bushes' in self.saved_data:
             for bush_data in self.saved_data['bushes']:
                 bush = Bush((bush_data['x'], bush_data['y']),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             bush_data.get('image_path', 'Ashen Legacy - Vine.png'))
                 self.bushes.append(bush)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'v':
                         bush = Bush((x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites,
                                     'Ashen Legacy - Vine.png')
                         self.bushes.append(bush)

         save_play_data(self.player, self.level_num, self.enemies, self.bushes)

    def create_attack(self):
        self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, strength, cost):
        if style == 'heal':
            self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])

        if style == 'flame':
            self.magic_player.flame(self.player, cost, [self.visible_sprites, self.attack_sprites])

    def destroy_attack(self):
        if self.current_attack:
            self.current_attack.kill()
        self.current_attack = None

    def player_attack_logic(self):
        if self.attack_sprites:
            for attack_sprite in self.attack_sprites:
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'bush':
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2(0, 75)
                            for leaf in range(randint(3, 6)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                            target_sprite.kill()
                        elif target_sprite.sprite_type in ['enemy', 'boss']:
                            target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.health -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

    def add_exp(self, amount):
        self.player.exp += amount
        self.session_exp += amount

    def toggle_menu(self):

        self.game_paused = not self.game_paused

    def trigger_death_particles(self, pos, particle_type):

        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    # checks if player is on a portal tile ('f')
    # if so saves game data and transfers exp/stats to the next level
    def check_exit_tile(self):
        player_tile_x = self.player.rect.centerx // TILESIZE
        player_tile_y = self.player.rect.centery // TILESIZE

        # Choose the correct map for the current level
        if self.level_num == 0:
            world_map = WORLD_MAP_0
        elif self.level_num == 1:
            world_map = WORLD_MAP_1
        elif self.level_num == 2:
            world_map = WORLD_MAP_2
        elif self.level_num == 3:
            world_map = WORLD_MAP_3
        else:
            return

        if 0 <= player_tile_y < len(world_map) and 0 <= player_tile_x < len(world_map[0]):
            current_tile = world_map[player_tile_y][player_tile_x]
            if current_tile == 'f':
                # Always show this message near 'f' tiles
                self.tutorial_text = "Press R to proceed to the next level"
                self.tutorial_timer = pygame.time.get_ticks()

                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    save_play_data(self.player, self.level_num, self.enemies, self.bushes)

                    # Update persistent EXP before moving to next level
                    if os.path.exists("persistent_exp.json"):
                        with open("persistent_exp.json", "r") as f:
                            data = json.load(f)
                            previous_total = data.get("earned_exp", 0)
                    else:
                        previous_total = 0

                    with open("persistent_exp.json", "w") as f:
                        json.dump({"earned_exp": self.player.exp}, f)

                    # Save exp/stats for next level
                    with open("exp_transfer.json", "w") as f:
                        json.dump({
                            'exp': self.player.exp,
                            'stats': self.player.stats,
                            'upgrade_cost': self.player.upgrade_cost,
                            'total_exp': self.player.exp
                        }, f)

                    self.session_exp = 0  # Reset session EXP after committing

                    next_level = self.level_num + 1 if self.level_num < 3 else 1
                    new_game = Game(level=next_level)
                    new_game.run()
                    pygame.quit()
                    sys.exit()

    def restart_level(self):
        # Load fallback values from exp_transfer.json
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        new_game = Game(
            level=self.level_num,
            restore_exp=transfer_data.get('exp', 0),
            restore_stats=transfer_data.get('stats'),
            restore_upgrade_cost=transfer_data.get('upgrade_cost')
        )
        new_game.run()
        pygame.quit()
        sys.exit()

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.enemy_update(self.player)
            self.visible_sprites.update()
            self.player_attack_logic()
            self.player.energy_recovery()
        self.check_exit_tile()
        self.draw_tutorial_text()

        if self.player.health <= 0 and not self.player_death_triggered:
            self.player.die(self.visible_sprites)  # Trigger death animation
            self.player_death_triggered = True
            self.player_death_time = pygame.time.get_ticks()

        # If already dead, wait for animation to finish before restart
        if self.player_death_triggered:
            if pygame.time.get_ticks() - self.player_death_time >= 2000:  # wait 2 seconds
                self.restart_level()
                return

# final level with boss fight and end screen logic
class Level_3:
    def __init__(self, level, restore_exp=None, restore_stats=None, restore_upgrade_cost=None, load_saved_data=True):
        self.saved_data = load_player_data(level) if load_saved_data else {}

        self.player_death_triggered = False
        self.player_death_time = 0

        self.session_exp = 0  # EXP earned this life only

        # Default fallbacks
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        default_stats = {'health': 100, 'energy': 60, 'attack': 10, 'magic': 4, 'speed': 5}
        default_upgrade_cost = {'health': 100, 'energy': 100, 'attack': 100, 'magic': 100, 'speed': 100}

        self.initial_exp = (
            restore_exp if restore_exp is not None else transfer_data.get('exp', 0)
        )
        self.initial_stats = restore_stats if restore_stats is not None else transfer_data.get('stats', default_stats)
        self.initial_upgrade_cost = restore_upgrade_cost if restore_upgrade_cost is not None else transfer_data.get(
            'upgrade_cost', default_upgrade_cost)

        self.enemies = []
        self.bushes = []
        self.level_num = level
        # get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        # sprite group setup
        self.visible_sprites = YSortCameraGroup('Ashen Legacy - Cave Background.png')
        self.obstacle_sprites = pygame.sprite.Group()

        # attack sprites
        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()

        # particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        # sprite setup
        self.create_map()

        # user interface
        self.ui = UI()
        self.upgrade = Upgrade(self.player)

        self.tutorial_text = None
        self.tutorial_font = pygame.font.Font(UI_FONT, 24)
        self.tutorial_timer = 0

        # end screen timer
        self.end_timer_started = False
        self.end_timer_start_time = 0

    def draw_tutorial_text(self):
        if self.tutorial_text and pygame.time.get_ticks() - self.tutorial_timer < 5000:
            text_surface = self.tutorial_font.render(self.tutorial_text, True, 'white')
            bg_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
            pygame.draw.rect(self.display_surface, (0, 0, 0), bg_rect.inflate(20, 10))
            self.display_surface.blit(text_surface, bg_rect)
        else:
            self.tutorial_text = None

    def create_map(self):
         world_map = WORLD_MAP_3
         for row_index, row in enumerate(world_map):
             for col_index, col in enumerate(row):
                 x = col_index * TILESIZE
                 y = row_index * TILESIZE

                 if col == 'x':
                     Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object', 'Ashen Legacy - Cave Wall.png')

                 elif col == 'p':
                     # Default position based on 'p' tile
                     start_pos = (x, y)

                     # Override with saved position if available
                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']
                         if 'x' in pdata and 'y' in pdata:
                             start_pos = (pdata['x'], pdata['y'])

                     self.player = Player(
                         start_pos,
                         [self.visible_sprites],
                         self.obstacle_sprites,
                         self.create_attack,
                         self.destroy_attack,
                         self.create_magic,
                         self.saved_data,
                         self.animation_player,
                         initial_stats=self.initial_stats,
                         initial_exp=self.initial_exp,
                         initial_upgrade_cost=self.initial_upgrade_cost
                     )

                     self.player.level = self

                     if self.saved_data and 'player' in self.saved_data:
                         pdata = self.saved_data['player']

                         self.player.health = pdata.get('health', self.player.health)
                         self.player.energy = pdata.get('energy', self.player.energy)
                         # Only override EXP if it's actually in the saved data
                         if 'exp' in pdata:
                             self.player.exp = pdata['exp']
                         else:
                             self.player.exp = self.initial_exp
                         self.player.stats = pdata.get('stats', self.player.stats)
                         self.player.upgrade_cost = pdata.get('upgrade_cost', self.player.upgrade_cost)
                         self.player.weapon_index = pdata.get('weapon_index', self.player.weapon_index)
                         self.player.magic_index = pdata.get('magic_index', self.player.magic_index)

                 elif col == 'f':
                     portal_frames = load_portal_frames("Ashen Legacy - Portal")
                     self.portal = Portal((x, y), portal_frames, [self.visible_sprites])

                 elif col == 'a':  # Boss spawn
                     if not self.saved_data.get('boss_defeated', False):
                         boss = Boss(
                             "ancient_skeleton",
                             (x, y),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             self.damage_player,
                             self.trigger_death_particles,
                             self.add_exp)
                         self.enemies.append(boss)

         # Load saved enemies if any
         if self.saved_data and 'enemies' in self.saved_data:
             for enemy_data in self.saved_data['enemies']:
                 enemy = Enemy(
                     enemy_data['type'],
                     (enemy_data['x'], enemy_data['y']),
                     [self.visible_sprites, self.attackable_sprites],
                     self.obstacle_sprites,
                     self.damage_player,
                     self.trigger_death_particles,
                     self.add_exp
                 )
                 enemy.health = enemy_data['health']
                 self.enemies.append(enemy)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'e':
                         enemy_type = random.choice(['skeleton', 'goblin', 'ghost'])
                         enemy = Enemy(
                             enemy_type,
                             (x, y),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             self.damage_player,
                             self.trigger_death_particles,
                             self.add_exp
                         )
                         self.enemies.append(enemy)

         # Load saved bushes
         if self.saved_data and 'bushes' in self.saved_data:
             for bush_data in self.saved_data['bushes']:
                 bush = Bush((bush_data['x'], bush_data['y']),
                             [self.visible_sprites, self.attackable_sprites],
                             self.obstacle_sprites,
                             bush_data.get('image_path', 'Ashen Legacy - Vine.png'))
                 self.bushes.append(bush)
         else:
             for row_index, row in enumerate(world_map):
                 for col_index, col in enumerate(row):
                     x = col_index * TILESIZE
                     y = row_index * TILESIZE
                     if col == 'v':
                         bush = Bush((x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites,
                                     'Ashen Legacy - Vine.png')
                         self.bushes.append(bush)

         save_play_data(self.player, self.level_num, self.enemies, self.bushes)

    def create_attack(self):
        self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, strength, cost):
        if style == 'heal':
            self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])

        if style == 'flame':
            self.magic_player.flame(self.player, cost, [self.visible_sprites, self.attack_sprites])

    def destroy_attack(self):
        if self.current_attack:
            self.current_attack.kill()
        self.current_attack = None

    def player_attack_logic(self):
        if self.attack_sprites:
            for attack_sprite in self.attack_sprites:
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'bush':
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2(0, 75)
                            for leaf in range(randint(3, 6)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                            target_sprite.kill()
                        elif target_sprite.sprite_type in ['enemy', 'boss']:
                            target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.health -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

    def add_exp(self, amount):
        self.player.exp += amount
        self.session_exp += amount

    def toggle_menu(self):

        self.game_paused = not self.game_paused

    def trigger_death_particles(self, pos, particle_type):

        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    # checks if player is on a portal tile ('f')
    # if so saves game data and transfers exp/stats to the next level
    def check_exit_tile(self):
        player_tile_x = self.player.rect.centerx // TILESIZE
        player_tile_y = self.player.rect.centery // TILESIZE

        # Choose the correct map for the current level
        if self.level_num == 0:
            world_map = WORLD_MAP_0
        elif self.level_num == 1:
            world_map = WORLD_MAP_1
        elif self.level_num == 2:
            world_map = WORLD_MAP_2
        elif self.level_num == 3:
            world_map = WORLD_MAP_3
        else:
            return

        if 0 <= player_tile_y < len(world_map) and 0 <= player_tile_x < len(world_map[0]):
            current_tile = world_map[player_tile_y][player_tile_x]
            if current_tile == 'f':
                # Always show this message near 'f' tiles
                self.tutorial_text = "Press R to proceed to the next level"
                self.tutorial_timer = pygame.time.get_ticks()

                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    save_play_data(self.player, self.level_num, self.enemies, self.bushes)

                    # Update persistent EXP before moving to next level
                    if os.path.exists("persistent_exp.json"):
                        with open("persistent_exp.json", "r") as f:
                            data = json.load(f)
                            previous_total = data.get("earned_exp", 0)
                    else:
                        previous_total = 0

                    with open("persistent_exp.json", "w") as f:
                        json.dump({"earned_exp": self.player.exp}, f)

                    # Save exp/stats for next level
                    with open("exp_transfer.json", "w") as f:
                        json.dump({
                            'exp': self.player.exp,
                            'stats': self.player.stats,
                            'upgrade_cost': self.player.upgrade_cost,
                            'total_exp': self.player.exp
                        }, f)

                    self.session_exp = 0  # Reset session EXP after committing

                    next_level = self.level_num + 1 if self.level_num < 3 else 1
                    new_game = Game(level=next_level)
                    new_game.run()
                    pygame.quit()
                    sys.exit()

    def restart_level(self):
        # Load fallback values from exp_transfer.json
        if os.path.exists("exp_transfer.json"):
            with open("exp_transfer.json", "r") as f:
                transfer_data = json.load(f)
        else:
            transfer_data = {}

        new_game = Game(
            level=self.level_num,
            restore_exp=transfer_data.get('exp', 0),
            restore_stats=transfer_data.get('stats'),
            restore_upgrade_cost=transfer_data.get('upgrade_cost')
        )
        new_game.run()
        pygame.quit()
        sys.exit()

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.enemy_update(self.player)
            self.visible_sprites.update()
            self.player_attack_logic()
            self.player.energy_recovery()
        self.check_exit_tile()
        self.draw_tutorial_text()

        if self.player.health <= 0 and not self.player_death_triggered:
            self.player.die(self.visible_sprites)  # Trigger death animation
            self.player_death_triggered = True
            self.player_death_time = pygame.time.get_ticks()

        # If already dead, wait for animation to finish before restart
        if self.player_death_triggered:
            if pygame.time.get_ticks() - self.player_death_time >= 2000:  # wait 2 seconds
                self.restart_level()
                return

        # Check if all enemies are dead
        alive_enemies = [e for e in self.enemies if e.alive()]
        if not alive_enemies and not self.end_timer_started:
            self.end_timer_started = True
            self.end_timer_start_time = pygame.time.get_ticks()

        # If 5 seconds passed since boss death, show end screen
        if self.end_timer_started:
            if pygame.time.get_ticks() - self.end_timer_start_time >= 5000:
                final_score = self.player.exp  # ← Define this before the try blocks

                try:
                    if os.path.exists("persistent_exp.json"):
                        with open("persistent_exp.json", "r") as f:
                            data = json.load(f)
                            previous_total = data.get("earned_exp", 0)
                    else:
                        previous_total = 0

                    with open("persistent_exp.json", "w") as f:
                        json.dump({"earned_exp": self.player.exp}, f)
                    self.session_exp = 0
                except:
                    pass

                try:
                    with open("highscore.json", "r") as f:
                        highscore_data = json.load(f)
                        highscore = max(highscore_data.get("highscore", 0), final_score)
                except:
                    highscore = final_score

                with open("highscore.json", "w") as f:
                    json.dump({"highscore": highscore}, f)

                show_end_screen(final_score, highscore)
                main_menu()  # <- Return to menu instead of quitting
                return  # Exit run loop

class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self, background_path='Ashen Legacy - Grass Background.png'):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()

        # Load and scale background
        self.floor_surf = pygame.image.load(background_path).convert()
        self.floor_surf = pygame.transform.scale(self.floor_surf, self.display_surface.get_size())
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

    def custom_draw(self, player):

        # getting the offset
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # drawing the background
        self.display_surface.blit(self.floor_surf, (0, 0))

        # for sprite in self.sprites():
        for sprite in sorted(self.sprites(), key = lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

    def enemy_update(self, player):
        for sprite in self.sprites():
            if hasattr(sprite, 'sprite_type') and sprite.sprite_type in ['enemy', 'boss']:
                sprite.enemy_update(player)

class Game:
    def __init__(self, level=1, restore_exp=None, restore_stats=None, restore_upgrade_cost=None, load_saved_data=True):
        self.level_num = level
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Ashen Legacy')
        self.clock = pygame.time.Clock()

        # Pass restore_exp to the level constructor
        if level == 0:
            self.level = Level_0(level, restore_exp, restore_stats, restore_upgrade_cost, load_saved_data)
        elif level == 1:
            self.level = Level_1(level, restore_exp, restore_stats, restore_upgrade_cost, load_saved_data)
        elif level == 2:
            self.level = Level_2(level, restore_exp, restore_stats, restore_upgrade_cost, load_saved_data)
        elif level == 3:
            self.level = Level_3(level, restore_exp, restore_stats, restore_upgrade_cost, load_saved_data)
        else:
            self.level = Level_1(level, restore_exp, restore_stats, restore_upgrade_cost, load_saved_data)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        self.level.toggle_menu()
                    elif event.key == pygame.K_ESCAPE:
                        save_play_data(self.level.player, self.level_num, self.level.enemies, self.level.bushes)
                        main_menu()

            self.screen.fill('black')
            self.level.run()
            pygame.display.update()
            self.clock.tick(FPS)

class Button():
    def __init__(self, image, pos, text_input, font, base_color, hovering_color):
        self.image = image
        self.x_pos = pos[0]
        self.y_pos = pos[1]
        self.font = font
        self.base_color, self.hovering_color = base_color, hovering_color
        self.text_input = text_input
        self.text = self.font.render(self.text_input, True, self.base_color)
        if self.image is None:
            self.image = self.text
        self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

    def update(self, screen):
        if self.image is not None:
            screen.blit(self.image, self.rect)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position):
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
            return True
        return False

    def changeColor(self, position):
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
            self.text = self.font.render(self.text_input, True, self.hovering_color)
        else:
            self.text = self.font.render(self.text_input, True, self.base_color)

SCREEN = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Ashen Legacy - Menu")

# Load and play music
pygame.mixer.music.load('Ashen Legacy - SFX/main.ogg')
pygame.mixer.music.set_volume(music_volume)  # use global variable
pygame.mixer.music.play(-1)

BG = pygame.image.load("Ashen Legacy - Menu Background.png")

def get_font(size):
    return pygame.font.Font('Ashen Legacy - Font.ttf', size)

def play():
    while True:
        SCREEN.blit(BG, (0, 0))

        PLAY_MOUSE_POS = pygame.mouse.get_pos()

        PLAY_TEXT = get_font(100).render("PLAY", True, "#b68f40")
        PLAY_RECT = PLAY_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(PLAY_TEXT, PLAY_RECT)

        TUTORIAL_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 240),
                                 text_input="TUTORIAL", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        LEVELS_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 340),
                               text_input="LEVELS", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        BACK_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 440),
                             text_input="BACK", font=get_font(75), base_color="#d7fcd4", hovering_color="White")

        for button in [TUTORIAL_BUTTON, LEVELS_BUTTON, BACK_BUTTON]:
            button.changeColor(PLAY_MOUSE_POS)
            button.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if TUTORIAL_BUTTON.checkForInput(PLAY_MOUSE_POS):
                    game = Game(level=0)
                    game.run()
                    return
                if LEVELS_BUTTON.checkForInput(PLAY_MOUSE_POS):
                    selected_level = level_select()
                    if selected_level is not None:
                        game = Game(level=selected_level)
                        game.run()
                        return
                if BACK_BUTTON.checkForInput(PLAY_MOUSE_POS):
                    return  # Go back to main menu

        pygame.display.update()

def level_select():
    while True:
        SCREEN.blit(BG, (0, 0))

        LEVEL_TEXT = get_font(100).render("SELECT LEVEL", True, "#b68f40")
        LEVEL_RECT = LEVEL_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(LEVEL_TEXT, LEVEL_RECT)

        MOUSE_POS = pygame.mouse.get_pos()

        LEVEL1_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 240),
                               text_input="LEVEL 1", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        LEVEL2_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 340),
                               text_input="LEVEL 2", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        LEVEL3_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 440),
                               text_input="LEVEL 3", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        BACK_BUTTON = Button(image=pygame.image.load("Ashen Legacy - Menu Rect.png"), pos=(640, 540),
                             text_input="BACK", font=get_font(75), base_color="#d7fcd4", hovering_color="White")

        for button in [LEVEL1_BUTTON, LEVEL2_BUTTON, LEVEL3_BUTTON, BACK_BUTTON]:
            button.changeColor(MOUSE_POS)
            button.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if LEVEL1_BUTTON.checkForInput(MOUSE_POS):
                    return 1
                if LEVEL2_BUTTON.checkForInput(MOUSE_POS):
                    return 2
                if LEVEL3_BUTTON.checkForInput(MOUSE_POS):
                    return 3
                if BACK_BUTTON.checkForInput(MOUSE_POS):
                    return None

        pygame.display.update()

def options():
    global music_volume, sfx_volume

    slider_length = 400
    slider_height = 20

    # Center sliders horizontally
    slider_x = (1280 - slider_length) // 2
    music_slider_pos = (slider_x, 300)
    sfx_slider_pos = (slider_x, 400)

    running = True
    while running:
        OPTIONS_MOUSE_POS = pygame.mouse.get_pos()
        SCREEN.blit(BG, (0, 0))  # Use same background as main menu

        OPTIONS_TEXT = get_font(100).render("OPTIONS", True, "#b68f40")
        OPTIONS_RECT = OPTIONS_TEXT.get_rect(center=(640, 150))
        SCREEN.blit(OPTIONS_TEXT, OPTIONS_RECT)

        # Labels for sliders (centered above the slider)
        music_label_text = f"Music Volume: {int(music_volume * 100)}%"
        sfx_label_text = f"SFX Volume: {int(sfx_volume * 100)}%"

        music_label = get_font(35).render(music_label_text, True, "#d7fcd4")
        sfx_label = get_font(35).render(sfx_label_text, True, "#d7fcd4")

        music_label_rect = music_label.get_rect(center=(640, music_slider_pos[1] - 30))
        sfx_label_rect = sfx_label.get_rect(center=(640, sfx_slider_pos[1] - 30))

        SCREEN.blit(music_label, music_label_rect)
        SCREEN.blit(sfx_label, sfx_label_rect)

        # Slider bars
        pygame.draw.rect(SCREEN, (100, 100, 100), (*music_slider_pos, slider_length, slider_height))
        pygame.draw.rect(SCREEN, (100, 100, 100), (*sfx_slider_pos, slider_length, slider_height))

        # Knobs
        music_knob_x = music_slider_pos[0] + int(music_volume * slider_length)
        sfx_knob_x = sfx_slider_pos[0] + int(sfx_volume * slider_length)

        knob_rect_music = pygame.Rect(music_knob_x - 10, music_slider_pos[1] - 5, 20, 30)
        knob_rect_sfx = pygame.Rect(sfx_knob_x - 10, sfx_slider_pos[1] - 5, 20, 30)

        pygame.draw.rect(SCREEN, (255, 215, 0), knob_rect_music)
        pygame.draw.rect(SCREEN, (255, 215, 0), knob_rect_sfx)

        # Back button
        OPTIONS_BACK = Button(image=pygame.image.load('Ashen Legacy - Menu Rect.png'), pos=(640, 550),
                              text_input="BACK", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        OPTIONS_BACK.changeColor(OPTIONS_MOUSE_POS)
        OPTIONS_BACK.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if OPTIONS_BACK.checkForInput(OPTIONS_MOUSE_POS):
                    running = False

                # Volume control
                if music_slider_pos[0] <= event.pos[0] <= music_slider_pos[0] + slider_length and \
                   music_slider_pos[1] <= event.pos[1] <= music_slider_pos[1] + slider_height:
                    music_volume = (event.pos[0] - music_slider_pos[0]) / slider_length
                    music_volume = max(0, min(1, music_volume))
                    pygame.mixer.music.set_volume(music_volume)

                if sfx_slider_pos[0] <= event.pos[0] <= sfx_slider_pos[0] + slider_length and \
                   sfx_slider_pos[1] <= event.pos[1] <= sfx_slider_pos[1] + slider_height:
                    sfx_volume = (event.pos[0] - sfx_slider_pos[0]) / slider_length
                    sfx_volume = max(0, min(1, sfx_volume))

        pygame.display.update()

def main_menu():
    while True:
        SCREEN.blit(BG, (0, 0))

        MENU_MOUSE_POS = pygame.mouse.get_pos()

        MENU_TEXT = get_font(100).render("MAIN MENU", True, "#b68f40")
        MENU_RECT = MENU_TEXT.get_rect(center=(640, 100))

        PLAY_BUTTON = Button(image=pygame.image.load('Ashen Legacy - Menu Rect.png'), pos=(640, 240),
                             text_input="PLAY", font=get_font(75), base_color="#d7fcd4", hovering_color="White")

        OPTIONS_BUTTON = Button(image=pygame.image.load('Ashen Legacy - Menu Rect.png'), pos=(640, 340),
                                text_input="OPTIONS", font=get_font(75), base_color="#d7fcd4", hovering_color="White")

        RESET_BUTTON = Button(image=pygame.image.load('Ashen Legacy - Menu Rect.png'), pos=(640, 440),
                              text_input="RESET", font=get_font(75), base_color="#d7fcd4", hovering_color="White")

        QUIT_BUTTON = Button(image=pygame.image.load('Ashen Legacy - Menu Rect.png'), pos=(640, 540),
                             text_input="QUIT", font=get_font(75), base_color="#d7fcd4", hovering_color="White")

        SCREEN.blit(MENU_TEXT, MENU_RECT)

        for button in [PLAY_BUTTON, OPTIONS_BUTTON, RESET_BUTTON, QUIT_BUTTON]:
            button.changeColor(MENU_MOUSE_POS)
            button.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if PLAY_BUTTON.checkForInput(MENU_MOUSE_POS):
                    play()
                if OPTIONS_BUTTON.checkForInput(MENU_MOUSE_POS):
                    options()
                if QUIT_BUTTON.checkForInput(MENU_MOUSE_POS):
                    pygame.quit()
                    sys.exit()
                if RESET_BUTTON.checkForInput(MENU_MOUSE_POS):
                    reset_save_data()
                    if os.path.exists('highscore.json'):
                        os.remove('highscore.json')
                    pygame.time.wait(500)

        pygame.display.update()

main_menu()

if __name__=='__main__':
    main_menu()