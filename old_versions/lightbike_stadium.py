#!/usr/bin/env python3
import curses
import time
import random
import math
from collections import deque
from enum import Enum

class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

class Bike:
    def __init__(self, y, x, direction, color, name, bike_chars):
        self.y = y
        self.x = x
        self.direction = direction
        self.color = color
        self.name = name
        self.bike_chars = bike_chars  # Dict of direction -> bike appearance
        self.trail = deque(maxlen=1000)
        self.alive = True
        self.boost = 0
        
    def move(self):
        if not self.alive:
            return
            
        # Add current position to trail
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
        return self.bike_chars.get(self.direction, '●')

class LightBikeStadium:
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
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Player
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # AI
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Walls
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # UI
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Title
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Menu
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Crowd
        
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
        
        self.reset_game()
        
    def play_beep(self):
        """Play a beep sound using system command"""
        if not self.sound_enabled:
            return
        try:
            # Use printf and play command on macOS
            cmd = f"printf '\\a'"
            import subprocess
            subprocess.run(cmd, shell=True, capture_output=True)
        except:
            pass
            
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
        if hasattr(self, '_crash_played'):
            delattr(self, '_crash_played')
            
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
            except:
                pass
                        
        # Side crowds
        for y in range(self.stadium_top, self.stadium_bottom):
            # Left crowd
            for x in range(0, self.stadium_left - 1):
                if random.random() > 0.3:
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    try:
                        self.stdscr.addstr(y, x, char)
                    except:
                        pass
            # Right crowd
            for x in range(self.stadium_right + 1, self.width):
                if random.random() > 0.3:
                    char = crowd_chars[(x + y + self.crowd_animation) % len(crowd_chars)]
                    try:
                        self.stdscr.addstr(y, x, char)
                    except:
                        pass
                        
        self.stdscr.attroff(curses.color_pair(7))
        
        # Draw stadium border
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        
        # Top and bottom walls with decorations
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
        
        # Starting line
        mid_y = self.stadium_top + self.game_height // 2
        for x in range(self.stadium_left, self.stadium_right):
            if x % 2 == 0:
                self.stdscr.addstr(mid_y, x, '┊')
                
        # Finish areas
        finish_text = "START/FINISH"
        self.stdscr.addstr(mid_y - 1, (self.width - len(finish_text)) // 2, finish_text)
        
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
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
                except:
                    pass
        
        # Draw bike with direction sprite
        if self.stadium_top <= bike.y < self.stadium_bottom and self.stadium_left <= bike.x < self.stadium_right:
            self.stdscr.attron(curses.A_BOLD)
            try:
                self.stdscr.addstr(bike.y, bike.x, bike.get_sprite())
            except:
                pass
            self.stdscr.attroff(curses.A_BOLD)
            
        self.stdscr.attroff(curses.color_pair(bike.color))
        
    def check_collision(self, bike):
        # Check wall collision
        if (bike.y <= self.stadium_top - 1 or bike.y >= self.stadium_bottom or 
            bike.x <= self.stadium_left - 1 or bike.x >= self.stadium_right):
            return True
            
        # Check trail collision
        if (bike.y, bike.x) in self.player.trail:
            return True
        if (bike.y, bike.x) in self.ai.trail:
            return True
            
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
                
                # Score based on available space
                score = 0
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
        
        # Player status
        player_status = "ACTIVE" if self.player.alive else "CRASHED"
        ai_status = "ACTIVE" if self.ai.alive else "CRASHED"
        
        self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(score_y, 35, f"PLAYER: {player_status}")
        self.stdscr.attroff(curses.color_pair(1))
        
        self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(score_y, 55, f"CPU: {ai_status}")
        self.stdscr.attroff(curses.color_pair(2))
        
        # Controls
        self.stdscr.attron(curses.color_pair(4))
        self.stdscr.addstr(score_y + 1, 2, "CONTROLS: Arrow keys to move | R to restart | Q to quit | S for sound")
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
            "    ╔═╗╦═╗╔═╗╔╗╔╔═╗",
            "    ╠═╣╠╦╝║╣ ║║║╠═╣",
            "    ╩ ╩╩╚═╚═╝╝╚╝╩ ╩"
        ]
        
        # Draw title with glow effect
        start_y = 5
        colors = [5, 1, 2, 6]
        color_idx = int(time.time() * 2) % len(colors)
        
        self.stdscr.attron(curses.color_pair(colors[color_idx]) | curses.A_BOLD)
        for i, line in enumerate(title):
            x = (self.width - len(line)) // 2
            self.stdscr.addstr(start_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(colors[color_idx]) | curses.A_BOLD)
        
        # Draw stadium preview
        preview_y = start_y + len(title) + 3
        stadium_art = [
            "┌─────────────────────────────────────┐",
            "│ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ │",
            "│ ╔═══════════════════════════════╗ │",
            "│ ║  ▲ ═══════════════════▷      ║ │",
            "│ ║  ║                     ║      ║ │",
            "│ ║  ║      STADIUM        ║      ║ │",
            "│ ║  ║                     ║      ║ │",
            "│ ║  ◄═══════════════════ △      ║ │",
            "│ ╚═══════════════════════════════╝ │",
            "│ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ ☺ │",
            "└─────────────────────────────────────┘"
        ]
        
        self.stdscr.attron(curses.color_pair(3))
        for i, line in enumerate(stadium_art):
            if preview_y + i < self.height - 8:
                x = (self.width - len(line)) // 2
                self.stdscr.addstr(preview_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(3))
        
        # Menu options
        menu_y = preview_y + len(stadium_art) + 2
        self.stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
        menu_items = [
            "▸ Press SPACE to enter the arena",
            "▸ Press Q to quit",
            f"▸ Sound: {'ON' if self.sound_enabled else 'OFF'} (S to toggle)"
        ]
        for i, item in enumerate(menu_items):
            if menu_y + i < self.height - 2:
                x = (self.width - len(item)) // 2
                self.stdscr.addstr(menu_y + i, x, item)
        self.stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
        
        self.stdscr.refresh()
        
    def draw_game_over(self):
        if self.game_over and not hasattr(self, '_crash_played'):
            self.play_beep()
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
                except:
                    pass
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        self.stdscr.refresh()
    
    def run(self):
        # Set up curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)  # Faster refresh for smoother animation
        
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
                break
            elif key == ord('s') or key == ord('S'):
                self.sound_enabled = not self.sound_enabled
            elif self.show_menu:
                if key == ord(' '):
                    self.play_beep()
                    self.reset_game()
            elif key == ord('r') or key == ord('R'):
                self.reset_game()
                self.show_menu = True
            elif not self.game_over:
                if key == curses.KEY_UP:
                    self.player.turn(Direction.UP)
                elif key == curses.KEY_DOWN:
                    self.player.turn(Direction.DOWN)
                elif key == curses.KEY_LEFT:
                    self.player.turn(Direction.LEFT)
                elif key == curses.KEY_RIGHT:
                    self.player.turn(Direction.RIGHT)
                    
            # Game logic
            if not self.game_over and not self.show_menu:
                self.game_time += 1
                
                # AI decision
                self.ai_move()
                
                # Move bikes
                self.player.move()
                self.ai.move()
                
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
    import os
    import sys
    
    # Clear screen first
    os.system('clear' if os.name != 'nt' else 'cls')
    
    # Print instructions
    print("\033[1;36m" + "="*60 + "\033[0m")
    print("\033[1;33m         NEON CYCLE ARENA - LIGHT BIKE GAME\033[0m")
    print("\033[1;36m" + "="*60 + "\033[0m")
    print()
    print("\033[1;31mIMPORTANT: MAXIMIZE YOUR TERMINAL WINDOW NOW!\033[0m")
    print()
    print("\033[1;32mHow to maximize:\033[0m")
    print("  • \033[1;37mmacOS:\033[0m Press \033[1;33mCmd+Ctrl+F\033[0m or click the \033[1;32mgreen button\033[0m")
    print("  • \033[1;37mWindows:\033[0m Press \033[1;33mAlt+Enter\033[0m")
    print("  • \033[1;37mLinux:\033[0m Press \033[1;33mF11\033[0m")
    print()
    print("The game uses your \033[1;36mENTIRE TERMINAL SCREEN\033[0m for the best experience!")
    print()
    print("\033[1;33mPress ENTER when your terminal is maximized...\033[0m")
    input()
    
    # Run the game
    curses.wrapper(lambda stdscr: LightBikeStadium(stdscr).run())

if __name__ == "__main__":
    main()