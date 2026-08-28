# Campus Spectrum Display

LED panel that shows radio activity around WPI. An RTL-SDR hops through a few bands and each one gets a glowing circle on a 64x32 matrix. Frosted acrylic in front so it looks like a glow instead of a grid of pixels.

![visualizer pic](https://github.com/mschwedatschenko/SpectrumVisualizer/blob/main/images/visualizer.jpg)

## Hardware

- RTL-SDR Blog V4
- Raspberry Pi 4 (2GB)
- 64x32 RGB LED matrix, HUB75, P4
- Adafruit RGB Matrix Bonnet (#3211)
- 5V 4A supply
- Frosted acrylic sheet

## Bands

- **FM** 88–108 MHz. Amber. Pretty much always on.
- **NOAA weather sats** 137 MHz. Teal. A few slow passes a day.
- **EMS / hospital pagers** 150–170 MHz. Lavender. Bursts from UMass Medical.
- **LTE** 700–900 MHz. Red. Follows how busy campus is.
- **ADS-B** 1090 MHz. White. Flares when a plane goes over.

## How it works

The dongle tunes to each band, grabs IQ samples, FFT, mean power, log10. FM is wildly stronger than ADS-B so every band keeps its own rolling history (last 50 readings) and normalizes against itself. Otherwise the planes would never show up.

There's also an exponential moving average (`alpha = 0.2`) because raw FFT power jumps around a lot and looks terrible on LEDs.

Circles scale with signal level. Falloff from the center is just `dist ** 1.5`. Overlapping colors add together in a pixel buffer, then the whole frame gets sent to the display.

Python bindings for the matrix library are a pain to build on newer Python, so pixel writes go to a small C program (`pixel-server.cc`) over stdin:

```
x y r g b          set a pixel
-1 -1 0 0 0        flip the buffer
```

## Setup

```bash
sudo apt update
sudo apt install libusb-1.0-0-dev cmake pkg-config build-essential git -y
```

V4 needs the blog drivers. Stock `librtlsdr` will not work:

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

After reboot, `rtl_test` should print `RTL-SDR Blog V4 Detected`.

```bash
sudo pip3 install pyrtlsdr numpy --break-system-packages
```

## Run

```bash
sudo python3 main.py
```

Needs sudo for GPIO.

First ~30 seconds everything sits at half brightness while each band fills its history. After that they start moving independently. Ctrl+C stops it and clears the panel.

## Wiring

Bonnet sits on the Pi GPIO header, no soldering. Ribbon cable goes to the **input** side of the matrix (output does nothing). 5V 4A into the bonnet screw terminals — don't try to power the panel off the Pi.

SDR in a USB port, antenna on the SMA.

## Stuff this uses

- [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix)
- [rtlsdrblog/rtl-sdr-blog](https://github.com/rtlsdrblog/rtl-sdr-blog)
- [roger-/pyrtlsdr](https://github.com/roger-/pyrtlsdr)
