import numpy as np

def get_band_levels(fft_vals, freqs):
    bands = {
        'FM':    (88e6,  108e6),
        'NOAA':  (137e6, 138e6),
        'EMS':   (150e6, 170e6),
        'LTE':   (700e6, 900e6),
        'ADSB':  (1089e6, 1091e6),
    }
    levels = {}
    for name, (low, high) in bands.items():
        mask = (freqs >= low) & (freqs <= high)
        if mask.any():
            levels[name] = float(np.mean(fft_vals[mask]))
        else:
            levels[name] = 0.0
    return levels
