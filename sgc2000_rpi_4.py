# This piece of software allow RPI Zero 2W to manage directly SG2000 radio, 
# without any need of an external computer
# (see schematics for connections)


import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont  # Importing ImageFont to use system fonts
import time
import subprocess
import sg2000_basic as sg


# Define GPIO pins for the rotary encoder
PIN_A = 5
PIN_B = 6
PIN_BUTTON = 13

# Initialize the GPIO settings
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initial settings for frequency and mode
frequency = 35000  # Start at 3.5 MHz (in Hz)
lsb_mode = 0x64
usb_mode = 0x44
cw_mode = 0x00
current_mode = "80m"
current_mode_code = lsb_mode

modes = [["80m", 35000, lsb_mode], 
         ["60m", 50000, lsb_mode], 
         ["40m", 70000, lsb_mode], 
         ["30m", 101000, usb_mode], 
         ["20m", 140000, usb_mode], 
         ["17m", 180680, usb_mode],
         #["15m", 35000, usb_mode],
         ["LSB", None, lsb_mode], 
         ["USB", None, usb_mode], 
         ["CW", None, cw_mode]
        ]
commands = [["Manual", 0x64], ["Autoscan", 0x44], ["Shutdown", 0x00]]
# Autoscan variables

autoscan_interval = 1
autoscan_last_time = time.time()


selected_mode = 0  # Default to LSB
selected_command = 0  # Default to LSB
cursor_position = 1  # To keep track of the selected digit
editing_mode = 0  # Default change position

# Serial connection for the OLED display (I2C)
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Load system font (use path to the system font you want to use)
font_path_2 = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Adjust based on your system
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"  # Adjust based on your system

font_size = 35  # Set the font size to a large value
font_size_medium = 12
font_size_small = 8

# Create a font object with the specified font path and size
font = ImageFont.truetype(font_path, font_size)
font_medium = ImageFont.truetype(font_path, font_size_medium)
font_splash = ImageFont.truetype(font_path_2, 20)
font_small = ImageFont.truetype(font_path, font_size_small)

# Variable to control fast/slow scroll
state_A = GPIO.input(PIN_A)
state_B = GPIO.input(PIN_B)
button_state = GPIO.input(PIN_BUTTON)
last_state_A = state_A
last_state_B = state_B
last_button_state = button_state
counter = 0  # To store the encoder count (used for navigation and frequency)
last_counter_2 = 0
encoder_press = 0
encoder_change = 0
encoder_step = 0

debounce_time = 0.01  # Tempo di debounce (in secondi)
display_time = 0.3
display_change = 1
last_debounce_time_A = time.time()
last_debounce_time_B = time.time()
last_debounce_time_button = time.time()
last_display_refresh = time.time()

current_message = None

# Log flag (True to enable, False to disable)
LOG_ENABLED = True

# Log function
def log(message):
    if LOG_ENABLED:
        print(message)

