"""Generates the game's retro (GBA-style) sound effects into assets/SOUND/SFX/.

Everything is synthesized from square waves and filtered noise — the same
raw ingredients the GBA's sound channels use — so there are no outside
audio files involved. Tweak the numbers below and rerun:

    python tools/make_sfx.py

Any .wav in assets/SOUND/SFX/ can also simply be replaced by hand; the game
loads whatever file has the matching name (see sfx.py).
"""
import os
import wave
import numpy as np

RATE = 22050
OUT_DIR = os.path.join('assets', 'SOUND', 'SFX')
rng = np.random.default_rng(7)


def t_axis(dur):
    return np.arange(int(RATE * dur)) / RATE


def square(freq, dur, duty=0.5):
    """Square wave; `freq` may be a number or an array (for pitch sweeps)."""
    n = int(RATE * dur)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    phase = np.cumsum(f) / RATE
    return np.where((phase % 1.0) < duty, 1.0, -1.0)


def triangle(freq, dur):
    n = int(RATE * dur)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    phase = np.cumsum(f) / RATE
    return 2 * np.abs(2 * (phase % 1.0) - 1) - 1


def noise(dur):
    return rng.uniform(-1, 1, int(RATE * dur))


def lowpass(x, k):
    """One-pole low-pass; k in 0..1 (smaller = darker)."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def highpass(x, k):
    return x - lowpass(x, k)


def env(n, attack=0.002, decay_pow=1.0):
    """Fast attack, then a decay curve to zero."""
    a = max(1, int(RATE * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[a:] = np.linspace(1, 0, n - a) ** decay_pow
    return e


def crush(x, levels=16):
    """Coarse amplitude steps, like the GBA's 4-bit channel volumes."""
    return np.round(x * levels) / levels


def save(name, x, peak=0.55):
    x = x / (np.max(np.abs(x)) or 1) * peak
    data = (np.clip(x, -1, 1) * 32767).astype('<i2')
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    print('wrote', path, f'{len(x) / RATE:.3f}s')


def make_bump():
    # Dull low thud with a quick downward pitch bend
    dur = 0.11
    n = int(RATE * dur)
    f = np.linspace(110, 55, n)
    body = triangle(f, dur) * 0.9 + square(f, dur, 0.25) * 0.25
    thump = lowpass(noise(dur), 0.08) * 1.5
    x = (body + thump) * env(n, 0.001, 2.2)
    save('bump', crush(lowpass(x, 0.35)), peak=0.6)


def make_click():
    # A-press: two quick rising blips, kept low and rounded so they don't pierce
    a = square(587, 0.035, 0.5) * env(int(RATE * 0.035), 0.001, 0.6)
    b = square(880, 0.045, 0.5) * env(int(RATE * 0.045), 0.001, 1.4)
    save('click', crush(lowpass(np.concatenate([a, b]), 0.3)), peak=0.32)


def make_select():
    # Cursor move: one short, soft tick
    dur = 0.03
    x = square(784, dur, 0.5) * env(int(RATE * dur), 0.001, 1.8)
    save('select', crush(lowpass(x, 0.3)), peak=0.3)


def make_door():
    # Entering a door/cave: a soft whoosh sweeping down, with a low step at the end
    dur = 0.38
    n = int(RATE * dur)
    t = t_axis(dur)
    nz = noise(dur)
    sweep_k = np.linspace(0.55, 0.05, n)            # filter closes as it whooshes
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += sweep_k[i] * (nz[i] - acc)
        y[i] = acc
    whoosh = y * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.8
    step_t = 0.08
    step = triangle(np.linspace(140, 70, int(RATE * step_t)), step_t) * env(int(RATE * step_t), 0.001, 2)
    x = whoosh * 1.4
    start = n - len(step)
    x[start:] += step * 0.8
    save('door', crush(x, 24), peak=0.5)


def make_grass():
    # Rustle: a few crinkly bursts of bright noise
    dur = 0.16
    n = int(RATE * dur)
    x = np.zeros(n)
    for start, length, amp in ((0.0, 0.05, 1.0), (0.045, 0.045, 0.75), (0.085, 0.06, 0.55)):
        s, l = int(RATE * start), int(RATE * length)
        burst = highpass(noise(length), 0.25) * env(l, 0.003, 1.6) * amp
        x[s:s + l] += burst[: max(0, min(l, n - s))]
    save('grass', crush(lowpass(x, 0.6), 20), peak=0.38)


# ── Event sounds (legendaries, transformations, night events) ────────────

def sine(freq, dur):
    n = int(RATE * dur)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / RATE)


