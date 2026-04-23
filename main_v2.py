import numpy as np
import subprocess
import time
from rtlsdr import RtlSdr

# ── Start pixel server ────────────────────────────────────
proc = subprocess.Popen(
    ['sudo', '/home/mary/rpi-rgb-led-matrix/pixel-server'],
    stdin=subprocess.PIPE,
    text=True,
    bufsize=1
)

def set_pixel(x, y, r, g, b):
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
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
BANDS = [
    {'name': 'FM',   'freq': 98e6,    'color': (255, 120, 0),   'cx': 6},
    {'name': 'NOAA', 'freq': 137.5e6, 'color': (0,   200, 180), 'cx': 19},
    {'name': 'EMS',  'freq': 160e6,   'color': (200, 200, 255), 'cx': 32},
    {'name': 'LTE',  'freq': 800e6,   'color': (220, 30,  30),  'cx': 45},
    {'name': 'ADSB', 'freq': 1090e6,  'color': (255, 255, 255), 'cx': 57},
]

# ── SDR setup ─────────────────────────────────────────────
from rtlsdr import RtlSdr
sdr = RtlSdr()
sdr.sample_rate = 2.4e6
sdr.gain = 49.6

# ── Per-band history for relative normalization ───────────
band_history = {b['name']: [] for b in BANDS}

def get_power(freq):
    sdr.center_freq = freq
    samples = sdr.read_samples(64 * 1024)
    fft_vals = np.abs(np.fft.fft(samples)) ** 2
    power = float(np.mean(fft_vals))
    return np.log10(power + 1)  # log scale

def get_relative_level(name, raw_power):
    history = band_history[name]
    history.append(raw_power)
    if len(history) > 50:
        history.pop(0)
    mn = min(history)
    mx = max(history)
    if mx == mn:
        return 0.5
    return (raw_power - mn) / (mx - mn)

# ── Smoother ──────────────────────────────────────────────
smoothed = {b['name']: 0.5 for b in BANDS}

def smooth(name, new_val, alpha=0.2):
    smoothed[name] = alpha * new_val + (1 - alpha) * smoothed[name]
    return smoothed[name]

# ── Draw ──────────────────────────────────────────────────
def draw_frame(levels):
    pixels = [[(0, 0, 0)] * 32 for _ in range(64)]

    for band in BANDS:
        name = band['name']
        level = levels[name]
        cx = band['cx']
        cy = 16
        r, g, b = band['color']

        max_radius = 14 * level
        if max_radius < 0.5:
            continue

        for dx in range(-12, 13):
            for dy in range(-15, 16):
                x = cx + dx
                y = cy + dy
                if x < 0 or x >= 64 or y < 0 or y >= 32:
                    continue
                dist = (dx**2 + dy**2) ** 0.5
                if dist > max_radius:
                    continue
                falloff = (1 - (dist / (max_radius + 0.001))) ** 1.5
                brightness = level * falloff
                pr, pg, pb = pixels[x][y]
                pixels[x][y] = (
                    min(255, pr + int(r * brightness)),
                    min(255, pg + int(g * brightness)),
                    min(255, pb + int(b * brightness)),
                )

    for x in range(64):
        for y in range(32):
            pr, pg, pb = pixels[x][y]
            set_pixel(x, y, pr, pg, pb)
    show()

# ── Main loop ─────────────────────────────────────────────
print("Campus Spectrum Display starting...")
print("Note: first 50 readings calibrate each band — give it ~30 seconds")
print("Press Ctrl+C to stop")

try:
    while True:
        for band in BANDS:
            name = band['name']
            raw = get_power(band['freq'])
            relative = get_relative_level(name, raw)
            smooth(name, relative)

        draw_frame(smoothed)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    clear()
    sdr.close()
    proc.stdin.close()
    proc.wait()
    print("Done.")
