# audio.py
"""Короткие звуковые эффекты поверх фоновой музыки."""
import os

import pygame

import settings


class SoundBank:
    """Хранит загруженные SFX и проигрывает их по ключу.

    Если аудиоустройство недоступно или файл не найден, игра просто
    работает без звука — без падений.
    """

    def __init__(self):
        self.sounds = {}
        self.volume = settings.SFX_VOLUME
        if not pygame.mixer.get_init():
            print("[ПРЕДУПРЕЖДЕНИЕ] Микшер не инициализирован — звуки отключены")
            return

        for key, path in settings.SOUNDS.items():
            if not os.path.exists(path):
                print(f"[ПРЕДУПРЕЖДЕНИЕ] Звук не найден: {path}")
                continue
            try:
                sound = pygame.mixer.Sound(path)
            except pygame.error as exc:
                print(f"[ОШИБКА] Звук не загружен ({path}): {exc}")
                continue
            sound.set_volume(self.volume)
            self.sounds[key] = sound
        print(f"[УСПЕХ] Звуки: {len(self.sounds)}/{len(settings.SOUNDS)}")

    def play(self, key):
        sound = self.sounds.get(key)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.volume)
