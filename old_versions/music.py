import pygame
import numpy as np

def create_synth_music():
    """Create retro-style synth music for the game"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    sample_rate = 22050
    duration = 2.0  # 2 second loop
    
    # Create a retro synth pattern
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Base frequency pattern (arpeggio)
    base_freq = 110  # A2
    frequencies = [base_freq, base_freq * 1.25, base_freq * 1.5, base_freq * 2]
    
    # Generate the wave
    wave = np.zeros_like(t)
    for i, freq in enumerate(frequencies):
        start = int(i * len(t) / 4)
        end = int((i + 1) * len(t) / 4)
        wave[start:end] = 0.3 * np.sin(2 * np.pi * freq * t[start:end])
        
    # Add some harmonics for richness
    wave += 0.1 * np.sin(4 * np.pi * base_freq * t)
    wave += 0.05 * np.sin(8 * np.pi * base_freq * t)
    
    # Convert to 16-bit integer format
    wave = (wave * 32767).astype(np.int16)
    
    # Make stereo
    stereo_wave = np.zeros((len(wave), 2), dtype=np.int16)
    stereo_wave[:, 0] = wave
    stereo_wave[:, 1] = wave
    
    return pygame.sndarray.make_sound(stereo_wave)

def create_crash_sound():
    """Create a crash/explosion sound effect"""
    sample_rate = 22050
    duration = 0.3
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # White noise burst that fades out
    noise = np.random.normal(0, 0.3, len(t))
    envelope = np.exp(-10 * t)  # Exponential decay
    wave = noise * envelope
    
    # Add low frequency rumble
    wave += 0.2 * envelope * np.sin(2 * np.pi * 50 * t)
    
    # Convert to 16-bit
    wave = (wave * 32767).astype(np.int16)
    
    # Make stereo
    stereo_wave = np.zeros((len(wave), 2), dtype=np.int16)
    stereo_wave[:, 0] = wave
    stereo_wave[:, 1] = wave
    
    return pygame.sndarray.make_sound(stereo_wave)