import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rtlsdr import RtlSdr

sdr = RtlSdr()
sdr.sample_rate = 2.4e6
sdr.center_freq = 98e6
sdr.gain = 40

samples = sdr.read_samples(256 * 1024)
sample_rate = 2.4e6
center_freq = 98e6
sdr.close()

fft_vals = np.abs(np.fft.fftshift(np.fft.fft(samples))) ** 2
freqs = np.fft.fftshift(np.fft.fftfreq(len(samples), 1/sample_rate)) + center_freq

plt.figure(figsize=(10,4))
plt.plot(freqs/1e6, 10*np.log10(fft_vals))
plt.xlabel("Frequency (MHz)")
plt.ylabel("Power (dB)")
plt.title("FM Band Spectrum")
plt.grid(True, alpha=0.3)
plt.savefig("spectrum.png")
sdr.close()
print("Saved spectrum.png")
