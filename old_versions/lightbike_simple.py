#!/usr/bin/env python3
import curses
import time
import random
import os
import subprocess
import threading
from collections import deque
from enum import Enum

class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

class Bike:
    def __init__(self, y, x, direction, color, trail_char='#'):
        self.y = y
        self.x = x
        self.direction = direction
        self.color = color
        self.trail_char = trail_char
        self.trail = deque(maxlen=1000)
        self.alive = True
        
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

class LightBikeGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.game_height = self.height - 4
        self.game_width = self.width - 2
        self.show_menu = True
        self.sound_enabled = True
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Player
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # AI
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Walls
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # UI
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Title
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Menu
        
        self.reset_game()
        
    def play_beep(self, frequency=440, duration=0.1):
        """Play a beep sound using system command"""
        if not self.sound_enabled:
            return
        try:
            # Use printf and play command on macOS
            cmd = f"printf '\\a'"
            subprocess.run(cmd, shell=True, capture_output=True)
        except:
            pass
            
    def reset_game(self):
        # Initialize bikes
        player_y = self.game_height // 2
        player_x = self.game_width // 4
        ai_y = self.game_height // 2
        ai_x = 3 * self.game_width // 4
        
        self.player = Bike(player_y, player_x, Direction.RIGHT, 1, '█')
        self.ai = Bike(ai_y, ai_x, Direction.LEFT, 2, '█')
        
        self.score = 0
        self.game_over = False
        self.winner = None
        self.show_menu = False
        if hasattr(self, '_crash_played'):
            delattr(self, '_crash_played')
        
    def draw_border(self):
        # Draw game border
        self.stdscr.attron(curses.color_pair(3))
        for x in range(self.game_width + 1):
            self.stdscr.addstr(0, x, '═')
            self.stdscr.addstr(self.game_height, x, '═')
        for y in range(self.game_height + 1):
            self.stdscr.addstr(y, 0, '║')
            self.stdscr.addstr(y, self.game_width, '║')
        # Corners
        self.stdscr.addstr(0, 0, '╔')
        self.stdscr.addstr(0, self.game_width, '╗')
        self.stdscr.addstr(self.game_height, 0, '╚')
        self.stdscr.addstr(self.game_height, self.game_width, '╝')
        self.stdscr.attroff(curses.color_pair(3))
        
    def draw_bike(self, bike):
        if not bike.alive:
            return
            
        # Draw trail
        self.stdscr.attron(curses.color_pair(bike.color))
        for y, x in bike.trail:
            if 0 < y < self.game_height and 0 < x < self.game_width:
                self.stdscr.addstr(y, x, bike.trail_char)
        
        # Draw bike head
        if 0 < bike.y < self.game_height and 0 < bike.x < self.game_width:
            self.stdscr.addstr(bike.y, bike.x, '●')
        self.stdscr.attroff(curses.color_pair(bike.color))
        
    def check_collision(self, bike):
        # Check wall collision
        if bike.y <= 0 or bike.y >= self.game_height or bike.x <= 0 or bike.x >= self.game_width:
            return True
            
        # Check trail collision (both own and opponent's)
        if (bike.y, bike.x) in self.player.trail:
            return True
        if (bike.y, bike.x) in self.ai.trail:
            return True
            
        return False
        
    def ai_move(self):
        # Simple AI that tries to avoid walls and trails
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
            
        # Calculate safe moves
        safe_moves = []
        for direction in directions:
            dy, dx = direction.value
            new_y = self.ai.y + dy
            new_x = self.ai.x + dx
            
            # Check if move is safe
            if (0 < new_y < self.game_height and 0 < new_x < self.game_width and
                (new_y, new_x) not in self.player.trail and
                (new_y, new_x) not in self.ai.trail):
                safe_moves.append(direction)
                
        # Choose move
        if safe_moves:
            # Prefer to continue straight if safe
            if self.ai.direction in safe_moves and random.random() > 0.3:
                return
            # Otherwise pick a random safe move
            self.ai.turn(random.choice(safe_moves))
        
    def draw_ui(self):
        # Draw score and instructions
        self.stdscr.attron(curses.color_pair(4))
        self.stdscr.addstr(self.game_height + 1, 2, f"Score: {self.score}")
        self.stdscr.addstr(self.game_height + 2, 2, "Use arrow keys to move | Q to quit | R to restart | S to toggle sound")
        sound_status = "ON" if self.sound_enabled else "OFF"
        self.stdscr.addstr(self.game_height + 1, self.game_width - 15, f"Sound: {sound_status}")
        self.stdscr.attroff(curses.color_pair(4))
        
    def draw_title_screen(self):
        if not self.show_menu:
            return
            
        self.stdscr.clear()
        
        # ASCII art title - LIGHT CYCLES
        title = [
            "██╗     ██╗ ██████╗ ██╗  ██╗████████╗",
            "██║     ██║██╔════╝ ██║  ██║╚══██╔══╝",
            "██║     ██║██║  ███╗████████║   ██║   ",
            "██║     ██║██║   ██║██╔══██║   ██║   ",
            "███████╗██║╚██████╔╝██║  ██║   ██║   ",
            "╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ",
            "",
            " ██████╗██╗   ██╗ ██████╗██╗     ███████╗███████╗",
            "██╔════╝╚██╗ ██╔╝██╔════╝██║     ██╔════╝██╔════╝",
            "██║      ╚████╔╝ ██║     ██║     █████╗  ███████╗",
            "██║       ╚██╔╝  ██║     ██║     ██╔══╝  ╚════██║",
            "╚██████╗   ██║   ╚██████╗███████╗███████╗███████║",
            " ╚═════╝   ╚═╝    ╚═════╝╚══════╝╚══════╝╚══════╝"
        ]
        
        # Center and draw title
        start_y = max(2, self.height // 4 - len(title) // 2)
        self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
        for i, line in enumerate(title):
            if start_y + i < self.height - 10:
                x = max(0, (self.width - len(line)) // 2)
                self.stdscr.addstr(start_y + i, x, line)
        self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
        
        # Draw animated light cycles
        frame = int(time.time() * 2) % 2
        
        if frame == 0:
            bike_art = [
                "     ╔═══╗      ",
                "     ║▓▓▓║      ",
                "╔════╬═══╬════╗ ",
                "║░░░░║   ║░░░░║ ",
                "╚════╝   ╚════╝ ",
                "═══════════════>"
            ]
        else:
            bike_art = [
                "      ╔═══╗     ",
                "      ║▓▓▓║     ",
                " ╔════╬═══╬════╗",
                " ║░░░░║   ║░░░░║",
                " ╚════╝   ╚════╝",
                "<═══════════════"
            ]
        
        bike_y = start_y + len(title) + 3
        if bike_y + len(bike_art) < self.height - 6:
            self.stdscr.attron(curses.color_pair(1))
            for i, line in enumerate(bike_art):
                x = max(0, (self.width - len(line)) // 2)
                self.stdscr.addstr(bike_y + i, x, line)
            self.stdscr.attroff(curses.color_pair(1))
        
        # Menu options
        menu_y = min(bike_y + len(bike_art) + 3, self.height - 4)
        self.stdscr.attron(curses.color_pair(6))
        menu_items = [
            "Press SPACE to start",
            "Press Q to quit",
            f"Sound: {'ON' if self.sound_enabled else 'OFF'} (press S to toggle)"
        ]
        for i, item in enumerate(menu_items):
            if menu_y + i < self.height - 1:
                x = max(0, (self.width - len(item)) // 2)
                self.stdscr.addstr(menu_y + i, x, item)
        self.stdscr.attroff(curses.color_pair(6))
        
        # Credits
        credit = "Light Bike - Terminal Edition"
        if self.height > 2:
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(self.height - 2, max(0, (self.width - len(credit)) // 2), credit)
            self.stdscr.attroff(curses.color_pair(3))
        
        self.stdscr.refresh()
    
    def draw_game_over(self):
        if self.game_over and not hasattr(self, '_crash_played'):
            # Play crash sound only once
            self.play_beep()
            self._crash_played = True
        
        if self.game_over:
            msg = f"GAME OVER! {self.winner} wins!" if self.winner else "GAME OVER! It's a tie!"
            y = self.game_height // 2
            x = max(0, (self.game_width - len(msg)) // 2)
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(y, x, msg)
            self.stdscr.addstr(y + 2, max(0, x), "Press R to restart or Q to quit")
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
    def run(self):
        # Set up curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(100)
        
        while True:
            if self.show_menu:
                self.draw_title_screen()
            else:
                self.stdscr.clear()
                
                # Draw game elements
                self.draw_border()
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
                    self.winner = "AI"
                elif ai_crashed:
                    self.game_over = True
                    self.winner = "Player"
                    self.score += 100
                else:
                    self.score += 1

def main():
    curses.wrapper(lambda stdscr: LightBikeGame(stdscr).run())

if __name__ == "__main__":
    main()