def encoder_callback(channel):
    global encoder_change, encoder_step, counter, state_A, state_B, last_counter_2, last_debounce_time_A,last_debounce_time_B, last_state_A, last_state_B
    global display_time, display_change, last_display_refresh, editing_mode, cursor_position, frequency, autoscan_interval, commands, selected_command
    global selected_mode, selected_command, current_message
    #print(cursor_position)
    state_A = GPIO.input(PIN_A)
    state_B = GPIO.input(PIN_B)
    
    current_time = time.time()

    # Gestione debounce per PIN A
    if state_A != last_state_A:
        if (state_B != state_A):
            counter += 1
            if (last_counter_2 != int(counter/2)):
                last_counter_2 = int(counter/2)
                encoder_change = 1
                encoder_step = 1
        else:
            counter -= 1
            if (last_counter_2 != int(counter/2)):
                last_counter_2 = int(counter/2)
                encoder_change = 1
                encoder_step = -1
           
        last_debounce_time_A = current_time
    
    #encoder_change = 1
    #encoder_step = counter
    
    
    print(f"Counter: A {state_A} B {state_B} counter={counter} change={encoder_change} step={encoder_step}")

    # Gestione debounce per PIN B
    if state_B != last_state_B:
        if current_time - last_debounce_time_B > debounce_time:
            last_debounce_time_B = current_time

    last_state_A = state_A
    last_state_B = state_B
    
    if encoder_change == 1:
        if editing_mode == 0:
            cursor_position = cursor_position + encoder_step
            if cursor_position < 1:
                cursor_position = 1
            if cursor_position > 8:  # Fixed indentation
                cursor_position = 8
            log(f"cursor_position: {cursor_position}")
        else:
            if cursor_position >= 1 and cursor_position <= 6:
                if commands[selected_command][0] == "Autoscan":
                    if encoder_step > 0:
                        autoscan_interval = autoscan_interval / 2
                    else:
                        autoscan_interval = autoscan_interval * 2
                    autoscan_interval = (max(0.125, min(autoscan_interval, 6)))
                    log(f"Autoscan interval: {autoscan_interval}")
                    message(f"Int. {autoscan_interval} s", modal=False)
                else:
                    step = (10 ** (6 - cursor_position)) * encoder_step
                    frequency = frequency + step 
                    frequency = max(35000, min(frequency, 550000)) 
                    log(f"frequency: {frequency} step: {step}")
                
            if cursor_position == 7:
               selected_mode = selected_mode + encoder_step
               if selected_mode < 0: 
                  selected_mode = len(modes) - 1 
               if selected_mode > len(modes) - 1: 
                  selected_mode = 0
            
            if cursor_position == 8:
               selected_command = selected_command + encoder_step
               if selected_command < 0: 
                  selected_command = len(commands) - 1 
               if selected_command > len(commands) - 1: 
                  selected_command = 0
                  
        display_change = 1      
            
     
    encoder_change = 0
    encoder_step = 0

GPIO.add_event_detect(PIN_A, GPIO.BOTH, callback=encoder_callback, bouncetime=10)
GPIO.add_event_detect(PIN_B, GPIO.BOTH, callback=encoder_callback, bouncetime=10)


def update_frequency():
    global frequency, cursor_position, editing_mode
    log(f"Update display")
    # Scale the frequency to 6 digits (multiply by 100,000)
    scaled_frequency = frequency

    # Format the scaled frequency as XXYYYY (6 digits with leading zeros)
    freq_str = f"{scaled_frequency:06d}"

    with canvas(device) as draw:
        # Clear the screen with a black background
        #draw.rectangle(device.bounding_box, outline="white", fill="black")
        # Display the frequency (formatted as XXYYYY)
        draw.text((0, 10), f"{freq_str}", fill="white", font=font)
        # Display the selected mode below the frequency
        
        if cursor_position == 7:
           if editing_mode == 1:
               selmode1 = "<"
               selmode2 = ">"
           else:
               selmode1 = ">"
               selmode2 = "<"
        else:
           selmode1 = " "
           selmode2 = " "
           
        if cursor_position == 8:
           if editing_mode == 1:
               selcommand1 = "<"
               selcommand2 = ">"
           else:
               selcommand1 = ">"
               selcommand2 = "<"
        else:
           selcommand1 = " "
           selcommand2 = " "

        draw.text((5, 50), f"{selmode1}{modes[selected_mode][0]}{selmode2}", fill="white", font=font_medium)
        draw.text((40, 50), f"{selcommand1}{commands[selected_command][0]}{selcommand2}", fill="white", font=font_medium)
        current_mode_label = "LSB"
        if current_mode_code == usb_mode:
           current_mode_label  = "USB"
        if current_mode_code == cw_mode:
            current_mode_label = "CW"
        if current_message:
            draw.text((0, 6), f"{current_message}", fill="white", font=font_small)
        draw.text((90, 6), f"Mhz {current_mode_label}", fill="white", font=font_small)
        draw.line((42, 42, 43, 42), fill="white")
        draw.line((42, 43, 42, 43), fill="white")
        font_step = 20
        # If the cursor is within the 6 digit range, draw it under the selected digit
        if cursor_position <= 6:
            baseline = (cursor_position - 1) * font_step
            if editing_mode == 1:
                draw.line((4 + baseline, 15, 2 + baseline + font_step, 15), fill="white")
            draw.line((4 + baseline, 9 + font_size, 2 + baseline + font_step, 9 + font_size), fill="white")
