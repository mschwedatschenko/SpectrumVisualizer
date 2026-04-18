import numpy as np
import time
from rtlsdr import RtlSdr
from rgbmatrix import RGBMatrix, RGBMatrixOptions

# ── Matrix setup ──────────────────────────────────────────
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# ── SDR setup ─────────────────────────────────────────────
sdr = RtlSdr()
sdr.sample_rate = 2.4e6
sdr.gain = 40

# ── Band definitions ──────────────────────────────────────
BANDS = {
    'FM':   {'freq': 98e6,     'color': (255, 140, 0),   'col': 0},
    'NOAA': {'freq': 137.5e6,  'color': (0,   200, 180), 'col': 11},
    'EMS':  {'freq': 160e6,    'color': (220, 220, 255), 'col': 22},
    'LTE':  {'freq': 800e6,    'color': (200, 30,  30),  'col': 33},
    'ADSB': {'freq': 1090e6,   'color': (255, 255, 255), 'col': 54},
}

BAND_WIDTH = 10  # pixels wide per band

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
    canvas.Clear()
    for band, info in BANDS.items():
        level = levels[band]
        r, g, b = info['color']
        col_start = info['col']
        bar_height = int(level * 32)

        for x in range(col_start, min(col_start + BAND_WIDTH, 64)):
            for y in range(32):
                # Draw from bottom up
                pixel_y = 31 - y
                if y < bar_height:
                    # Scale brightness with level
                    brightness = level ** 0.7
                    matrix.canvas.SetPixel(
                        x, pixel_y,
                        int(r * brightness),
                        int(g * brightness),
                        int(b * brightness)
                    )
    matrix.SwapOnVSync(canvas)

print("Starting Spectrum Visualizer...")
print("Press Ctrl+C to stop")

try:
    while True:
        raw = {}
        for band, info in BANDS.items():
            raw[band] = get_power(info['freq'])

        normalized = normalize(raw)

        for band, val in normalized.items():
            smoothed[band] = smooth(band, val)

        draw(smoothed)
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    matrix.Clear()
    sdr.close()
    print("Done.")
