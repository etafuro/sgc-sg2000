import serial
import time
data_tot = b''

# Set up the serial port
def open_port(port):
    # The  SG-2000 serial line parameters are preset to 9600 baud, 8 bits, no parity, and one stop bit
    ser = serial.Serial(
        port=port,                     # Change to your serial port
        baudrate=9600,                 # 9600 baud rate
        bytesize=serial.EIGHTBITS,     # 8 bits
        parity=serial.PARITY_NONE,     # No parity
        stopbits=serial.STOPBITS_ONE,  # One stop bit
        timeout=0.1
    )
    return ser


def send_attention(ser):
    # Set break condition (SPACE, +V)
    # Mark condition (-V)
    #ser.write(b'\x00')  # Sending a 0-byte simulates a MARK (-V) condition
    #time.sleep(0.01)  # 10 ms
    ser.break_condition = True
    time.sleep(0.01)  # 10 ms
    ser.break_condition = False
    
    # Mark condition (-V)
    ser.write(b'\x00')  # Sending a 0-byte simulates a MARK (-V) condition
    time.sleep(0.01)  # 10 ms

def send_close(ser):
    ser.write(b'\x00')  # Sending a 0-byte simulates a MARK (-V) condition
    time.sleep(0.01)  # 10 ms

# Send a command to the radio after the ATTENTION signal
def send_command(ser, command):
    send_attention(ser)  # Send the attention signal first
    ser.write(command)  # Send the actual command
    send_close(ser)

def frequency_to_hex_array(frequency_mhz):
    # Convert the frequency to a string and remove the decimal point
    freq_str = f"{frequency_mhz:07.4f}".replace(".", "")
    # Split the string into pairs of digits and convert each pair to a hex number
    hex_array = [int(freq_str[i:i+2], 16) for i in range(0, len(freq_str), 2)]
    
    return hex_array

# This function build command string 
def build_command(command_code, channel, frequency, mode):
    if command_code == "RESET":
        # Basic variables
        command_code        = 0x80            
        # Single values
        command = bytes([command_code])
        # Command sequence
        command_seq = command
    elif command_code == "STORE":
        # Basic variables
        hex_array = frequency_to_hex_array(frequency)
        command_code        = 0x84             # Command
        channelLSB          = channel     # Channel 15
        channelMSB          = 0x00
        rx_frequency_high   = hex_array[0]     
        rx_frequency_middle = hex_array[1]
        rx_frequency_low    = hex_array[2]
        tx_frequency_high   = hex_array[0]     
        tx_frequency_middle = hex_array[1]
        tx_frequency_low    = hex_array[2]
        mode_value          = 0x44     # USB mode
        # Single values
        command = bytes([command_code])
        channel = bytes([channelLSB]) + bytes([channelMSB])
        rx_frequency = bytes([rx_frequency_low]) + bytes([rx_frequency_middle]) + bytes([rx_frequency_high])
        tx_frequency = bytes([tx_frequency_low]) + bytes([tx_frequency_middle]) + bytes([tx_frequency_high])
        mode = bytes([mode_value])
        # Command sequence
        command_seq = command + channel + rx_frequency + tx_frequency + mode
    elif command_code == "RECALL":
        command_code        = 0x81            
        # Single values
        command = bytes([command_code])
        channelLSB          = channel
        channelMSB          = 0x00
        channel = bytes([channelLSB]) + bytes([channelMSB])
        # Command sequence
        command_seq = command + channel   
    elif command_code == "SET":
        # Basic variables
        if frequency:
            hex_array = frequency_to_hex_array(frequency)
        command_code        = 0x85     # Command
        channelLSB          = 0x00     # Channel 15
        channelMSB          = 0x00
        rx_frequency_high   = hex_array[0]     
        rx_frequency_middle = hex_array[1]
        rx_frequency_low    = hex_array[2]
        tx_frequency_high   = hex_array[0]     
        tx_frequency_middle = hex_array[1]
        tx_frequency_low    = hex_array[2]
        mode_value          = mode     # USB mode=0x44; LSB mode=0x64
        # Single values
        command = bytes([command_code])
        channel = bytes([channelLSB]) + bytes([channelMSB])
        rx_frequency = bytes([rx_frequency_low]) + bytes([rx_frequency_middle]) + bytes([rx_frequency_high])
        tx_frequency = bytes([tx_frequency_low]) + bytes([tx_frequency_middle]) + bytes([tx_frequency_high])
        mode = bytes([mode_value])
        # Command sequence
        # command_seq = command + channel + rx_frequency + tx_frequency + mode
        zero = bytes([0x00])
        command_seq = command + rx_frequency + tx_frequency + mode 
   
    else:
        return ""
    

    # Calculate lenght and checksum
    length = len(command_seq)
    length_byte = bytes([length])
    command_sum = sum(byte for byte in command_seq)
    checksum = bytes([(command_sum) & 0xFF])

    command_string = length_byte + command_seq + checksum

    return command_string

def show_command(command):
    outpf = ""
    for byte in command:
    # Convert byte to hex and format it as [XX]
        outpf = outpf + f"[{byte:02X}] "
    print(outpf)

def set_frequency(ser, frequency, mode):
    #command = build_command("RESET", channel=None, frequency=None, mode=None)
    #show_command(command)
    #send_command(ser, command)
    command = build_command("SET", channel=None, frequency=frequency, mode=mode)
    #command = build_command("STORE", channel=0x01, frequency=frequency, mode=mode)
    #show_command(command)
    #send_command(ser, command)
    #time.sleep(0.5)  # 10 ms
    #command = build_command("RECALL", channel=0x01, frequency=None, mode=None)
    show_command(command)
    send_command(ser, command)
    listen(ser)

def listen(ser):
    data_tot = b''
    while True:  
        data = ser.read()  # Can specify number of bytes if needed, e.g., ser.read(10)# If there's data, print it
        if data:
            data_tot = data_tot + data
        else:
            show_command(data_tot)
            break


