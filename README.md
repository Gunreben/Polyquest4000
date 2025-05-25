# Tarmac Festival - Polytron 4000 Game

A retro CRT-style exploration game for the Tarmac Festival, controlled with a MIDI Kaossilator Pro touchpad.

## Overview

You are tasked with activating the mighty **Polytron 4000** to restore power to the Tarmac Festival. Navigate the festival grounds, interact with various Points of Interest (POIs), collect items, and complete quests to achieve your goal.

## Features

- **MIDI Control**: Primary movement via Kaossilator Pro touchpad (X/Y controls 12/13)
- **Retro CRT Aesthetic**: Green-on-black terminal styling
- **Quest System**: Collect items and complete tasks to progress
- **Interactive Dialogue**: Talk to POIs and make choices
- **Map-based Navigation**: TMX map with collision detection
- **Inventory Management**: Track collected items

## Controls

### Primary (MIDI)
- **Kaossilator Pro Touchpad**: Move player around the map
  - Control 12: X-axis movement (max value 128)
  - Control 13: Y-axis movement (max value 127)

### Fallback (Keyboard)
- **WASD** or **Arrow Keys**: Move player
- **SPACE** or **ENTER**: Interact with POIs / Confirm dialogue choices
- **UP/DOWN Arrows**: Navigate dialogue choices
- **F1**: Toggle debug information
- **ESC**: Quit game

## Quest System

### Objective
Activate the **Polytron 4000** by collecting the **Hyperraumantrieb**.

### Quest Chain
1. **Visit Brausecus** → Get coffee (requires paper)
2. **Visit Resonant** → Get paper (requires coffee)
3. **Visit Vacanza** → Get Hyperraumantrieb (requires both coffee and paper)
4. **Return to Polytron 4000** → Activate and win!

### POIs (Points of Interest)
- **Polytron4000**: The main objective - needs Hyperraumantrieb to activate
- **Brausecus**: Coffee vendor - provides energy boost
- **Resonant**: Music venue - has important documents
- **Vacanza**: Travel agency - holds the key component
- **Looserlounge**: Relaxation area
- **L300**: Technical equipment
- **Orgia**: Entertainment venue

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Connect your Kaossilator Pro** via USB/MIDI

3. **Run the game**:
   ```bash
   python game.py
   ```

## File Structure

```
Polyquest4000/
├── game.py              # Main game file
├── requirements.txt     # Python dependencies
├── assets/
│   ├── map.tmx         # Tiled map file with POIs and walkable areas
│   └── dialogue.json  # Dialogue and quest data
└── README.md           # This file
```

## Technical Details

### Map System
- Uses TMX format (Tiled Map Editor)
- Object types:
  - Type 99: Walkable areas (paths)
  - Types 1-6: Interactive POIs
- Collision detection prevents walking outside paths

### MIDI Integration
- Automatically detects Kaossilator Pro or compatible MIDI devices
- Real-time control change processing
- Fallback to keyboard if MIDI unavailable

### Game State
- Inventory system tracks collected items
- Quest flags manage progression
- Dialogue system with conditional choices
- Win condition triggers victory screen

## Troubleshooting

### MIDI Issues
- Ensure Kaossilator Pro is connected and recognized by the system
- Check MIDI device drivers are installed
- Game will fall back to keyboard controls if MIDI fails

### Performance
- Game runs at 60 FPS
- Optimized for 1024x768 resolution
- Minimal system requirements

## Development

Built with:
- **Python 3.x**
- **Pygame** for graphics and input
- **Mido** for MIDI handling
- **XML parsing** for TMX map loading

## Credits

Created for the Tarmac Festival interactive experience.

Enjoy exploring the festival and activating the Polytron 4000! 🎵⚡ 