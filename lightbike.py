#!/usr/bin/env python3
import curses
import time
import random
import math
import subprocess
import threading
import os
import sys
from collections import deque
from enum import Enum

class SoundManager:
    def __init__(self):
        self.music_process = None
        self.sound_enabled = True
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
    def play_background_music(self):
        """Play background music once using afplay"""
        if not self.sound_enabled:
            return
            
        def play_music():
            try:
                music_path = os.path.join(self.base_path, 'background_music.wav')
                if os.path.exists(music_path) and sys.platform == 'darwin':
                    subprocess.run(['afplay', music_path], capture_output=True, timeout=300)
            except:
                pass
        
        if self.music_process is None or not self.music_process.is_alive():
            self.music_process = threading.Thread(target=play_music, daemon=True)
            self.music_process.start()
    
    def play_sound_effect(self, sound_file):
        """Play a sound effect using afplay"""
        if not self.sound_enabled:
            return
            
        def play():
            try:
                sound_path = os.path.join(self.base_path, sound_file)
                if os.path.exists(sound_path) and sys.platform == 'darwin':
                    subprocess.run(['afplay', sound_path], capture_output=True, timeout=5)
            except:
                pass
        
        threading.Thread(target=play, daemon=True).start()
    
    def play_crash(self):
        """Play crash sound effect"""
        self.play_sound_effect('crash.wav')
    
    def play_menu_select(self):
        """Play menu selection sound"""
        self.play_sound_effect('menu_select.wav')
    
    def stop_music(self):
        """Stop background music"""
        self.sound_enabled = False
        try:
            subprocess.run(['killall', 'afplay'], capture_output=True)
        except:
            pass
    
    def toggle_sound(self):
        """Toggle sound on/off"""
        if self.sound_enabled:
            self.stop_music()
            self.sound_enabled = False
        else:
            self.sound_enabled = True
            self.play_background_music()

class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

class PickupType(Enum):
    SHIELD = ("SHIELD", "🛡", 7, 50)    # name, symbol, color, duration (5 seconds)
    BOOST = ("BOOST", "🚀", 4, 100)     # speed boost
    SPEED = ("SPEED", "🏁", 5, 200)    # longer speed boost

class Pickup:
    def __init__(self, y, x, pickup_type):
        self.y = y
        self.x = x
        self.type = pickup_type
        self.name, self.symbol, self.color, self.duration = pickup_type.value
        self.collected = False

class Dropper:
    """Spinning circle that drops obstacles and pickups"""
    def __init__(self, y, x):
        self.y = y
        self.x = x
        self.angle = 0
        self.move_timer = 0
        self.drop_timer = random.randint(50, 100)
        self.direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
        self.speed = random.randint(3, 5)
        
    def update(self):
        """Update dropper position and rotation"""
        self.angle = (self.angle + 10) % 360  # Spin
        
        # Move around
        self.move_timer += 1
        if self.move_timer >= self.speed:
            self.move_timer = 0
            dy, dx = self.direction.value
            self.y += dy
            self.x += dx
            
            # Random direction change
            if random.random() < 0.1:
                self.direction = random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT])
        
        # Drop timer
        self.drop_timer -= 1
        
    def get_sprite_lines(self):
        """Get the lines radiating from the center"""
        lines = []
        # 8 lines at 45 degree intervals
        for i in range(8):
            angle_offset = (self.angle + i * 45) % 360
            if angle_offset < 45 or angle_offset >= 315:
                lines.append((0, 1))  # Right
            elif angle_offset < 135:
                lines.append((1, 0))  # Down
            elif angle_offset < 225:
                lines.append((0, -1))  # Left
            else:
                lines.append((-1, 0))  # Up
        return lines

class Obstacle:
    def __init__(self, y, x, width, height, shape_type="rock"):
        self.y = y
        self.x = x
        self.width = width
        self.height = height
        self.shape_type = shape_type
        self.cells = set()
        self._generate_shape()
        
    def _generate_shape(self):
        """Generate obstacle cells based on shape type"""
        if self.shape_type == "rock":
            # Irregular rock shape
            for dy in range(self.height):
                for dx in range(self.width):
                    if random.random() > 0.3:  # Irregular edges
                        self.cells.add((self.y + dy, self.x + dx))
        elif self.shape_type == "rectangle":
            # Simple rectangle
            for dy in range(self.height):
                for dx in range(self.width):
                    self.cells.add((self.y + dy, self.x + dx))
        elif self.shape_type == "triangle":
            # Triangle shape
            for dy in range(self.height):
                width_at_row = self.width * (self.height - dy) // self.height
                offset = (self.width - width_at_row) // 2
                for dx in range(width_at_row):
                    self.cells.add((self.y + dy, self.x + offset + dx))
                    
    def contains(self, y, x):
        """Check if a coordinate is inside the obstacle"""
        return (y, x) in self.cells

class Bike:
    def __init__(self, y, x, direction, color, name, bike_chars):
        self.y = y
        self.x = x
        self.direction = direction
        self.color = color
        self.name = name
        self.bike_chars = bike_chars
        self.trail = deque(maxlen=1000)
        self.alive = True
        
        # Abilities
        self.shield_timer = 0
        self.boost_timer = 0
        self.boost_charges = 0  # Number of boosts available to use
        self.speed_timer = 0
        self.stealth_timer = 0  # Trail off timer
        self.trail_enabled = True
        self.manual_trail_off = False  # Track manual trail toggle
        
        # Jump mechanics
        self.jumps_remaining = 3
        self.jump_timer = 0  # Duration of current jump
        self.jump_invincibility = False
        self.jump_flash_counter = 0
        
        # Movement
        self.move_cooldown = 0
        self.base_speed = 1  # Faster speed (lower value = faster movement)
        self.vertical_speed_multiplier = 2  # Compensate for terminal character aspect ratio
        
        # AI properties
        self.ai_difficulty = 1
        
    def update_timers(self):
        """Update all ability timers"""
        if self.shield_timer > 0:
            self.shield_timer -= 1
        if self.speed_timer > 0:
            self.speed_timer -= 1
        if self.boost_timer > 0:
            self.boost_timer -= 1
        if self.stealth_timer > 0:
            self.stealth_timer -= 1
        if self.jump_timer > 0:
            self.jump_timer -= 1
            self.jump_flash_counter += 1
            if self.jump_timer == 0:
                self.jump_invincibility = False
            
    def can_move(self):
        """Check if bike can move based on speed"""
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            return False
        
        # Set cooldown based on current speed
        speed = self.base_speed
        if self.speed_timer > 0:
            speed = max(1, speed - 1)  # Faster when speed powerup
        if self.boost_timer > 0:
            speed = 1  # Maximum speed with boost
        
        # No cooldown for horizontal movement to make it faster
        if self.direction in [Direction.LEFT, Direction.RIGHT]:
            speed = 0  # No cooldown = maximum speed horizontally
        
        self.move_cooldown = speed
        return True
        
    def move(self):
        if not self.alive or not self.can_move():
            return
            
        # Add current position to trail only if trail is enabled
        # Check both manual toggle and stealth timer
        if not self.manual_trail_off and self.stealth_timer <= 0:
            self.trail.append((self.y, self.x))
        
        # Move in current direction
        dy, dx = self.direction.value
        self.y += dy
        self.x += dx
        
        
    def turn(self, new_direction):
        # Prevent turning back on yourself
        dy, dx = self.direction.value
        new_dy, new_dx = new_direction.value
        if dy + new_dy == 0 and dx + new_dx == 0:
            return
        self.direction = new_direction
        
    def jump(self):
        """Activate jump if jumps remaining"""
        if self.jumps_remaining > 0 and self.jump_timer == 0:
            self.jumps_remaining -= 1
            self.jump_timer = 15  # Jump lasts for 15 frames (about 0.75 seconds)
            self.jump_invincibility = True
            self.jump_flash_counter = 0
            return True
        return False
    
    def use_boost(self):
        """Activate boost if available"""
        if self.boost_charges > 0 and self.boost_timer == 0:
            self.boost_charges -= 1
            self.boost_timer = 150  # 7.5 seconds at 20 FPS
            self.boost = True
            return True
        return False
        
    def get_sprite(self):
        # Show different sprite based on active powerups
        if self.jump_timer > 0:
            # Bigger sprite when jumping
            return '⬤'  # Large circle to represent being in the air
        elif self.shield_timer > 0:
            return '◈'
        elif self.manual_trail_off:
            return '◌'
        elif self.boost_timer > 0:
            return '⚫'
        elif self.speed_timer > 0:
            return '◉'
        return self.bike_chars.get(self.direction, '●')

class SpikeEnemy:
    def __init__(self, y, x, pattern="horizontal"):
        self.y = y
        self.x = x
        self.start_x = x
        self.start_y = y
        self.pattern = pattern  # "horizontal", "vertical", "circle"
        self.alive = True
        self.move_timer = 0
        self.move_counter = 0
        self.radius = 5  # For circle pattern
        
    def update(self):
        """Update spike enemy movement"""
        self.move_timer += 1
        if self.move_timer >= 10:  # Move every 10 frames
            self.move_timer = 0
            self.move_counter += 1
            
            if self.pattern == "horizontal":
                # Move back and forth horizontally
                self.x = self.start_x + int(10 * math.sin(self.move_counter * 0.2))
            elif self.pattern == "vertical":
                # Move back and forth vertically
                self.y = self.start_y + int(5 * math.sin(self.move_counter * 0.2))
            elif self.pattern == "circle":
                # Move in a circle
                angle = self.move_counter * 0.3
                self.x = self.start_x + int(self.radius * math.cos(angle))
                self.y = self.start_y + int(self.radius * math.sin(angle))
    
    def get_sprite(self):
        return "♠"  # Spade symbol for spike

