# Audio-Based Communication for Airgapped Microscope Control

## Overview

This folder contains an **FSK (Frequency Shift Keying) audio modem** for communicating between:
- **Microfluidics PC** (this computer) running `cli.py`
- **Microscope PC** (airgapped computer) running `microscope_control.exe`

The system uses audio tones (like old-school modems) to send commands without any physical connection.

---

## Files

- **`audio_protocol.py`** - Core FSK modem implementation with error correction
- **`microscope_audio_test.py`** - Standalone test suite for feasibility testing
- **`build_standalone.py`** - Build script to create `.exe` for airgapped transfer
- **`requirements.txt`** - Python dependencies (sounddevice, numpy)

---

## How It Works

### FSK Protocol Features

The protocol is based on Bell 202 modem standard with safety features:

- **Two frequencies for binary data:**
  - 1200 Hz = binary 0 (mark)
  - 1800 Hz = binary 1 (space)

- **Preamble sync tone (2400 Hz for 500ms)**
  - Prevents false triggers from background speech
  - Signals "start of transmission"

- **4-bit checksum**
  - Detects corrupted transmissions
  - Auto-rejects invalid data

- **Noise immunity:**
  - Minimum tone duration (80ms) filters out speech
  - Frequency tolerance (±100 Hz) handles speaker variations
  - Minimum signal power threshold

- **Total transmission time: ~1.3 seconds per command**
  - Too long for accidental speech patterns to trigger

### Available Commands

```python
Command.CAPTURE  # Trigger image capture
Command.DONE     # Capture complete
Command.ERROR    # Capture failed
Command.PING     # Test connection
Command.PONG     # Respond to ping
```

---

## Testing on Two Computers

### Step 1: Install Dependencies (on THIS PC)

```powershell
cd test_audio_comunication
pip install -r requirements.txt
```

### Step 2: Run Feasibility Test (on THIS PC first)

```powershell
python microscope_audio_test.py
```

**Expected output:**
- Test 1: Hear system beep ✓
- Test 2: Hear 1200 Hz tone ✓
- Test 3: Clap hands, see audio detected ✓
- Test 4: Frequency detection working ✓
- Test 5: FSK protocol encode/decode ✓
- Test 6: Noise rejection working ✓

### Step 3: Transfer to Second Test PC

**Option A: Standalone Executable (Recommended)**

```powershell
# Build .exe
pip install pyinstaller
python build_standalone.py

# Copy to USB stick:
# dist/microscope_audio_test.exe
```

**Option B: Python Script (if Python installed on test PC)**

Copy to USB stick:
- `audio_protocol.py`
- `microscope_audio_test.py`
- `requirements.txt`

On test PC:
```powershell
pip install -r requirements.txt
python microscope_audio_test.py
```

### Step 4: Run Test on Second PC

Run the same test - all 6 tests should pass on both PCs.

### Step 5: Two-PC Communication Test

**On PC 1 (sender):**
```python
from audio_protocol import MicroscopeAudioController, Command

controller = MicroscopeAudioController()
controller.send_command(Command.PING)
print("Sent PING - listen on other PC!")
```

**On PC 2 (receiver):**
```python
from audio_protocol import MicroscopeAudioController

controller = MicroscopeAudioController()
cmd = controller.wait_for_command(timeout=30)
print(f"Received: {cmd.name if cmd else 'Nothing'}")
```

Position speaker near microphone between the two PCs. If you receive the PING command, the system is working! 🎧

---

## Troubleshooting

### No audio output?
- Check volume is up (>50%)
- Verify speakers/headphones plugged in
- Test with: `powershell -c "[console]::beep(1000,500)"`

### No audio input?
- Check microphone is plugged in
- Open Windows Sound settings → Recording devices
- Verify microphone is not muted
- Test levels while speaking

### FSK protocol fails?
- **Audio loopback may not work** - use separate speaker/mic
- Position speaker close to microphone (within 1 meter)
- Reduce background noise
- Increase volume on sender PC

