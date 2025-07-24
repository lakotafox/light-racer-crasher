#!/usr/bin/env python3
import numpy as np
import wave
import struct

def create_wav_file(filename, audio_data, sample_rate=44100):
    """Create a WAV file from audio data"""
    with wave.open(filename, 'wb') as wav_file:
        # Set parameters
        nchannels = 1  # Mono
        sampwidth = 2  # 2 bytes per sample (16-bit)
        framerate = sample_rate
        nframes = len(audio_data)
        
        wav_file.setparams((nchannels, sampwidth, framerate, nframes, 'NONE', 'NONE'))
        
        # Convert float audio to 16-bit integers
        audio_int16 = (audio_data * 32767).astype(np.int16)
        wav_file.writeframes(audio_int16.tobytes())

def generate_background_music():
    """Generate retro-style background music"""
    sample_rate = 44100
    duration = 4.0  # 4 second loop
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a retro arpeggio pattern
    notes = [110, 138.59, 164.81, 220]  # A2, C#3, E3, A3
    audio = np.zeros_like(t)
    
    # Each note plays for 1 second
    for i, freq in enumerate(notes):
        start = int(i * len(t) / 4)
        end = int((i + 1) * len(t) / 4)
        
        # Square wave with some harmonics for retro sound
        audio[start:end] = 0.3 * np.sign(np.sin(2 * np.pi * freq * t[start:end]))
        audio[start:end] += 0.1 * np.sin(4 * np.pi * freq * t[start:end])
        
    # Add a subtle envelope
    envelope = np.ones_like(audio)
    fade_samples = int(0.05 * sample_rate)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    
    audio = audio * envelope
    
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.5
    
    create_wav_file('background_music.wav', audio, sample_rate)
    print("Created background_music.wav")

def generate_crash_sound():
    """Generate crash/explosion sound effect"""
    sample_rate = 44100
    duration = 0.5
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # White noise burst
    noise = np.random.normal(0, 0.3, len(t))
    
    # Exponential decay envelope
    envelope = np.exp(-8 * t)
    
    # Low frequency rumble
    rumble = 0.4 * np.sin(2 * np.pi * 60 * t)
    
    # Combine
    audio = (noise + rumble) * envelope
    
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.7
    
    create_wav_file('crash.wav', audio, sample_rate)
    print("Created crash.wav")

def generate_menu_select():
    """Generate menu selection sound"""
    sample_rate = 44100
    duration = 0.1
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Quick ascending tone
    freq_start = 400
    freq_end = 800
    freq = np.linspace(freq_start, freq_end, len(t))
    
    audio = 0.3 * np.sin(2 * np.pi * freq * t)
    
    # Quick envelope
    envelope = np.ones_like(audio)
    fade = int(0.01 * sample_rate)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    
    audio = audio * envelope
    
    create_wav_file('menu_select.wav', audio, sample_rate)
    print("Created menu_select.wav")

if __name__ == "__main__":
    print("Generating sound files...")
    generate_background_music()
    generate_crash_sound()
    generate_menu_select()
    print("\nAll sound files generated successfully!")