"""Generates looping music into assets/SOUND/, synthesized in code
(same idea as tools/make_sfx.py — no outside audio).

    python tools/make_music.py              # every track
    python tools/make_music.py battle boss  # just those

  route1        calm, happy flute tune over harp arpeggios (C major)
  silverleaf    music-box -> ocarina waltz lullaby for home (G major, 3/4)
  route3        slow, dreamy ocarina over pads and glass bells (D major)
  battle        upbeat GBA pulse-wave battle theme (A minor, 150 BPM)
  boss2         bigger, faster battle theme (D minor) — boss.wav itself is hand-made
  spacial       eerie: drone, detuned ghostly lead, heartbeat, far-off bells
                (the planets + Horizon Cave)
  route4        bright: flute over shimmering bell cascades (E major)
  corn_maze     eerie, slow sub-bass beat, ghostly detuned lead (E phrygian, 72 BPM)
  route2        relaxed, quiet lo-fi: electric piano, brushes, ocarina (F major)
  palmport      melodic + crystalline: flute over harp/bell arpeggios, drips (B minor)
  cobalt_cave   ominous but chill: half-time sub-bass groove, dark pad, low e-piano (D minor)

Every track is rendered circularly (anything that rings past the end wraps
back onto the start), so it loops seamlessly with mixer.music.play(-1).
"""
import os
import wave
import numpy as np

RATE = 22050
OUT_DIR = os.path.join('assets', 'SOUND')


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ── instruments ──────────────────────────────────────────────────────────

def flute(freq, dur, rng):
    """Soft flute: mostly-sine tone with a touch of 2nd/3rd harmonic, a
    breathy attack, vibrato that blooms on held notes, gentle release."""
    tail = 0.18
    n = int(RATE * (dur + tail))
    t = np.arange(n) / RATE
    vib_depth = 0.005 * np.clip((t - 0.22) / 0.3, 0, 1)
    f = freq * (1 + vib_depth * np.sin(2 * np.pi * 5.2 * t))
    phase = 2 * np.pi * np.cumsum(f) / RATE
    tone = np.sin(phase) + 0.22 * np.sin(2 * phase) + 0.07 * np.sin(3 * phase)
    # breath: filtered noise, strongest in the attack
    breath = rng.standard_normal(n)
    for _ in range(3):
        breath = np.convolve(breath, np.ones(6) / 6, mode='same')
    breath *= 0.35 * (0.25 + 0.75 * np.exp(-t / 0.08))
    env = np.ones(n)
    a = int(RATE * 0.06)
    env[:a] = np.linspace(0, 1, a) ** 1.5
    r0 = int(RATE * dur)
    env[r0:] = np.linspace(1, 0, n - r0) ** 2
    swell = 1 + 0.08 * np.sin(np.pi * np.clip(t / max(dur, 0.01), 0, 1))   # notes lean in a little
    return (tone + breath) * env * swell


def harp(freq, dur=1.6):
    """Plucked, harp-ish: triangle + sine with a soft exponential decay."""
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    phase = 2 * np.pi * freq * t
    tri = 2 / np.pi * np.arcsin(np.sin(phase))
    x = 0.6 * np.sin(phase) + 0.4 * tri + 0.15 * np.sin(2 * phase) * np.exp(-t / 0.15)
    a = int(RATE * 0.004)
    env = np.exp(-t / 0.55)
    env[:a] *= np.linspace(0, 1, a)
    return x * env


def bass(freq, dur):
    n = int(RATE * (dur + 0.1))
    t = np.arange(n) / RATE
    x = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)
    env = np.exp(-t / 0.9) * np.clip(t / 0.01, 0, 1)
    env[int(RATE * dur):] *= np.linspace(1, 0, n - int(RATE * dur))
    return x * env


def add_wrapped(buf, x, at):
    """Mix x into buf at sample `at`, wrapping past the end back to the start."""
    idx = (np.arange(len(x)) + at) % len(buf)
    np.add.at(buf, idx, x)


# ── the tune ─────────────────────────────────────────────────────────────

BPM = 84
BEAT = 60 / BPM
# C4 = 60. Each bar is 4 beats: (note or None for a rest, beats)
MELODY = [
    [(67, 1), (72, 1), (76, 1.5), (74, 0.5)],              # C   — a little rise
    [(72, 1), (69, 1), (76, 2)],                           # Am
    [(77, 1), (76, 0.5), (74, 0.5), (72, 1), (69, 1)],     # F   — skipping down
    [(71, 1), (72, 0.5), (74, 0.5), (67, 2)],              # G   — the question
    [(67, 1), (72, 1), (76, 1.5), (79, 0.5)],              # C   — rise again, higher
    [(81, 1.5), (79, 0.5), (76, 2)],                       # Am
    [(77, 1), (76, 0.5), (74, 0.5), (74, 1), (71, 1)],     # F / G
    [(72, 3), (None, 1)],                                  # C   — home
]
# chords per bar: (root midi, quality, beats); quality 'maj' / 'min'
CHORDS = [
    [(48, 'maj', 4)], [(45, 'min', 4)], [(41, 'maj', 4)], [(43, 'maj', 4)],
    [(48, 'maj', 4)], [(45, 'min', 4)], [(41, 'maj', 2), (43, 'maj', 2)], [(48, 'maj', 4)],
]
ARP = [0, 7, 12, 16, 19, 16, 12, 7]   # semitones above the root, one per eighth note


def make_route1():
    rng = np.random.default_rng(1)
    bars = len(MELODY)
    n = int(RATE * BEAT * 4 * bars)
    lead, harps, low = np.zeros(n), np.zeros(n), np.zeros(n)

    for b, bar in enumerate(MELODY):
        beat = b * 4.0
        for note, beats in bar:
            if note is not None:
                add_wrapped(lead, flute(midi_hz(note), beats * BEAT * 0.97, rng), int(RATE * beat * BEAT))
            beat += beats

    for b, bar in enumerate(CHORDS):
        beat = b * 4.0
        for root, quality, beats in bar:
            third = 3 if quality == 'min' else 4
            steps = [s - 4 + third if s % 12 == 4 else s for s in ARP]   # minor: flatten the 3rds
            for i in range(int(beats * 2)):
                f = midi_hz(root + 12 + steps[i % len(steps)])
                vel = 0.9 if i % 2 == 0 else 0.65
                add_wrapped(harps, harp(f) * vel, int(RATE * (beat + i * 0.5) * BEAT))
            for k in range(0, int(beats), 2):   # bass on beats 1 and 3
                add_wrapped(low, bass(midi_hz(root - 12 if root > 45 else root), 2 * BEAT),
                            int(RATE * (beat + k) * BEAT))
            beat += beats

    mix = 0.55 * lead + 0.16 * harps + 0.28 * low
    # light echo for space (wrapped too, so the loop point stays seamless)
    wet = np.zeros(n)
    for delay, gain in ((0.21, 0.22), (0.37, 0.14), (0.61, 0.08)):
        wet += np.roll(mix, int(RATE * delay)) * gain
    mix = mix + wet
    # gentle low-pass to round off the top end
    mix = np.convolve(np.concatenate([mix[-2:], mix]), np.ones(3) / 3, mode='valid')
    save('route1', mix, peak=0.7)