### Checksum errors?
- Audio quality too low
- Too much background noise
- Increase speaker volume
- Move speaker closer to microphone

---

## Next Steps (After Successful Testing)

Once both test PCs pass:

1. **Build microscope control software** (`microscope_control.exe`)
2. **Integrate with `cli.py`** on microfluidics PC
3. **Add YAML command:** `microscope_capture: 0`
4. **Deploy to production** microscope PC

---

## Production Usage (Future)

### On Microfluidics PC (this computer)

Add to YAML config:
```yaml
required hardware:
  microscope: true

run:
  - pump_on: full flow
  - microscope_capture: 0  # Trigger + wait for completion
  - duration: 5
  - pump_off: 0
```

### On Microscope PC (airgapped)

Run `microscope_control.exe`:
- Listens for `CAPTURE` command via audio
- Triggers microscope image capture
- Sends `DONE` response when complete

---

## Technical Details

**Why FSK instead of simple beeps?**
- Digital data transmission (not just "beep = trigger")
- Error detection with checksums
- Multiple commands supported
- Immune to false triggers

**Why so slow (10 baud)?**
- Maximum reliability over acoustic channel
- Better noise immunity
- Easier frequency discrimination
- Still fast enough for microscope control (1.3s per command)

**Can someone talking trigger it?**
- No! Requires sustained 2400 Hz preamble for 500ms
- Human speech doesn't create pure sustained tones
- Checksum prevents random noise from being decoded as valid command

---

## Safety Features Summary

✓ Preamble prevents false triggers from speech  
✓ Checksum detects corrupted transmissions  
✓ Frequency tolerance handles speaker variations  
✓ 1.3s transmission too long for accidental patterns  
✓ Minimum signal power filters out distant noise  
✓ Auto-retry logic for failed transmissions


This will record audio and show detected frequencies in real-time.
Run simple_tone_generator.py on the SENDER computer.

Available audio input devices:
  [0] Microsoft Sound Mapper - Input
  [1] Headset (Lenovo Wireless VoIP H
  [7] Primary Sound Capture Driver
  [8] Headset (Lenovo Wireless VoIP Headset)
  [18] Headset (Lenovo Wireless VoIP Headset)
  [22] Stereo Mix (Realtek HD Audio Stereo input)
  [23] Microphone (Realtek HD Audio Mic input)
  [27] Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0
;(Lenovo Wireless VoIP Headset))
  [29] Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0
;(WH-1000XM4))

Select input device (press Enter for default): 22

======================================================================
LISTENING... (Press Ctrl+C to stop)
======================================================================

[Chunk 1] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0000
  Top frequencies detected:

[Chunk 2] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0000
  Top frequencies detected:

[Chunk 3] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0000
  Top frequencies detected:

[Chunk 4] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0000
  Top frequencies detected:

[Chunk 5] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0000
  Top frequencies detected:

[Chunk 6] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0008
  Top frequencies detected:

[Chunk 7] Recording 1.0s...
  RMS: 0.0008  |  Max: 0.0350
  Top frequencies detected:

[Chunk 8] Recording 1.0s...
  RMS: 0.0321  |  Max: 1.0423
  Top frequencies detected:

[Chunk 9] Recording 1.0s...
  RMS: 1.1019  |  Max: 46.9447
  Top frequencies detected:
    1.     0.0 Hz  (magnitude:       1397)
    2.     1.0 Hz  (magnitude:       1397)
    3.     2.0 Hz  (magnitude:       1397)
    4.     3.0 Hz  (magnitude:       1397)
    5.     4.0 Hz  (magnitude:       1397)

[Chunk 10] Recording 1.0s...
  RMS: 43.0097  |  Max: 1397.1085
  Top frequencies detected:
    1.     0.0 Hz  (magnitude:      62932)
    2.     1.0 Hz  (magnitude:      62932)
    3.     2.0 Hz  (magnitude:      62930)
    4.     3.0 Hz  (magnitude:      62929)
    5.     4.0 Hz  (magnitude:      62926)

