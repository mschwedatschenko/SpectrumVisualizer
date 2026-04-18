import time
import random
import os

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

COLORS = {
    'FM':   '🟠',
    'NOAA': '🟢',
    'EMS':  '⚪',
    'LTE':  '🔴',
    'ADSB': '⚡',
}

smoother = BandSmoother(alpha=0.1)

while True:
    os.system('clear')
    
    fake_levels = {
        'FM':   random.uniform(0.6, 0.9),
        'NOAA': random.uniform(0.0, 0.1),
        'EMS':  random.uniform(0.0, 0.3),
        'LTE':  random.uniform(0.3, 0.6),
        'ADSB': random.uniform(0.0, 0.05),
    }
    
    smoothed = smoother.update(fake_levels)
    
    print("Campus Spectrum Display — live band levels\n")
    for band, level in smoothed.items():
        bar = '█' * int(level * 40)
        print(f"{COLORS[band]} {band:6} {bar:<40} {level:.2f}")
    
    print("\n(simulated data — replace with real SDR input later)")
    time.sleep(0.1)