# ══════════════════════════════════════════════════════════════════════
# More instruments + a small track builder for the other areas.
# (Route 1 above is left exactly as it was written.)
# ══════════════════════════════════════════════════════════════════════

def _t(n):
    return np.arange(n) / RATE


def _adsr(n, attack, release_at, release, decay_to=1.0, decay=0.0):
    """Attack ramp, optional decay toward `decay_to`, then a release ramp."""
    env = np.ones(n)
    a = max(1, int(RATE * attack))
    env[:a] = np.linspace(0, 1, a)
    if decay > 0:
        t = _t(n - a)
        env[a:] = decay_to + (1 - decay_to) * np.exp(-t / decay)
    r0 = min(n, int(RATE * release_at))
    if r0 < n:
        env[r0:] *= np.linspace(1, 0, n - r0) ** 1.5
    return env


def music_box(freq, dur=None):
    """Music-box tine: bright inharmonic partials, quick pluck, long ring."""
    n = int(RATE * 2.2)
    t = _t(n)
    x = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.9)
         + 0.35 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t / 0.18)
         + 0.15 * np.sin(2 * np.pi * freq * 5.43 * t) * np.exp(-t / 0.06))
    x[:int(RATE * 0.002)] *= np.linspace(0, 1, int(RATE * 0.002))
    return x


def ocarina(freq, dur, rng, vib=0.006, detune=0.0):
    """Ocarina: near-pure sine, soft breath, gentle vibrato. `detune` (in
    semitone fractions) adds a second, slightly-off voice for an eerie chorus."""
    tail = 0.25
    n = int(RATE * (dur + tail))
    t = _t(n)
    depth = vib * np.clip((t - 0.25) / 0.35, 0, 1)
    f = freq * (1 + depth * np.sin(2 * np.pi * 4.8 * t))
    ph = 2 * np.pi * np.cumsum(f) / RATE
    x = np.sin(ph) + 0.08 * np.sin(2 * ph)
    if detune:
        ph2 = 2 * np.pi * np.cumsum(f * 2 ** (detune / 12)) / RATE
        x = 0.6 * x + 0.6 * np.sin(ph2)
    breath = rng.standard_normal(n)
    for _ in range(4):
        breath = np.convolve(breath, np.ones(8) / 8, mode='same')
    x += breath * 0.25 * np.exp(-t / 0.1)
    return x * _adsr(n, 0.09, dur, tail)


def pulse(freq, dur, duty=0.5, vib=0.0, staccato=1.0):
    """GBA pulse channel: square wave with a soft edge and a short envelope."""
    play = dur * staccato
    n = int(RATE * (play + 0.04))
    t = _t(n)
    f = freq * (1 + vib * np.clip((t - 0.15) / 0.2, 0, 1) * np.sin(2 * np.pi * 6 * t))
    ph = np.cumsum(f) / RATE % 1.0
    x = np.where(ph < duty, 1.0, -1.0) - (2 * duty - 1)      # centred: narrow pulses aren't zero-mean
    x = np.convolve(x, np.ones(4) / 4, mode='same')          # take the fizz off
    return x * _adsr(n, 0.005, play, 0.04, decay_to=0.7, decay=0.25)


def tri_bass(freq, dur, staccato=0.85):
    """GBA wave-channel bass: triangle, plucky."""
    play = dur * staccato
    n = int(RATE * (play + 0.03))
    ph = freq * _t(n) % 1.0
    x = 2 * np.abs(2 * ph - 1) - 1
    return x * _adsr(n, 0.004, play, 0.03, decay_to=0.75, decay=0.2)


def pad(freqs, dur, attack=0.6, bright=0.3):
    """Soft sustained chord: a few detuned sines per note, slow swell."""
    n = int(RATE * (dur + 0.6))
    t = _t(n)
    x = np.zeros(n)
    for f in freqs:
        for d in (-0.003, 0.0, 0.003):
            x += np.sin(2 * np.pi * f * (1 + d) * t) + bright * np.sin(4 * np.pi * f * (1 + d) * t) * 0.5
    x /= max(1, len(freqs) * 3)
    return x * _adsr(n, attack, dur, 0.6)


def glass_bell(freq, dur=None, decay=1.6):
    n = int(RATE * (decay * 2.5))
    t = _t(n)
    x = np.zeros(n)
    for mult, amp in ((1.0, 1.0), (2.0, 0.45), (3.0, 0.2), (4.2, 0.12)):
        x += np.sin(2 * np.pi * freq * mult * t) * amp * np.exp(-t * mult ** 0.6 / decay)
    x[:int(RATE * 0.003)] *= np.linspace(0, 1, int(RATE * 0.003))
    return x


def kick():
    n = int(RATE * 0.18)
    t = _t(n)
    f = 45 + 110 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t / 0.07)


def snare(rng):
    n = int(RATE * 0.16)
    t = _t(n)
    noise = rng.uniform(-1, 1, n)
    noise -= np.convolve(noise, np.ones(5) / 5, mode='same')   # brighten
    return (noise * 0.9 + 0.5 * np.sin(2 * np.pi * 185 * t)) * np.exp(-t / 0.05)


def hat(rng, length=0.04):
    n = int(RATE * length)
    noise = rng.uniform(-1, 1, n)
    noise -= np.convolve(noise, np.ones(3) / 3, mode='same')
    return noise * np.exp(-_t(n) / (length / 3))


def crash(rng):
    n = int(RATE * 1.2)
    noise = rng.uniform(-1, 1, n)
    noise -= np.convolve(noise, np.ones(3) / 3, mode='same')
    return noise * np.exp(-_t(n) / 0.35)