#            draw.line((5 + cursor_position * font_step, 10 + font_size, 5 + cursor_position * font_step + font_step, 10 + font_size), fill="white")


# Splash screen function
def message(message, modal):
    global current_message
    if len(message) > 10:
        current_message = message[:10] + "\u2026"
    else:
        current_message = message
    if modal == True:
        with canvas(device) as draw:
            #draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 5), message, fill="white", font=font_medium)
        time.sleep(2)

# Splash screen function
def splash_screen():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((10, 5), "SGC 2000", fill="white", font=font_splash)
        draw.text((10, 35), "Controller", fill="white", font=font_splash)
    time.sleep(2)

# Main loop to handle encoder input and button presses
def main():
    global frequency, last_state_A, last_state_B, last_button_state, cursor_position, selected_mode, counter, last_debounce_time_A, last_debounce_time_B, encoder_change, encoder_step, encoder_press, last_counter_2, state_A, state_B, button_state, commands, selected_command, current_mode_code
    global display_time, display_change, last_display_refresh, autoscan_interval, autoscan_last_time
    global editing_mode
    splash_screen()  # Show splash screen on startup
    last_frequency = 0
    ser = None
    #command = sg.build_command("SET", channel=None, frequency=7.0, mode=0x44)
    if ser == None:
        try:
            log("Opening port")
            message("Opening port", modal=False)
            ser = sg.open_port("/dev/ttyUSB0")
        except:
            log("Failed opening port")
            message("Failed open port", modal=True)

    try:
        while True:
                               
            if frequency != last_frequency and ser != None:
                try:
                    send_frequency = frequency / 10000
                    log(f"send_frequency: {send_frequency}")
                    command = sg.build_command("SET", channel=None, frequency=send_frequency, mode=current_mode_code)
                    sg.show_command(command)
                    sg.send_command(ser, command)
                except:
                    log("Failed sending cmd")
                    message("Failed sending cmd", modal=False)
                last_frequency = frequency

            current_time = time.time()
            button_state = GPIO.input(PIN_BUTTON)
            if button_state == GPIO.LOW and last_button_state == GPIO.HIGH:
                encoder_press = 1
                last_button_state = button_state
                if editing_mode == 0:
                    editing_mode = 1
                else:
                    editing_mode = 0
                    log("Editing mode=0")
                    if cursor_position == 7:
                        current_mode = modes[selected_mode][0]
                        if modes[selected_mode][1]:
                            frequency = modes[selected_mode][1]
                        current_mode_code = modes[selected_mode][2]
                    if cursor_position == 8:
                        log(f"command: {commands[selected_command]}")
                        if commands[selected_command][0] == "Shutdown":
                            log("Shutdown request")
                            try:
                                message("Shutdown...", modal=True)
                                update_frequency()
                                # Run the shutdown command
                                subprocess.run(["sudo", "shutdown", "now"], check=True)
                                #subprocess.run(["sudo", "systemctl", "poweroff"], check=True)
                            except subprocess.CalledProcessError as e:
                                log(f"Error occurred: {e}")

                    
                display_change = 1


            #log(f"Encoder Counter: {counter}")

            # Autoscan
            #log(f"editing_mode {editing_mode} {commands[selected_command][0]}")
            if editing_mode == 1 and commands[selected_command][0] == "Autoscan":
                #log(f"editing_mode {autoscan_last_time - time.time()}")
                if (time.time() - autoscan_last_time) > autoscan_interval:
                    if cursor_position >= 1 and cursor_position <= 6:
                        log("Autoscan step")
                        display_change = 1
                        autoscan_last_time = time.time()
                        step = (10 ** (6 - cursor_position)) 
                        frequency = frequency + step 
                        frequency = max(35000, min(frequency, 550000))
                  
            
            if display_change == 1 and (current_time - last_display_refresh) > display_time:
                display_change = 0
                last_display_refresh = current_time
                update_frequency()

            last_button_state = button_state
            encoder_change = 0
            encoder_step = 0
            encoder_press = 0
            
            time.sleep(0.001)

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Cleaning up GPIO and exiting.")

if __name__ == "__main__":
    update_frequency()
    main()