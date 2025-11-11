# Two-PC Audio Communication Test Instructions

## Setup Requirements
- Two PCs physically close to each other (within ~1 meter)
- Both PCs have speakers/headphones for audio output
- Both PCs have microphones (built-in or headset)
- Quiet room for best results

## Step-by-Step Instructions

### PC1 (Receiver - Start This First)
1. Open PowerShell in `c:\git\micropump_controller`
2. Run:
   ```powershell
   C:\Program_files\UV\uv.exe run python test_audio_comunication\two_pc_test.py receiver
   ```
3. Wait for audio hardware test to complete
4. Watch for status messages - it will show:
   - "- silence" when no audio detected
   - "~ weak audio" when faint sounds detected
   - "🔊 SOUND DETECTED!" when loud sounds detected

### PC2 (Sender - Start After Receiver is Ready)
1. Open PowerShell in `c:\git\micropump_controller`
2. Run:
   ```powershell
   C:\Program_files\UV\uv.exe run python test_audio_comunication\two_pc_test.py sender
   ```
3. Wait for audio hardware test (you should hear a beep)
4. Press Enter when receiver PC is ready
5. The sender will play the PING signal

## What to Watch For

### On RECEIVER PC:
- You should see "🔊 SOUND DETECTED!" when sender plays audio
- Debug output will show detected frequencies
- Should decode the PING command

### On SENDER PC:
- You'll hear beeps when sending commands
- Watch for PONG response from receiver

## Troubleshooting

### No Sound Detected on Receiver:
- **Increase sender volume** - turn up PC2's volume to maximum
- **Move PCs closer** - ideally within 30cm of each other
- **Reduce background noise** - close windows, turn off fans
- **Check microphone** - make sure receiver isn't muted
- **Position speakers** - point PC2's speakers at PC1's microphone

### Sound Detected But Not Decoded:
- **Too much ambient noise** - try quieter environment
- **Volume too high/low** - causes distortion or weak signal
- **Interference** - other sounds in the room

### Optimal Setup:
1. Place PC2's speakers very close to PC1's microphone (~10-20cm)
2. Set PC2 volume to 70-80% (not maximum - can cause distortion)
3. Test in quiet room
4. Use external speakers if available (louder than laptop speakers)

## Debug Output Explained

```
Listening... (30s remaining, chunk #1)
🔊 SOUND DETECTED! max=0.0523, rms=0.0142
  [DEBUG] Scanning for preamble (2400 Hz)...
  [DEBUG] pos=0.50s: freq=2398Hz, power=0.0156
  [DEBUG] ✓ Preamble found at 0.50s!
  [DEBUG] Decoding command bits...
  [DEBUG] bit 0: freq=1205Hz, power=0.0145 → 0 (mark)
  [DEBUG] bit 1: freq=1795Hz, power=0.0138 → 1 (space)
  ...
✓ DECODED: PING
```

This shows:
- Sound was detected
- Preamble (sync tone) was found at 2400 Hz
- Individual bits were decoded at 1200 Hz (0) and 1800 Hz (1)
- Command successfully decoded as PING

## Expected Timeline

1. **Receiver starts**: Audio test (~10 seconds)
2. **Sender starts**: Audio test (~10 seconds)
3. **Test 1 - PING/PONG**: 
   - Sender plays PING (~1.5s tone)
   - Receiver detects and decodes PING
   - Receiver plays PONG (~1.5s tone)
   - Sender detects and decodes PONG
4. **Test 2 - CAPTURE/DONE**:
   - Similar process with different commands

Total test time: ~2-3 minutes if successful