def thump():
    """Low heartbeat thud for the lunar track."""
    n = int(RATE * 0.35)
    t = _t(n)
    return np.sin(2 * np.pi * np.cumsum(38 + 30 * np.exp(-t / 0.05)) / RATE) * np.exp(-t / 0.12)


QUALITY = {'maj': (0, 4, 7), 'min': (0, 3, 7), 'dim': (0, 3, 6), 'sus': (0, 5, 7),
           'maj7': (0, 4, 7, 11), 'min7': (0, 3, 7, 10), 'add9': (0, 4, 7, 14)}


class Track:
    """A loop of `bars` bars. Everything is mixed in circularly so the end
    rings over into the start and the loop is seamless."""

    def __init__(self, bpm, bars, beats_per_bar=4, seed=0):
        self.beat = 60 / bpm
        self.bpb = beats_per_bar
        self.n = int(RATE * self.beat * beats_per_bar * bars)
        self.mix = np.zeros(self.n)
        self.rng = np.random.default_rng(seed)

    def at(self, beat):
        return int(RATE * beat * self.beat)

    def add(self, x, beat, gain=1.0):
        add_wrapped(self.mix, x * gain, self.at(beat))

    def melody(self, bars, inst, gain, transpose=0, start_bar=0, **kw):
        """bars: [[(midi or None, beats), ...], ...] — one list per bar."""
        for b, bar in enumerate(bars):
            beat = (start_bar + b) * self.bpb
            for note, beats in bar:
                if note is not None:
                    self.add(inst(midi_hz(note + transpose), beats * self.beat, **kw), beat, gain)
                beat += beats

    def chords(self, prog):
        """[(root, quality, beats), ...] -> [(start_beat, root, intervals, beats)]"""
        out, beat = [], 0.0
        for root, quality, beats in prog:
            out.append((beat, root, QUALITY[quality], beats))
            beat += beats
        return out

    def echo(self, taps):
        wet = np.zeros(self.n)
        for delay, g in taps:
            wet += np.roll(self.mix, int(RATE * delay)) * g
        self.mix += wet

    def lowpass(self, width=3):
        m = self.mix
        self.mix = np.convolve(np.concatenate([m[-(width - 1):], m]), np.ones(width) / width, mode='valid')


# ── Silverleaf Town: a music-box / ocarina waltz lullaby (G major, 3/4) ──

def make_silverleaf():
    tr = Track(bpm=96, bars=16, beats_per_bar=3, seed=2)
    tune = [
        [(71, 1), (74, 1), (79, 1)],            # G
        [(78, 1.5), (76, 0.5), (74, 1)],        # Em
        [(76, 2), (74, 0.5), (72, 0.5)],        # C
        [(74, 2), (69, 1)],                     # D
        [(71, 1), (74, 1), (79, 1)],            # G
        [(79, 1.5), (81, 0.5), (83, 1)],        # Em
        [(81, 1), (76, 1), (78, 1)],            # Am / D
        [(79, 3)],                              # G
    ]
    prog = [(55, 'maj', 3), (52, 'min', 3), (48, 'maj', 3), (50, 'maj', 3),
            (55, 'maj', 3), (52, 'min', 3), (45, 'min', 2), (50, 'maj', 1), (55, 'maj', 3)] * 2
    # first time: music box alone; second time: ocarina sings it, music box answers
    tr.melody(tune, music_box, 0.55, transpose=12)
    tr.melody(tune, ocarina, 0.5, start_bar=8, rng=tr.rng)
    for start, root, iv, beats in tr.chords(prog):
        tr.add(bass(midi_hz(root - 12), 1.2 * tr.beat), start, 0.32)          # oom
        for k in range(1, int(beats)):                                       # pah-pah
            for i in iv:
                tr.add(harp(midi_hz(root + 12 + i), 0.9), start + k, 0.07)
        if start >= 24:   # second half: music-box sparkles on the chord's top note
            tr.add(music_box(midi_hz(root + 24 + iv[-1])), start + 0.5, 0.18)
    tr.echo(((0.25, 0.2), (0.45, 0.12), (0.8, 0.06)))
    tr.lowpass()
    save('silverleaf', tr.mix, peak=0.65)


# ── Route 3 (first written for Lake Meridian): slow and dreamy (D major, a lydian lift) ──

def make_lake():
    tr = Track(bpm=66, bars=8, seed=3)
    tune = [
        [(81, 3), (78, 1)],                     # D
        [(76, 2), (74, 1), (78, 1)],            # Bm
        [(83, 3), (81, 0.5), (80, 0.5)],        # G — the G# is the lydian shimmer
        [(81, 4)],                              # A
        [(81, 2), (86, 1), (85, 1)],            # D
        [(81, 2), (78, 2)],                     # F#m
        [(79, 1), (83, 1), (86, 1.5), (85, 0.5)],   # G
        [(81, 3), (None, 1)],                   # Asus
    ]
    prog = [(50, 'add9', 4), (47, 'min7', 4), (43, 'maj7', 4), (45, 'sus', 4),
            (50, 'add9', 4), (42, 'min', 4), (43, 'maj7', 4), (45, 'sus', 4)]
    tr.melody(tune, ocarina, 0.42, rng=tr.rng, vib=0.008)
    for start, root, iv, beats in tr.chords(prog):
        tr.add(pad([midi_hz(root + 12 + i) for i in iv], beats * tr.beat, attack=1.2, bright=0.15), start, 0.5)
        tr.add(bass(midi_hz(root - 12 if root > 45 else root), beats * tr.beat), start, 0.22)
        # glass bells drifting up through the chord, one per beat
        for k in range(int(beats)):
            note = root + 24 + iv[k % len(iv)] + (12 if k == 3 else 0)
            tr.add(glass_bell(midi_hz(note), decay=1.8), start + k + 0.5 * (k % 2), 0.09)
    tr.echo(((0.33, 0.28), (0.66, 0.18), (1.0, 0.1), (1.4, 0.05)))
    tr.lowpass(4)
    # Written for Lake Meridian, now Route 3's theme. lake_meridian.wav is a separate hand-made track.
    save('route3', tr.mix, peak=0.6)


# ── Wild / trainer battle: upbeat GBA pulse lead (A minor, 150 BPM) ──

def _drums(tr, bars, kicks, snares, hats, hat_gain=0.12, crash_bars=()):
    for b in range(bars):
        o = b * tr.bpb
        for k in kicks:
            tr.add(kick(), o + k, 0.55)
        for s in snares:
            tr.add(snare(tr.rng), o + s, 0.32)
        for h in hats:
            tr.add(hat(tr.rng), o + h, hat_gain)
        if b in crash_bars:
            tr.add(crash(tr.rng), o, 0.14)


