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


if __name__ == '__main__':
    make_bump()
    make_click()
    make_select()
    make_door()
    make_grass()
