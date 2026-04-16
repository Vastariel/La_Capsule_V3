# 🧪 GPIO & Pico Testing - Complete Guide

## Overview

Three levels of testing for GPIO and Pico components:

| Level | Command | Time | Purpose |
|-------|---------|------|---------|
| **Quick** | `python3 gpio.py` | 2 min | Verify module loads |
| **Quick** | `python3 pico.py` | 2 min | Verify module loads |
| **FULL** | `python3 tests/test_gpio_interactive.py` | 20-25 min | Complete GPIO testing |
| **FULL** | `python3 tests/test_pico_interactive.py` | 15-20 min | Complete Pico testing |

---

## What Were the Problems?

### Before (Old gpio.py)
```python
if __name__ == "__main__":
    print("GPIO module - use with main.py")
```
❌ Not a real test
❌ No actual testing
❌ No diagnostics
❌ No feedback

### After (New Tests)
✅ Real hardware testing
✅ Interactive diagnostics
✅ Live data visualization
✅ Detailed results report
✅ Troubleshooting guidance

---

## How to Use GPIO Interactive Test

### Start Test
```bash
cd ~/La_Capsule_V3/bridge_python
python3 tests/test_gpio_interactive.py
```

### What Happens

**Step 1: Configuration Check**
```
ℹ Configuration loaded
  - Red LEDs: [24, 27, 25, 21]
  - Green LEDs: [18, 12]
  - Leviers: [16, 26, 22]
  - Buttons: [6, 13, 11, 5, 20, 7, 23, 8, 4, 19]
```

**Step 2: Choose GPIO Mode**
```
✓ GPIO utilise BCM GPIO local
  or
✓ GPIO factory connecté à 192.168.1.56 via pigpio
```

**Step 3: Red LEDs Test** (5 min, 4 LEDs)
```
[1] GPIO 24 → ON → OFF ✓
[2] GPIO 27 → ON → OFF ✓
[3] GPIO 25 → ON → OFF ✓
[4] GPIO 21 → ON → OFF ✓

✓ 4/4 red LEDs working
```

**Step 4: Green LEDs Test** (2.5 min, 2 LEDs)
```
[1] GPIO 18 → ON → OFF ✓
[2] GPIO 12 → ON → OFF ✓

✓ 2/2 green LEDs working
```

**Step 5: LED Sequence Test** (3 sec)
```
All LEDs ON for 3 seconds...
All LEDs OFF...
✓ All LEDs sequence completed
```

**Step 6: Levier Switches Test** (20 sec)
```
Found 3 levier switches:
  - GPIO 16: SAS
  - GPIO 26: RCS
  - GPIO 22: THROTTLE_CONTROL

⏱ Monitoring levier states for 20 seconds...
(Move switches to test)

⏱ [At 5.2s] GPIO 16 (SAS): PRESSED
⏱ [At 10.5s] GPIO 16 (SAS): RELEASED
⏱ [At 15.3s] GPIO 26 (RCS): PRESSED
⏱ [At 18.7s] GPIO 26 (RCS): RELEASED

✓ 2/3 levier changes detected
```

**Step 7: Buttons Test** (30 sec)
```
Found 10 momentary buttons:
  - GPIO 6: HEAT_SHIELD
  - GPIO 13: PARACHUTE
  ... (more buttons)

⏱ Monitoring button presses for 30 seconds...
(Press buttons to test)

✓ GPIO 6 (HEAT_SHIELD): PRESSED
✓ GPIO 13 (PARACHUTE): PRESSED
✓ GPIO 11 (LANDING_GEAR): PRESSED

✓ 3/10 buttons detected (5 presses total)
```

**Step 8: Test Summary**
```
============================================================
🧪 TEST SUMMARY
============================================================
✓ Red LEDs: 4/4 working
✓ Green LEDs: 2/2 working
✓ Levier Switches: 2/3 detected
✓ Buttons: 3/10 detected (5 presses total)

============================================================
✅ ALL TESTS PASSED
✓ GPIO cleaned up
```

---

## How to Use Pico Interactive Test