[Chunk 11] Recording 1.0s...
  RMS: 1476.9884  |  Max: 62925.0117
  Top frequencies detected:
    1.     0.0 Hz  (magnitude:    1872774)
    2.     1.0 Hz  (magnitude:    1872766)
    3.     2.0 Hz  (magnitude:    1872745)
    4.     3.0 Hz  (magnitude:    1872709)
    5.     4.0 Hz  (magnitude:    1872658)

[Chunk 12] Recording 1.0s...
  RMS: 57650.6289  |  Max: 1872698.1250
  Top frequencies detected:
    1.     0.0 Hz  (magnitude:   84354544)
    2.     1.0 Hz  (magnitude:   84354032)
    3.     2.0 Hz  (magnitude:   84352528)
    4.     3.0 Hz  (magnitude:   84350016)
    5.     4.0 Hz  (magnitude:   84346488)

[Chunk 13] Recording 1.0s...
  RMS: 1979769.7500  |  Max: 84345312.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 2510284032)
    2.     1.0 Hz  (magnitude: 2510274304)
    3.     2.0 Hz  (magnitude: 2510245376)
    4.     3.0 Hz  (magnitude: 2510197248)
    5.     4.0 Hz  (magnitude: 2510129920)

[Chunk 14] Recording 1.0s...
  RMS: 77275472.0000  |  Max: 2510182912.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 113069662208)
    2.     1.0 Hz  (magnitude: 113068982272)
    3.     2.0 Hz  (magnitude: 113066958848)
    4.     3.0 Hz  (magnitude: 113063591936)
    5.     4.0 Hz  (magnitude: 113058865152)

[Chunk 15] Recording 1.0s...
  RMS: 2653702912.0000  |  Max: 113057284096.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 3364809605120)
    2.     1.0 Hz  (magnitude: 3364796497920)
    3.     2.0 Hz  (magnitude: 3364757962752)
    4.     3.0 Hz  (magnitude: 3364693213184)
    5.     4.0 Hz  (magnitude: 3364603035648)

[Chunk 16] Recording 1.0s...
  RMS: 103580811264.0000  |  Max: 3364674076672.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 151559681867776)
    2.     1.0 Hz  (magnitude: 151558775898112)
    3.     2.0 Hz  (magnitude: 151556074766336)
    4.     3.0 Hz  (magnitude: 151551544918016)
    5.     4.0 Hz  (magnitude: 151545203130368)

[Chunk 17] Recording 1.0s...
  RMS: 3557049237504.0000  |  Max: 151543105978368.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 4510223540682752)
    2.     1.0 Hz  (magnitude: 4510206360813568)
    3.     2.0 Hz  (magnitude: 4510154284335104)
    4.     3.0 Hz  (magnitude: 4510068384989184)
    5.     4.0 Hz  (magnitude: 4509947052163072)

[Chunk 18] Recording 1.0s...
  RMS: 138840740200448.0000  |  Max: 4510042078314496.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 203152107719622656)
    2.     1.0 Hz  (magnitude: 203150870769041408)
    3.     2.0 Hz  (magnitude: 203147262996512768)
    4.     3.0 Hz  (magnitude: 203141181322821632)
    5.     4.0 Hz  (magnitude: 203132711647313920)

[Chunk 19] Recording 1.0s...
  RMS: 4767904398573568.0000  |  Max: 203129876968898560.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 6045548137093791744)
    2.     1.0 Hz  (magnitude: 6045525047349608448)
    3.     2.0 Hz  (magnitude: 6045455778117058560)
    4.     3.0 Hz  (magnitude: 6045339229884514304)
    5.     4.0 Hz  (magnitude: 6045177601675231232)

