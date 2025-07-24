#!/bin/bash

# This is a .command file that will open in Terminal on macOS

# Change to the game directory
cd "$(dirname "$0")"

# Try to set terminal to fullscreen using AppleScript
osascript <<EOF
tell application "Terminal"
    activate
    
    -- Get the front window
    set frontWindow to front window
    
    -- Try to maximize (this works on newer macOS versions)
    try
        set zoomed of frontWindow to true
    on error
        -- Fallback: set to large size
        set bounds of frontWindow to {0, 23, 1440, 900}
    end try
    
    -- Set nice colors
    set background color of frontWindow to {0, 0, 0}
    set normal text color of frontWindow to {65535, 65535, 65535}
    set font size of frontWindow to 14
end tell
EOF

# Small delay to let the window resize
sleep 0.5

# Run the game
python3 lightbike.py