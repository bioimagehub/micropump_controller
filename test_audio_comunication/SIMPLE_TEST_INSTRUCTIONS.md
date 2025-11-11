# Two-PC Audio Diagnostic Test

## What This Does

These two simple scripts help you find the **best frequencies** for your specific setup:

- **`simple_tone_generator.py`** - Plays tones at many different frequencies (SENDER)
- **`simple_audio_listener.py`** - Shows exactly what frequencies are heard (RECEIVER)

**No filtering, no protocol - just raw audio testing!**

---

## How to Run

### Step 1: Setup RECEIVER First

**On RECEIVER computer:**
```bash
cd test_audio_comunication
python simple_audio_listener.py
```

- Select your microphone input device
- Wait for "LISTENING..." message
- Keep this running!

---

### Step 2: Run SENDER

**On SENDER computer (in a different terminal or different PC):**
```bash
cd test_audio_comunication  
python simple_tone_generator.py
```

- Press Enter to start
- Watch SENDER play different tones
- Watch RECEIVER display detected frequencies

---

## What to Look For

### On RECEIVER Output

You should see output like this for each tone:

```
[Chunk 5] Recording 1.0s...
  RMS: 0.0234  |  Max: 0.1245
  Top frequencies detected:
    1.  1200.5 Hz  (magnitude:    450000)
    2.  2401.2 Hz  (magnitude:     12000)
    3.   300.8 Hz  (magnitude:      5000)
```

**Good signs:**
- ✓ Detected frequency matches what SENDER is playing (±50 Hz)
- ✓ High magnitude values (>100,000) for the tone
- ✓ Clear peak at expected frequency

**Bad signs:**
- ✗ Wrong frequency detected (speaker/mic issue)
- ✗ Very low magnitude (<10,000) - volume too low
- ✗ No clear peak - too much noise

---

## Frequency Test Results

Fill this out as you go:

| Frequency | Detected? | Peak Magnitude | Notes |
|-----------|-----------|----------------|-------|
| 300 Hz    | ☐ Yes ☐ No | __________ | _____________ |
| 500 Hz    | ☐ Yes ☐ No | __________ | _____________ |
| 700 Hz    | ☐ Yes ☐ No | __________ | _____________ |
| 1000 Hz   | ☐ Yes ☐ No | __________ | _____________ |
| **1200 Hz** | ☐ Yes ☐ No | __________ | **FSK Mark** |
| 1500 Hz   | ☐ Yes ☐ No | __________ | _____________ |
| **1800 Hz** | ☐ Yes ☐ No | __________ | **FSK Space** |
| 2000 Hz   | ☐ Yes ☐ No | __________ | _____________ |
| **2400 Hz** | ☐ Yes ☐ No | __________ | **FSK Preamble** |
| 3000 Hz   | ☐ Yes ☐ No | __________ | _____________ |
| 4000 Hz   | ☐ Yes ☐ No | __________ | _____________ |

---

## Troubleshooting

### RECEIVER shows very low magnitudes (<1000)
- Increase volume on SENDER computer (try 80%)
- Move speaker closer to microphone (<1 meter)
- Check microphone is not muted

### RECEIVER shows wrong frequencies
- Background noise is too loud
- Move to quieter location
- Point speaker directly at microphone

### RECEIVER shows no clear peaks
- Microphone might not be working
- Check Windows sound settings
- Try different microphone device

### High frequencies (2400+ Hz) not detected
- **This is the key finding!**
- Some speaker/mic combos don't transmit high frequencies well
- Solution: Use lower frequencies for FSK protocol

---

## Next Steps Based on Results

### If 1200, 1800, 2400 Hz all work well:
✓ **FSK protocol is fine as-is!** The issue might be elsewhere.

### If 2400 Hz fails but 1200/1800 work:
📝 **Adjust preamble frequency** in `audio_protocol.py`:
```python
preamble_freq: int = 1500  # Changed from 2400
```

### If only low frequencies work (500-1000 Hz):
📝 **Adjust ALL frequencies** in `audio_protocol.py`:
```python
mark_freq: int = 700       # Changed from 1200
space_freq: int = 1000     # Changed from 1800  
preamble_freq: int = 1400  # Changed from 2400
```

### If NO frequencies work:
⚠️ **Hardware issue** - check:
- Microphone permissions in Windows
- Volume levels (both PCs)
- Physical speaker/mic positioning
- Try different audio devices

---

## Example Output

**GOOD RESULT:**
```
🔊 FSK Preamble - 2400 Hz
   Playing 2400 Hz for 1 second...
   ✓ Done

[Chunk 12] Recording 1.0s...
  RMS: 0.0456  |  Max: 0.2134
  Top frequencies detected:
    1.  2399.8 Hz  (magnitude:    890000)  ← Perfect!
    2.   120.3 Hz  (magnitude:      4500)
```

**BAD RESULT (2400 Hz not transmitting):**
```
🔊 FSK Preamble - 2400 Hz
   Playing 2400 Hz for 1 second...
   ✓ Done

[Chunk 12] Recording 1.0s...
  RMS: 0.0023  |  Max: 0.0145
  Top frequencies detected:
    1.   120.5 Hz  (magnitude:      8000)  ← Just noise!
    2.   300.2 Hz  (magnitude:      5000)
```

---

## Quick Reference

**Start RECEIVER:** `python simple_audio_listener.py`  
**Start SENDER:** `python simple_tone_generator.py`  
**Stop either:** Press `Ctrl+C`

Position: Speaker <1 meter from microphone, pointed directly at it  
Volume: 60-80% on sender  
Environment: Quiet room preferred

---

Report back what frequencies worked! 🎧
