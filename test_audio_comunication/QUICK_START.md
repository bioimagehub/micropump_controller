# Quick Start Guide - Audio Communication Testing

## What You Have

A complete **FSK audio modem** system for airgapped computer communication using sound!

## Testing on Two Other Computers (Not the Microscope Yet)

### Files to Copy to USB Stick

```
test_audio_comunication/
├── audio_protocol.py               (Core FSK modem)
├── microscope_audio_test.py        (Full test suite)
├── two_pc_test.py                  (Two-computer demo)
├── requirements.txt                (Dependencies)
└── QUICK_START.md                  (This file)
```

---

## Test Plan

### Phase 1: Single Computer Test (5 minutes each PC)

**On Computer 1:**
```bash
cd test_audio_comunication
pip install -r requirements.txt
python microscope_audio_test.py
```

**Expected:** All 6 tests pass ✓

**On Computer 2:**
- Copy folder from USB stick
- Run same commands
- Verify all 6 tests pass ✓

---

### Phase 2: Two-Computer Communication (10 minutes)

**Setup:**
1. Place computers within 1-2 meters
2. Position Computer 1's speaker near Computer 2's microphone
3. Volume at ~60% on both

**On Computer 2 (Receiver) - START THIS FIRST:**
```bash
python two_pc_test.py receiver
```

**On Computer 1 (Sender) - START SECOND:**
```bash
python two_pc_test.py sender
```

**Expected Results:**
- Sender sends PING → Receiver responds with PONG ✓
- Sender sends CAPTURE → Receiver responds with DONE ✓
- Total test time: ~10 seconds

---

## Troubleshooting

### No sound heard?
```powershell
# Quick beep test
powershell -c "[console]::beep(1000,500)"
```
If no beep → Check volume/speakers

### Tests fail?
- **Test 1-2 fail:** Check pip install worked
- **Test 3 fails:** Microphone muted or not plugged in
- **Test 5-6 fail:** Audio loopback issue (normal - use two PCs)

### Two-PC test fails?
- Move speaker closer to microphone (<1 meter)
- Increase volume (70-80%)
- Reduce background noise
- Check both PCs passed Phase 1 tests

---

## Success Criteria

✓ Both PCs pass all 6 tests in Phase 1  
✓ Two-PC test completes PING/PONG exchange  
✓ Two-PC test completes CAPTURE/DONE exchange  

**If all pass → Audio communication is viable for microscope control! 🎉**

---

## What This Proves

- Airgapped computers can communicate via audio
- FSK protocol is robust against background noise
- No network/cables needed - just speakers and microphones
- Ready for microscope PC deployment

---

## Next Steps (After Successful Testing)

1. Report back results from both test computers
2. Build production `microscope_control.exe` for airgapped microscope PC
3. Integrate with microfluidics control system (`cli.py`)

---

## How to Build Standalone .exe (Optional)

If test PCs don't have Python installed:

```bash
pip install pyinstaller
python build_standalone.py
```

Copy `dist/microscope_audio_test.exe` to USB → Run on test PC (no Python needed)

---

## Technical Notes

**Protocol:** FSK (Frequency Shift Keying) - same tech as old modems  
**Speed:** 10 baud (~1.3 seconds per command)  
**Reliability:** Checksum + preamble + noise filtering  
**Safety:** Won't trigger from speech/background noise  

**Frequencies:**
- Preamble: 2400 Hz (sync tone)
- Binary 0: 1200 Hz (mark)
- Binary 1: 1800 Hz (space)

---

## Questions?

Check `README.md` for full documentation and troubleshooting guide.