def make_battle():
    tr = Track(bpm=150, bars=16, seed=4)
    lead = [
        [(69, .5), (72, .5), (76, .5), (81, 1), (79, .5), (76, 1)],          # Am
        [(77, 1.5), (76, .5), (72, 1), (69, 1)],                             # F
        [(79, .5), (77, .5), (76, .5), (74, .5), (71, 1), (74, 1)],          # G
        [(76, 3), (None, 1)],                                                # Em
        [(69, .5), (72, .5), (76, .5), (81, 1), (83, .5), (84, 1)],          # Am
        [(81, 1.5), (79, .5), (77, 1), (72, 1)],                             # F
        [(74, .5), (76, .5), (77, .5), (79, .5), (81, 1), (83, 1)],          # G
        [(80, 3), (None, 1)],                                                # E
        [(84, 1), (81, 1), (77, 1), (81, 1)],                                # F
        [(83, 1), (79, 1), (74, 1), (79, 1)],                                # G
        [(84, .5), (83, .5), (81, 1), (76, 1), (81, 1)],                     # Am
        [(76, .5), (77, .5), (79, .5), (81, .5), (83, 1), (84, 1)],          # Am
        [(81, 1.5), (84, .5), (77, 2)],                                      # F
        [(83, 1.5), (86, .5), (79, 2)],                                      # G
        [(80, 1), (83, 1), (88, 1), (86, 1)],                                # E
        [(83, .5), (80, .5), (76, .5), (74, .5), (76, 2)],                   # E
    ]
    prog = [(45, 'min', 4), (41, 'maj', 4), (43, 'maj', 4), (40, 'min', 4),
            (45, 'min', 4), (41, 'maj', 4), (43, 'maj', 4), (40, 'maj', 4),
            (41, 'maj', 4), (43, 'maj', 4), (45, 'min', 4), (45, 'min', 4),
            (41, 'maj', 4), (43, 'maj', 4), (40, 'maj', 4), (40, 'maj', 4)]
    tr.melody(lead, pulse, 0.3, duty=0.5, vib=0.004, staccato=0.9)
    tr.melody(lead, pulse, 0.1, transpose=-12, duty=0.25, staccato=0.6)    # a thin octave shadow
    for start, root, iv, beats in tr.chords(prog):
        for e in range(int(beats * 2)):          # driving eighth-note bass, root / octave
            note = root - 12 + (12 if e % 2 else 0)
            tr.add(tri_bass(midi_hz(note), 0.5 * tr.beat), start + e * 0.5, 0.42)
        for off in (0.5, 1.5, 2.5, 3.5):         # off-beat chord stabs
            for i in iv:
                tr.add(pulse(midi_hz(root + 24 + i), 0.25 * tr.beat, duty=0.125, staccato=0.6), start + off, 0.045)
    _drums(tr, 16, kicks=(0, 2, 2.5), snares=(1, 3), hats=[h / 2 for h in range(8)], crash_bars=(0, 8))
    tr.echo(((0.2, 0.12),))
    save('battle', tr.mix, peak=0.7)


# ── Big battles (gym leaders, rival, bosses, legendaries): D minor, 168 BPM ──

def make_boss():
    tr = Track(bpm=168, bars=16, seed=5)
    lead = [
        [(74, 1), (81, 1), (77, .5), (76, .5), (74, 1)],                     # Dm
        [(76, .5), (77, .5), (79, .5), (81, .5), (86, 2)],                   # Dm
        [(84, 1), (82, 1), (81, 1), (77, 1)],                                # Bb
        [(79, 1.5), (81, .5), (76, 2)],                                      # C
        [(74, 1), (81, 1), (77, .5), (76, .5), (74, 1)],                     # Dm
        [(77, .5), (79, .5), (81, .5), (84, .5), (86, 2)],                   # Dm
        [(86, 1), (82, 1), (77, 1), (86, 1)],                                # Bb
        [(85, 3), (None, 1)],                                                # A
        [(82, 1.5), (81, .5), (79, 1), (74, 1)],                             # Gm
        [(76, 1.5), (77, .5), (79, 1), (73, 1)],                             # A
        [(74, .5), (77, .5), (81, .5), (86, .5), (89, 2)],                   # Dm
        [(86, 1), (84, 1), (82, 1), (81, 1)],                                # Bb
        [(79, .5), (81, .5), (82, .5), (84, .5), (86, 2)],                   # Gm
        [(85, 1), (81, 1), (76, 1), (79, 1)],                                # A
        [(77, 1), (76, 1), (74, 1), (73, 1)],                                # A
        [(76, .5), (77, .5), (79, .5), (81, .5), (85, 2)],                   # A
    ]
    prog = [(50, 'min', 4), (50, 'min', 4), (46, 'maj', 4), (48, 'maj', 4),
            (50, 'min', 4), (50, 'min', 4), (46, 'maj', 4), (45, 'maj', 4),
            (43, 'min', 4), (45, 'maj', 4), (50, 'min', 4), (46, 'maj', 4),
            (43, 'min', 4), (45, 'maj', 4), (45, 'maj', 4), (45, 'maj', 4)]
    tr.melody(lead, pulse, 0.3, duty=0.25, vib=0.005, staccato=0.92)
    tr.melody(lead, pulse, 0.12, transpose=-12, duty=0.5, staccato=0.92)    # full octave doubling
    for start, root, iv, beats in tr.chords(prog):
        pattern = (0, 0, 12, 0)                  # galloping sixteenth bass
        for s in range(int(beats * 4)):
            tr.add(tri_bass(midi_hz(root - 12 + pattern[s % 4]), 0.25 * tr.beat, staccato=0.8), start + s * 0.25, 0.4)
        tr.add(pad([midi_hz(root + 12 + i) for i in iv], beats * tr.beat, attack=0.15, bright=0.6), start, 0.35)
    _drums(tr, 16, kicks=(0, 1, 2, 3, 3.5), snares=(1, 3), hats=[h / 4 for h in range(16)],
           hat_gain=0.08, crash_bars=(0, 4, 8, 12))
    tr.echo(((0.18, 0.1),))
    save('boss2', tr.mix, peak=0.72)   # boss.wav is a separate hand-made track


# ── Lunar Planet: eerie and low (A phrygian / minor, 60 BPM) ──

