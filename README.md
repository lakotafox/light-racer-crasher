# Light Racer Crasher

A retro-style terminal-based light cycle racing game inspired by TRON, featuring ASCII graphics, power-ups, and thrilling gameplay!

## Features

- 🏍️ Retro terminal-based gameplay with ASCII art
- 🎮 Play against AI opponent
- 🛡️ Multiple power-ups:
  - **Shield** - Protects from crashes for 5 seconds
  - **Boost** - Maximum speed boost
  - **Speed** - Faster movement
  - **Stealth** - Temporarily disable your trail
- 🎵 Sound effects and background music
- 💻 Retro boot sequence with "SIMULATOR 78" theme
- 🏟️ Animated stadium with crowd effects

## Requirements

- Python 3.6+
- macOS (uses `afplay` for sound)
- Terminal with support for Unicode characters

## Installation

1. Clone the repository:
```bash
git clone https://github.com/lakotafox/light-racer-crasher.git
cd light-racer-crasher
```

No external dependencies required — the game uses Python's built-in `curses` library.

## How to Play

1. Run the game:
```bash
python3 lightbike.py
```

2. At boot prompt, type `Y` to start the game

3. Controls:
   - **Arrow Keys** - Move your light cycle
   - **T** - Toggle trail on/off
   - **S** - Toggle sound on/off
   - **R** - Restart game
   - **Q** - Quit

## Gameplay Tips

- Avoid crashing into walls, your own trail, or the opponent's trail
- Collect power-ups to gain advantages
- Use the trail toggle strategically to confuse your opponent
- The Shield power-up can save you from crashes!

## Terminal Requirements

For the best experience:
- Maximize your terminal window before starting
- Minimum recommended size: 80x24 characters
- The game will warn you if your terminal is too small

## Sound Files

The game includes three sound effects:
- `background_music.wav` - Plays once when the game starts
- `crash.wav` - Plays when a bike crashes
- `menu_select.wav` - Plays for menu selections and pickups

## License

This project is open source and available under the MIT License.

## Credits

Created with ❤️ using Python and curses library