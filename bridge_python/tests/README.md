# Test Suite for bridge_python

Complete testing infrastructure for GPIO, Pico, and configuration components.

## Quick Tests (Quick Check)

Use these for quick validation:

```bash
# Quick GPIO check
python3 gpio.py

# Quick Pico check
python3 pico.py

# Quick config validation
python3 -m pytest tests/test_configuration.py -v
```

## Interactive Tests (Full Hardware Validation)

For comprehensive hardware testing with live data and diagnostics:

### GPIO Interactive Test

Test all GPIO operations interactively:

```bash
python3 tests/test_gpio_interactive.py
```

**What it tests:**
- ✓ **Red LEDs**: Lights each LED individually (5 sec ON, 2 sec OFF)
- ✓ **Green LEDs**: Lights each LED individually 
- ✓ **Leviers**: Monitors switch states in real-time (20 sec)
- ✓ **Buttons**: Monitors button presses in real-time (30 sec)
- ✓ **Sequence**: All LEDs on/off together
- ✓ **Summary**: Reports which components are working

**Usage:**
```bash
cd bridge_python
python3 tests/test_gpio_interactive.py

# Choose: Local or Remote GPIO
# Watch each LED light up
# Press buttons/switches when prompted
# Get detailed test results
```

**Expected Output:**
```
🧪 RED LEDs Test
Found 4 red LEDs: [24, 27, 25, 21]

Testing each LED (5 seconds ON, 2 seconds OFF)...

  [1] GPIO 24 → ON → OFF ✓
  [2] GPIO 27 → ON → OFF ✓
  [3] GPIO 25 → ON → OFF ✓
  [4] GPIO 21 → ON → OFF ✓

✓ 4/4 red LEDs working
```

### Pico ADC Interactive Test

Test Pico ADC readings interactively:

```bash
python3 tests/test_pico_interactive.py
```

**What it tests:**
- ✓ **Connection**: Verifies Pico is connected via USB
- ✓ **ADC Channels**: Reads all 4 channels with live data (15 sec)
- ✓ **Smoothing**: Compares raw vs smoothed values
- ✓ **Throttle Conversion**: Tests 0-4095 → 0.0-1.0 conversion
- ✓ **Statistics**: Min/max/range for each channel

**Usage:**
```bash
python3 tests/test_pico_interactive.py

# Check connection
# Rotate potentiometer to see values change
# Watch smoothing in action
# Get detailed statistics
```

**Expected Output:**
```
✓ Pico is connected on port: /dev/ttyACM0

Reading ADC channels for 15 seconds...

Time     │ CH0(Raw)  │ CH1(Raw)  │ CH2(Raw)  │ CH3(Raw)
------
0s      │    500 ██░░░░░░░░│    200 ░░░░░░░░░░│    100 ░░░░░░░░░░│    150 ░░░░░░░░░░
0.5s    │    520 ██░░░░░░░░│    200 ░░░░░░░░░░│    100 ░░░░░░░░░░│    150 ░░░░░░░░░░
...
```

## Unit Tests (Configuration)

Test configuration loading and validation:

```bash
python3 -m pytest tests/test_configuration.py -v
```

**What it tests:**
- ✓ Configuration file exists and is valid JSON
- ✓ All required sections present
- ✓ Network parameters configured
- ✓ GPIO pins configured
- ✓ No duplicate pins

**Usage:**
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_configuration.py::TestConfiguration::test_krpc_config -v

# Run with coverage
pytest --cov=. tests/
```

## Test Workflow

### Recommended Testing Order

1. **Start with Configuration** (5 min)
   ```bash
   python3 utils/config_loader.py
   pytest tests/test_configuration.py -v
   ```
   → Verify config.json is correct

2. **Quick Module Check** (5 min)
   ```bash
   python3 gpio.py
   python3 pico.py
   ```
   → See if modules load correctly

3. **Hardware Tests** (30-45 min)
   ```bash
   python3 tests/test_gpio_interactive.py
   python3 tests/test_pico_interactive.py
   ```
   → Test actual hardware connections

4. **System Integration** (depends on KSP)
   ```bash
   python3 main.py
   ```
   → Run full system

## Troubleshooting Test Failures

### GPIO Test Fails

**Error: "GPIO permission denied"**
```bash
# Start pigpio daemon
sudo pigpiod

