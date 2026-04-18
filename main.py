import numpy as np
import subprocess
import sys
import time
import os

# ── Start pixel server ────────────────────────────────────
proc = subprocess.Popen(
    ['sudo', '/home/mary/rpi-rgb-led-matrix/pixel-server'],
    stdin=subprocess.PIPE,
    text=True,
    bufsize=1
)

def set_pixel(x, y, r, g, b):
    proc.stdin.write(f"{x} {y} {r} {g} {b}\n")

def show():
    proc.stdin.write("-1 -1 0 0 0\n")
    proc.stdin.flush()

def clear():
    for x in range(64):
        for y in range(32):
            set_pixel(x, y, 0, 0, 0)
    show()

# ── Band definitions ──────────────────────────────────────
BANDS = {
    'FM':   {'freq': 98e6,    'color': (255, 140, 0),   'col': 0},
    'NOAA': {'freq': 137.5e6, 'color': (0,   200, 180), 'col': 11},
    'EMS':  {'freq': 160e6,   'color': (220, 220, 255), 'col': 22},
    'LTE':  {'freq': 800e6,   'color': (200, 30,  30),  'col': 33},
    'ADSB': {'freq': 1090e6,  'color': (255, 255, 255), 'col': 54},
}
BAND_WIDTH = 10

# ── SDR setup ─────────────────────────────────────────────
from rtlsdr import RtlSdr
sdr = RtlSdr()
sdr.sample_rate = 2.4e6
sdr.gain = 40

# ── Smoother ──────────────────────────────────────────────
smoothed = {band: 0.0 for band in BANDS}

def smooth(band, new_val, alpha=0.15):
    smoothed[band] = alpha * new_val + (1 - alpha) * smoothed[band]
    return smoothed[band]

def get_power(freq):
    sdr.center_freq = freq
    samples = sdr.read_samples(64 * 1024)
    fft_vals = np.abs(np.fft.fft(samples)) ** 2
    return float(np.mean(fft_vals))

def normalize(levels):
    vals = list(levels.values())
    mn, mx = min(vals), max(vals)
    if mx == mn:
        return {k: 0.0 for k in levels}
    return {k: (v - mn) / (mx - mn) for k, v in levels.items()}

def draw(levels):
    for band, info in BANDS.items():
        level = levels[band]
        r, g, b = info['color']
        col_start = info['col']
        bar_height = int(level * 32)
        brightness = level ** 0.7

        for x in range(col_start, min(col_start + BAND_WIDTH, 64)):
            for y in range(32):
                if (31 - y) < bar_height:
                    set_pixel(x, y,
                        int(r * brightness),
                        int(g * brightness),
                        int(b * brightness))
                else:
                    set_pixel(x, y, 0, 0, 0)
    show()

# ── Main loop ─────────────────────────────────────────────
print("Campus Spectrum Display starting...")
print("Press Ctrl+C to stop")

try:
    while True:
        raw = {}
        for band, info in BANDS.items():
            raw[band] = get_power(info['freq'])

        normalized = normalize(raw)

        for band, val in normalized.items():
            smooth(band, val)

        draw(smoothed)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    clear()
    sdr.close()
    proc.stdin.close()
    proc.wait()
    print("Done.")
