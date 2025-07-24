#!/bin/bash

# Clear the screen
clear

# Set terminal title
echo -ne "\033]0;NEON CYCLE ARENA - Light Bike Game\007"

# Colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
RESET='\033[0m'

# Animated intro
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${YELLOW}                    NEON CYCLE ARENA${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo

# Try to maximize terminal on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Check if we can use AppleScript
    if command -v osascript &> /dev/null; then
        echo -e "${GREEN}Attempting to maximize terminal window...${RESET}"
        osascript -e 'tell application "Terminal" to set bounds of front window to {0, 0, 1920, 1080}' 2>/dev/null || true
        sleep 0.5
    fi
fi

# Get current terminal size
COLS=$(tput cols)
LINES=$(tput lines)

echo -e "${WHITE}Current terminal size: ${GREEN}${COLS}x${LINES}${RESET}"
echo

# Check if terminal is large enough
if [ $COLS -lt 80 ] || [ $LINES -lt 24 ]; then
    echo -e "${RED}⚠️  WARNING: Terminal window is too small!${RESET}"
    echo -e "${RED}   Minimum size required: 80x24${RESET}"
    echo -e "${RED}   Your current size: ${COLS}x${LINES}${RESET}"
    echo
fi

echo -e "${YELLOW}📐 MAXIMIZE YOUR TERMINAL WINDOW FOR THE BEST EXPERIENCE!${RESET}"
echo
echo -e "${WHITE}How to maximize:${RESET}"
echo -e "  ${CYAN}•${RESET} ${WHITE}macOS:${RESET} Press ${YELLOW}Cmd+Ctrl+F${RESET} or click the ${GREEN}green button${RESET}"
echo -e "  ${CYAN}•${RESET} ${WHITE}Windows:${RESET} Press ${YELLOW}Alt+Enter${RESET}"
echo -e "  ${CYAN}•${RESET} ${WHITE}Linux:${RESET} Press ${YELLOW}F11${RESET}"
echo
echo -e "${MAGENTA}The game will use your ENTIRE terminal screen!${RESET}"
echo
echo -e "${GREEN}Press ENTER when ready to start...${RESET}"
read

# Launch the game
python3 lightbike.py