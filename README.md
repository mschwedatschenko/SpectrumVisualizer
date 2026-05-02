# Campus Spectrum Display

A light art installation that visualizes the invisible radio frequency environment of WPI's campus in real time. A software-defined radio continuously samples the electromagnetic spectrum — FM radio, NOAA weather satellites, EMS pagers, cellular LTE, and aircraft transponders — and maps each band's activity to a glowing circle on an LED matrix panel mounted behind frosted acrylic.

The piece is never the same twice. It looks different at 8am than at midnight, during finals week than over break. It is a portrait of a place rendered in light, drawn from signals that have always been there but that nobody has ever seen.

---

## Hardware

| Component | Part |
|-----------|------|
| SDR Receiver | RTL-SDR Blog V4 (500 kHz – 1.766 GHz) |
| Single Board Computer | Raspberry Pi 4 (2GB) |
| LED Display | 64x32 RGB LED Matrix Panel (HUB75, P4) |
| LED Driver | Adafruit RGB Matrix Bonnet (#3211) |
| Power Supply | 5V 4A |
| Diffuser | 3mm frosted acrylic sheet |

---

## Frequency Bands

| Band | Frequency | Color | Character |
|------|-----------|-------|-----------|
| FM Radio | 88–108 MHz | Warm amber | Constant, stable — the background hum of the city |
| NOAA Weather Satellites | 137 MHz | Teal | Slow passes overhead a few times daily |
| EMS / Hospital Pagers | 150–170 MHz | Cool white | Sharp bursts from UMass Medical nearby |
| Cellular LTE | 700–900 MHz | Deep red | Steady pulse that rises with campus activity |
| ADS-B Aircraft | 1090 MHz | Bright white | Sudden flares when planes pass overhead, then silence |

---

## How It Works

### 1. SDR Pipeline

The RTL-SDR dongle continuously tunes to each band's center frequency and captures raw IQ (in-phase/quadrature) samples. IQ samples represent the radio wave as a complex number stream — the raw electromagnetic signal digitized.

### 2. Fast Fourier Transform (FFT)

Raw IQ samples are passed through `numpy.fft.fft()`, which converts the time-domain signal into the frequency domain — essentially decomposing the noisy jumble of all signals into individual frequency components and their power levels. The result is a power-vs-frequency array where active signals appear as peaks.

```python
fft_vals = np.abs(np.fft.fft(samples)) ** 2
power = float(np.mean(fft_vals))
return np.log10(power + 1)  # log scale compresses dynamic range
```

Log scale is used because RF power varies over enormous ranges — FM might be 1,000,000x stronger than ADS-B. Log scale compresses that into a manageable range for visualization.

### 3. Per-Band Relative Normalization

Rather than normalizing all bands against each other (which would crush weak signals like ADS-B against strong ones like FM), each band maintains its own rolling history of the last 50 readings and normalizes relative to its own min/max range:

```python
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
```

This means every band shows meaningful activity relative to its own baseline — a quiet ADS-B band will still flare visibly when a plane passes, even though its absolute power level is far below FM.

### 4. Exponential Smoothing

Raw FFT output is noisy and jumpy. An exponential moving average smooths the signal so LED transitions are fluid rather than flickering:

```python
smoothed[name] = alpha * new_val + (1 - alpha) * smoothed[name]
```

`alpha = 0.2` means each new reading contributes 20% to the output and the previous smoothed value contributes 80%. Lower alpha = smoother but slower to react. Higher alpha = more reactive but flickery.

### 5. Circular Glow Rendering

Each band is rendered as a circular glow on the LED matrix. The radius and brightness of the circle scale with signal level. Brightness falls off from center to edge using a power curve for a soft, organic look:

```python
dist = (dx**2 + dy**2) ** 0.5
falloff = (1 - (dist / (max_radius + 0.001))) ** 1.5
brightness = level * falloff
```

Bands are drawn into a virtual pixel buffer before being sent to the display, which allows overlapping bands to blend their colors additively.

### 6. Pixel Server

Because the Python bindings for the RGB matrix library require a compiled C extension that is difficult to build on newer Python versions, this project uses a custom C pixel server (`pixel-server.cc`) that reads pixel coordinates and colors from stdin:

```
x y r g b\n       # set pixel at (x,y) to color (r,g,b)
-1 -1 0 0 0\n     # swap frame buffer (display current frame)
```

Python communicates with it via `subprocess.Popen` with `stdin=subprocess.PIPE`, writing pixel data as text lines. This approach completely bypasses the Python binding issue and is actually faster for bulk pixel writes.

---

## Installation

### Prerequisites

```bash
sudo apt update
sudo apt install libusb-1.0-0-dev cmake pkg-config build-essential git -y
```

### RTL-SDR V4 Drivers

The V4 requires custom drivers — the stock `librtlsdr` does not include V4-specific functions:

```bash
git clone https://github.com/rtlsdrblog/rtl-sdr-blog
cd rtl-sdr-blog
mkdir build && cd build
cmake ..
make
sudo make install
sudo ldconfig
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo reboot
```

After reboot, verify with:
```bash
rtl_test
```

You should see `RTL-SDR Blog V4 Detected`.

### Python Dependencies

```bash
sudo pip3 install pyrtlsdr numpy --break-system-packages
```

The V4 requires two patches to pyrtlsdr to remove symbols not present in the custom library:

```bash
# Patch 1 — remove missing symbols
sudo sed -i '/rtlsdr_set_dithering\|rtlsdr_set_gpio_output\|rtlsdr_set_gpio_input\|rtlsdr_set_gpio_bit\|rtlsdr_get_gpio_bit\|rtlsdr_set_gpio_byte\|rtlsdr_get_gpio_byte\|rtlsdr_set_gpio_status\|rtlsdr_set_and_get_tuner_bandwidth/d' \
    /usr/local/lib/python3.13/dist-packages/rtlsdr/librtlsdr.py

# Patch 2 — stub out dithering call
sudo sed -i 's/result = librtlsdr.rtlsdr_set_dithering(self.dev_p, int(dithering_enabled))/result = 0  # not supported/' \
    /usr/local/lib/python3.13/dist-packages/rtlsdr/rtlsdr.py
```

### RGB Matrix Library

```bash
# Disable Pi sound module (conflicts with LED library)
echo 'blacklist snd_bcm2835' | sudo tee /etc/modprobe.d/blacklist-rgb-matrix.conf
sudo reboot

# Clone and build
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
make
```

### Build the Pixel Server

```bash
cd ~/rpi-rgb-led-matrix
g++ -O3 -o pixel-server pixel-server.cc \
    -I./include \
    -L./lib \
    -lrgbmatrix -lrt -lm -lpthread
```

---

## Running

```bash
sudo python3 main.py
```

`sudo` is required for direct GPIO hardware access.

**Note:** The first ~30 seconds are a calibration period. Each band builds a history of 50 readings before relative normalization kicks in. During this time all bands display at half brightness. After calibration, each band responds to its own signal activity independently.

Press `Ctrl+C` to stop cleanly — the display will clear and the SDR will close properly.

---

## Auto-Start on Boot

To run automatically when the Pi powers on:

```bash
sudo nano /etc/systemd/system/spectrum.service
```

Paste:
```
[Unit]
Description=Campus Spectrum Display
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/mary/SpectrumVisualizer/main.py
WorkingDirectory=/home/mary/SpectrumVisualizer
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable spectrum
sudo systemctl start spectrum
```

---

## Project Structure

```
campus-spectrum-display/
├── main.py              # Main pipeline — SDR → FFT → LED
├── pixel-server.cc      # C program that drives the LED matrix
└── README.md
```

---

## Wiring

```
Raspberry Pi 4
    └── Adafruit RGB Matrix Bonnet (GPIO header, no soldering)
            ├── HUB75 ribbon cable → LED Matrix (INPUT side)
            └── 5V 4A power supply → green screw terminals

RTL-SDR V4 dongle → USB port on Pi
Antenna → SMA connector on dongle
```

**Important:** Connect the ribbon cable to the INPUT side of the matrix, not the output. Connect the 5V supply to the bonnet's screw terminals — the Pi cannot supply enough current for the matrix.

---

## Acknowledgements

- [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) — RGB matrix driver
- [rtlsdrblog/rtl-sdr-blog](https://github.com/rtlsdrblog/rtl-sdr-blog) — RTL-SDR V4 drivers
- [roger-/pyrtlsdr](https://github.com/roger-/pyrtlsdr) — Python SDR bindings

---

*Built as a Humanities Capstone light art installation at Worcester Polytechnic Institute, 2025.*
