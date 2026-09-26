#!/usr/bin/env python3
"""
Generate a realistic demo phone call audio file (WAV) for the sample note.
Uses pure Python standard library (wave, struct, math, random).
Generates gentle speech-like phone audio with natural pauses, realistic formant frequencies,
and soft ambiance, total duration 132.26 seconds (02:12.26).
"""

import os
import wave
import struct
import math
import random

def generate_call_audio(output_path, duration=132.26, sample_rate=22050):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    num_samples = int(duration * sample_rate)
    
    # Dialog segments: (start_s, end_s, base_pitch, person)
    # Tonio: base ~150Hz, Rigo: base ~110Hz
    segments = [
        (0.5, 2.5, 155, "tonio"),
        (3.2, 18.0, 115, "rigo"),
        (19.2, 32.2, 150, "tonio"),
        (33.5, 50.8, 112, "rigo"),
        (52.2, 61.8, 152, "tonio"),
        (63.2, 80.8, 114, "rigo"),
        (82.2, 86.2, 150, "tonio"),
        (87.2, 94.0, 115, "rigo"),
        (95.2, 98.0, 152, "tonio"),
        (99.2, 106.0, 115, "rigo"),
        (107.0, 114.26, 150, "tonio"),
        (116.0, 131.0, 112, "rigo"),
    ]
    
    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        chunk_size = 4096
        samples = []
        
        for i in range(num_samples):
            t = i / sample_rate
            
            # Check if within speech segment
            active_seg = None
            for seg in segments:
                if seg[0] <= t <= seg[1]:
                    active_seg = seg
                    break
            
            val = 0.0
            # Subtle background comfort noise / phone line warmth
            val += (random.random() - 0.5) * 0.008
            
            if active_seg:
                start_s, end_s, base_pitch, person = active_seg
                seg_t = t - start_s
                
                # Syllable modulation (approx 4-5 syllables per sec)
                syllable_mod = 0.5 + 0.5 * math.sin(2 * math.pi * 4.5 * seg_t)
                # Word pauses modulation
                word_mod = 0.7 + 0.3 * math.sin(2 * math.pi * 1.8 * seg_t)
                
                # Formant synthesis: fundamental + harmonics
                f0 = base_pitch + 8.0 * math.sin(2 * math.pi * 1.5 * seg_t)
                # Formants: F1 ~ 500Hz, F2 ~ 1500Hz, F3 ~ 2500Hz
                v_f0 = math.sin(2 * math.pi * f0 * t)
                v_f1 = 0.6 * math.sin(2 * math.pi * (f0 * 3) * t)
                v_f2 = 0.35 * math.sin(2 * math.pi * (f0 * 7) * t)
                v_f3 = 0.15 * math.sin(2 * math.pi * (f0 * 12) * t)
                
                voice = (v_f0 + v_f1 + v_f2 + v_f3) * syllable_mod * word_mod
                
                # Envelope at edges
                fade = min(1.0, seg_t / 0.15, (end_s - t) / 0.15)
                val += voice * 0.38 * max(0.0, fade)
                
            sample_int = int(max(-32767, min(32767, val * 32767)))
            samples.append(struct.pack('<h', sample_int))
            
            if len(samples) >= chunk_size:
                wav_file.writeframes(b''.join(samples))
                samples = []
                
        if samples:
            wav_file.writeframes(b''.join(samples))
            
    print(f"Generated sample audio: {output_path} ({duration}s)")

if __name__ == "__main__":
    generate_call_audio("/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/sample_audio_call.wav")
