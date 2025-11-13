# Configuration Examples for Micropump Controller

This folder contains YAML configuration files for automating micropump, valve, stage3d, and microscope operations. The format is designed to be human-readable, extensible, and easy for both users and AIs to generate new configs.

## YAML Structure Overview

### Sections
- **pump settings**: Named profiles for pump operation (waveform, voltage, frequency)
- **positions**: Named 3D coordinates for well plate positions, wash, image, etc.
- **well_generator**: Defines a sequence of wells for automated iteration
- **required hardware**: Which devices are present (pump, valve, pipetting robot, microscope)
- **run**: The main sequence of actions to execute

---

## Supported Actions in `run`

- `move: <position>`: Move stage to a named position (e.g., `A1`, `wash`, `image`)
- `pump_on: <profile>`: Start pump using a named profile from `pump settings`
- `pump_off: 0`: Stop pump
- `wait: <seconds>`: Wait/pause for specified seconds
- `image: 1`: Trigger microscope imaging (legacy - use microscope_acquire instead)
- `microscope_acquire: true`: **NEW** Bidirectional microscope control - sends CAPTURE, waits for DONE
- `valve_on: <seconds>`: Open valve for specified seconds
- `valve_off: 0`: Close valve
- `loop`: Repeat a block of steps (see below)

---

## Looping and Well Plate Automation

### Loop Over Wells
```yaml
- loop:
    wells: well_generator
    steps:
      - move: $well
      - pump_on: sample
      - wait: 10
      - pump_off: 0
      - move: wash
      - pump_on: wash
      - wait: 10
      - pump_off: 0
      - move: image
      - image: 1
```
- `$well` is replaced by the current well name from the generator.

### Valve Pulse Loop
```yaml
- pump_on: sample
- loop:
    repeat: 5
    steps:
      - valve_on: 2
      - wait: 1
      - valve_off: 0
- pump_off: 0
```
- This pulses the valve 5 times, 2 seconds each, with 1 second between pulses.

---

## Example: Full Sequence
```yaml
run:
  - move: wash
  - pump_on: wash
  - wait: 10
  - pump_off: 0

  - loop:
      wells: well_generator
      steps:
        - move: $well
        - pump_on: sample
        - wait: 10
        - pump_off: 0
        - move: wash
        - pump_on: wash
        - wait: 10
        - pump_off: 0
        - move: image
        - image: 1

  - move: A1
  - pump_on: sample
  - loop:
      repeat: 5
      steps:
        - valve_on: 2
        - wait: 1
        - valve_off: 0
  - pump_off: 0
```

---

## Best Practices
- Always turn the pump on before valve pulses and off after.
- Use named positions for clarity and maintainability.
- Use generators for well plate automation.
- Add comments for clarity.
- For edge cases, mix direct moves, loops, and waits as needed.

---

## Extending for Stage3D and Microscope
- Add new actions like `move_stage: {x, y, z}` or `image: microscope1` as needed.
- Use the `positions` section to define all named locations.
- For well plates, use generators and specify columns/rows in a separate section if needed.

---

## Template for New Configs
```yaml
pump settings:
  sample:
    waveform: RECT
    voltage: 100
    freq: 50
positions:
  A1: {x: 0, y: 0, z: -42}
  wash: {x: 20, y: 137, z: -40}
well_generator:
  wells: [A1, A2, A3]
required hardware:
  pump: true
  valve: true
run:
  # Add your sequence here
```

---

For more examples, see the other YAML files in this folder.