class LightBikeEnhanced:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Check terminal size
        self.min_width = 80
        self.min_height = 24
        
        # Initialize state variables first
        self.show_menu = True
        self.show_fullscreen_warning = False
        self.show_character_select = False
        self.sound_enabled = True
        self.fullscreen_mode = False
        
        # Stadium dimensions - use most of the screen
        self.update_stadium_dimensions()
        
        # Character definitions with unique stats
        self.characters = [
            {
                'name': 'COB',
                'color': 4,  # Blue
                'description': 'Mysterious rider who speaks in binary. Half-computer, half-corn.',
                'quote': '"01001000 01101001!" (Translation: "Hi!")',
                'ability': 'TECH SAVVY: Starts with a shield!',
                'stats': {
                    'jumps': 3,
                    'speed_bonus': 0,
                    'start_with_shield': True,
                    'start_with_boost': False
                }
            },
            {
                'name': 'JAKE',
                'color': 2,  # Green
                'description': 'Ex-snake charmer turned racer. Still hisses when turning.',
                'quote': '"Ssssseriously fast!"',
                'ability': 'SLIPPERY: +10% faster movement!',
                'stats': {
                    'jumps': 3,
                    'speed_bonus': 1,  # Faster cooldown reduction
                    'start_with_shield': False,
                    'start_with_boost': False
                }
            },
            {
                'name': 'CHOD',
                'color': 1,  # Red
                'description': 'Former hot sauce tester. Now burns rubber instead of taste buds.',
                'quote': '"Spicy speeds ahead!"',
                'ability': 'HOT BLOODED: Starts with boost ready!',
                'stats': {
                    'jumps': 3,
                    'speed_bonus': 0,
                    'start_with_shield': False,
                    'start_with_boost': True
                }
            },
            {
                'name': 'ELI',
                'color': 3,  # Orange/Yellow
                'description': 'Ex-elevator operator. Got tired of up/down, now goes sideways!',
                'quote': '"Taking it to the next level!"',
                'ability': 'VERTICAL MASTER: 4 jumps instead of 3!',
                'stats': {
                    'jumps': 4,
                    'speed_bonus': 0,
                    'start_with_shield': False,
                    'start_with_boost': False
                }
            },
            {
                'name': 'PORK',
                'color': 5,  # Pink/Magenta
                'description': 'Vegetarian with an ironic name. Powered by tofu and determination.',
                'quote': '"Oink oink, zoom zoom!"',
                'ability': 'JUST AWESOME: No special ability, just pure skill!',
                'stats': {
                    'jumps': 3,
                    'speed_bonus': 0,
                    'start_with_shield': False,
                    'start_with_boost': False
                }
            }
        ]
        self.selected_character = 0
        self.player_color = 1  # Default red
        self.crowd_animation = 0
        
        # Level system
        self.current_level = 1
        self.max_level = 15
        self.level_won = False
        self.level_start_time = 0
        self.level_duration = 300  # 30 seconds per level
        
        # Obstacles
        self.obstacles = []
        
        # Droppers
        self.droppers = []
        
        # Initialize sound manager
        self.sound_manager = SoundManager()
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Player
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # AI 1
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Walls/AI 2
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # UI/Jump
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Speed
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Trail Off
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Shield
        
        # Bike sprites for different directions
        self.player_sprites = {
            Direction.UP: '▲',
            Direction.DOWN: '▼',
            Direction.LEFT: '◄',
            Direction.RIGHT: '►'
        }
        
        self.ai_sprites = {
            Direction.UP: '△',
            Direction.DOWN: '▽',
            Direction.LEFT: '◁',
            Direction.RIGHT: '▷'
        }
        
        self.pickups = []
        self.pickup_spawn_timer = 0
        
        # Multiple enemies list
        self.enemies = []
        
        # Spike enemies (new hazard type)
        self.spike_enemies = []
        
        self.reset_game()
        
    def update_stadium_dimensions(self):
        """Update stadium dimensions based on fullscreen mode"""
        if self.fullscreen_mode:
            # Use entire screen in fullscreen mode
            self.stadium_top = 0
            self.stadium_bottom = self.height - 1
            self.stadium_left = 0
            self.stadium_right = self.width - 1
        else:
            # Normal mode with borders
            self.stadium_top = 3
            self.stadium_bottom = self.height - 4
            self.stadium_left = 2
            self.stadium_right = self.width - 2
            
        self.game_height = self.stadium_bottom - self.stadium_top
        self.game_width = self.stadium_right - self.stadium_left
            
    def reset_game(self):
        # Initialize bikes in starting positions
        start_y = self.stadium_top + self.game_height // 2
        
        player_x = self.stadium_left + self.game_width // 4
        
        self.player = Bike(start_y, player_x, Direction.RIGHT, self.player_color, "PLAYER", self.player_sprites)
        
        # Apply character-specific stats
        char_stats = self.characters[self.selected_character]['stats']
        self.player.jumps_remaining = char_stats['jumps']
        
        # Apply starting items
        if char_stats['start_with_shield']:
            self.player.shield_timer = 300  # 15 seconds
            self.player.shield = True
        if char_stats['start_with_boost']:
            self.player.boost_charges = 1
            
        # Apply speed bonus (reduce cooldown for faster movement)
        if char_stats['speed_bonus'] > 0:
            self.player.vertical_speed_multiplier = max(1, self.player.vertical_speed_multiplier - char_stats['speed_bonus'])
        
        # Initialize enemies based on level
        self.enemies = []
        self.setup_level_enemies()
        
        # Initialize spike enemies
        self.spike_enemies = []
        self.setup_spike_enemies()
        
        # Keep reference to first enemy for compatibility
        self.ai = self.enemies[0] if self.enemies else None
        
        self.score = 0
        self.game_over = False
        self.winner = None
        self.show_menu = False
        self.game_time = 0
        self.pickups = []
        self.pickup_spawn_timer = 100  # Spawn first pickup after 100 ticks
        self.level_start_time = 0
        self.level_won = False
        
        # Setup level obstacles
        self.setup_level_obstacles()
        
        # Setup droppers
        self.setup_level_droppers()
    
    def setup_spike_enemies(self):
        """Setup spike enemies based on current level"""
        self.spike_enemies = []
        
        # Add spike enemies starting from level 1
        if self.current_level >= 1:
            # More spike enemies in early levels for more action
            if self.current_level <= 3:
                num_spikes = self.current_level + 1  # 2, 3, 4 spikes for levels 1-3
            else:
                num_spikes = min(self.current_level, 6)  # Up to 6 spike enemies later
            
            patterns = ["horizontal", "vertical", "circle"]
            
            for i in range(num_spikes):
                # Find a good position for spike enemy
                for attempt in range(30):
                    x = random.randint(self.stadium_left + 15, self.stadium_right - 15)
                    y = random.randint(self.stadium_top + 10, self.stadium_bottom - 10)
                    
                    # Check not too close to players
                    too_close = False
                    if abs(self.player.x - x) < 20 and abs(self.player.y - y) < 15:
                        too_close = True
                    for enemy in self.enemies:
                        if abs(enemy.x - x) < 20 and abs(enemy.y - y) < 15:
                            too_close = True
                            break
                    
                    # Check not overlapping with obstacles
                    for obstacle in self.obstacles:
                        if (obstacle.x <= x <= obstacle.x + obstacle.width and 
                            obstacle.y <= y <= obstacle.y + obstacle.height):
                            too_close = True
                            break
                    
                    if not too_close:
                        pattern = patterns[i % len(patterns)]
                        self.spike_enemies.append(SpikeEnemy(y, x, pattern))
                        break
        
        if hasattr(self, '_crash_played'):
            delattr(self, '_crash_played')
            
    def setup_level_enemies(self):
        """Setup enemies based on current level"""
        # Number of enemies increases progressively
        if self.current_level <= 2:
            num_enemies = 1
        elif self.current_level <= 5:
            num_enemies = 2
        elif self.current_level <= 9:
            num_enemies = 3
        else:
            num_enemies = 4
        
        # Enemy starting positions
        positions = [
            (self.stadium_top + self.game_height // 2, self.stadium_left + 3 * self.game_width // 4, Direction.LEFT),
            (self.stadium_top + self.game_height // 3, self.stadium_left + self.game_width // 2, Direction.DOWN),
            (self.stadium_top + 2 * self.game_height // 3, self.stadium_left + self.game_width // 2, Direction.UP),
            (self.stadium_top + self.game_height // 2, self.stadium_left + self.game_width // 4, Direction.RIGHT)
        ]
        
        for i in range(min(num_enemies, len(positions))):
            y, x, direction = positions[i]
            enemy = Bike(y, x, direction, 2 + i % 2, f"CPU{i+1}", self.ai_sprites)
            
            # Set AI difficulty based on level
            enemy.ai_difficulty = self.current_level
            enemy.base_speed = max(1, 2 - self.current_level // 8)  # Adjust AI speed with new base speed
            
            # AI strategies per level
            enemy.ai_strategy = self._get_ai_strategy()
            
            self.enemies.append(enemy)
            
    def _get_ai_strategy(self):
        """Get AI strategy based on level"""
        strategies = []
        
        if self.current_level >= 2:
            strategies.append('aggressive')  # Chase player more
        if self.current_level >= 4:
            strategies.append('predictive')  # Predict player movement
        if self.current_level >= 6:
            strategies.append('cutoff')     # Try to cut off player
        if self.current_level >= 8:
            strategies.append('territorial') # Control areas
        if self.current_level >= 10:
            strategies.append('cooperative') # Work with other AIs
        if self.current_level >= 12:
            strategies.append('trap')       # Set traps
        if self.current_level >= 14:
            strategies.append('kamikaze')   # Sacrifice to trap player
            
        return strategies
            
    def setup_level_obstacles(self):
        """Setup obstacles based on current level"""
        self.obstacles = []
        
        if self.current_level >= 1:
            # Add obstacles starting from level 1 for more variety
            if self.current_level == 1:
                num_obstacles = 2  # Start with 2 obstacles in level 1
            else:
                # More obstacles in early levels for action
                base_obstacles = self.current_level
                additional_obstacles = int(base_obstacles * 0.3 * (self.current_level - 1))
                num_obstacles = min(base_obstacles + additional_obstacles, 20)  # Cap at 20 obstacles
            
            shapes = ["rock", "rectangle", "triangle"]
            
            for _ in range(num_obstacles):
                # Try to place obstacle in a good spot
                for attempt in range(50):
                    width = random.randint(3, 7)
                    height = random.randint(3, 6)
                    x = random.randint(self.stadium_left + 5, self.stadium_right - width - 5)
                    y = random.randint(self.stadium_top + 5, self.stadium_bottom - height - 5)
                    
                    # Check if too close to starting positions
                    too_close = False
                    for enemy in self.enemies:
                        if abs(enemy.x - x) < 10 and abs(enemy.y - y) < 10:
                            too_close = True
                            break
                    if abs(self.player.x - x) < 10 and abs(self.player.y - y) < 10:
                        too_close = True
                        
                    if not too_close:
                        shape = random.choice(shapes)
                        self.obstacles.append(Obstacle(y, x, width, height, shape))
                        break
                        
    def setup_level_droppers(self):
        """Setup droppers based on current level"""
        self.droppers = []
        
        if self.current_level >= 2:  # Start droppers from level 2
            num_droppers = min((self.current_level - 1), 4)  # Max 4 droppers
            
            for _ in range(num_droppers):
                # Find a good spot for dropper
                for attempt in range(20):
                    x = random.randint(self.stadium_left + 10, self.stadium_right - 10)
                    y = random.randint(self.stadium_top + 10, self.stadium_bottom - 10)
                    
                    # Check not too close to players
                    too_close = False
                    if abs(self.player.x - x) < 15 and abs(self.player.y - y) < 10:
                        too_close = True
                    for enemy in self.enemies:
                        if abs(enemy.x - x) < 15 and abs(enemy.y - y) < 10:
                            too_close = True
                            break
                            
                    if not too_close:
                        self.droppers.append(Dropper(y, x))
                        break
                        
    def load_custom_level(self, level_num):
        """Load a custom level from JSON file"""
        import json
        
        filename = f"levels/level_{level_num:02d}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        if not os.path.exists(filepath):
            print(f"Custom level {filepath} not found")
            return False
            
        try:
            with open(filepath, 'r') as f:
                level_data = json.load(f)
                
            # Set level properties
            self.current_level = level_data['number']
            self.level_duration = level_data['duration']
            
            # Clear existing elements
            self.obstacles = []
            self.pickups = []
            self.droppers = []
            self.enemies = []
            
            # Load elements
            for element in level_data['elements']:
                elem_type = element['type']
                x = element['x'] + self.stadium_left
                y = element['y'] + self.stadium_top
                
                if elem_type == 'PLAYER_SPAWN':
                    self.player.y = y
                    self.player.x = x
                    self.player.direction = Direction.RIGHT
                    
                elif elem_type == 'ENEMY_SPAWN':
                    enemy = Bike(y, x, Direction.LEFT, 2, f"CPU{len(self.enemies)+1}", self.ai_sprites)
                    enemy.ai_difficulty = self.current_level
                    enemy.base_speed = max(1, 2 - self.current_level // 8)
                    enemy.ai_strategy = self._get_ai_strategy()
                    self.enemies.append(enemy)
                    
                elif elem_type.startswith('OBSTACLE_'):
                    shape = elem_type.split('_')[1].lower()
                    if shape == 'rect':
                        shape = 'rectangle'
                    elif shape == 'tri':
                        shape = 'triangle'
                    obstacle = Obstacle(y, x, 3, 3, shape)
                    self.obstacles.append(obstacle)
                    
                elif elem_type == 'DROPPER':
                    self.droppers.append(Dropper(y, x))
                    
                elif elem_type.startswith('PICKUP_'):
                    pickup_name = elem_type.split('_')[1]
                    if pickup_name == 'SHIELD':
                        pickup_type = PickupType.SHIELD
                    elif pickup_name == 'BOOST':
                        pickup_type = PickupType.BOOST
                    elif pickup_name == 'SPEED':
                        pickup_type = PickupType.SPEED
                    self.pickups.append(Pickup(y, x, pickup_type))
                    
            # Ensure we have at least one enemy
            if not self.enemies:
                self.setup_level_enemies()
                
            self.ai = self.enemies[0] if self.enemies else None
            
            print(f"Loaded custom level: {level_data['name']}")
            return True
            
        except Exception as e:
            print(f"Error loading custom level: {e}")
            return False
                        
    def spawn_pickup(self):
        """Spawn a random pickup on the field"""
        # Validate stadium dimensions first
        if self.stadium_bottom - self.stadium_top < 5 or self.stadium_right - self.stadium_left < 5:
            return  # Stadium too small for pickups
            
        # Try to find a valid spawn location
        for _ in range(50):  # Try 50 times to find a spot
            y = random.randint(self.stadium_top + 2, self.stadium_bottom - 2)
            x = random.randint(self.stadium_left + 2, self.stadium_right - 2)
            
            # Check if location is clear
            location_clear = True
            
            # Check player trail and position
            if (y, x) in self.player.trail or (y, x) == (self.player.y, self.player.x):
                location_clear = False
                
            # Check all enemy trails and positions
            for enemy in self.enemies:
                if (y, x) in enemy.trail or (y, x) == (enemy.y, enemy.x):
                    location_clear = False
                    break
                    
            # Check obstacles
            for obstacle in self.obstacles:
                if obstacle.contains(y, x):
                    location_clear = False
                    break
                    
            if location_clear:
                
                # Don't spawn on existing pickups
                valid = True
                for pickup in self.pickups:
                    if pickup.y == y and pickup.x == x:
                        valid = False
                        break
                
                if valid:
                    pickup_type = random.choice(list(PickupType))
                    self.pickups.append(Pickup(y, x, pickup_type))
                    break
                    
    def check_pickups(self, bike):
        """Check if bike collected any pickups"""
        for pickup in self.pickups[:]:
            if not pickup.collected and pickup.y == bike.y and pickup.x == bike.x:
                pickup.collected = True
                
                # Apply pickup effect
                if pickup.type == PickupType.SHIELD:
                    bike.shield_timer = pickup.duration
                    bike.shield = True
                elif pickup.type == PickupType.BOOST:
                    bike.boost_charges += 1  # Give boost charge instead of automatic boost
                elif pickup.type == PickupType.SPEED:
                    bike.speed_timer = pickup.duration
                    
                self.pickups.remove(pickup)
                self.sound_manager.play_menu_select()  # Pickup sound
                return pickup
        return None
            
    def draw_stadium(self):
        if self.fullscreen_mode:
            # In fullscreen mode, just draw a simple border
            self.stdscr.attron(curses.color_pair(4))
            # Top and bottom borders
            for x in range(self.width):
                try:
                    self.stdscr.addstr(0, x, '═')
                    self.stdscr.addstr(self.height - 1, x, '═')
                except:
                    pass
            # Side borders
            for y in range(self.height):
                try:
                    self.stdscr.addstr(y, 0, '║')
                    self.stdscr.addstr(y, self.width - 1, '║')
                except:
                    pass
            self.stdscr.attroff(curses.color_pair(4))
            return
            
        # Normal mode - Draw crowd at top
        crowd_chars = ['o', 'O', '0', 'θ', '*', '°', '●', '◦', '◉', '◊']
        self.stdscr.attron(curses.color_pair(7))
        
        # Top crowd (denser)
        for y in range(0, self.stadium_top - 1):
            crowd_line = ''
            for x in range(0, self.width):
                if random.random() > 0.1:  # More dense crowd (was 0.3)
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    crowd_line += char
                else:
                    crowd_line += ' '
            try:
                self.stdscr.addstr(y, 0, crowd_line[:self.width-1])
            except:
                pass
                        
        # Side crowds
        for y in range(self.stadium_top, self.stadium_bottom):
            # Left crowd (denser)
            for x in range(0, self.stadium_left - 1):
                if random.random() > 0.1:  # More dense
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    try:
                        self.stdscr.addstr(y, x, char)
                    except:
                        pass
            # Right crowd (denser)
            for x in range(self.stadium_right + 1, self.width):
                if random.random() > 0.1:  # More dense
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    try:
                        self.stdscr.addstr(y, x, char)
                    except:
                        pass
                        
        self.stdscr.attroff(curses.color_pair(7))
        
        # Draw obstacles
        self.stdscr.attron(curses.color_pair(3))
        for obstacle in self.obstacles:
            for cell_y, cell_x in obstacle.cells:
                if self.stadium_top <= cell_y < self.stadium_bottom and self.stadium_left <= cell_x < self.stadium_right:
                    try:
                        if obstacle.shape_type == "rock":
                            self.stdscr.addstr(cell_y, cell_x, '▓')
                        elif obstacle.shape_type == "rectangle":
                            self.stdscr.addstr(cell_y, cell_x, '█')
                        elif obstacle.shape_type == "triangle":
                            self.stdscr.addstr(cell_y, cell_x, '▲')
                    except:
                        pass
        self.stdscr.attroff(curses.color_pair(3))
        
        # Draw stadium border
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        
        # Top and bottom walls
        for x in range(self.stadium_left, self.stadium_right + 1):
            self.stdscr.addstr(self.stadium_top - 1, x, '═')
            self.stdscr.addstr(self.stadium_bottom, x, '═')
            
        # Side walls
        for y in range(self.stadium_top, self.stadium_bottom):
            self.stdscr.addstr(y, self.stadium_left - 1, '║')
            self.stdscr.addstr(y, self.stadium_right, '║')
            
        # Corners
        self.stdscr.addstr(self.stadium_top - 1, self.stadium_left - 1, '╔')
        self.stdscr.addstr(self.stadium_top - 1, self.stadium_right, '╗')
        self.stdscr.addstr(self.stadium_bottom, self.stadium_left - 1, '╚')
        self.stdscr.addstr(self.stadium_bottom, self.stadium_right, '╝')
        
        # Draw tunnel entrances
        tunnel_width = 5
        mid_y = (self.stadium_top + self.stadium_bottom) // 2
        mid_x = (self.stadium_left + self.stadium_right) // 2
        
        self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
        
        # North tunnel
        for i in range(tunnel_width):
            try:
                self.stdscr.addstr(self.stadium_top - 1, mid_x - tunnel_width//2 + i, ' ')
            except:
                pass
        if self.stadium_top >= 2:
            try:
                self.stdscr.addstr(self.stadium_top - 2, mid_x - 5, '↑ TUNNEL ↑')
            except:
                pass
        
        # South tunnel
        for i in range(tunnel_width):
            try:
                self.stdscr.addstr(self.stadium_bottom, mid_x - tunnel_width//2 + i, ' ')
            except:
                pass
        try:
            self.stdscr.addstr(self.stadium_bottom + 1, mid_x - 5, '↓ TUNNEL ↓')
        except:
            pass
        
        # West tunnel
        for i in range(tunnel_width):
            y = mid_y - tunnel_width//2 + i
            if self.stadium_top <= y < self.stadium_bottom:
                try:
                    self.stdscr.addstr(y, self.stadium_left - 1, ' ')
                except:
                    pass
        
        # East tunnel
        for i in range(tunnel_width):
            y = mid_y - tunnel_width//2 + i
            if self.stadium_top <= y < self.stadium_bottom:
                try:
                    self.stdscr.addstr(y, self.stadium_right, ' ')
                except:
                    pass
        
        self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
        
        # Stadium name banner
        banner = "★ NEON CYCLE ARENA ★"
        banner_x = (self.width - len(banner)) // 2
        self.stdscr.addstr(self.stadium_top - 2, banner_x, banner)
        
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Draw pickups
        for pickup in self.pickups:
            if not pickup.collected:
                self.stdscr.attron(curses.color_pair(pickup.color) | curses.A_BOLD)
                try:
                    # Draw pickup with animation
                    frame = int(time.time() * 3) % 3
                    if frame == 0:
                        self.stdscr.addstr(pickup.y, pickup.x, pickup.symbol)
                    elif frame == 1:
                        self.stdscr.addstr(pickup.y, pickup.x, '◊')
                    else:
                        self.stdscr.addstr(pickup.y, pickup.x, '♦')
                except:
                    pass
                self.stdscr.attroff(curses.color_pair(pickup.color) | curses.A_BOLD)
        
        # Draw droppers
        self.stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
        for dropper in self.droppers:
            # Handle tunnel transport for droppers
            if dropper.x <= self.stadium_left:
                dropper.x = self.stadium_right - 1
            elif dropper.x >= self.stadium_right - 1:
                dropper.x = self.stadium_left + 1
            if dropper.y <= self.stadium_top:
                dropper.y = self.stadium_bottom - 1
            elif dropper.y >= self.stadium_bottom - 1:
                dropper.y = self.stadium_top + 1
                
            if self.stadium_top <= dropper.y < self.stadium_bottom and self.stadium_left <= dropper.x < self.stadium_right:
                try:
                    # Draw center
                    self.stdscr.addstr(dropper.y, dropper.x, '◎')
                    # Draw radiating lines
                    lines = dropper.get_sprite_lines()
                    for i, (dy, dx) in enumerate(lines[:4]):  # Only draw 4 lines to avoid clutter
                        line_y = dropper.y + dy
                        line_x = dropper.x + dx
                        if self.stadium_top <= line_y < self.stadium_bottom and self.stadium_left <= line_x < self.stadium_right:
                            line_char = '─' if dx != 0 else '│'
                            self.stdscr.addstr(line_y, line_x, line_char)
                except:
                    pass
        self.stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
        
    def draw_bike(self, bike):
        if not bike.alive:
            return
            
        # Choose color based on jump state
        if bike.jump_timer > 0:
            # Flash between different colors when jumping
            flash_colors = [1, 2, 3, 4, 5, 6, 7]  # All available colors
            color_idx = (bike.jump_flash_counter // 2) % len(flash_colors)
            bike_color = flash_colors[color_idx]
        else:
            bike_color = bike.color
            
        # Draw trail with gradient effect
        self.stdscr.attron(curses.color_pair(bike_color))
        trail_chars = ['░', '▒', '▓', '█']
        trail_len = len(bike.trail)
        
        for i, (y, x) in enumerate(bike.trail):
            if self.stadium_top <= y < self.stadium_bottom and self.stadium_left <= x < self.stadium_right:
                # Use different characters based on trail age
                char_idx = min(3, i * 4 // trail_len) if trail_len > 0 else 3
                try:
                    self.stdscr.addstr(y, x, trail_chars[char_idx])
                except:
                    pass
        
        # Draw bike with direction sprite
        if self.stadium_top <= bike.y < self.stadium_bottom and self.stadium_left <= bike.x < self.stadium_right:
            # Special effects based on active powerups
            if bike.shield_timer > 0:
                # Shield effect - draw a protective aura
                self.stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = bike.y + dy, bike.x + dx
                        if self.stadium_top <= ny < self.stadium_bottom and self.stadium_left <= nx < self.stadium_right:
                            try:
                                self.stdscr.addstr(ny, nx, '·')
                            except:
                                pass
                self.stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
            
            self.stdscr.attron(curses.A_BOLD)
            try:
                self.stdscr.addstr(bike.y, bike.x, bike.get_sprite())
            except:
                pass
            self.stdscr.attroff(curses.A_BOLD)
            
        self.stdscr.attroff(curses.color_pair(bike_color))
        
    def handle_tunnel_transport(self, bike):
        """Handle tunnel transport for bikes"""
        # Check if bike hit a wall (tunnel entrance)
        transported = False
        
        # Left tunnel - transport to right
        if bike.x <= self.stadium_left - 1:
            bike.x = self.stadium_right - 1
            transported = True
        # Right tunnel - transport to left
        elif bike.x >= self.stadium_right:
            bike.x = self.stadium_left
            transported = True
        # Top tunnel - transport to bottom
        elif bike.y <= self.stadium_top - 1:
            bike.y = self.stadium_bottom - 1
            transported = True
        # Bottom tunnel - transport to top
        elif bike.y >= self.stadium_bottom:
            bike.y = self.stadium_top
            transported = True
            
        return transported
    
    def check_collision(self, bike):
        # Tunnels never cause collision - bike will be transported
        # Don't check wall collision since we have tunnels now
        
        # Jump invincibility protects from all collisions
        if bike.jump_invincibility:
            return False
            
        # Check trail collision with player
        if (bike.y, bike.x) in self.player.trail:
            return not (bike.shield_timer > 0)  # Shield protects
            
        # Check trail collision with all enemies
        for enemy in self.enemies:
            if (bike.y, bike.x) in enemy.trail:
                return not (bike.shield_timer > 0)  # Shield protects
                
        # Check obstacle collision
        for obstacle in self.obstacles:
            if obstacle.contains(bike.y, bike.x):
                return not (bike.shield_timer > 0)  # Shield protects
        
        # Check spike enemy collision
        for spike in self.spike_enemies:
            if spike.alive and spike.y == bike.y and spike.x == bike.x:
                return not (bike.shield_timer > 0)  # Shield protects
            
        return False
        
    def ai_move_single(self, enemy):
        """Move a single AI enemy"""
        if not enemy.alive:
            return
            
        directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        
        # Remove opposite direction
        opposite = None
        dy, dx = enemy.direction.value
        for d in directions:
            d_dy, d_dx = d.value
            if dy + d_dy == 0 and dx + d_dx == 0:
                opposite = d
                break
        if opposite:
            directions.remove(opposite)
            
        # Calculate safe moves with look-ahead
        safe_moves = []
        best_score = -999
        best_move = None
        
        for direction in directions:
            dy, dx = direction.value
            new_y = enemy.y + dy
            new_x = enemy.x + dx
            
            # Check immediate safety (tunnels are always safe)
            tunnel_move = (new_y < self.stadium_top or new_y >= self.stadium_bottom or
                          new_x < self.stadium_left or new_x >= self.stadium_right)
            
            if tunnel_move or ((self.stadium_top <= new_y < self.stadium_bottom and 
                self.stadium_left <= new_x < self.stadium_right and
                (new_y, new_x) not in self.player.trail)):
                
                # Check against all enemy trails
                trail_clear = True
                for other_enemy in self.enemies:
                    if (new_y, new_x) in other_enemy.trail:
                        trail_clear = False
                        break
                        
                # Check obstacles
                obstacle_clear = True
                for obstacle in self.obstacles:
                    if obstacle.contains(new_y, new_x):
                        obstacle_clear = False
                        break
                        
                if trail_clear and obstacle_clear:
                
                    # Score based on available space and pickups
                    score = 0
                    
                    # Check for nearby pickups
                    for pickup in self.pickups:
                        dist = abs(pickup.y - new_y) + abs(pickup.x - new_x)
                        if dist < 10:
                            score += (10 - dist) * 2  # Prioritize pickups
                            
                    # Strategy-based scoring
                    if hasattr(enemy, 'ai_strategy'):
                        # Cutoff strategy - try to intercept player
                        if 'cutoff' in enemy.ai_strategy:
                            # Predict where player will be
                            player_dy, player_dx = self.player.direction.value
                            future_player_y = self.player.y + player_dy * 5
                            future_player_x = self.player.x + player_dx * 5
                            
                            dist_to_future = abs(new_y - future_player_y) + abs(new_x - future_player_x)
                            score += max(0, 20 - dist_to_future) * 2
                            
                        # Aggressive strategy - chase player
                        if 'aggressive' in enemy.ai_strategy:
                            dist_to_player = abs(new_y - self.player.y) + abs(new_x - self.player.x)
                            score += max(0, 15 - dist_to_player)
                            
                        # Territorial strategy - control center
                        if 'territorial' in enemy.ai_strategy:
                            center_y = (self.stadium_top + self.stadium_bottom) // 2
                            center_x = (self.stadium_left + self.stadium_right) // 2
                            dist_to_center = abs(new_y - center_y) + abs(new_x - center_x)
                            score += max(0, 10 - dist_to_center)
                            
                        # Trap strategy - create confined spaces
                        if 'trap' in enemy.ai_strategy:
                            # Check if this move creates a smaller space for player
                            if self._creates_trap(new_y, new_x, enemy):
                                score += 30
                    
                    # AI difficulty affects look-ahead distance
                    look_ahead = 3 + getattr(enemy, 'ai_difficulty', 1) // 2
                    
                    # Check moves ahead
                    for ahead in range(1, look_ahead):
                        check_y = enemy.y + dy * ahead
                        check_x = enemy.x + dx * ahead
                        
                        blocked = False
                        
                        # Don't break on boundaries - AI can plan through tunnels
                        # Check if would go through tunnel
                        if (check_y < self.stadium_top or check_y >= self.stadium_bottom or
                            check_x < self.stadium_left or check_x >= self.stadium_right):
                            # AI considers tunnel as valid path
                            score += 5  # Bonus for using tunnels strategically
                            break  # But stop looking further
                            
                        # Check player trail
                        if (check_y, check_x) in self.player.trail:
                            break
                            
                        # Check enemy trails
                        for other_enemy in self.enemies:
                            if (check_y, check_x) in other_enemy.trail:
                                blocked = True
                                break
                                
                        # Check obstacles
                        for obstacle in self.obstacles:
                            if obstacle.contains(check_y, check_x):
                                blocked = True
                                break
                                
                        if blocked:
                            break
                            
                        score += 1
                        
                    safe_moves.append(direction)
                    if score > best_score:
                        best_score = score
                        best_move = direction
                        
        # Choose move - smarter AI at higher difficulty
        ai_randomness = max(0.02, 0.15 - 0.02 * getattr(enemy, 'ai_difficulty', 1))
        
        if best_move and random.random() > ai_randomness:
            enemy.turn(best_move)
        elif safe_moves:
            enemy.turn(random.choice(safe_moves))
            
    def ai_move(self):
        """Move all AI enemies"""
        for enemy in self.enemies:
            # Allow AI to toggle trail on/off at higher levels
            if hasattr(enemy, 'ai_difficulty') and enemy.ai_difficulty >= 4:
                if random.random() < 0.01:  # 1% chance per frame
                    enemy.manual_trail_off = not enemy.manual_trail_off
                    
            self.ai_move_single(enemy)
            
    def _creates_trap(self, y, x, enemy):
        """Check if position helps create a trap for player"""
        # Simple trap detection - check if player has limited escape routes
        player_escapes = 0
        for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            dy, dx = d.value
            check_y = self.player.y + dy
            check_x = self.player.x + dx
            
            if (self.stadium_top <= check_y < self.stadium_bottom and
                self.stadium_left <= check_x < self.stadium_right and
                (check_y, check_x) not in self.player.trail):
                
                # Check if move would block this escape
                if abs(y - check_y) + abs(x - check_x) <= 3:
                    continue
                    
                blocked = False
                for other in self.enemies:
                    if (check_y, check_x) in other.trail:
                        blocked = True
                        break
                        
                if not blocked:
                    player_escapes += 1
                    
        return player_escapes <= 2  # Trap if 2 or fewer escapes
            
    def draw_ui(self):
        # Draw score and stats
        self.stdscr.attron(curses.color_pair(4))
        
        # Score board
        score_y = self.stadium_bottom + 1
        self.stdscr.addstr(score_y, 2, f"SCORE: {self.score:06d}")
        self.stdscr.addstr(score_y, 20, f"TIME: {self.game_time // 10}s")
        
        # Show level info
        self.stdscr.attron(curses.color_pair(4))
        self.stdscr.addstr(score_y - 1, 2, f"LEVEL: {self.current_level}/{self.max_level}")
        time_left = max(0, self.level_duration - (self.game_time - self.level_start_time))
        self.stdscr.addstr(score_y - 1, 20, f"TIME LEFT: {time_left // 10}s")
        self.stdscr.attroff(curses.color_pair(4))
        
        # Player status and abilities
        status_x = 35
        
        # Player
        self.stdscr.attron(curses.color_pair(1))
        player_status = "ACTIVE" if self.player.alive else "CRASHED"
        try:
            self.stdscr.addstr(score_y, status_x, f"PLAYER: {player_status}")
            
            # Player abilities
            abilities = []
            if self.player.shield_timer > 0:
                abilities.append(f"🛡{self.player.shield_timer//10}")
            if self.player.boost_timer > 0:
                abilities.append(f"🚀{self.player.boost_timer//10}")
            if self.player.speed_timer > 0:
                abilities.append(f"🏁{self.player.speed_timer//10}")
            if self.player.stealth_timer > 0:
                abilities.append(f"👁{self.player.stealth_timer//10}")
            if self.player.jump_timer > 0:
                abilities.append(f"🦘{self.player.jump_timer//10}")
            
            if self.player.manual_trail_off:
                abilities.append(f"👁")
                
            # Show jumps remaining
            if self.player.jumps_remaining > 0:
                abilities.append(f"JUMPS:{self.player.jumps_remaining}")
                
            if abilities and status_x + 17 < self.width - 10:
                self.stdscr.addstr(score_y, status_x + 17, " ".join(abilities))
        except:
            pass
        self.stdscr.attroff(curses.color_pair(1))
        
        # Show all enemies
        enemy_y = score_y + 1
        for i, enemy in enumerate(self.enemies):
            # Check if we have space to draw this enemy
            if enemy_y + i >= self.height - 2:
                break
                
            self.stdscr.attron(curses.color_pair(2 + i % 2))
            enemy_status = "ACTIVE" if enemy.alive else "CRASHED"
            enemy_name = enemy.name if len(self.enemies) == 1 else f"{enemy.name}"
            try:
                self.stdscr.addstr(enemy_y + i, status_x, f"{enemy_name}: {enemy_status}")
                
                # Enemy abilities
                abilities = []
                if enemy.shield_timer > 0:
                    abilities.append(f"🛡")
                if enemy.boost_timer > 0:
                    abilities.append(f"🚀")
                if enemy.speed_timer > 0:
                    abilities.append(f"🏁")
                if enemy.manual_trail_off:
                    abilities.append(f"👁")
                    
                if abilities and status_x + 14 < self.width - 10:
                    self.stdscr.addstr(enemy_y + i, status_x + 14, " ".join(abilities))
            except:
                pass
            self.stdscr.attroff(curses.color_pair(2 + i % 2))
        
        # Controls
        self.stdscr.attron(curses.color_pair(4))
        if score_y + 2 < self.height - 1:
            try:
                self.stdscr.addstr(score_y + 2, 2, "ARROWS: move | SPACE: jump | T: trail | S: sound | R: restart | Q: quit")
            except:
                pass
        self.stdscr.attroff(curses.color_pair(4))
        
    def draw_fullscreen_warning(self):
        """Draw fullscreen warning after boot"""
        self.stdscr.clear()
        
        warning_lines = [
            "╔═══════════════════════════════════════╗",
            "║      MAXIMIZE YOUR TERMINAL NOW!      ║",
            "╚═══════════════════════════════════════╝",
            "",
            "For the best experience, please maximize",
            "your terminal window now!",
            "",
            "The arena requires maximum space!",
            "",
            "Press ENTER when ready..."
        ]
        
        start_y = max(0, (self.height - len(warning_lines)) // 2)
        
        # Flashing effect
        flash = int(time.time() * 2) % 2
        color = 4 if flash else 1
        
        self.stdscr.attron(curses.color_pair(color) | curses.A_BOLD)
        for i, line in enumerate(warning_lines):
            if start_y + i < self.height:
                x = max(0, (self.width - len(line)) // 2)
                try:
                    self.stdscr.addstr(start_y + i, x, line[:self.width-1])
                except:
                    pass
        self.stdscr.attroff(curses.color_pair(color) | curses.A_BOLD)
        
        self.stdscr.refresh()
        
    def draw_character_select(self):
        """Draw the character selection screen"""
        if not self.show_character_select:
            return
            
        self.stdscr.clear()
        
        # Title
        title = "SELECT YOUR RIDER"
        title_y = 3
        title_x = (self.width - len(title)) // 2
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(title_y, title_x, title)
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Draw characters
        start_y = 6
        for i, char in enumerate(self.characters):
            y = start_y + i * 8  # Much more spacing for readability
            
            # Check if we have enough space
            if y + 7 >= self.height - 8:
                break
                
            # Character name with color
            name_text = f"[{i+1}] {char['name']}"
            bike_text = "►►►"
            full_line = f"{name_text:<15}{bike_text}"
            
            # Highlight selected character - full line
            if i == self.selected_character:
                self.stdscr.attron(curses.color_pair(char['color']) | curses.A_REVERSE | curses.A_BOLD)
                # Fill the entire line width with highlight
                highlight_line = full_line + " " * (self.width - len(full_line) - 5)
                if y < self.height - 1:
                    self.stdscr.addstr(y, 5, highlight_line[:self.width-6])
                self.stdscr.attroff(curses.color_pair(char['color']) | curses.A_REVERSE | curses.A_BOLD)
            else:
                # Normal display
                self.stdscr.attron(curses.color_pair(char['color']) | curses.A_BOLD)
                if y < self.height - 1:
                    self.stdscr.addstr(y, 5, name_text)
                self.stdscr.attroff(curses.color_pair(char['color']) | curses.A_BOLD)
                
                # Show a sample bike
                self.stdscr.attron(curses.color_pair(char['color']))
                if y < self.height - 1:
                    self.stdscr.addstr(y, 20, bike_text)
                self.stdscr.attroff(curses.color_pair(char['color']))
            
            # Blank line after name
            if y + 1 < self.height - 1:
                self.stdscr.addstr(y + 1, 8, "")
            
            # Description - wrap if needed
            desc = char['description']
            max_width = min(70, self.width - 10)
            if y + 2 < self.height - 1:
                if len(desc) > max_width:
                    # Find a good break point
                    break_point = desc[:max_width].rfind(' ')
                    if break_point > 0:
                        self.stdscr.addstr(y + 2, 8, desc[:break_point])
                    else:
                        self.stdscr.addstr(y + 2, 8, desc[:max_width])
                else:
                    self.stdscr.addstr(y + 2, 8, desc)
            
            # Blank line after description
            if y + 3 < self.height - 1:
                self.stdscr.addstr(y + 3, 8, "")
            
            # Ability
            if y + 4 < self.height - 1:
                self.stdscr.attron(curses.A_BOLD)
                self.stdscr.addstr(y + 4, 8, char['ability'][:60])
                self.stdscr.attroff(curses.A_BOLD)
            
            # Blank line after ability
            if y + 5 < self.height - 1:
                self.stdscr.addstr(y + 5, 8, "")
            
            # Quote
            self.stdscr.attron(curses.color_pair(char['color']))
            if y + 6 < self.height - 1:
                self.stdscr.addstr(y + 6, 8, char['quote'][:50])
            self.stdscr.attroff(curses.color_pair(char['color']))
            
            # Extra blank line after each character
            if y + 7 < self.height - 1:
                self.stdscr.addstr(y + 7, 8, "")
                
        # Instructions
        instructions = [
            "Use UP/DOWN arrows to select",
            "Press ENTER to choose your rider",
            "",
            "Each rider has unique abilities!",
            "In-game: SPACE=jump, B=boost, T=trail toggle"
        ]
        
        inst_y = max(self.height - len(instructions) - 2, start_y + len(self.characters) * 4 + 1)
        for i, inst in enumerate(instructions):
            if inst_y + i >= self.height - 1:
                break
            x = (self.width - len(inst)) // 2
            if i < 2:
                self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(inst_y + i, x, inst)
            if i < 2:
                self.stdscr.attroff(curses.color_pair(3))
                
        self.stdscr.refresh()
        
    def draw_title_screen(self):
        if not self.show_menu:
            return
            
        self.stdscr.clear()
        
        # Animated title
        title = [
            "╔╗╔╔═╗╔═╗╔╗╔  ╔═╗╦ ╦╔═╗╦  ╔═╗",
            "║║║║╣ ║ ║║║║  ║  ╚╦╝║  ║  ║╣ ",
            "╝╚╝╚═╝╚═╝╝╚╝  ╚═╝ ╩ ╚═╝╩═╝╚═╝",
            "",
            "    ╔═╗╦═╗╔═╗╔╗╔╔═╗  ╔═╗╔╗╔╦ ╦╔═╗╔╗╔╔═╗╔═╗╔╦╗",
            "    ╠═╣╠╦╝║╣ ║║║╠═╣  ║╣ ║║║╠═╣╠═╣║║║║  ║╣  ║║",
            "    ╩ ╩╩╚═╚═╝╝╚╝╩ ╩  ╚═╝╝╚╝╩ ╩╩ ╩╝╚╝╚═╝╚═╝═╩╝"
        ]
        
        # Draw title with glow effect
        start_y = 3
        colors = [5, 1, 2, 6]
        color_idx = int(time.time() * 2) % len(colors)
        
        self.stdscr.attron(curses.color_pair(colors[color_idx]) | curses.A_BOLD)
        for i, line in enumerate(title):
            x = (self.width - len(line)) // 2
            self.stdscr.addstr(start_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(colors[color_idx]) | curses.A_BOLD)
        
        # Draw powerup info
        info_y = start_y + len(title) + 2
        powerup_info = [
            "POWERUPS:",
            "🛡 SHIELD - Protects from crashes (5 seconds)",
            "🚀 BOOST - Maximum speed boost",  
            "🏁 SPEED - Move faster"
        ]
        
        self.stdscr.attron(curses.color_pair(3))
        for i, line in enumerate(powerup_info):
            if info_y + i < self.height - 10:
                x = (self.width - len(line)) // 2
                self.stdscr.addstr(info_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(3))
        
        # Level info
        level_y = info_y + len(powerup_info) + 2
        self.stdscr.attron(curses.color_pair(5))
        level_info = [
            "LEVELS:",
            "1-2: Basic training",
            "3-5: Multiple enemies", 
            "6-8: AI learns to cut you off!",
            "9-11: Tactical AI cooperation",
            "12-15: ULTIMATE CHALLENGE!"
        ]
        for i, line in enumerate(level_info[:4]):  # Show first 4 lines
            if level_y + i < self.height - 10:
                x = (self.width - len(line)) // 2
                self.stdscr.addstr(level_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(5))
        
        # Menu options
        menu_y = level_y + 4
        self.stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
        menu_items = [
            f"▸ Press ENTER for Level {self.current_level}",
            "▸ Press 1-9, A-F for levels 1-15",
            "▸ Press Q to quit",
            "▸ Trail toggle: T key",
            "▸ Sound toggle: S key",
            f"▸ Fullscreen: F key {'[ON]' if self.fullscreen_mode else '[OFF]'}"
        ]
        for i, item in enumerate(menu_items):
            if menu_y + i < self.height - 2:
                x = (self.width - len(item)) // 2
                self.stdscr.addstr(menu_y + i, x, item)
        self.stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
        
        self.stdscr.refresh()
        
    def draw_game_over(self):
        if self.game_over and not hasattr(self, '_crash_played'):
            self.sound_manager.play_crash()
            self._crash_played = True
            
        if self.game_over:
            # Draw explosion effect at crash site
            if not self.player.alive:
                self.draw_explosion(self.player.y, self.player.x)
            for enemy in self.enemies:
                if not enemy.alive:
                    self.draw_explosion(enemy.y, enemy.x)
                
            # Game over message
            box_width = 40
            box_height = 7
            box_y = (self.stadium_top + self.stadium_bottom) // 2 - box_height // 2
            box_x = (self.width - box_width) // 2
            
            # Draw box
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            for y in range(box_y, box_y + box_height):
                for x in range(box_x, box_x + box_width):
                    self.stdscr.addstr(y, x, ' ')
                    
            # Box border
            for x in range(box_x, box_x + box_width):
                self.stdscr.addstr(box_y, x, '═')
                self.stdscr.addstr(box_y + box_height - 1, x, '═')
            for y in range(box_y, box_y + box_height):
                self.stdscr.addstr(y, box_x, '║')
                self.stdscr.addstr(y, box_x + box_width - 1, '║')
                
            # Message
            msg1 = "GAME OVER!"
            if self.level_won:
                msg1 = "LEVEL COMPLETE!"
                msg2 = f"Level {self.current_level} cleared!"
                msg3 = f"Score: {self.score}"
                msg4 = "Press ENTER for next level"
            else:
                msg2 = f"{self.winner} WINS!" if self.winner else "IT'S A TIE!"
                msg3 = f"Final Score: {self.score}"
                msg4 = "Press R to restart"
            
            self.stdscr.addstr(box_y + 1, box_x + (box_width - len(msg1)) // 2, msg1)
            self.stdscr.addstr(box_y + 2, box_x + (box_width - len(msg2)) // 2, msg2)
            self.stdscr.addstr(box_y + 3, box_x + (box_width - len(msg3)) // 2, msg3)
            self.stdscr.addstr(box_y + 5, box_x + (box_width - len(msg4)) // 2, msg4)
            
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
    def draw_explosion(self, y, x):
        """Draw explosion effect at crash site"""
        explosion = ['*', 'x', '+', '.']
        frame = int(time.time() * 10) % len(explosion)
        
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if (self.stadium_top <= y + dy < self.stadium_bottom and 
                    self.stadium_left <= x + dx < self.stadium_right):
                    try:
                        self.stdscr.addstr(y + dy, x + dx, explosion[frame])
                    except:
                        pass
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
    def check_terminal_size(self):
        """Check if terminal is large enough"""
        if self.width < self.min_width or self.height < self.min_height:
            return False
        return True
    
    def draw_size_warning(self):
        """Draw warning about terminal size"""
        self.stdscr.clear()
        
        warnings = [
            "TERMINAL TOO SMALL!",
            "",
            f"Current size: {self.width}x{self.height}",
            f"Minimum required: {self.min_width}x{self.min_height}",
            "",
            "Please maximize your terminal window",
            "or manually resize it larger",
            "",
            "Press Q to quit"
        ]
        
        start_y = max(0, (self.height - len(warnings)) // 2)
        
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        for i, line in enumerate(warnings):
            if start_y + i < self.height:
                x = max(0, (self.width - len(line)) // 2)
                try:
                    self.stdscr.addstr(start_y + i, x, line)
                except:
                    pass
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        self.stdscr.refresh()
    
    def boot_sequence(self):
        """Display retro boot sequence"""
        self.stdscr.clear()
        self.stdscr.nodelay(False)
        
        # Check if terminal is too small
        if self.height < 20 or self.width < 60:
            self.stdscr.attron(curses.color_pair(4))
            msg = "Terminal too small! Please resize and press any key..."
            try:
                self.stdscr.addstr(self.height // 2, max(0, (self.width - len(msg)) // 2), msg[:self.width-1])
            except:
                pass
            self.stdscr.refresh()
            self.stdscr.getch()
            return True  # Continue anyway
        
        curses.curs_set(1)  # Show cursor for typing effect
        
        # Terminal green color
        curses.init_pair(8, curses.COLOR_GREEN, curses.COLOR_BLACK)
        
        # Boot message
        boot_lines = [
            "SYSTEM INITIALIZED...",
            "LOADING SIMULATOR MODULE...",
            "",
            "HELLO SIR SHALL I FIRE SIMULATOR 78 Y/N? "
        ]
        
        y = 5
        for line in boot_lines[:-1]:
            self.stdscr.attron(curses.color_pair(8))
            for i, char in enumerate(line):
                self.stdscr.addstr(y, 2 + i, char)
                self.stdscr.refresh()
                time.sleep(0.02)
            self.stdscr.attroff(curses.color_pair(8))
            y += 1
            time.sleep(0.2)
        
        # Ask for input
        self.stdscr.attron(curses.color_pair(8) | curses.A_BOLD)
        for i, char in enumerate(boot_lines[-1]):
            self.stdscr.addstr(y, 2 + i, char)
            self.stdscr.refresh()
            time.sleep(0.03)
        
        # Wait for Y/N
        while True:
            key = self.stdscr.getch()
            if key in [ord('y'), ord('Y')]:
                self.stdscr.addstr(y, 2 + len(boot_lines[-1]), "Y")
                self.stdscr.refresh()
                self.sound_manager.play_menu_select()
                time.sleep(0.5)
                break
            elif key in [ord('n'), ord('N'), ord('q'), ord('Q')]:
                self.stdscr.addstr(y, 2 + len(boot_lines[-1]), "N")
                self.stdscr.refresh()
                time.sleep(0.5)
                return False
        
        self.stdscr.attroff(curses.color_pair(8) | curses.A_BOLD)
        
        # Show motorcycle ASCII art for 3 seconds
        self.stdscr.clear()
        motorcycle_art = [
            "                                :b                                                ",
            "                  .'\\          $                                                ",
            "                 /   ;         :P                                                ",
            "                /   ,;         ;`                                                ",
            "               /_.-\" L        _:_                                                ",
            "              :\"      \\      ;  .j-.                                             ",
            "              ;   _    ; .--/ : ;-.()                                            ",
            "             :  .' \"-./.'.-'  ;  \"\"    __.._                                     ",
            "             './ __..-`.-\"-._/\"\"\"\"\"\"--:._   \"-.                                  ",
            "           _.-\"\"\"\"-._                    \"-.   \\                                 ",
            "        .-\"  __..----\"\"t\"\"\"----.._          \\   \\             ___...+------.     ",
            "      .'__.-\"_..--\"\"-.__jj-. (+)\\  `.         ;   ;         .-\"    .-\"     /;    ",
            "      \"\"   \"\"         j /  ;    .^\"       .-\"  .' \"-------\"       \\__..--j._     ",
            "                     / i   :_.-\"   _..--\"\"   .'                 .-\" /\\\\\\/  \\;    ",
            "                    / /;;  ;(      ___...-+-\"                .-\"   /o.-\" .-t\\    ",
            "                   / / :;  '._LL.+\"\\    `.o`..._          .-\"    .'\"\" .-\"   \"    ",
            "                 /`-:   ;;   ;   ;  \\    :`. `. \"\"\"\"----\"\"-.__.'.\\ .-\"           ",
            "        _......_/   /   ::   :`-':   \\    \\ `. `. ====     .-j\\ .+t..._          ",
            "     .-\"       /   /     ;    ;  :-.  \\  .'`. `. `.===  .-\".'.-\"       \"-.       ",
            "   .'     _.../   /`.    :    :  ;  \\  `:_.._`--`. `---' .'.'   _..._     `..-.  ",
            "  /    .-\"   /   /   \\         ; ;   L.+\" .. `,  :     .'.'  .-\"     \"-. .-\"\\  \\ ",
            " :    /     /   /\\    ;       ,:_;.-\"  : (  ) ;   )  .'.'-._/         .-t   .--.;",
            " ;   :   .-/   /  ;   :       :  \\`._  '. \"\" .'  : .'.'-._  \"-._----\"   t-\" :  '",
            ":   :   ; /   i    ;   ;       \\_ `. \"\"\"\"\"\"\"\" `. ;'.;  :  \"+._  \"-:_  .-\" ;   ;  ",
            ";   ;   ;/   /:    :   :        `., \"\"\"\"\"\";..__.'.',^--;   ;  \"+._o \"^.   :   :  ",
            ":   :   '\\_.'.'    ;   ;          \"-:____/...___\"--^-+-:   :   '. \"-._;   ;   ;  ",
            " ;   :    \"\"\"     ;   :                         \"\"\"\"\"'  ;   :    \"\"\"     ;   :   ",
            " :    \\          /    ;                             bug :    \\          /    ;   ",
            "  \\    \"-.____.-\"    /                                   \\    \"-.____.-\"    /    ",
            "   `.              .'                                     `.              .'     ",
            "     \"-._      _.-\"                                         \"-._      _.-\"       ",
            "         \"\"\"\"\"\"                                                 \"\"\"\"\"\"  "
        ]
        
        # Display motorcycle art centered
        art_start_y = max(2, (self.height - len(motorcycle_art)) // 2)
        self.stdscr.attron(curses.color_pair(8))
        for i, line in enumerate(motorcycle_art):
            if art_start_y + i >= self.height - 1:
                break
            art_x = max(0, (self.width - len(line)) // 2)
            try:
                self.stdscr.addstr(art_start_y + i, art_x, line[:self.width-1])
            except:
                pass
        self.stdscr.attroff(curses.color_pair(8))
        
        self.stdscr.refresh()
        time.sleep(3.0)  # Show for 3 seconds
        
        # Loading sequence
        self.stdscr.clear()
        curses.curs_set(0)
        
        # ASCII art computer
        computer_art = [
            "     ╔═══════════════════════════╗",
            "     ║  ┌─────────────────────┐  ║",
            "     ║  │  SIMULATOR 78 v2.1  │  ║",
            "     ║  │                     │  ║",
            "     ║  │   LOADING SYSTEM    │  ║",
            "     ║  │                     │  ║",
            "     ║  └─────────────────────┘  ║",
            "     ╠═══════════════════════════╣",
            "     ║  [■][■][■]  ○○○○○○○○○○  ║",
            "     ╚═══════════════════════════╝",
            "            ╔═══════╗",
            "            ║ ||||| ║",
            "            ╚═══════╝"
        ]
        
        # Draw computer
        start_y = 3
        for i, line in enumerate(computer_art):
            if start_y + i >= self.height - 1:
                break
            x = max(0, (self.width - len(line)) // 2)
            self.stdscr.attron(curses.color_pair(8))
            try:
                self.stdscr.addstr(start_y + i, x, line[:self.width-1])
            except:
                pass
            self.stdscr.attroff(curses.color_pair(8))
        
        # Loading bar
        loading_y = start_y + len(computer_art) + 2
        loading_x = max(1, (self.width - 50) // 2)
        
        if loading_y + 4 < self.height - 1:
            self.stdscr.attron(curses.color_pair(8))
            try:
                self.stdscr.addstr(loading_y, loading_x, "BOOTING NEON CYCLE ARENA...")
                self.stdscr.addstr(loading_y + 2, loading_x, "[" + " " * 46 + "]")
            except:
                pass
        
        # Loading stages
        stages = [
            "INITIALIZING LIGHT CYCLES...",
            "LOADING ARENA MATRIX...",
            "CALIBRATING PHOTON TRAILS...",
            "SYNCING CROWD SIMULATOR...",
            "ACTIVATING NEON SHADERS...",
            "PREPARING QUANTUM PICKUPS...",
            "SYSTEM READY!"
        ]
        
        for i, stage in enumerate(stages):
            if loading_y + 4 >= self.height - 1:
                break
                
            try:
                # Update stage text
                self.stdscr.move(loading_y + 4, 0)
                self.stdscr.clrtoeol()
                stage_x = max(0, (self.width - len(stage)) // 2)
                self.stdscr.addstr(loading_y + 4, stage_x, stage[:self.width-1])
                
                # Update progress bar
                progress = int((i + 1) / len(stages) * 46)
                bar = "█" * progress + "░" * (46 - progress)
                if loading_x + 1 < self.width - 47:
                    self.stdscr.addstr(loading_y + 2, loading_x + 1, bar)
                
                # Percentage
                percent = int((i + 1) / len(stages) * 100)
                percent_str = f"{percent}%"
                if loading_x + 48 < self.width - 4:
                    self.stdscr.addstr(loading_y + 2, loading_x + 48, percent_str)
            except:
                pass
            
            self.stdscr.refresh()
            
            # Play a beep for each stage
            if i % 2 == 0:
                self.sound_manager.play_menu_select()
            
            time.sleep(0.4)
        
        self.stdscr.attroff(curses.color_pair(8))
        
        # Final message
        time.sleep(0.5)
        if loading_y + 6 < self.height - 1:
            self.stdscr.attron(curses.color_pair(8) | curses.A_BOLD | curses.A_BLINK)
            ready_msg = "PRESS ANY KEY TO ENTER THE ARENA"
            msg_x = max(0, (self.width - len(ready_msg)) // 2)
            try:
                self.stdscr.addstr(loading_y + 6, msg_x, ready_msg[:self.width-1])
            except:
                pass
            self.stdscr.attroff(curses.color_pair(8) | curses.A_BOLD | curses.A_BLINK)
        
        self.stdscr.refresh()
        self.stdscr.getch()  # Wait for any key
        self.sound_manager.play_menu_select()
        
        # Reset for game
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)
        
        # Show fullscreen warning
        self.show_fullscreen_warning = True
        
        return True
    
    def run(self):
        # Set up curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)  # Faster refresh for smoother animation
        
        # Run boot sequence first
        if not self.boot_sequence():
            return  # User chose not to play
            
        # Handle fullscreen warning
        while self.show_fullscreen_warning:
            self.draw_fullscreen_warning()
            key = self.stdscr.getch()
            if key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                self.show_fullscreen_warning = False
                self.show_menu = True
                self.sound_manager.play_menu_select()
            elif key == ord('q') or key == ord('Q'):
                return
        
        while True:
            # Update terminal size
            self.height, self.width = self.stdscr.getmaxyx()
            self.stadium_bottom = self.height - 4
            self.stadium_right = self.width - 2
            self.game_height = self.stadium_bottom - self.stadium_top
            self.game_width = self.stadium_right - self.stadium_left
            
            # Check if terminal is big enough
            if not self.check_terminal_size():
                self.draw_size_warning()
                key = self.stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    break
                continue
                
            if self.show_menu:
                self.draw_title_screen()
            elif self.show_character_select:
                self.draw_character_select()
            else:
                self.stdscr.clear()
                
                # Update animations
                self.crowd_animation = (self.crowd_animation + 1) % 10
                
                # Draw game elements
                self.draw_stadium()
                self.draw_bike(self.player)
                for enemy in self.enemies:
                    self.draw_bike(enemy)
                
                # Draw spike enemies
                for spike in self.spike_enemies:
                    if spike.alive:
                        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)  # Red spikes
                        try:
                            self.stdscr.addstr(spike.y, spike.x, spike.get_sprite())
                        except:
                            pass
                        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                
                self.draw_ui()
                self.draw_game_over()
                
                self.stdscr.refresh()
                
            # Handle input
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                self.sound_manager.stop_music()
                break
            elif key == ord('s') or key == ord('S'):
                self.sound_manager.toggle_sound()
            elif key == ord('f') or key == ord('F'):
                # Toggle fullscreen mode
                self.fullscreen_mode = not self.fullscreen_mode
                self.update_stadium_dimensions()
                # Reset game positions to new dimensions
                if not self.game_over and not self.show_menu and not self.show_character_select:
                    self.reset_game()
            elif self.show_character_select:
                if key == curses.KEY_UP:
                    self.selected_character = (self.selected_character - 1) % len(self.characters)
                    self.sound_manager.play_menu_select()
                elif key == curses.KEY_DOWN:
                    self.selected_character = (self.selected_character + 1) % len(self.characters)
                    self.sound_manager.play_menu_select()
                elif key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                    # Select character and start game
                    self.player_color = self.characters[self.selected_character]['color']
                    self.sound_manager.play_menu_select()
                    self.show_character_select = False
                    self.reset_game()
                    self.sound_manager.play_background_music()
            elif self.show_menu:
                if key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                    self.sound_manager.play_menu_select()
                    self.show_menu = False
                    self.show_character_select = True
                # Level selection 1-9
                elif ord('1') <= key <= ord('9'):
                    self.current_level = key - ord('0')
                    self.sound_manager.play_menu_select()
                    self.show_menu = False
                    self.show_character_select = True
                # Level selection 10-15 (A-F)
                elif ord('a') <= key <= ord('f'):
                    self.current_level = 10 + (key - ord('a'))
                    self.sound_manager.play_menu_select()
                    self.show_menu = False
                    self.show_character_select = True
                elif ord('A') <= key <= ord('F'):
                    self.current_level = 10 + (key - ord('A'))
                    self.sound_manager.play_menu_select()
                    self.show_menu = False
                    self.show_character_select = True
            elif key == ord('r') or key == ord('R'):
                if self.game_over and not self.level_won:
                    self.reset_game()
                    self.show_menu = True
            elif self.game_over and self.level_won:
                # Next level on enter
                if key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                    if self.current_level < self.max_level:
                        self.current_level += 1
                        self.reset_game()
                        self.sound_manager.play_menu_select()
                    else:
                        # Beat all levels - back to menu
                        self.current_level = 1
                        self.show_menu = True
                        self.reset_game()
            elif not self.game_over:
                # Player controls
                if key == curses.KEY_UP:
                    self.player.turn(Direction.UP)
                elif key == curses.KEY_DOWN:
                    self.player.turn(Direction.DOWN)
                elif key == curses.KEY_LEFT:
                    self.player.turn(Direction.LEFT)
                elif key == curses.KEY_RIGHT:
                    self.player.turn(Direction.RIGHT)
                elif key == ord('t') or key == ord('T'):  # Toggle trail
                    self.player.manual_trail_off = not self.player.manual_trail_off
                    self.sound_manager.play_menu_select()
                elif key == ord(' '):  # Spacebar for jump
                    if self.player.jump():
                        self.sound_manager.play_menu_select()  # Play jump sound
                elif key == ord('b') or key == ord('B'):  # B key for boost
                    if self.player.use_boost():
                        self.sound_manager.play_menu_select()  # Play boost sound
                    
            # Game logic
            if not self.game_over and not self.show_menu:
                self.game_time += 1
                
                # Update bike timers
                self.player.update_timers()
                for enemy in self.enemies:
                    enemy.update_timers()
                
                # Spawn pickups
                self.pickup_spawn_timer -= 1
                if self.pickup_spawn_timer <= 0:
                    self.spawn_pickup()
                    self.pickup_spawn_timer = random.randint(100, 200)  # Random spawn interval
                    
                # Update droppers
                for dropper in self.droppers:
                    dropper.update()
                    
                    # Check if dropper should drop something
                    if dropper.drop_timer <= 0:
                        dropper.drop_timer = random.randint(30, 80)
                        
                        # 70% chance to drop obstacle, 30% pickup
                        if random.random() < 0.7:
                            # Drop obstacle
                            size = random.randint(2, 4)
                            shape = random.choice(["rock", "rectangle", "triangle"])
                            obstacle = Obstacle(dropper.y + 2, dropper.x - size//2, size, size, shape)
                            self.obstacles.append(obstacle)
                        else:
                            # Drop pickup
                            pickup_type = random.choice(list(PickupType))
                            self.pickups.append(Pickup(dropper.y + 2, dropper.x, pickup_type))
                
                # AI decision
                self.ai_move()
                
                # Move bikes
                self.player.move()
                # Handle tunnel transport for player
                self.handle_tunnel_transport(self.player)
                
                for enemy in self.enemies:
                    enemy.move()
                    # Handle tunnel transport for enemies
                    self.handle_tunnel_transport(enemy)
                
                # Update spike enemies
                for spike in self.spike_enemies:
                    spike.update()
                
                # Check pickups
                self.check_pickups(self.player)
                for enemy in self.enemies:
                    self.check_pickups(enemy)
                
                # Check collisions
                player_crashed = self.check_collision(self.player)
                if player_crashed:
                    self.player.alive = False
                    
                enemies_alive = 0
                for enemy in self.enemies:
                    if enemy.alive:
                        enemy_crashed = self.check_collision(enemy)
                        if enemy_crashed:
                            enemy.alive = False
                            self.score += 500
                        else:
                            enemies_alive += 1
                    
                # Check game over conditions
                if not self.player.alive:
                    self.game_over = True
                    self.winner = "CPU"
                elif enemies_alive == 0:
                    # All enemies defeated
                    self.game_over = True
                    self.level_won = True
                    self.winner = "PLAYER"
                    self.score += 1000 * self.current_level
                elif self.game_time - self.level_start_time >= self.level_duration:
                    # Time's up - player survives
                    self.game_over = True
                    self.level_won = True
                    self.winner = "PLAYER"
                    self.score += 500 * self.current_level
                else:
                    self.score += 1

def main():
    import os
    import sys
    
    # Clear screen first
    os.system('clear' if os.name != 'nt' else 'cls')
    
    # Check for custom level argument
    custom_level = None
    if len(sys.argv) > 2 and sys.argv[1] == '--level':
        try:
            custom_level = int(sys.argv[2])
        except:
            pass
    
    # Run the game
    def run_with_level(stdscr):
        game = LightBikeEnhanced(stdscr)
        if custom_level:
            game.load_custom_level(custom_level)
        return game.run()
    
    curses.wrapper(run_with_level)

if __name__ == "__main__":
    main()