### Start Test
```bash
python3 tests/test_pico_interactive.py
```

### What Happens

**Step 1: Configuration Check**
```
Port: /dev/ttyACM0
Baud: 115200
Smoothing Window: 10 samples
```

**Step 2: Connection Test** (1 min)
```
Connection details:
  Port: /dev/ttyACM0
  Connected: True
  Errors: 0

✓ Pico is connected
```

**Step 3: ADC Channels Monitoring** (15 sec)
```
Reading ADC channels for 15 seconds...
(Rotate potentiometer to see values change)

Time     │ CH0(Raw)     │ CH1(Raw)     │ CH2(Raw)     │ CH3(Raw)
------
0s       │    500 ███░░ │     50 ░░░░░ │    100 ░░░░░ │    150 ░░░░░
0.5s     │    510 ███░░ │     50 ░░░░░ │    100 ░░░░░ │    150 ░░░░░
...
14.5s    │   2800 ██████│     50 ░░░░░ │    100 ░░░░░ │    150 ░░░░░

Statistics:
Channel 0:
  Reads: 30
  Min: 500
  Max: 2800
  Range: 2300
✓ Channel 0: data is changing

Channel 1:
  Reads: 30
  Min: 50
  Max: 50
  Range: 0
⚠ Channel 1: values not changing much
```

**Step 4: Smoothing Test** (10 sec)
```
Comparing RAW vs SMOOTHED values (Channel 0)
Smoothing window: 10 samples

Time     Raw      Smoothed    Difference
----
0.0s  ↑  500      500.0       0.0
0.1s  ↑  510      502.5       7.5
0.2s  ↑  520      507.5       12.5
...
9.8s  ↓  2300     2250.0      50.0
9.9s  ↓  2290     2260.0      30.0

✓ Smoothing test completed
```

**Step 5: Throttle Conversion** (2 sec)
```
Reading throttle potentiometer...
(Channel 0 is throttle)

Raw(0-4095)    Normalized(0-1)    Percent(0-100%)
---
500            0.1221             ████████░░░░░░░░░░░░ 12.2%
510            0.1245             ████████░░░░░░░░░░░░ 12.5%
520            0.1270             ████████░░░░░░░░░░░░ 12.7%
...
2800           0.6837             ████████████████░░░░░ 68.4%

✓ Throttle conversion working
```

**Step 6: Test Summary**
```
============================================================
🧪 TEST SUMMARY
============================================================
✓ Pico connection successful
  Port: /dev/ttyACM0
  Errors: 0

============================================================
```

---

## Reading Test Results

### ✓ Green (Passing)
```
✓ 4/4 red LEDs working
```
**Meaning**: All 4 red LEDs responded correctly
**Action**: Continue to next component

### ⚠ Yellow (Partial)
```
⚠ 2/3 levier changes detected
```
**Meaning**: 2 out of 3 switches detected, 1 didn't respond
**Action**: Check wiring for GPIO 22, verify pull-up resistor

### ✗ Red (Failing)
```
✗ Pico not connected
```
**Meaning**: Pico not detected on USB
**Action**: See troubleshooting section

### → Arrow (Direction indicator)
```
⏱ [At 5.2s] GPIO 16 (SAS): PRESSED ↑
```
**↑ Up**: Value changed from 0 to 1 (button/switch pressed)
**↓ Down**: Value changed from 1 to 0 (button/switch released)
**= Equal**: Value unchanged

---

## Common Test Scenarios

### Scenario 1: All LEDs Working, No Buttons
```
✓ Red LEDs: 4/4 working
✓ Green LEDs: 2/2 working
⚠ Levier Switches: 0/3 detected
⚠ Buttons: 0/10 detected

Diagnosis: Button GPIO pins not connected or misconfigured
Action: Check GPIO numbers in config.json match wiring
```

### Scenario 2: Partial LED Response
```
✓ Red LEDs: 3/4 working
  └ GPIO 21: ERROR

Diagnosis: GPIO 21 LED not responding
Action: Check LED wiring on GPIO 21, test with multimeter
```