def make_lunar():
    tr = Track(bpm=60, bars=8, seed=6)
    tune = [
        [(76, 3), (None, 1)],                   # Am
        [(77, 2), (74, 2)],                     # Bb
        [(72, 1), (71, 1), (69, 2)],            # Am
        [(68, 3), (None, 1)],                   # Fm  — the borrowed Ab
        [(76, 2), (77, 1), (76, 1)],            # Am
        [(74, 3), (None, 1)],                   # Bb
        [(77, 2), (81, 2)],                     # Dm
        [(68, 3), (None, 1)],                   # E   — G# hangs, unresolved
    ]
    prog = [(45, 'min', 4), (46, 'maj', 4), (45, 'min', 4), (41, 'min', 4),
            (45, 'min', 4), (46, 'maj', 4), (50, 'min', 4), (40, 'maj', 4)]
    tr.melody(tune, ocarina, 0.36, transpose=-12, rng=tr.rng, vib=0.012, detune=0.12)
    # a drone on A that slowly breathes the whole time
    t = _t(tr.n)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)) * (0.7 + 0.3 * np.sin(2 * np.pi * t / (tr.n / RATE / 2)))
    tr.mix += drone * 0.18
    for start, root, iv, beats in tr.chords(prog):
        tr.add(pad([midi_hz(root + i) for i in iv], beats * tr.beat, attack=1.5, bright=0.05), start, 0.42)
        tr.add(thump(), start, 0.4)
        tr.add(thump(), start + 0.35, 0.25)      # lub-dub
    # distant glassy bells, a little dissonant
    for beat, note in ((1.5, 93), (6.5, 94), (11, 88), (14.5, 92), (19.5, 93), (22, 94), (27, 89), (30.5, 92)):
        tr.add(glass_bell(midi_hz(note), decay=2.4), beat, 0.05)
    tr.echo(((0.45, 0.3), (0.9, 0.2), (1.35, 0.12), (1.8, 0.06)))
    tr.lowpass(6)
    save('spacial', tr.mix, peak=0.6)


# ── Solar Planet: bright and shimmering (E major, 108 BPM) ──

def make_solar():
    tr = Track(bpm=108, bars=8, seed=7)
    tune = [
        [(83, 1), (80, .5), (83, .5), (88, 2)],             # E
        [(87, 1), (85, .5), (83, .5), (78, 2)],             # B
        [(80, 1), (81, .5), (83, .5), (85, 1), (88, 1)],    # C#m
        [(85, 3), (None, 1)],                               # A
        [(83, 1), (80, .5), (83, .5), (88, 1.5), (90, .5)], # E
        [(87, 2), (78, 1), (83, 1)],                        # B
        [(85, 1), (83, .5), (81, .5), (80, 1), (78, 1)],    # A
        [(78, 1), (80, 1), (83, 2)],                        # B
    ]
    prog = [(52, 'maj', 4), (47, 'maj', 4), (49, 'min', 4), (45, 'maj', 4),
            (52, 'maj', 4), (47, 'maj', 4), (45, 'maj', 4), (47, 'sus', 2), (47, 'maj', 2)]
    rng = np.random.default_rng(1)
    tr.melody(tune, flute, 0.45, rng=rng)
    tr.melody(tune, lambda f, d: glass_bell(f, decay=0.9), 0.08, transpose=12)   # sparkle on top
    for start, root, iv, beats in tr.chords(prog):
        tr.add(pad([midi_hz(root + 12 + i) for i in iv], beats * tr.beat, attack=0.4, bright=0.4), start, 0.3)
        for k in range(0, int(beats), 2):
            tr.add(bass(midi_hz(root - 12 if root > 45 else root), 2 * tr.beat), start + k, 0.26)
        # shimmering sixteenth-note bell cascade up and down the chord
        notes = [root + 24 + i + 12 * o for o in (0, 1) for i in iv]
        cascade = notes + notes[-2:0:-1]
        for s in range(int(beats * 4)):
            tr.add(glass_bell(midi_hz(cascade[s % len(cascade)]), decay=0.5), start + s * 0.25,
                   0.045 if s % 4 else 0.065)
    for b in range(8):                           # a soft shaker on the off-beats
        for h in (0.5, 1.5, 2.5, 3.5):
            tr.add(hat(tr.rng, 0.06), b * 4 + h, 0.05)
    tr.echo(((0.28, 0.2), (0.55, 0.12)))
    save('route4', tr.mix, peak=0.62)   # first written for the Solar Planet, then Palm Port


# ── more instruments: electric piano, brushes, water drips, sub bass ──

def rhodes(freq, dur):
    """Mellow electric piano: sine body + a soft bell-like tine on the attack,
    with a slow tremolo."""
    n = int(RATE * (dur + 0.5))
    t = _t(n)
    body = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t) * np.exp(-t / 0.4)
    tine = 0.3 * np.sin(2 * np.pi * freq * 7.0 * t) * np.exp(-t / 0.05)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    env = np.exp(-t / 1.4) * _adsr(n, 0.004, dur, 0.5)
    return (body + tine) * trem * env


def brush(rng):
    """Soft brushed snare."""
    n = int(RATE * 0.22)
    noise = rng.uniform(-1, 1, n)
    noise = np.convolve(noise, np.ones(3) / 3, mode='same')
    return noise * np.exp(-_t(n) / 0.07) * np.clip(_t(n) / 0.008, 0, 1)


def soft_kick():
    n = int(RATE * 0.22)
    t = _t(n)
    return np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-t / 0.025)) / RATE) * np.exp(-t / 0.09)


def drip(freq):
    """A water drop in a cave: a quick falling 'plink'."""
    n = int(RATE * 0.35)
    t = _t(n)
    f = freq * (1 + 0.9 * np.exp(-t / 0.012))
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t / 0.08) * np.clip(t / 0.002, 0, 1)


def sub_bass(freq, dur):
    """Deep, round bass with a slight pitch dip on the attack."""
    n = int(RATE * (dur + 0.08))
    t = _t(n)
    f = freq * (1 + 0.15 * np.exp(-t / 0.03))
    x = np.sin(2 * np.pi * np.cumsum(f) / RATE) + 0.15 * np.sin(4 * np.pi * np.cumsum(f) / RATE)
    return x * _adsr(n, 0.01, dur, 0.08, decay_to=0.6, decay=0.35)


def rustle(rng, length=0.12):
    """Dry corn-leaf shaker."""
    n = int(RATE * length)
    noise = rng.uniform(-1, 1, n)
    noise -= np.convolve(noise, np.ones(8) / 8, mode='same')
    return noise * np.sin(np.pi * np.clip(_t(n) / length, 0, 1)) ** 2


