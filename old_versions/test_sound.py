#!/usr/bin/env python3
import pygame
import numpy as np
import sys

print("Testing pygame audio...")

try:
    # Initialize pygame mixer
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    print(f"Mixer initialized: {pygame.mixer.get_init()}")
    
    # Create a simple test tone
    sample_rate = 22050
    duration = 1.0
    frequency = 440  # A4 note
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit stereo
    wave = (wave * 32767).astype(np.int16)
    stereo_wave = np.zeros((len(wave), 2), dtype=np.int16)
    stereo_wave[:, 0] = wave
    stereo_wave[:, 1] = wave
    
    # Create and play sound
    sound = pygame.sndarray.make_sound(stereo_wave)
    print("Playing test tone (440Hz for 1 second)...")
    sound.play()
    
    # Wait for sound to finish
    pygame.time.wait(1000)
    
    print("Sound test completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nPossible solutions:")
    print("1. Make sure your audio is not muted")
    print("2. Check if other applications can play sound")
    print("3. Try running: brew install sdl2 sdl2_mixer")
    
pygame.quit()