### Scenario 3: Pico Has Noise
```
⚠ Channel 0: values not changing much
  Min: 500
  Max: 505
  Range: 5

Diagnosis: ADC sees noise, not actual potentiometer movement
Action: Rotate potentiometer more to see bigger changes
        or check potentiometer is connected
```

### Scenario 4: Only Detecting Presses
```
✓ Buttons: 3/10 detected (5 presses total)

✓ GPIO 6 (HEAT_SHIELD): PRESSED (2x)
✓ GPIO 13 (PARACHUTE): PRESSED (2x)
✓ GPIO 11 (LANDING_GEAR): PRESSED (1x)

Diagnosis: Only tested 3 buttons, others not pressed
Action: Press more buttons during test
        or verify button wiring
```

---

## Troubleshooting Failed Tests

### LED Won't Light
**Problem**: GPIO 24 shows "ERROR"

**Diagnostics**:
1. Check physical connection
2. Test LED independently:
   ```bash
   # Manual GPIO test
   python3 -c "
   from gpiozero import LED
   led = LED(24)
   led.on()
   print('LED should be ON')
   input('Press Enter...')
   led.off()
   "
   ```
3. Check for reversed LED polarity
4. Verify resistor is present

### Button Not Detected
**Problem**: Levier GPIO 22 not responding

**Diagnostics**:
1. Check pin number in config.json
2. Test with gpiozero:
   ```bash
   python3 -c "
   from gpiozero import Button
   btn = Button(22, pull_up=True)
   print('Press button...')
   while True:
       print(f'Button: {btn.is_pressed}')
   "
   ```
3. Verify pull-up resistor is connected
4. Check for loose wiring

### Pico Not Found
**Problem**: "✗ Pico not connected"

**Diagnostics**:
```bash
# Check USB
ls /dev/ttyACM*
# Should show /dev/ttyACM0

# Check dmesg
dmesg | tail -20
# Look for "RP2040" or similar

# Check permissions
ls -la /dev/ttyACM0
# Should be readable by user

# Fix permissions
sudo usermod -a -G dialout $USER
newgrp dialout
```

### ADC Reads Garbage
**Problem**: Pico connected but values are 0 or 4095

**Diagnostics**:
1. Verify Pico firmware has picod installed
2. Check ADC not shorted
3. Test individual code:
   ```bash
   python3 -c "
   import picod
   pico = picod.pico()
   for i in range(10):
       status, ch, val = pico.adc_read(0)
       print(f'Status: {status}, Value: {val}')
   "
   ```

---

## Test Performance Expectations

| Component | Ideal | Acceptable | Problem |
|-----------|-------|-----------|---------|
| LED response | <1ms | <10ms | >100ms |
| Button press | <50ms | <200ms | >1000ms |
| ADC read | 5-10ms | <50ms | >100ms |
| Smoothing | 50ms | 100ms | >500ms |

---

## Next Steps After Testing

### If All Tests Pass ✅
1. System is ready for deployment
2. Run `python3 main.py` to start bridge
3. Connect Godot client
4. Test full workflow

### If Some Tests Fail ⚠️
1. Fix identified issues
2. Re-run tests to verify
3. Check troubleshooting section
4. Consult hardware documentation

### If Most Tests Fail ❌
1. Verify GPIO pins are correct
2. Check hardware connections
3. Test with simple Python code
4. Consult community/documentation

---

## Testing Checklist

- [ ] Configuration test passes
- [ ] GPIO quick test shows info
- [ ] Pico quick test shows info
- [ ] GPIO interactive test: all LEDs working
- [ ] GPIO interactive test: buttons detected
- [ ] Pico interactive test: connected
- [ ] Pico interactive test: ADC channels responsive
- [ ] Pico throttle conversion working
- [ ] KSP connection test successful
- [ ] Godot client connects to WebSocket

**Everything checked? You're ready for deployment!**

---

See [QUICKSTART.md](QUICKSTART.md) for system setup
See [ACTIONS.md](ACTIONS.md) for testing schedule