# ── Corn Maze: eerie, slow bass beat (E phrygian, 72 BPM) ──

def make_corn_maze():
    tr = Track(bpm=72, bars=8, seed=8)
    # chords: Em, F (the phrygian half-step), Em, Bb (a tritone away — unsettling)...
    prog = [(40, 'min', 4), (41, 'maj', 4), (40, 'min', 4), (46, 'maj', 4),
            (40, 'min', 4), (41, 'maj', 4), (45, 'min', 4), (47, 'maj', 4)]
    # a slow, prowling bass line: (beat in bar, semitones above the root, beats)
    groove = [(0, 0, 1.5), (1.5, 0, 0.5), (2, 7, 0.75), (3, 1, 0.5), (3.5, 0, 0.5)]
    for start, root, iv, beats in tr.chords(prog):
        for b, semis, length in groove:
            tr.add(sub_bass(midi_hz(root - 12 + semis), length * tr.beat), start + b, 0.55)
        tr.add(pad([midi_hz(root + 24 + i) for i in iv], beats * tr.beat, attack=1.4, bright=0.05), start, 0.16)
        # heartbeat kick: 1 and the "and" of 3
        tr.add(soft_kick(), start, 0.5)
        tr.add(soft_kick(), start + 2.5, 0.35)
        tr.add(brush(tr.rng), start + 3, 0.12)                        # a dry rim on 4
        for k in range(8):                                            # corn leaves rustling, uneven
            if tr.rng.random() < 0.7:
                tr.add(rustle(tr.rng), start + k * 0.5 + tr.rng.uniform(0, 0.08), 0.05 + 0.03 * (k % 2))
    lead = [
        [(None, 1), (76, 2), (75, 1)],          # Em  — a sour half-step slide
        [(77, 3), (None, 1)],                   # F
        [(None, 1), (79, 1.5), (76, 1.5)],      # Em
        [(74, 3), (None, 1)],                   # Bb  — clashing against the chord
        [(None, 1), (76, 2), (77, 1)],          # Em
        [(76, 2), (72, 2)],                     # F
        [(None, 1), (69, 2), (72, 1)],          # Am
        [(71, 3), (None, 1)],                   # B   — hanging, unresolved
    ]
    tr.melody(lead, ocarina, 0.3, transpose=-12, rng=tr.rng, vib=0.014, detune=0.15)
    # far-off bells answering from somewhere in the corn
    for beat, note in ((6.5, 88), (14.5, 87), (22.5, 91), (30.5, 87)):
        tr.add(music_box(midi_hz(note)), beat, 0.09)
        tr.add(music_box(midi_hz(note - 1)), beat + 0.75, 0.07)
    tr.echo(((0.42, 0.25), (0.83, 0.15), (1.25, 0.08)))
    tr.lowpass(5)
    save('corn_maze', tr.mix, peak=0.62)


# ── Route 2: relaxed, quiet lo-fi beat (F major, 84 BPM) ──

def make_route2():
    tr = Track(bpm=84, bars=16, seed=9)
    loop = [(53, 'maj7', 4), (52, 'min7', 4), (50, 'min7', 4), (48, 'add9', 4)]   # Fmaj7 Em7 Dm7 Cadd9
    prog = loop * 4
    for start, root, iv, beats in tr.chords(prog):
        # electric piano: chord on 1, a softer re-strike on the "and" of 2
        for off, vel in ((0, 0.10), (1.5, 0.06)):
            for i in iv:
                tr.add(rhodes(midi_hz(root + 12 + i), 1.6 * tr.beat), start + off, vel)
        # warm bass: root, then the fifth leading back
        tr.add(bass(midi_hz(root - 12), 1.8 * tr.beat), start, 0.3)
        tr.add(bass(midi_hz(root - 12 + 7), 0.9 * tr.beat), start + 2.5, 0.2)
        tr.add(bass(midi_hz(root - 12 + 12), 0.4 * tr.beat), start + 3.5, 0.12)
        # lazy beat: kick 1 / "and" of 2, brushes on 2 and 4, quiet ghost hats
        tr.add(soft_kick(), start, 0.32)
        tr.add(soft_kick(), start + 1.5, 0.22)
        tr.add(brush(tr.rng), start + 1, 0.14)
        tr.add(brush(tr.rng), start + 3, 0.14)
        for h in range(8):
            tr.add(hat(tr.rng, 0.03), start + h * 0.5 + (0.08 if h % 2 else 0), 0.025 if h % 2 else 0.04)   # a little swing
    tune = [
        [(None, 2), (72, 1), (74, 1)],          # Fmaj7
        [(76, 2), (74, 1), (71, 1)],            # Em7
        [(72, 3), (69, 1)],                     # Dm7
        [(67, 4)],                              # Cadd9
        [(None, 2), (72, 1), (74, 1)],
        [(76, 1.5), (79, 0.5), (76, 1), (74, 1)],
        [(77, 2), (76, 1), (74, 1)],
        [(72, 4)],
    ]
    # bars 1-4 just the groove; the tune drifts in at bar 5, rests, then returns varied
    tr.melody(tune[:4], ocarina, 0.22, start_bar=4, rng=tr.rng, vib=0.005)
    tr.melody(tune[4:], ocarina, 0.22, start_bar=12, rng=tr.rng, vib=0.005)
    tr.echo(((0.36, 0.18), (0.71, 0.1)))
    tr.lowpass(4)                                # a soft, slightly dusty top end
    save('route2', tr.mix, peak=0.5)


# ── Palm Port (first written for Cobalt Cave): melodic, crystalline (B minor, 96 BPM) ──