def lowpass_sweep(x, k):
    """Low-pass whose cutoff `k` is an array the same length as x."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k[i] * (v - acc)
        y[i] = acc
    return y


def place(buf, x, at):
    """Mix x into buf starting at `at` seconds (clipped to buf's length)."""
    s = int(RATE * at)
    end = min(len(buf), s + len(x))
    if end > s:
        buf[s:end] += x[: end - s]


def bell(freq, dur, bright=1.0, decay=4.0):
    """Chime: a few inharmonic partials, each fading at its own rate."""
    t = t_axis(dur)
    x = np.zeros(len(t))
    for mult, amp in ((1.0, 1.0), (2.01, 0.5 * bright), (3.02, 0.3 * bright), (4.17, 0.18 * bright)):
        x += sine(freq * mult, dur) * amp * np.exp(-t * decay * mult ** 0.5)
    a = int(RATE * 0.003)
    x[:a] *= np.linspace(0, 1, a)
    return x


def make_celes_awaken():
    # Celestreeyl awakens: a shimmering arpeggio that speeds up and climbs
    # over a rising noise swell (1.8s), then a bright white-out burst.
    charge, total = 1.8, 2.6
    n = int(RATE * total)
    x = np.zeros(n)
    notes = (523, 659, 784, 988, 1175, 1319, 1568, 1976)   # C major, climbing
    t, step, i = 0.0, 0.16, 0
    while t < charge:
        f = notes[i % len(notes)] * (2 if i >= 2 * len(notes) else 1)
        d = 0.12
        blip = (square(f, d, 0.25) * 0.4 + triangle(f, d)) * env(int(RATE * d), 0.002, 1.5)
        place(x, blip * (0.35 + 0.65 * t / charge), t)
        t += step
        step = max(0.045, step * 0.9)
        i += 1
    sw = int(RATE * charge)
    swell = lowpass_sweep(noise(charge), np.linspace(0.02, 0.5, sw)) * np.linspace(0, 1, sw) ** 2
    x[:sw] += swell * 1.6
    # The burst: noise crash + a high major chord ringing out
    bd = total - charge
    crash = highpass(noise(bd), 0.15) * env(int(RATE * bd), 0.002, 2.5) * 1.6
    chord = sum(bell(f, bd, 0.8, 2.2) for f in (1047, 1319, 1568, 2093)) * 0.6
    place(x, crash + chord, charge)
    save('celes_awaken', crush(x, 24), peak=0.6)


def make_solar_shard():
    # Celestreeyl defeated: motes spiral in — soft twinkles drifting down in
    # pitch while the shard descends (plays from the start of the reveal).
    dur = 2.7
    x = np.zeros(int(RATE * dur))
    r = np.random.default_rng(11)
    t = 0.3
    while t < dur - 0.2:
        p = t / dur
        f = 2600 - 1400 * p + r.uniform(-200, 200)
        place(x, bell(f, 0.35, 0.4, 9.0) * r.uniform(0.4, 0.9), t)
        t += r.uniform(0.07, 0.14)
    pad_t = t_axis(dur)
    pad = (sine(523, dur) + sine(784, dur) * 0.7 + sine(1047, dur) * 0.4) * np.sin(np.pi * pad_t / dur) * 0.35
    save('solar_shard', crush(x + pad, 24), peak=0.45)


def make_shard_land():
    # Shard touches down: a bright rainbow chime with a quick upward sparkle
    dur = 1.6
    x = sum(bell(f, dur, 1.0, 2.0) for f in (784, 988, 1175, 1568))
    for k, f in enumerate((1568, 1976, 2349, 3136)):
        place(x, bell(f, 0.3, 0.3, 10.0) * 0.6, 0.03 + k * 0.045)
    save('shard_land', crush(x, 24), peak=0.55)


def make_dark_pulse():
    # One throb of Cobaltion's aura: a deep heartbeat-like swell with a
    # faint hollow whoosh — quiet, since it repeats the whole time you're near.
    dur = 0.55
    n = int(RATE * dur)
    t = t_axis(dur)
    body = sine(np.linspace(70, 42, n), dur) + triangle(np.linspace(140, 84, n), dur) * 0.25
    swell = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    air = lowpass(noise(dur), 0.04) * 1.8 * swell
    x = body * env(n, 0.04, 1.6) + air
    save('dark_pulse', crush(lowpass(x, 0.25), 20), peak=0.5)


def make_dark_collapse():
    # The rings collapse into Cobaltion (0.6s, a reversed whoosh sucking
    # inward and rising), then the burst: a deep boom and a scatter of noise.
    condense, total = 0.6, 1.5
    n = int(RATE * total)
    x = np.zeros(n)
    cn = int(RATE * condense)
    suck = lowpass_sweep(noise(condense), np.linspace(0.03, 0.6, cn)) * np.linspace(0, 1, cn) ** 2.5
    rise = square(np.linspace(55, 220, cn), condense, 0.3) * np.linspace(0, 1, cn) ** 3 * 0.35
    x[:cn] += suck * 1.8 + rise
    bd = total - condense
    bn = int(RATE * bd)
    boom = sine(np.linspace(90, 30, bn), bd) * env(bn, 0.002, 1.8) * 1.4
    blast = lowpass_sweep(noise(bd), np.linspace(0.5, 0.03, bn)) * env(bn, 0.002, 1.4) * 1.8
    place(x, boom + blast, condense)
    save('dark_collapse', crush(x, 20), peak=0.65)


def make_dark_roar():
    # Cobaltion's cry: a gritty descending growl with a fast wobble
    dur = 0.95
    n = int(RATE * dur)
    t = t_axis(dur)
    f = (260 * np.exp(-t * 1.1)) * (1 + 0.06 * np.sin(2 * np.pi * 22 * t))
    voice = square(f, dur, 0.3) + square(f * 1.5, dur, 0.5) * 0.4 + square(f * 0.5, dur, 0.5) * 0.5
    grit = highpass(noise(dur), 0.3) * 0.5
    x = (voice + grit) * env(n, 0.03, 1.2)
    save('dark_roar', crush(lowpass(x, 0.3), 16), peak=0.55)


def make_lunar_shard():
    # The Twilight Lunar Shard appears: a cold, hollow minor chime that
    # hangs over a low drone.
    dur = 2.2
    t = t_axis(dur)
    x = sum(bell(f, dur, 0.7, 1.6) for f in (440, 523, 659, 880)) * 0.7
    place(x, bell(1319, 1.0, 0.5, 3.0) * 0.5, 0.25)
    place(x, bell(1047, 1.0, 0.5, 3.0) * 0.4, 0.5)
    drone = (sine(110, dur) + sine(110.6, dur)) * np.sin(np.pi * t / dur) * 0.35
    save('lunar_shard', crush(x + drone, 24), peak=0.5)


def make_lunar_descend():
    # Twilight shard reveal: cold, glassy twinkles drifting down in pitch
    # over a hollow beating drone while the shard descends.
    dur = 2.7
    x = np.zeros(int(RATE * dur))
    r = np.random.default_rng(23)
    t = 0.3
    while t < dur - 0.2:
        p = t / dur
        f = 1900 - 900 * p + r.uniform(-150, 150)
        place(x, bell(f, 0.45, 0.6, 7.0) * r.uniform(0.35, 0.8), t)
        t += r.uniform(0.09, 0.17)
    tt = t_axis(dur)
    pad = (sine(220, dur) + sine(261.6, dur) * 0.6 + sine(220.8, dur) * 0.8) * np.sin(np.pi * tt / dur) * 0.35
    save('lunar_descend', crush(x + pad, 24), peak=0.45)


def make_morph():
    # Scarecrux <-> Gourdecrux: dark orbs swirl for 4s — detuned tones
    # wobbling around each other, climbing, with a whispery wind building.
    dur = 4.0
    n = int(RATE * dur)
    t = t_axis(dur)
    base = 110 * 2 ** (t / dur * 1.5)          # climbs an octave and a half
    wob = 1 + 0.03 * np.sin(2 * np.pi * (2 + 6 * t / dur) * t)
    a = triangle(base * wob, dur)
    b = square(base * 1.498 / wob, dur, 0.25) * 0.35   # a fifth, wobbling the other way
    c = triangle(base * 0.5 * 1.012, dur) * 0.6
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * (3 + 9 * t / dur) * t)
    wind = lowpass_sweep(noise(dur), np.linspace(0.02, 0.25, n)) * 1.4
    build = (t / dur) ** 1.2
    x = ((a + b + c) * trem + wind) * build
    x[-int(RATE * 0.05):] *= np.linspace(1, 0, int(RATE * 0.05))
    save('morph', crush(lowpass(x, 0.4), 20), peak=0.55)


