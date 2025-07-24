import subprocess
import threading
import os

class SoundManager:
    def __init__(self):
        self.music_process = None
        self.sound_enabled = True
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
    def play_background_music(self):
        """Play background music in a loop using afplay"""
        if not self.sound_enabled:
            return
            
        def music_loop():
            while self.sound_enabled:
                try:
                    music_path = os.path.join(self.base_path, 'background_music.wav')
                    if os.path.exists(music_path):
                        subprocess.run(['afplay', music_path], capture_output=True)
                except:
                    break
        
        if self.music_process is None or not self.music_process.is_alive():
            self.music_process = threading.Thread(target=music_loop, daemon=True)
            self.music_process.start()
    
    def play_sound_effect(self, sound_file):
        """Play a sound effect using afplay"""
        if not self.sound_enabled:
            return
            
        def play():
            try:
                sound_path = os.path.join(self.base_path, sound_file)
                if os.path.exists(sound_path):
                    subprocess.run(['afplay', sound_path], capture_output=True)
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
        # Kill any running afplay processes
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