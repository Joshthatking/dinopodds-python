"""Sound effects + audio settings. Loads every .wav in assets/SOUND/SFX/ by file name.

    game.sfx.play('bump', cooldown=0.3)

Missing files or no audio device are silently ignored, so the game runs
the same without them. Regenerate the stock effects with tools/make_sfx.py,
or drop in a replacement .wav with the same name.

The on/off toggles and 1-10 volume levels (i menu -> Options) are stored in
settings.json, separate from the save file, so they apply to every save.
"""
import json
import os
import pygame

SFX_DIR = os.path.join('assets', 'SOUND', 'SFX')
SETTINGS_PATH = 'settings.json'

# Loudest each one gets at volume 10; the 1-10 level scales down from here.
SFX_MAX_VOLUME = 0.6
MUSIC_MAX_VOLUME = 0.6

DEFAULT_SETTINGS = {
    'sfx_on': True,
    'sfx_level': 7,     # a bit under full by default
    'music_on': True,
    'music_level': 10,
}

# Per-effect volume tweaks on top of the SFX level
VOLUMES = {
    'bump': 0.9,
    'click': 0.7,
    'select': 0.6,
    'door': 0.9,
    'grass': 0.55,
    'dark_pulse': 0.6,   # loops the whole time you're in Cobaltion's room
    'portal_lunar': 1.0,  # repeats while you're near a celestial portal (scaled by distance)
    'portal_solar': 1.0,
}


class SFX:
    def __init__(self):
        self.sounds = {}
        self._last = {}
        self.settings = dict(DEFAULT_SETTINGS)
        self._load_settings()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            return
        if not os.path.isdir(SFX_DIR):
            return
        for fname in os.listdir(SFX_DIR):
            name, ext = os.path.splitext(fname)
            if ext.lower() not in ('.wav', '.ogg'):
                continue
            try:
                self.sounds[name] = pygame.mixer.Sound(os.path.join(SFX_DIR, fname))
            except pygame.error:
                continue
        self.apply_volumes()

    # ── settings ──────────────────────────────────────────────────────────

    def _load_settings(self):
        try:
            with open(SETTINGS_PATH) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        for k, default in DEFAULT_SETTINGS.items():
            v = data.get(k, default)
            if isinstance(default, bool):
                self.settings[k] = bool(v)
            else:
                self.settings[k] = max(1, min(10, int(v)))

    def save_settings(self):
        try:
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except OSError:
            pass

    def music_volume(self):
        """What pygame.mixer.music's volume should be right now."""
        s = self.settings
        return MUSIC_MAX_VOLUME * s['music_level'] / 10 if s['music_on'] else 0.0

    def apply_volumes(self):
        """Push the current settings to every loaded effect and to music."""
        level = SFX_MAX_VOLUME * self.settings['sfx_level'] / 10
        for name, snd in self.sounds.items():
            snd.set_volume(level * VOLUMES.get(name, 1.0))
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self.music_volume())

    # ── playback ──────────────────────────────────────────────────────────

    def play(self, name, cooldown=0.0, volume=None):
        """Play `name`; with a cooldown, skip it if it played less than
        that many seconds ago (e.g. bumping into a wall while holding a key).
        `volume` (0-1) scales just this playback, e.g. by distance."""
        if not self.settings['sfx_on']:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = pygame.time.get_ticks() / 1000.0
        if cooldown and now - self._last.get(name, -99) < cooldown:
            return
        self._last[name] = now
        channel = snd.play()
        if channel is not None and volume is not None:
            channel.set_volume(max(0.0, min(1.0, volume)))
