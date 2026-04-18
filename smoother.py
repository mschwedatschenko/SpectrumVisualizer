import time
import random
import numpy as np

class BandSmoother:
    def __init__(self, alpha=0.1):
        self.alpha = alpha  # lower = smoother, higher = more reactive
        self.values = {}

    def update(self, levels):
        for band, value in levels.items():
            if band not in self.values:
                self.values[band] = value
            else:
                # Exponential moving average
                self.values[band] = (self.alpha * value +
                                    (1 - self.alpha) * self.values[band])
        return self.values

smoother = BandSmoother(alpha=0.1)

while True:
    # Fake band levels — replace with real FFT output later
    fake_levels = {
        'FM':   random.uniform(0.6, 0.9),
        'NOAA': random.uniform(0.0, 0.1),
        'EMS':  random.uniform(0.0, 0.3),
        'LTE':  random.uniform(0.3, 0.6),
        'ADSB': random.uniform(0.0, 0.05),
    }
    
    smoothed = smoother.update(fake_levels)
    
    # Print as a simple bar visualization
    for band, level in smoothed.items():
        bar = '█' * int(level * 30)
        print(f"{band:6} {bar:<30} {level:.2f}")
    print("---")
    time.sleep(0.1)
