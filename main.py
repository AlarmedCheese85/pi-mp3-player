import os
import time
import threading
import pygame
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

# --- HARDWARE PIN DEFINITIONS (BCM Mode) ---
ENC_CLK = 17       # Rotary Encoder Clock (A)
ENC_DT = 27        # Rotary Encoder Data (B)
ENC_SW = 22        # Rotary Encoder Push Button
BTN_PLAY = 23      # Play / Pause Button
BTN_NEXT = 24      # Next Track Button
BTN_POWER = 25     # Safe Shutdown Button

# --- SETUP OLED DISPLAY (I2C) ---
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)

# --- SETUP GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(ENC_CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENC_DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENC_SW, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_PLAY, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_NEXT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_POWER, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- SETUP PYGAME AUDIO ---
pygame.mixer.init()
MUSIC_DIR = "/home/alarmedcheese85/Music"  # Path to your MP3 files

def get_playlist():
    if not os.path.exists(MUSIC_DIR):
        os.makedirs(MUSIC_DIR)
    return [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]

playlist = get_playlist()
current_track_index = 0
is_playing = False

def play_current_track():
    global current_track_index, is_playing
    playlist = get_playlist()
    if not playlist:
        return
    current_track_index = current_track_index % len(playlist)
    track_path = os.path.join(MUSIC_DIR, playlist[current_track_index])
    try:
        pygame.mixer.music.load(track_path)
        pygame.mixer.music.play()
        is_playing = True
    except Exception as e:
        print(f"Error playing track: {e}")

def toggle_play_pause():
    global is_playing
    if pygame.mixer.music.get_busy():
        if is_playing:
            pygame.mixer.music.pause()
            is_playing = False
        else:
            pygame.mixer.music.unpause()
            is_playing = True
    else:
        play_current_track()

def next_track():
    global current_track_index, playlist
    playlist = get_playlist()
    if not playlist:
        return
    current_track_index = (current_track_index + 1) % len(playlist)
    play_current_track()

def shutdown_system(channel):
    print("Shutting down safely...")
    # Optional: draw goodbye screen here before shutdown
    os.system("sudo shutdown -h now")

# Register event listeners for buttons
GPIO.add_event_detect(BTN_PLAY, GPIO.FALLING, callback=lambda c: toggle_play_pause(), bouncetime=300)
GPIO.add_event_detect(BTN_NEXT, GPIO.FALLING, callback=lambda c: next_track(), bouncetime=300)
GPIO.add_event_detect(BTN_POWER, GPIO.FALLING, callback=shutdown_system, bouncetime=500)

# --- ROTARY ENCODER LISTENER THREAD ---
def encoder_listener():
    global current_track_index
    last_clk = GPIO.input(ENC_CLK)
    while True:
        clk_state = GPIO.input(ENC_CLK)
        dt_state = GPIO.input(ENC_DT)
        if clk_state != last_clk:
            if dt_state != clk_state:
                # Rotated Clockwise (e.g., skip forward or turn volume up)
                print("Encoder turned Clockwise")
            else:
                # Rotated Counter-Clockwise
                print("Encoder turned Counter-Clockwise")
        last_clk = clk_state
        time.sleep(0.005)

# Start encoder loop in background
threading.Thread(target=encoder_listener, daemon=True).start()

# --- MAIN DISPLAY & EVENT LOOP ---
print("MP3 Player Started. Press Ctrl+C to exit.")
try:
    while True:
        playlist = get_playlist()
        track_name = playlist[current_track_index] if playlist else "No Music Found"
        status = "Playing" if is_playing else "Paused"
        
        # Draw status and track name to OLED Screen
        image = Image.new("1", (device.width, device.height))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), f"Status: {status}", fill=255)
        draw.text((0, 15), f"Track:", fill=255)
        draw.text((0, 30), track_name[:20], fill=255)
        device.display(image)
        
        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()