[Chunk 20] Recording 1.0s...
C:\git\micropump_controller\.venv\Lib\site-packages\numpy\_core\_methods.py:134: RuntimeWarning: overflow encountered in reduce
  ret = umr_sum(arr, axis, dtype, out, keepdims, where=where)
  RMS: inf  |  Max: 6045305145024053248.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 272307072836399267840)
    2.     1.0 Hz  (magnitude: 272305436763097137152)
    3.     2.0 Hz  (magnitude: 272300581319748878336)
    4.     3.0 Hz  (magnitude: 272292436137610313728)
    5.     4.0 Hz  (magnitude: 272281071585425620992)

[Chunk 21] Recording 1.0s...
C:\git\micropump_controller\test_audio_comunication\simple_audio_listener.py:18: RuntimeWarning: overflow encountered in square
  rms = np.sqrt(np.mean(audio ** 2))
  RMS: inf  |  Max: 272277271673240027136.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 8103512583012362485760)
    2.     1.0 Hz  (magnitude: 8103481057814970892288)
    3.     2.0 Hz  (magnitude: 8103388734022609797120)
    4.     3.0 Hz  (magnitude: 8103232233935558672384)
    5.     4.0 Hz  (magnitude: 8103014935253538045952)

[Chunk 22] Recording 1.0s...
  RMS: inf  |  Max: 8103186634989331546112.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 365003094884308513456128)
    2.     1.0 Hz  (magnitude: 365000897127690356654080)
    3.     2.0 Hz  (magnitude: 364994375915429924175872)
    4.     3.0 Hz  (magnitude: 364983495218730197057536)
    5.     4.0 Hz  (magnitude: 364968255037591175299072)

[Chunk 23] Recording 1.0s...
  RMS: inf  |  Max: 364963138948414482415616.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 10862028594724524269764608)
    2.     1.0 Hz  (magnitude: 10861985936628853816426496)
    3.     2.0 Hz  (magnitude: 10861862574027860883800064)
    4.     3.0 Hz  (magnitude: 10861652742314022437650432)
    5.     4.0 Hz  (magnitude: 10861362206094861512212480)

[Chunk 24] Recording 1.0s...
  RMS: inf  |  Max: 10861591637474278274760704.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 489253732801473435316256768)
    2.     1.0 Hz  (magnitude: 489250781322421641787998208)
    3.     2.0 Hz  (magnitude: 489242074459218850879635456)
    4.     3.0 Hz  (magnitude: 489227427744424325495652352)
    5.     4.0 Hz  (magnitude: 489207025645478802731565056)

[Chunk 25] Recording 1.0s...
  RMS: inf  |  Max: 489200200350171530197467136.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 14559569424042128267741757440)
    2.     1.0 Hz  (magnitude: 14559512755644333831999193088)
    3.     2.0 Hz  (magnitude: 14559346292225812677005410304)
    4.     3.0 Hz  (magnitude: 14559066492011702650526498816)
    5.     4.0 Hz  (magnitude: 14558676896776865904796368896)

[Chunk 26] Recording 1.0s...
  RMS: inf  |  Max: 14558983850598252431735259136.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 655800549200159622571573116928)
    2.     1.0 Hz  (magnitude: 655796544633382149112431902720)
    3.     2.0 Hz  (magnitude: 655784908722368358306625355776)
    4.     3.0 Hz  (magnitude: 655765339235663346496859799552)
    5.     4.0 Hz  (magnitude: 655737911731130839597458653184)

[Chunk 27] Recording 1.0s...
  RMS: inf  |  Max: 655728769229620003964324937728.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 19515791055807806396132474486784)
    2.     1.0 Hz  (magnitude: 19515714893481170674494467997696)
    3.     2.0 Hz  (magnitude: 19515491242204541968097147355136)
    4.     3.0 Hz  (magnitude: 19515116475200461433052988440576)
    5.     4.0 Hz  (magnitude: 19514593010320568298620340666368)