# Or enable as service
sudo systemctl start pigpiod
sudo systemctl enable pigpiod
```

**Error: "GPIO factory not connected"**
```bash
# Choose LOCAL GPIO instead of REMOTE
# Or verify Raspberry Pi is running pigpiod
```

**LEDs don't light up**
- Check GPIO pin numbers in config.json match your wiring
- Check power to LEDs (3.3V rail)
- Check current-limiting resistors on LEDs
- Test with multimeter

**Buttons don't respond**
- Check GPIO pin numbers in config.json
- Check pull-up resistors (should be on Raspi board already)
- Test with: `gpio readall` (from wiringPi tools)

### Pico Test Fails

**Error: "Pico not found"**
```bash
# Check USB connection
ls /dev/ttyACM0

# If not found, check dmesg
dmesg | tail -20

# You should see something like:
# usb 1-1.1: RP2040 Board in FS mode found at 2
```

**Error: "Permission denied /dev/ttyACM0"**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
newgrp dialout

# Then disconnect/reconnect USB
```

**ADC reads as zero or garbage**
- Check Pico firmware is flashed with picod
- Try: `python3 pico.py` for quick diagnostic
- Verify ADC channels are connected
- Check Pico power supply

### Configuration Test Fails

**Error: "JSON decode error"**
```bash
# Check config.json syntax
python3 -m json.tool setup/config.json
# Should output formatted JSON without errors
```

**Error: "Missing required key"**
- Verify `setup/config.json` has all sections:
  - network
  - hardware
  - performance
  - telemetry
  - logging

## Creating Custom Tests

Add your own tests to `tests/` directory:

```python
# tests/test_custom.py
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import RASPI_IP

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        self.assertEqual(RASPI_IP, "192.168.1.56")  # Update as needed

if __name__ == '__main__':
    unittest.main()
```

Run it:
```bash
pytest tests/test_custom.py -v
```

## Test Execution Modes

### Mode 1: Quick Diagnostics (5 min)
```bash
python3 gpio.py && python3 pico.py
```

### Mode 2: Full Validation (45 min)
```bash
pytest tests/ -v                      # Config tests
python3 tests/test_gpio_interactive.py  # Hardware tests
python3 tests/test_pico_interactive.py  # Sensor tests
```

### Mode 3: Automated CI/CD (future)
```bash
pytest --cov=. --cov-report=html tests/
# Generates HTML coverage report
```

## Continuous Testing During Development

Watch for changes and re-run tests:

```bash
# Requires: pip install pytest-watch
ptw tests/

# Or manually
while true; do pytest tests/ && echo "✓" || echo "✗"; done
```

## Test Results Interpretation

### ✓ All Green
Everything is working correctly. Ready for deployment.

### ⚠ Some Yellow
Some components present but not fully responsive:
- GPIO detected but LED brightness varies
- Pico connected but ADC values noisy
- Monitor and verify hardware connections

### ✗ Red/Failed
Component not working:
- Check physical connections
- Verify configuration
- Check system logs
- See troubleshooting section

## Performance Testing

Monitor system response times:

```bash
# Add to test for benchmarks
import time

start = time.perf_counter()
# ... code to test ...
elapsed = time.perf_counter() - start
print(f"Operation took {elapsed*1000:.2f}ms")
```

Expected performance:
- GPIO read/write: <1ms
- Pico ADC read: <10ms
- Configuration load: <50ms
- WebSocket message: <5ms

---

For system architecture details, see [ARCHITECTURE.md](../ARCHITECTURE.md)
For quick start, see [QUICKSTART.md](../QUICKSTART.md)

