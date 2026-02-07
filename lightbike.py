#!/usr/bin/env python3
import curses
import time
import random
import subprocess
import threading
import os
from collections import deque
from enum import Enum

class SoundManager:
    def __init__(self):
        self.music_process = None
        self.sound_enabled = True
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self._active_procs = []
        
    def play_background_music(self):
        """Play background music once using afplay"""
        if not self.sound_enabled:
            return
            
        def play_music():
            try:
                music_path = os.path.join(self.base_path, 'background_music.wav')
                if os.path.exists(music_path):
                    proc = subprocess.Popen(['afplay', music_path],
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                    self._active_procs.append(proc)
                    proc.wait()
            except (OSError, subprocess.SubprocessError):
                pass
        
        if self.music_process is None or not self.music_process.is_alive():
            self.music_process = threading.Thread(target=play_music, daemon=True)
            self.music_process.start()
    
    ALLOWED_SOUNDS = {'crash.wav', 'menu_select.wav', 'background_music.wav'}

    def play_sound_effect(self, sound_file):
        """Play a sound effect using afplay"""
        if not self.sound_enabled:
            return
        if sound_file not in self.ALLOWED_SOUNDS:
            return

        def play():
            try:
                sound_path = os.path.join(self.base_path, sound_file)
                if os.path.exists(sound_path):
                    proc = subprocess.Popen(['afplay', sound_path],
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                    self._active_procs.append(proc)
                    proc.wait()
            except (OSError, subprocess.SubprocessError):
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
        for proc in self._active_procs:
            try:
                proc.terminate()
            except OSError:
                pass
        self._active_procs.clear()
    
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
    TRAIL_OFF = ("TRAIL OFF", "💨", 6, 150) # trail off temporarily

class Pickup:
    def __init__(self, y, x, pickup_type):
        self.y = y
        self.x = x
        self.type = pickup_type
        self.name, self.symbol, self.color, self.duration = pickup_type.value
        self.collected = False

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
        self.speed_timer = 0
        self.stealth_timer = 0  # Trail off timer
        self.trail_enabled = True
        self.manual_trail_off = False  # Track manual trail toggle
        
        # Movement
        self.move_cooldown = 0
        self.base_speed = 3  # Slower speed (higher = slower)
        
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
        
    def get_sprite(self):
        # Show different sprite based on active powerups
        if self.shield_timer > 0:
            return '◈'
        elif self.stealth_timer > 0 or self.manual_trail_off:
            return '◌'
        elif self.boost_timer > 0:
            return '⚫'
        elif self.speed_timer > 0:
            return '◉'
        return self.bike_chars.get(self.direction, '●')

class LightBikeEnhanced:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Check terminal size
        self.min_width = 80
        self.min_height = 24
        
        # Stadium dimensions - use most of the screen
        self.stadium_top = 3
        self.stadium_bottom = self.height - 4
        self.stadium_left = 2
        self.stadium_right = self.width - 2
        
        self.game_height = self.stadium_bottom - self.stadium_top
        self.game_width = self.stadium_right - self.stadium_left
        
        self.show_menu = True
        self.sound_enabled = True
        self.crowd_animation = 0
        
        # Initialize sound manager
        self.sound_manager = SoundManager()
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Player
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # AI
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Walls
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
        
        self.reset_game()
        
            
    def reset_game(self):
        # Initialize bikes in starting positions
        start_y = self.stadium_top + self.game_height // 2
        
        player_x = self.stadium_left + self.game_width // 4
        ai_x = self.stadium_left + 3 * self.game_width // 4
        
        self.player = Bike(start_y, player_x, Direction.RIGHT, 1, "PLAYER", self.player_sprites)
        self.ai = Bike(start_y, ai_x, Direction.LEFT, 2, "CPU", self.ai_sprites)
        
        self.score = 0
        self.game_over = False
        self.winner = None
        self.show_menu = False
        self.game_time = 0
        self.pickups = []
        self.pickup_spawn_timer = 100  # Spawn first pickup after 100 ticks
        
        if hasattr(self, '_crash_played'):
            delattr(self, '_crash_played')
            
    def spawn_pickup(self):
        """Spawn a random pickup on the field"""
        # Try to find a valid spawn location
        for _ in range(50):  # Try 50 times to find a spot
            y = random.randint(self.stadium_top + 2, self.stadium_bottom - 2)
            x = random.randint(self.stadium_left + 2, self.stadium_right - 2)
            
            # Check if location is clear
            if ((y, x) not in self.player.trail and 
                (y, x) not in self.ai.trail and
                (y, x) != (self.player.y, self.player.x) and
                (y, x) != (self.ai.y, self.ai.x)):
                
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
                elif pickup.type == PickupType.BOOST:
                    bike.boost_timer = pickup.duration
                elif pickup.type == PickupType.SPEED:
                    bike.speed_timer = pickup.duration
                elif pickup.type == PickupType.TRAIL_OFF:
                    bike.stealth_timer = pickup.duration
                    
                self.pickups.remove(pickup)
                self.sound_manager.play_menu_select()  # Pickup sound
                return pickup
        return None
            
    def draw_stadium(self):
        # Draw crowd at top
        crowd_chars = ['o', 'O', '0', 'θ', '*', '°']
        self.stdscr.attron(curses.color_pair(7))
        
        # Top crowd
        for y in range(0, self.stadium_top - 1):
            crowd_line = ''
            for x in range(0, self.width):
                if random.random() > 0.3:
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    crowd_line += char
                else:
                    crowd_line += ' '
            try:
                self.stdscr.addstr(y, 0, crowd_line[:self.width-1])
            except curses.error:
                pass
                        
        # Side crowds
        for y in range(self.stadium_top, self.stadium_bottom):
            # Left crowd
            for x in range(0, self.stadium_left - 1):
                if random.random() > 0.3:
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    try:
                        self.stdscr.addstr(y, x, char)
                    except curses.error:
                        pass
            # Right crowd
            for x in range(self.stadium_right + 1, self.width):
                if random.random() > 0.3:
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    try:
                        self.stdscr.addstr(y, x, char)
                    except curses.error:
                        pass
                        
        self.stdscr.attroff(curses.color_pair(7))
        
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
                except curses.error:
                    pass
                self.stdscr.attroff(curses.color_pair(pickup.color) | curses.A_BOLD)
        
    def draw_bike(self, bike):
        if not bike.alive:
            return
            
        # Draw trail with gradient effect
        self.stdscr.attron(curses.color_pair(bike.color))
        trail_chars = ['░', '▒', '▓', '█']
        trail_len = len(bike.trail)
        
        for i, (y, x) in enumerate(bike.trail):
            if self.stadium_top <= y < self.stadium_bottom and self.stadium_left <= x < self.stadium_right:
                # Use different characters based on trail age
                char_idx = min(3, i * 4 // trail_len) if trail_len > 0 else 3
                try:
                    self.stdscr.addstr(y, x, trail_chars[char_idx])
                except curses.error:
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
                            except curses.error:
                                pass
                self.stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
            
            self.stdscr.attron(curses.A_BOLD)
            try:
                self.stdscr.addstr(bike.y, bike.x, bike.get_sprite())
            except curses.error:
                pass
            self.stdscr.attroff(curses.A_BOLD)
            
        self.stdscr.attroff(curses.color_pair(bike.color))
        
    def check_collision(self, bike):
        # Check wall collision
        if (bike.y <= self.stadium_top - 1 or bike.y >= self.stadium_bottom or 
            bike.x <= self.stadium_left - 1 or bike.x >= self.stadium_right):
            return not (bike.shield_timer > 0)  # Shield protects from walls
            
        # Check trail collision
        if (bike.y, bike.x) in self.player.trail:
            return not (bike.shield_timer > 0)  # Shield protects
        if (bike.y, bike.x) in self.ai.trail:
            return not (bike.shield_timer > 0)  # Shield protects
            
        return False
        
    def ai_move(self):
        if not self.ai.alive:
            return
            
        
        directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        
        # Remove opposite direction
        opposite = None
        dy, dx = self.ai.direction.value
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
            new_y = self.ai.y + dy
            new_x = self.ai.x + dx
            
            # Check immediate safety
            if (self.stadium_top <= new_y < self.stadium_bottom and 
                self.stadium_left <= new_x < self.stadium_right and
                (new_y, new_x) not in self.player.trail and
                (new_y, new_x) not in self.ai.trail):
                
                # Score based on available space and pickups
                score = 0
                
                # Check for nearby pickups
                for pickup in self.pickups:
                    dist = abs(pickup.y - new_y) + abs(pickup.x - new_x)
                    if dist < 10:
                        score += (10 - dist) * 2  # Prioritize pickups
                
                # Check 3 moves ahead
                for ahead in range(1, 4):
                    check_y = self.ai.y + dy * ahead
                    check_x = self.ai.x + dx * ahead
                    if (self.stadium_top <= check_y < self.stadium_bottom and 
                        self.stadium_left <= check_x < self.stadium_right and
                        (check_y, check_x) not in self.player.trail and
                        (check_y, check_x) not in self.ai.trail):
                        score += 1
                    else:
                        break
                        
                safe_moves.append(direction)
                if score > best_score:
                    best_score = score
                    best_move = direction
                    
        # Choose move
        if best_move and random.random() > 0.1:  # Mostly pick best move
            self.ai.turn(best_move)
        elif safe_moves:
            self.ai.turn(random.choice(safe_moves))
            
    def draw_ui(self):
        # Draw score and stats
        self.stdscr.attron(curses.color_pair(4))
        
        # Score board
        score_y = self.stadium_bottom + 1
        self.stdscr.addstr(score_y, 2, f"SCORE: {self.score:06d}")
        self.stdscr.addstr(score_y, 20, f"TIME: {self.game_time // 10}s")
        
        # Player status and abilities
        status_x = 35
        
        # Player
        self.stdscr.attron(curses.color_pair(1))
        player_status = "ACTIVE" if self.player.alive else "CRASHED"
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
        
        if abilities:
            self.stdscr.addstr(score_y, status_x + 17, " ".join(abilities))
        self.stdscr.attroff(curses.color_pair(1))
        
        # AI
        self.stdscr.attron(curses.color_pair(2))
        ai_status = "ACTIVE" if self.ai.alive else "CRASHED"
        self.stdscr.addstr(score_y + 1, status_x, f"CPU: {ai_status}")
        
        # AI abilities
        abilities = []
        if self.ai.shield_timer > 0:
            abilities.append(f"🛡")
        if self.ai.boost_timer > 0:
            abilities.append(f"🚀")
        if self.ai.speed_timer > 0:
            abilities.append(f"🏁")
        if self.ai.stealth_timer > 0:
            abilities.append(f"👁")
            
        if abilities:
            self.stdscr.addstr(score_y + 1, status_x + 14, " ".join(abilities))
        self.stdscr.attroff(curses.color_pair(2))
        
        # Controls
        self.stdscr.attron(curses.color_pair(4))
        self.stdscr.addstr(score_y + 2, 2, "ARROWS: move | T: trail on/off | S: sound on/off | R: restart | Q: quit")
        self.stdscr.attroff(curses.color_pair(4))
        
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
            "🏁 SPEED - Move faster",
            "👁 STEALTH - No trail temporarily"
        ]
        
        self.stdscr.attron(curses.color_pair(3))
        for i, line in enumerate(powerup_info):
            if info_y + i < self.height - 10:
                x = (self.width - len(line)) // 2
                self.stdscr.addstr(info_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(3))
        
        # Menu options
        menu_y = info_y + len(powerup_info) + 2
        self.stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
        menu_items = [
            "▸ Press ENTER to start",
            "▸ Press Q to quit",
            "▸ Trail toggle: T key during game",
            "▸ Sound toggle: S key"
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
            if not self.ai.alive:
                self.draw_explosion(self.ai.y, self.ai.x)
                
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
                    except curses.error:
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
            "Please maximize your terminal window:",
            "• On macOS: Press Cmd+Ctrl+F or click green button",
            "• On Windows: Press Alt+Enter",
            "• On Linux: Press F11",
            "",
            "Or manually resize the window larger",
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
                except curses.error:
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
            except curses.error:
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
            except curses.error:
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
            except curses.error:
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
            except curses.error:
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
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(8) | curses.A_BOLD | curses.A_BLINK)
        
        self.stdscr.refresh()
        self.stdscr.getch()  # Wait for any key
        self.sound_manager.play_menu_select()
        
        # Reset for game
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)
        return True
    
    def run(self):
        # Set up curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)  # Faster refresh for smoother animation
        
        # Run boot sequence first
        if not self.boot_sequence():
            return  # User chose not to play
        
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
            else:
                self.stdscr.clear()
                
                # Update animations
                self.crowd_animation = (self.crowd_animation + 1) % 10
                
                # Draw game elements
                self.draw_stadium()
                self.draw_bike(self.player)
                self.draw_bike(self.ai)
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
            elif self.show_menu:
                if key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                    self.sound_manager.play_menu_select()
                    self.reset_game()
                    self.sound_manager.play_background_music()  # Start music when game starts
            elif key == ord('r') or key == ord('R'):
                self.reset_game()
                self.show_menu = True
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
                    
            # Game logic
            if not self.game_over and not self.show_menu:
                self.game_time += 1
                
                # Update bike timers
                self.player.update_timers()
                self.ai.update_timers()
                
                # Spawn pickups
                self.pickup_spawn_timer -= 1
                if self.pickup_spawn_timer <= 0:
                    self.spawn_pickup()
                    self.pickup_spawn_timer = random.randint(100, 200)  # Random spawn interval
                
                # AI decision
                self.ai_move()
                
                # Move bikes
                self.player.move()
                self.ai.move()
                
                # Check pickups
                self.check_pickups(self.player)
                self.check_pickups(self.ai)
                
                # Check collisions
                player_crashed = self.check_collision(self.player)
                ai_crashed = self.check_collision(self.ai)
                
                if player_crashed:
                    self.player.alive = False
                if ai_crashed:
                    self.ai.alive = False
                    
                # Check game over
                if player_crashed and ai_crashed:
                    self.game_over = True
                    self.winner = None
                elif player_crashed:
                    self.game_over = True
                    self.winner = "CPU"
                elif ai_crashed:
                    self.game_over = True
                    self.winner = "PLAYER"
                    self.score += 1000
                else:
                    self.score += 1

def main():
    # curses.wrapper already handles screen init/cleanup — no need for os.system('clear')
    curses.wrapper(lambda stdscr: LightBikeEnhanced(stdscr).run())

if __name__ == "__main__":
    main()