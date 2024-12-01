import sg2000_basic as sg
import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
from tkinter.font import Font

class FrequencyRegulatorApp:
    def __init__(self, root):
        
        self.port_status = False
        self.autosend = False
        self.last_frequency_sent = 0
        self.autoscan = False

        self.root = root
        self.root.title("SGC SG-2000 Frequency regulator")

        # Load custom font
        try:
            self.seven_segment_font = Font(family="WooveboxSegment7", size=64)
        except Exception as e:
            print(f"Error loading font: {e}")
            self.seven_segment_font = ("Helvetica", 24)  # Fallback font if custom font fails

        # Frequency display setup
        self.frequency = [0, 7, 0, 0, 0, 0]
        self.selected_digit = 0  # Default to second digit

        # Main frame for arranging controls
        self.main_frame = tk.Frame(self.root, padx=10, pady=10)
        self.main_frame.pack()

        # Frame for frequency display with black background
        self.freq_frame = tk.Frame(self.main_frame, bg="black", padx=10, pady=10)
        self.freq_frame.grid(row=0, column=0, padx=10)

        self.freq_frame.grid_columnconfigure(2, minsize=15)  # Adjust spacer width as needed

        # Create the decimal point label between the second and third digit
        self.decimal_label = tk.Label(
            self.freq_frame,
            text=".",
            font=self.seven_segment_font,
            fg="green",
            bg="black"
        )
        self.decimal_label.grid(row=0, column=2, padx=(0, 5))

        # Create individual labels for each digit
        self.digit_labels = []
        for i in range(6):
            label = tk.Label(
                self.freq_frame,
                text=str(self.frequency[i]),
                font=self.seven_segment_font,
                fg="green",  # Adjusted color for seven-segment style
                bg="black",
                borderwidth=2,
                relief="solid",
                padx=5,
                pady=5,
            )
            label.grid(row=0, column=i, padx=2)
            label.bind("<Button-1>", lambda event, index=i: self.select_digit(index))
            label.bind("<MouseWheel>", lambda event, index=i: self.scroll_digit(event, index))
            self.digit_labels.append(label)

       

        # MHz label in the lower-right corner of the freq_frame
        self.mhz_label = tk.Label(self.freq_frame, text="MHz", font=("Helvetica", 12), fg="green", bg="black")
        self.mhz_label.grid(row=1, column=5, sticky="se", padx=5, pady=5)

        # Initial update to show selected digit color
        self.update_frequency_display()

        # Controls to shift the selected digit left and right, positioned below the frequency
        self.shift_frame = tk.Frame(self.main_frame)
        self.shift_frame.grid(row=1, column=0, pady=5)

        self.left_button = tk.Button(self.shift_frame, text="◀", command=self.select_previous_digit)
        self.left_button.grid(row=0, column=0, padx=5)

        self.right_button = tk.Button(self.shift_frame, text="▶", command=self.select_next_digit)
        self.right_button.grid(row=0, column=1, padx=5)

        # Controls to adjust the selected digit value (Up/Down)
        self.up_down_frame = tk.Frame(self.main_frame)
        self.up_down_frame.grid(row=0, column=1, padx=10)

        self.up_button = tk.Button(self.up_down_frame, text="▲", command=self.increment_digit)
        self.up_button.grid(row=0, column=0, pady=5)

        self.down_button = tk.Button(self.up_down_frame, text="▼", command=self.decrement_digit)
        self.down_button.grid(row=1, column=0, pady=5)

        # Dropdown for band selection
        self.band_var = tk.StringVar(value="40m")
        self.band_dropdown = ttk.Combobox(self.root, textvariable=self.band_var, values=["160m", "80m", "40m", "20m", "10m"])
        self.band_dropdown.pack(pady=5)
        self.band_dropdown.bind("<<ComboboxSelected>>", self.update_frequency_from_band)

        # Dropdown for mode selection
        self.mode_var = tk.StringVar(value="USB")
        self.mode_dropdown = ttk.Combobox(self.root, textvariable=self.mode_var, values=["LSB", "USB", "CW", "FM", "AM"])
        self.mode_dropdown.pack(pady=5)

        # COM port selection dropdown
        self.com_port_var = tk.StringVar(value="Select COM Port")
        self.com_port_dropdown = ttk.Combobox(self.root, textvariable=self.com_port_var, values=self.get_com_ports())
        self.com_port_dropdown.pack(pady=5)

        # Send button and autosend toggle
        self.send_button = tk.Button(self.root, text="Send", command=self.send_frequency)
        self.send_button.pack(pady=5)

        self.autosend_var = tk.BooleanVar()
        self.autosend_check = tk.Checkbutton(self.root, text="Autosend", variable=self.autosend_var)
        self.autosend_check.pack(pady=5)

        # Scan controls
        self.scan_button = tk.Button(self.root, text="Start Scan", command=self.start_scan)
        self.scan_button.pack(pady=5)

        self.scan_delay_label = tk.Label(self.root, text="Scan Delay (ms):")
        self.scan_delay_label.pack()

        self.scan_delay_entry = tk.Entry(self.root)
        self.scan_delay_entry.insert(0, "1000")
        self.scan_delay_entry.pack()

        # Status label at the bottom to display messages
        self.status_label = tk.Label(self.root, text="", fg="red", anchor="w")
        self.status_label.pack(fill="x", pady=(10, 0), padx=10)
        self.schedule_trigger()

    def set_status_message(self, message, color="red"):
        """Set the message displayed in the status label."""
        self.status_label.config(text=message, fg=color)
        self.update_frequency_display()

    def calculate_frequencyMhz(self):
        frequencyMhz = self.frequency[0] * 10 + \
                       self.frequency[1] + \
                       self.frequency[2] * 0.1 + \
                       self.frequency[3] * 0.01 + \
                       self.frequency[4] * 0.001 + \
                       self.frequency[5] * 0.0001
        frequencyMhz = round(frequencyMhz, 4)
        return frequencyMhz
    
    def adjust_frequency_within_limits(self):
        frequencyMhz = self.calculate_frequencyMhz()
        if frequencyMhz < 1.81:
            self.frequency = [0, 1, 8, 1, 0, 0]
        elif frequencyMhz > 55.0:
            self.frequency = [5, 5, 0, 0, 0, 0]        
    
    def get_com_ports(self):
        """Retrieve a list of available COM ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def select_digit(self, index):
        """Select a specific digit by clicking on it."""
        self.selected_digit = index
        self.update_frequency_display()

    def scroll_digit(self, event, index):
        """Increment or decrement the digit with mouse scroll and handle carry-over."""
        if event.delta > 0:
            self.increment_digit_at_index(index)
            self.selected_digit = index
        else:
            self.decrement_digit_at_index(index)
            self.selected_digit = index

    def increment_digit_at_index(self, index):
        """Increment the digit at the given index, with carry-over."""
        self.frequency[index] += 1
        if self.frequency[index] > 9:
            self.frequency[index] = 0
            if index > 0:
                self.increment_digit_at_index(index - 1)
        self.adjust_frequency_within_limits()
        self.update_frequency_display()

    def decrement_digit_at_index(self, index):
        """Decrement the digit at the given index, with carry-under."""
        self.frequency[index] -= 1
        if self.frequency[index] < 0:
            self.frequency[index] = 9
            if index > 0:
                self.decrement_digit_at_index(index - 1)
        self.adjust_frequency_within_limits()
        self.update_frequency_display()

    def increment_digit(self):
        """Increase the selected digit by 1, with carry-over."""
        self.increment_digit_at_index(self.selected_digit)

    def decrement_digit(self):
        """Decrease the selected digit by 1, with carry-under."""
        self.decrement_digit_at_index(self.selected_digit)

    def select_previous_digit(self):
        """Select the previous digit, wrapping around to the last digit if needed."""
        self.selected_digit = (self.selected_digit - 1) % 6
        self.update_frequency_display()

    def select_next_digit(self):
        """Select the next digit, wrapping around to the first digit if needed."""
        self.selected_digit = (self.selected_digit + 1) % 6
        self.update_frequency_display()

    def update_frequency_display(self):
        """Update the frequency labels to reflect changes, highlighting the selected digit."""
        for i, label in enumerate(self.digit_labels):
            label.config(text=str(self.frequency[i]))
            # Change color of selected digit
            if i == self.selected_digit:
                label.config(fg="red")
            else:
                label.config(fg="green")

    def update_frequency_from_band(self, event):
        """Set frequency based on selected band."""
        band_defaults = {
            "160m": [0, 1, 8, 1, 0, 0],
            "80m": [0, 3, 5, 0, 0, 0],
            "40m": [0, 7, 0, 0, 0, 0],
            "20m": [1, 4, 0, 0, 0, 0],
            "10m": [2, 8, 0, 0, 0, 0],
        }
        self.frequency = band_defaults.get(self.band_var.get(), [7, 0, 0, 0, 0, 0])
        self.update_frequency_display()

   

    def send_frequency(self):
        """Send the current frequency."""
        self.update_frequency_display()
        com_port = self.com_port_var.get()
        frequencyMhz = self.calculate_frequencyMhz()
        if com_port != "Select COM Port":
            message = f"Sending frequency {frequencyMhz} to {com_port}..."
            print(message)
            self.set_status_message(message)
            try:
                if not self.port_status:
                    self.ser = sg.open_port(com_port)
                    self.port_status = True  # Update port status if successful
            except Exception as e:
                message = f"Failed to open port {com_port}: {e}"
                print(message)
                self.set_status_message(message)
            
            if self.mode_dropdown.get() == "LSB":
                mode = 0x64
            elif self.mode_dropdown.get() == "USB":
                mode = 0x44
            elif self.mode_dropdown.get() == "CW":
                mode = 0x00
            elif self.mode_dropdown.get() == "AM":
                mode = 0x00
            elif self.mode_dropdown.get() == "FM":
                mode = 0x00
            else:
                mode = 0x00  # Default value
            if self.port_status == True: 
                sg.set_frequency(self.ser, frequencyMhz, mode)
                self.port_status = True
                message = f"Frequency {frequencyMhz} sent to {com_port}..."
                print(message)
                self.set_status_message(message)
        else:
            print("Please select a COM port before sending.")
    
    def schedule_trigger(self):
        # Call the trigger function every 'self.trigger_time' milliseconds
        self.trigger_time = self.scan_delay_entry.get()
        self.root.after(self.trigger_time, self.trigger)
    
    def trigger(self):
        #try:
            #print("Trigger fired!")  # Replace with your actual trigger function logic
        self.autosend = self.autosend_var.get()
        if self.autoscan:
            self.increment_digit()

        if self.autosend or self.autoscan:
            frequencyMhz = self.calculate_frequencyMhz()
            if self.last_frequency_sent != frequencyMhz:
                self.last_frequency_sent = frequencyMhz
                self.send_frequency()
        data_tot = b""

        if self.port_status == True:
            while True:  
                data = self.ser.read()  # Can specify number of bytes if needed, e.g., ser.read(10)# If there's data, print it
                if data:
                    data_tot = data_tot + data
                else:
                    sg.show_command(data_tot)
                    break

        #except:
        #    print("Exception")
        
        #print(self.autosend)
        self.schedule_trigger()  # Reschedule the trigger

    def start_scan(self):
        """Start scanning with the specified delay."""
        try:
            delay = int(self.scan_delay_entry.get())
            message = f"Scanning with {delay} ms delay"
            print(message)
            self.set_status_message(message)
            self.autoscan = not self.autoscan
            if self.autoscan:
                self.scan_button.config(text = "Stop Scan")
            else:
                self.scan_button.config(text = "Start Scan")
            # Implement scanning behavior here, e.g., incrementing frequency with delay
        except ValueError:
            message = f"Invalid delay input"
            print(message)
            self.set_status_message(message)

root = tk.Tk()
app = FrequencyRegulatorApp(root)
root.mainloop()
