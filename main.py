import os
import glob
import time
import pygame
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

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

# Initialize Pygame Mixer for Audio
pygame.mixer.init()

# State variables
playlists = []
selected_index = 0
current_playlist = None
tracks = []
current_track_index = 0
in_menu = True  # True = picking playlist, False = playing music
is_playing = False

def scan_playlists():
    global playlists
    if not os.path.exists(MUSIC_DIR):
        os.makedirs(MUSIC_DIR)
    playlists = [d for d in os.listdir(MUSIC_DIR) if os.path.isdir(os.path.join(MUSIC_DIR, d))]
    playlists.sort()
    if not playlists:
        playlists = ["No Playlists Found"]

def draw_menu():
    with canvas(device) as draw:
        draw.text((0, 0), "--- SELECT PLAYLIST ---", fill="white")
        max_visible = 4
        start_idx = max(0, selected_index - 2)
        end_idx = min(len(playlists), start_idx + max_visible)
        
        y_offset = 15
        for i in range(start_idx, end_idx):
            prefix = "> " if i == selected_index else "  "
            text = f"{prefix}{playlists[i]}"
            draw.text((0, y_offset), text, fill="white")
            y_offset += 12

def draw_now_playing():
    with canvas(device) as draw:
        draw.text((0, 0), f"Playlist: {current_playlist}", fill="white")
        if tracks:
            track_name = os.path.basename(tracks[current_track_index])
            draw.text((0, 18), f"Track: {track_name}", fill="white")
            status = "Playing" if is_playing else "Paused"
            draw.text((0, 36), f"Status: {status}", fill="white")
        else:
            draw.text((0, 18), "No MP3s found!", fill="white")
        draw.text((0, 52), "Encoder=Back | Play=Toggle", fill="white")

def play_current_track():
    global is_playing
    if tracks:
        pygame.mixer.music.load(tracks[current_track_index])
        pygame.mixer.music.play()
        is_playing = True
        draw_now_playing()

# Initialize
scan_playlists()
draw_menu()

last_clk_state = GPIO.input(ENC_CLK)

try:
    while True:
        current_clk_state = GPIO.input(ENC_CLK)
        
        # 1. Menu Navigation (Rotation)
        if in_menu and current_clk_state != last_clk_state and current_clk_state == 0:
            if GPIO.input(ENC_DT) == 1:
                selected_index = (selected_index + 1) % len(playlists)
            else:
                selected_index = (selected_index - 1) % len(playlists)
            draw_menu()
        last_clk_state = current_clk_state

        # 2. Encoder Click (Enter Playlist or Go Back)
        if not GPIO.input(ENC_SW):
            if in_menu and playlists[0] != "No Playlists Found":
                current_playlist = playlists[selected_index]
                folder_path = os.path.join(MUSIC_DIR, current_playlist)
                tracks = glob.glob(os.path.join(folder_path, "*.mp3"))
                tracks.sort()
                
                current_track_index = 0
                in_menu = False
                
                if tracks:
                    play_current_track()
                else:
                    draw_now_playing()
            else:
                # Go back to menu and stop music
                pygame.mixer.music.stop()
                is_playing = False
                in_menu = True
                scan_playlists()
                draw_menu()
            
            while not GPIO.input(ENC_SW):
                time.sleep(0.05)  # Debounce click

        # 3. Play/Pause Button (BTN_PLAY on Pin 23)
        if not in_menu and not GPIO.input(BTN_PLAY):
            if tracks:
                if pygame.mixer.music.get_busy():
                    if is_playing:
                        pygame.mixer.music.pause()
                        is_playing = False
                    else:
                        pygame.mixer.music.unpause()
                        is_playing = True
                else:
                    play_current_track()
                draw_now_playing()
            while not GPIO.input(BTN_PLAY):
                time.sleep(0.05)

        # 4. Next Track Button (BTN_NEXT on Pin 24)
        if not in_menu and not GPIO.input(BTN_NEXT):
            if tracks:
                current_track_index = (current_track_index + 1) % len(tracks)
                play_current_track()
            while not GPIO.input(BTN_NEXT):
                time.sleep(0.05)

        # Auto-advance to next song if current song finishes playing
        if not in_menu and tracks and not pygame.mixer.music.get_busy() and is_playing:
            current_track_index = (current_track_index + 1) % len(tracks)
            play_current_track()

        time.sleep(0.01)

except KeyboardInterrupt:
    pygame.mixer.quit()
    GPIO.cleanup()