def make_morph_done():
    # Transformation finishes: a hollow, eerie hit — low thud plus a
    # dissonant minor-second chime.
    dur = 1.4
    n = int(RATE * dur)
    thud = sine(np.linspace(120, 45, n), dur) * env(n, 0.002, 3.0) * 1.3
    chime = bell(622, dur, 0.8, 2.5) + bell(659, dur, 0.8, 2.5) * 0.8 + bell(311, dur, 0.5, 2.0) * 0.6
    save('morph_done', crush(thud + chime, 20), peak=0.55)


def make_eerie():
    # The scarecrow wakes: a ghostly, wavering descending moan over a
    # dissonant drone and cold wind.
    dur = 2.8
    n = int(RATE * dur)
    t = t_axis(dur)
    moan_f = 660 * 2 ** (-t / dur * 0.9) * (1 + 0.025 * np.sin(2 * np.pi * 5.5 * t))
    moan = triangle(moan_f, dur) + sine(moan_f * 1.06, dur) * 0.5     # slightly sour
    moan *= np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    drone = (triangle(98, dur) + triangle(104, dur)) * 0.35            # beating minor second
    wind = lowpass_sweep(highpass(noise(dur), 0.05), 0.08 + 0.06 * np.sin(2 * np.pi * 0.7 * t)) * 1.5
    x = (moan + drone + wind) * env(n, 0.4, 0.8)
    save('eerie', crush(lowpass(x, 0.35), 20), peak=0.5)


if __name__ == '__main__':
    make_bump()
    make_click()
    make_select()
    make_door()
    make_grass()
    make_celes_awaken()
    make_solar_shard()
    make_shard_land()
    make_dark_pulse()
    make_dark_collapse()
    make_dark_roar()
    make_lunar_shard()
    make_lunar_descend()
    make_morph()
    make_morph_done()
    make_eerie()
