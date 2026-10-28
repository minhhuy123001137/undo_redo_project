"""Procedural Sound Synthesizer for Time Shift.

Generates high-fidelity audio waves dynamically into pygame.mixer.Sound
objects with no external MP3/WAV dependencies.
"""
import io
import math
import struct
import wave
from typing import Dict, Optional
import pygame


class SoundManager:
    """Manages synthetic audio sound effects with dynamic volume controls."""

    def __init__(self, sfx_volume: float = 0.8) -> None:
        self.available: bool = False
        self.sfx_volume: float = max(0.0, min(1.0, sfx_volume))
        self.sounds: Dict[str, pygame.mixer.Sound] = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.available = True
            self._generate_all_sounds()
            self.set_volume(self.sfx_volume)
        except Exception:
            self.available = False

    def _create_wav_sound(self, generator_func) -> Optional[pygame.mixer.Sound]:
        """Synthesize PCM audio samples into a pygame.mixer.Sound."""
        sample_rate = 22050
        duration_samples, samples = generator_func(sample_rate)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
            wf.writeframes(raw_bytes)

        buf.seek(0)
        try:
            return pygame.mixer.Sound(buf)
        except Exception:
            return None

    def _generate_all_sounds(self) -> None:
        """Procedurally synthesize sound effects."""
        # 1. UI Click
        def gen_click(sr: int):
            duration = 0.035
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                freq = 1400 - (t / duration) * 800
                env = (1.0 - t / duration) ** 2
                val = int(env * math.sin(2 * math.pi * freq * t) * 16000)
                samples.append(val)
            return total, samples

        # 2. UI Hover
        def gen_hover(sr: int):
            duration = 0.02
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                env = (1.0 - t / duration)
                val = int(env * math.sin(2 * math.pi * 950 * t) * 6000)
                samples.append(val)
            return total, samples

        # 3. Player Step
        def gen_step(sr: int):
            duration = 0.045
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                freq = 240 - (t / duration) * 120
                env = (1.0 - t / duration) ** 1.5
                val = int(env * math.sin(2 * math.pi * freq * t) * 12000)
                samples.append(val)
            return total, samples

        # 4. Box Push
        def gen_push(sr: int):
            duration = 0.09
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                freq = 110 - (t / duration) * 40
                rumble = math.sin(2 * math.pi * freq * t) + 0.4 * math.sin(2 * math.pi * (freq * 2) * t)
                env = math.sin(math.pi * (t / duration))
                val = int(env * rumble * 14000)
                samples.append(val)
            return total, samples

        # 5. Goal Pad Activated
        def gen_goal(sr: int):
            duration = 0.22
            total = int(sr * duration)
            samples = []
            freqs = [440, 554, 659, 880]  # A major chord arpeggio
            for i in range(total):
                t = i / sr
                note_idx = min(len(freqs) - 1, int(t / (duration / len(freqs))))
                f = freqs[note_idx]
                env = (1.0 - (t / duration)) ** 1.2
                val = int(env * math.sin(2 * math.pi * f * t) * 18000)
                samples.append(val)
            return total, samples

        # 6. Rewind (Undo) - Descending sci-fi time reverse
        def gen_rewind(sr: int):
            duration = 0.16
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                freq = 880 - (t / duration) * 580
                vibrato = math.sin(2 * math.pi * 30 * t) * 30
                env = (1.0 - t / duration)
                val = int(env * math.sin(2 * math.pi * (freq + vibrato) * t) * 16000)
                samples.append(val)
            return total, samples

        # 7. Redo (Fast-Forward) - Ascending sci-fi time advance
        def gen_redo(sr: int):
            duration = 0.14
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                freq = 320 + (t / duration) * 540
                env = (1.0 - t / duration)
                val = int(env * math.sin(2 * math.pi * freq * t) * 16000)
                samples.append(val)
            return total, samples

        # 8. Wall Bump
        def gen_bump(sr: int):
            duration = 0.05
            total = int(sr * duration)
            samples = []
            for i in range(total):
                t = i / sr
                env = (1.0 - t / duration) ** 2
                val = int(env * math.sin(2 * math.pi * 90 * t) * 12000)
                samples.append(val)
            return total, samples

        # 9. Victory Fanfare
        def gen_victory(sr: int):
            duration = 0.45
            total = int(sr * duration)
            samples = []
            chords = [(523, 659), (587, 739), (659, 830), (784, 987)]  # Harmonized progression
            for i in range(total):
                t = i / sr
                idx = min(len(chords) - 1, int(t / (duration / len(chords))))
                f1, f2 = chords[idx]
                env = (1.0 - (t / duration)) ** 1.1
                tone = 0.6 * math.sin(2 * math.pi * f1 * t) + 0.4 * math.sin(2 * math.pi * f2 * t)
                val = int(env * tone * 18000)
                samples.append(val)
            return total, samples

        generators = {
            "click": gen_click,
            "hover": gen_hover,
            "step": gen_step,
            "push": gen_push,
            "goal": gen_goal,
            "rewind": gen_rewind,
            "redo": gen_redo,
            "bump": gen_bump,
            "victory": gen_victory,
        }

        for name, gen in generators.items():
            snd = self._create_wav_sound(gen)
            if snd:
                self.sounds[name] = snd

    def set_volume(self, volume: float) -> None:
        """Set master volume for all sound effects (0.0 to 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, volume))
        for snd in self.sounds.values():
            try:
                snd.set_volume(self.sfx_volume)
            except Exception:
                pass

    def play(self, name: str) -> None:
        """Play sound by name if audio is enabled."""
        if not self.available or self.sfx_volume <= 0.001:
            return
        snd = self.sounds.get(name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass


# Global singleton instance
_sound_instance: Optional[SoundManager] = None

def get_sound_manager() -> SoundManager:
    global _sound_instance
    if _sound_instance is None:
        _sound_instance = SoundManager()
    return _sound_instance
