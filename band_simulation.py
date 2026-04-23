import numpy as np
import time
import os
from rtlsdr import RtlSdr

class BandSmoother:
    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.values = {}
    
    def update(self, levels):
        for band, value in levels.items():
            if band not in self.values:
                self.values[band] = value
            else:
                self.values[band] = (self.alpha * value +
                                    (1 - self.alpha) * self.values[band])
        return self.values

band_history = {b['name']: [] for b in BANDS}

def get_relative_level(name, raw_power):
    history = band_history[name]
    history.append(raw_power)
    if len(history) > 50:  # keep last 50 readings
        history.pop(0)
    mn = min(history)
    mx = max(history)
    if mx == mn:
        return 0.5
    return (raw_power - mn) / (mx - mn)

def get_band_levels(fft_vals, freqs):
    bands = {
        'FM':   (88e6,  108e6),
        'NOAA': (137e6, 138e6),
        'EMS':  (150e6, 170e6),
        'LTE':  (700e6, 900e6),
        'ADSB': (1089e6, 1091e6),
    }
    levels = {}
    for name, (low, high) in bands.items():
        mask = (freqs >= low) & (freqs <= high)
        if mask.any():
            levels[name] = float(np.mean(fft_vals[mask]))
        else:
            levels[name] = 0.0
    return levels

def normalize(levels):
    vals = list(levels.values())
    min_val = min(vals)
    max_val = max(vals)
    if max_val == min_val:
        return {k: 0.0 for k in levels}
    return {k: (v - min_val) / (max_val - min_val) for k, v in levels.items()}

ICONS = {
    'FM':   '🟠',
    'NOAA': '🟢',
    'EMS':  '⚪',
    'LTE':  '🔴',
    'ADSB': '⚡',
}

# SDR setup
sdr = RtlSdr()
sdr.sample_rate = 2.4e6
sdr.gain = 40

smoother = BandSmoother(alpha=0.15)

print("Starting — press Ctrl+C to stop")
time.sleep(1)

try:
    while True:
        all_levels = {}

        # Scan each band center frequency
        scan_freqs = {
            'FM':   98e6,
            'NOAA': 137.5e6,
            'EMS':  160e6,
            'LTE':  800e6,
            'ADSB': 1090e6,
        }

        for band, freq in scan_freqs.items():
            sdr.center_freq = freq
            samples = sdr.read_samples(64 * 1024)
            fft_vals = np.abs(np.fft.fftshift(np.fft.fft(samples))) ** 2
            freqs = np.fft.fftshift(np.fft.fftfreq(
                len(samples), 1/2.4e6)) + freq
            band_levels = get_band_levels(fft_vals, freqs)
            all_levels[band] = band_levels.get(band, 0.0)
            sdr.center_freq = freq
    samples = sdr.read_samples(64 * 1024)
    fft_vals = np.abs(np.fft.fft(samples)) ** 2
    power = float(np.mean(fft_vals))
    return np.log10(power + 1)

        normalized = {}
        for band in BANDS:
             normalized[band['name']] = get_relative_level(
             band['name'], 
            raw[band['name']]
        )
        smoothed = smoother.update(normalized)

        os.system('clear')
        print("Campus Spectrum Display — LIVE\n")
        for band, level in smoothed.items():
            bar = '█' * int(level * 40)
            print(f"{ICONS[band]} {band:6} {bar:<40} {level:.2f}")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    sdr.close()
    print("SDR closed.")