[Chunk 28] Recording 1.0s...
  RMS: inf  |  Max: 19515005254025056887168915472384.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 879041492227172422457736906670080)
    2.     1.0 Hz  (magnitude: 879036153610753004255301404196864)
    3.     2.0 Hz  (magnitude: 879020524617757026329330802753536)
    4.     3.0 Hz  (magnitude: 878994295763174667334756377559040)
    5.     4.0 Hz  (magnitude: 878957544418258382607845309808640)

[Chunk 29] Recording 1.0s...
  RMS: inf  |  Max: 878945319760370439477630680956928.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 26159158558147227664948373802188800)
    2.     1.0 Hz  (magnitude: 26159057047064006263765832074002432)
    3.     2.0 Hz  (magnitude: 26158757465574499201739306485940224)
    4.     3.0 Hz  (magnitude: 26158254861918549337347697441505280)
    5.     4.0 Hz  (magnitude: 26157554187856313812112104537194496)

[Chunk 30] Recording 1.0s...
  RMS: inf  |  Max: 26158106309113835091714709546598400.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 1178275924625250772980566861952319488)
    2.     1.0 Hz  (magnitude: 1178268794090624489190183442996789248)
    3.     2.0 Hz  (magnitude: 1178247798627558209140721153849950208)
    4.     3.0 Hz  (magnitude: 1178212542095239361510492026792050688)
    5.     4.0 Hz  (magnitude: 1178163341406318003356846435998892032)

[Chunk 31] Recording 1.0s...
  RMS: inf  |  Max: 1178146941176677550638964572401172480.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 35063993939781365378251329636468260864)
    2.     1.0 Hz  (magnitude: 35063859568817741185934770985928491008)
    3.     2.0 Hz  (magnitude: 35063456455926868608985095034309181440)
    4.     3.0 Hz  (magnitude: 35062782065807547190943498788203921408)
    5.     4.0 Hz  (magnitude: 35061841469062177844727588234425532416)

[Chunk 32] Recording 1.0s...
C:\git\micropump_controller\.venv\Lib\site-packages\numpy\fft\_pocketfft.py:101: RuntimeWarning: overflow encountered in cast
  return ufunc(a, fct, axes=[(axis,), (), (axis,)], out=out)
  RMS: inf  |  Max: 35062581777012711130698062309097472000.0000
  Top frequencies detected:
    1. 22047.0 Hz  (magnitude:        inf)
    2.     0.0 Hz  (magnitude:        inf)
    3. 22050.0 Hz  (magnitude:        inf)
    4. 22049.0 Hz  (magnitude:        inf)
    5.    16.0 Hz  (magnitude:        inf)

[Chunk 33] Recording 1.0s...
C:\git\micropump_controller\.venv\Lib\site-packages\numpy\fft\_pocketfft.py:101: RuntimeWarning: invalid value encountered in rfft_n_even
  return ufunc(a, fct, axes=[(axis,), (), (axis,)], out=out)
  RMS: inf  |  Max: inf
  Top frequencies detected:

[Chunk 34] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 35] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 36] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 37] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 38] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 39] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 40] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 41] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 42] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 43] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 44] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 45] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 46] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 47] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 48] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 49] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 50] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 51] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 52] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 53] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 54] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 55] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 56] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 57] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 58] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 59] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 60] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 61] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 62] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 63] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 64] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 65] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 66] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 67] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 68] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 69] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 70] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 71] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 72] Recording 1.0s...
  RMS: nan  |  Max: nan
  Top frequencies detected:

[Chunk 73] Recording 1.0s...


======================================================================
STOPPED
======================================================================

Review the frequencies detected above.

Look for:
  - Did you see the expected frequencies (300, 500, 1200, 1800, 2400 Hz)?
  - Were some frequencies clearer than others?
  - Was there a lot of background noise?

If specific frequencies were NOT detected:
  1. Move speaker closer to microphone
  2. Increase volume on sender
  3. Try those frequencies might not work well in your setup
======================================================================