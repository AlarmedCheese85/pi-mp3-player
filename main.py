import os
import glob
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# Pin Definitions
ENC_CLK = 17
ENC_DT = 18
ENC_SW = 22
BTN_PLAY = 23
BTN_NEXT = 24

MUSIC_DIR = "/home/alarmedcheese85/pi-mp3-player/Music"

# Setup OLED
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
for pin in [ENC_CLK, ENC_DT, ENC_SW, BTN_PLAY, BTN_NEXT]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# State variables
playlists = []
selected_index = 0
current_playlist = None
in_menu = True  # True = picking playlist, False = playing music

def scan_playlists():
    global playlists
    if not os.path.exists(MUSIC_DIR):
        os.makedirs(MUSIC_DIR)
    # Get all subdirectories in Music/
    playlists = [d for d in os.listdir(MUSIC_DIR) if os.path.isdir(os.path.join(MUSIC_DIR, d))]
    playlists.sort()
    if not playlists:
        playlists = ["No Playlists Found"]

def draw_menu():
    with canvas(device) as draw:
        draw.text((0, 0), "--- SELECT PLAYLIST ---", fill="white")
        
        # Display up to 4 playlists on screen at once
        max_visible = 4
        start_idx = max(0, selected_index - 2)
        end_idx = min(len(playlists), start_idx + max_visible)
        
        y_offset = 15
        for i in range(start_idx, end_idx):
            prefix = "> " if i == selected_index else "  "
            text = f"{prefix}{playlists[i]}"
            draw.text((0, y_offset), text, fill="white")
            y_offset += 12

def draw_now_playing(track_name):
    with canvas(device) as draw:
        draw.text((0, 0), f"Playing: {current_playlist}", fill="white")
        draw.text((0, 20), f"Track: {track_name}", fill="white")
        draw.text((0, 50), "Press encoder to exit", fill="white")

# Initialize playlist list
scan_playlists()
draw_menu()

# Rotary encoder state tracking
last_clk_state = GPIO.input(ENC_CLK)

try:
    while True:
        current_clk_state = GPIO.input(ENC_CLK)
        
        # Handle Encoder Rotation (Only active when in menu)
        if in_menu and current_clk_state != last_clk_state and current_clk_state == 0:
            if GPIO.input(ENC_DT) == 1:
                selected_index = (selected_index + 1) % len(playlists)
            else:
                selected_index = (selected_index - 1) % len(playlists)
            draw_menu()
        last_clk_state = current_clk_state

        # Handle Encoder Click (Select playlist or go back to menu)
        if not GPIO.input(ENC_SW):
            if in_menu and playlists[0] != "No Playlists Found":
                current_playlist = playlists[selected_index]
                folder_path = os.path.join(MUSIC_DIR, current_playlist)
                tracks = glob.glob(os.path.join(folder_path, "*.mp3"))
                
                print(f"Selected playlist: {current_playlist} with {len(tracks)} tracks.")
                in_menu = False
                draw_now_playing(os.path.basename(tracks[0]) if tracks else "Empty Folder")
            else:
                # Return to menu
                in_menu = True
                draw_menu()
            while not GPIO.input(ENC_SW):
                pass  # Debounce click release

        # Handle Play/Pause button or track skipping while playing...
        # (Integrate your pygame mixer code here)

        import time
        time.sleep(0.005)

except KeyboardInterrupt:
    GPIO.cleanup()