def make_palmport():
    tr = Track(bpm=96, bars=16, seed=10)
    loop = [(47, 'min', 4), (43, 'maj7', 4), (50, 'maj', 4), (45, 'sus', 2), (45, 'maj', 2)]   # Bm Gmaj7 D Asus-A
    prog = loop * 4
    for start, root, iv, beats in tr.chords(prog):
        tr.add(pad([midi_hz(root + 12 + i) for i in iv], beats * tr.beat, attack=0.8, bright=0.2), start, 0.28)
        for k in range(0, int(beats), 2):
            tr.add(bass(midi_hz(root - 12 if root > 45 else root), 2 * tr.beat), start + k, 0.24)
        # rippling harp arpeggio in eighths, crystal bells doubling the top
        notes = [root + 12 + i for i in iv] + [root + 24 + iv[0]]
        for e in range(int(beats * 2)):
            n = notes[[0, 1, 2, 3, 2, 1, 2, 3][e % 8] % len(notes)]
            tr.add(harp(midi_hz(n), 1.2), start + e * 0.5, 0.09)
            if e % 4 == 3:
                tr.add(glass_bell(midi_hz(n + 12), decay=1.2), start + e * 0.5, 0.05)
    # water drips falling at uneven moments, each a different pitch
    rng = np.random.default_rng(12)
    for _ in range(26):
        tr.add(drip(rng.choice([1568, 1760, 1976, 2349, 2637])), rng.uniform(0, 64), rng.uniform(0.04, 0.09))
    tune_a = [
        [(78, 1), (81, 1), (83, 1.5), (81, 0.5)],     # Bm
        [(79, 2), (78, 1), (74, 1)],                  # Gmaj7
        [(76, 1), (78, 1), (81, 1.5), (78, 0.5)],     # D
        [(76, 3), (None, 1)],                         # Asus-A
        [(78, 1), (81, 1), (83, 1.5), (86, 0.5)],     # Bm
        [(86, 1.5), (83, 0.5), (79, 2)],              # Gmaj7
        [(81, 1), (78, 1), (76, 1), (74, 1)],         # D
        [(73, 3), (None, 1)],                         # A
    ]
    tune_b = [   # the answer, higher and brighter
        [(86, 2), (85, 1), (83, 1)],
        [(83, 2), (79, 1), (81, 1)],
        [(81, 1.5), (78, 0.5), (81, 1), (86, 1)],
        [(85, 3), (None, 1)],
        [(86, 1), (88, 1), (90, 1.5), (88, 0.5)],
        [(86, 2), (83, 2)],
        [(81, 1), (83, 1), (85, 1), (86, 1)],
        [(83, 3), (None, 1)],
    ]
    rng = np.random.default_rng(13)
    tr.melody(tune_a, flute, 0.4, rng=rng)
    tr.melody(tune_b, flute, 0.36, start_bar=8, rng=rng)
    tr.melody(tune_b, lambda f, d: glass_bell(f, decay=0.8), 0.05, start_bar=8, transpose=12)
    tr.echo(((0.31, 0.3), (0.62, 0.2), (0.94, 0.12), (1.4, 0.06)))   # a big cave echo
    tr.lowpass(3)
    save('palmport', tr.mix, peak=0.6)   # first written for Cobalt Cave


# ── Cobalt Cave: ominous but chill — a half-time bass groove (D minor, 70 BPM) ──

def swell_boom(dur=2.4):
    """A deep boom that swells up out of nothing and cuts off (reverse-cymbal feel)."""
    n = int(RATE * dur)
    t = _t(n)
    rise = (t / dur) ** 3
    body = np.sin(2 * np.pi * 36.7 * t) + 0.4 * np.sin(2 * np.pi * 55 * t)
    air = np.convolve(np.random.default_rng(14).uniform(-1, 1, n), np.ones(40) / 40, mode='same') * 2
    x = (body + air) * rise
    x[-int(RATE * 0.03):] *= np.linspace(1, 0, int(RATE * 0.03))
    return x


def make_cobalt_cave():
    tr = Track(bpm=70, bars=16, seed=15)
    loop = [(50, 'min', 4), (46, 'maj7', 4), (43, 'min7', 4), (45, 'sus', 2), (45, 'maj', 2)]   # Dm Bbmaj7 Gm7 Asus-A
    prog = loop * 4
    # half-time sub-bass ostinato that creeps up to the flat-six (the ominous note) each bar
    groove = [(0, 0, 1.5), (2, 0, 0.9), (3, 7, 0.5), (3.5, 8, 0.5)]
    bar_starts = []
    for start, root, iv, beats in tr.chords(prog):
        if beats == 4 or start % 4 == 0:
            bar_starts.append((start, root))
        tr.add(pad([midi_hz(root + i) for i in iv], beats * tr.beat, attack=1.6, bright=0.04), start, 0.3)
    for start, root in bar_starts:
        for b, semis, length in groove:
            tr.add(sub_bass(midi_hz(root - 12 + semis), length * tr.beat), start + b, 0.6)
        # chill, muffled half-time beat: kick on 1 (and a ghost before 3), brushed snare on 3
        tr.add(soft_kick(), start, 0.45)
        tr.add(soft_kick(), start + 1.75, 0.18)
        tr.add(brush(tr.rng), start + 2, 0.16)
        for h in range(8):
            tr.add(hat(tr.rng, 0.03), start + h * 0.5 + (0.06 if h % 2 else 0), 0.018 if h % 2 else 0.03)
    # the pad breathes slowly — a gentle, uneasy pulse
    t = _t(tr.n)
    tr.mix *= 0.85 + 0.15 * np.sin(2 * np.pi * t / (tr.beat * 8))
    for bar in (3, 7, 11, 15):                    # a deep swell rising into every 4th downbeat
        tr.add(swell_boom(2.4), (bar + 1) * 4 - 2.4 / tr.beat, 0.22)
    rng = np.random.default_rng(16)
    for _ in range(12):                            # sparse drips, lower and duller than before
        tr.add(drip(rng.choice([880, 988, 1175, 1319])), rng.uniform(0, 64), rng.uniform(0.03, 0.06))
    # second half: a low electric-piano melody leaning on the C# leading tone
    tune = [
        [(None, 1), (69, 1.5), (65, 1.5)],             # Dm
        [(70, 2), (69, 1), (65, 1)],                   # Bbmaj7
        [(67, 3), (None, 1)],                          # Gm7
        [(64, 2), (61, 2)],                            # Asus-A — the C# pulls back to D
        [(None, 1), (69, 1), (72, 1), (74, 1)],        # Dm
        [(77, 2), (74, 1), (70, 1)],                   # Bbmaj7
        [(72, 1.5), (70, 0.5), (67, 2)],               # Gm7
        [(64, 2), (61, 2)],                            # A
    ]
    tr.melody(tune, rhodes, 0.2, start_bar=8)
    tr.melody(tune, lambda f, d: glass_bell(f, decay=1.0), 0.03, start_bar=8, transpose=12)
    # first half: a lonely two-note bell motif, far away
    for bar in (1, 5):
        tr.add(glass_bell(midi_hz(81), decay=2.0), bar * 4 + 2, 0.05)
        tr.add(glass_bell(midi_hz(80), decay=2.0), bar * 4 + 3, 0.04)
    tr.echo(((0.43, 0.28), (0.86, 0.18), (1.29, 0.1), (1.9, 0.05)))   # big, dark cave echo
    tr.lowpass(6)                                   # keep the top end dark
    save('cobalt_cave', tr.mix, peak=0.6)


