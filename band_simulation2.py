import numpy as np
import time
import os
from rtlsdr import RtlSdr

# Configuration for bands
BANDS = [
    {'name': 'FM',   'center': 98e6},
    {'name': 'NOAA', 'center': 137.5e6},
    {'name': 'EMS',  'center': 160e6},
    {'name': 'LTE',  'center': 800e6},
    {'name': 'ADSB', 'center': 1090e6},
]

ICONS = {
    'FM':   '🟠',
    'NOAA': '🟢',
    'EMS':  '⚪',
    'LTE':  '🔴',
    'ADSB': '⚡',
}

# Global history for relative normalization
band_history = {b['name']: [] for b in BANDS}

class BandSmoother:
    def __init__(self, alpha=0.15):
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

def get_power(freq):
    """Tunes SDR to frequency and returns log-scale average power."""
    sdr.center_freq = freq
    # Capture samples
    samples = sdr.read_samples(64 * 1024)
    # Power Spectral Density calculation
    fft_vals = np.abs(np.fft.fft(samples)) ** 2
    power = float(np.mean(fft_vals))
    # Log scale compresses the dynamic range for better visualization
    return np.log10(power + 1)

def get_relative_level(name, raw_power):
    """Normalizes power based on the min/max history of that specific band."""
    history = band_history[name]
    history.append(raw_power)
    if len(history) > 50:  # keep last 50 readings
        history.pop(0)
    
    mn = min(history)
    mx = max(history)
    
    if mx == mn:
        return 0.5
    return (raw_power - mn) / (mx - mn)

# SDR setup
sdr = RtlSdr()
sdr.sample_rate = 2.4e6
sdr.gain = 40

smoother = BandSmoother(alpha=0.2)

print("Starting Campus Spectrum Display — press Ctrl+C to stop")
time.sleep(1)

try:
    while True:
        raw_results = {}
        
        # 1. Capture raw power for all bands
        for band in BANDS:
            name = band['name']
            raw_results[name] = get_power(band['center'])

        # 2. Normalize levels relative to their own history
        normalized = {}
        for band in BANDS:
            name = band['name']
            normalized[name] = get_relative_level(name, raw_results[name])

        # 3. Apply exponential smoothing for visual stability
        smoothed = smoother.update(normalized)

        # 4. Display output
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Campus Spectrum Display — LIVE (Relative Normalization)\n")
        print(f"{'Band':<8} {'Activity Level':<42} {'Val'}")
        print("-" * 55)
        
        for name, level in smoothed.items():
            bar_length = int(level * 40)
            # Ensure bar length is within bounds
            bar_length = max(0, min(40, bar_length))
            bar = '█' * bar_length
            icon = ICONS.get(name, '📡')
            print(f"{icon} {name:5} |{bar:<40}| {level:.2f}")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    sdr.close()
    print("SDR closed.")