# ── Elder Town: a chill, farm-like acoustic guitar beat (G major, 88 BPM) ──

def guitar(freq, dur=None, ring=2.4, bright=0.6, t60=2.2, seed=0):
    """Plucked acoustic string (Karplus-Strong). Rendered at 4x the sample
    rate so the whole-sample delay keeps high notes in tune, then averaged
    back down. `dur` damps the string (a palm/finger mute) after that long."""
    up = 4
    sr = RATE * up
    period = sr / freq - 0.5                   # the 2-tap average adds half a sample of delay
    N = max(2, int(round(period)))
    n = int(sr * ring)
    rng = np.random.default_rng(seed)
    y = np.zeros(n + N + 1)
    burst = rng.uniform(-1, 1, N + 1)
    for _ in range(int(1 + (1 - bright) * 4)):          # darker pick = smoother burst
        burst = 0.5 * (burst + np.roll(burst, 1))
    y[:N + 1] = burst - burst.mean()
    d = 0.001 ** (1 / (t60 * freq))                     # per-period loss for the given decay time
    i = N + 1
    while i < len(y):
        k = min(N, len(y) - i)
        y[i:i + k] = d * 0.5 * (y[i - N:i - N + k] + y[i - N - 1:i - N - 1 + k])
        i += k
    y = y[:n]
    if dur is not None:                                  # damp after `dur`
        cut = int(sr * (dur + 0.06))
        if cut < n:
            y[cut:] *= np.exp(-np.arange(n - cut) / (sr * 0.08))
    y = y[: n // up * up].reshape(-1, up).mean(axis=1)   # back down to RATE
    return y


def make_elder_town():
    tr = Track(bpm=88, bars=16, seed=17)
    # open-chord voicings: (thumb bass root, alternate bass, three treble strings)
    shapes = {
        'G':  (43, 50, (55, 59, 67)),
        'C':  (48, 55, (60, 64, 67)),
        'D':  (50, 57, (62, 66, 69)),
        'Em': (40, 47, (55, 59, 64)),
    }
    strum_notes = {'G': (43, 47, 50, 55, 59, 67), 'C': (48, 52, 55, 60, 64), 'D': (50, 57, 62, 66),
                   'Em': (40, 47, 52, 55, 59, 64)}
    roots = {'G': 43, 'C': 36, 'D': 38, 'Em': 40}
    prog = ['G', 'C', 'G', 'D', 'Em', 'C', 'G', 'D',
            'C', 'G', 'Em', 'C', 'G', 'C', 'D', 'G']
    seed = 0
    for bar, ch in enumerate(prog):
        o = bar * 4
        b1, b2, tre = shapes[ch]
        # Travis picking: thumb alternates bass on the beats, fingers pluck on the off-beats
        pattern = [b1, tre[1], b2, tre[2], b1, tre[0], b2, tre[2]]
        for e, note in enumerate(pattern):
            seed += 1
            is_bass = e % 2 == 0
            g = guitar(midi_hz(note), dur=0.9 * tr.beat if is_bass else None,
                       bright=0.45 if is_bass else 0.7, t60=1.6 if is_bass else 2.4, seed=seed)
            tr.add(g, o + e * 0.5 + (0.02 if e % 2 else 0), 0.26 if is_bass else 0.2)   # a hint of swing
        if bar >= 8:   # second half: a soft downstroke strum on each downbeat
            for s, note in enumerate(strum_notes[ch]):
                seed += 1
                tr.add(guitar(midi_hz(note), bright=0.55, t60=1.8, seed=seed), o + s * 0.018 / tr.beat, 0.04)
        # upright-style bass, soft, on 1 and 3
        tr.add(bass(midi_hz(roots[ch]), 1.6 * tr.beat), o, 0.22)
        tr.add(bass(midi_hz(roots[ch] + 7), 1.6 * tr.beat), o + 2, 0.16)
        # chill beat: soft kick 1 and 3, brushes on 2 and 4, a shaker in eighths
        tr.add(soft_kick(), o, 0.3)
        tr.add(soft_kick(), o + 2, 0.22)
        tr.add(brush(tr.rng), o + 1, 0.12)
        tr.add(brush(tr.rng), o + 3, 0.12)
        for h in range(8):
            tr.add(rustle(tr.rng, 0.09), o + h * 0.5 + (0.02 if h % 2 else 0), 0.035 if h % 2 else 0.05)
    # a whistled melody over the second half
    whistle = [
        [(76, 1.5), (74, 0.5), (72, 1), (76, 1)],      # C
        [(74, 2), (71, 1), (67, 1)],                   # G
        [(71, 1.5), (69, 0.5), (67, 1), (64, 1)],      # Em
        [(67, 3), (None, 1)],                          # C
        [(71, 1), (74, 1), (79, 1.5), (78, 0.5)],      # G
        [(76, 2), (79, 1), (76, 1)],                   # C
        [(74, 1.5), (72, 0.5), (71, 1), (69, 1)],      # D
        [(67, 3), (None, 1)],                          # G
    ]
    tr.melody(whistle, ocarina, 0.12, start_bar=8, transpose=12, rng=tr.rng, vib=0.01)
    tr.echo(((0.3, 0.14), (0.6, 0.07)))
    tr.lowpass(3)
    save('elder_town', tr.mix, peak=0.6)


def save(name, x, peak):
    x = x / (np.max(np.abs(x)) or 1) * peak
    data = (np.clip(x, -1, 1) * 32767).astype('<i2')
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    print('wrote', path, f'{len(x) / RATE:.1f}s')


TRACKS = {
    'route1': make_route1,
    'silverleaf': make_silverleaf,
    'route3': make_lake,
    'battle': make_battle,
    'boss2': make_boss,
    'spacial': make_lunar,
    'route4': make_solar,
    'corn_maze': make_corn_maze,
    'route2': make_route2,
    'palmport': make_palmport,
    'cobalt_cave': make_cobalt_cave,
    'elder_town': make_elder_town,
}

if __name__ == '__main__':
    # python tools/make_music.py            -> every track
    # python tools/make_music.py lake boss  -> just those
    import sys
    for name in sys.argv[1:] or TRACKS:
        TRACKS[name]()
