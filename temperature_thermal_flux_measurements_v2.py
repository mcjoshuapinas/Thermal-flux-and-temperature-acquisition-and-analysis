import time
import os
import nidaqmx
from nidaqmx.constants import ThermocoupleType, AcquisitionType
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# --- PATH CONFIGURATION ---
# Get the absolute path of the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define relative paths for data input and results output
# This ensures the code works on any computer without modification
output_directory = os.path.join(BASE_DIR, "output")

# Create the output directory automatically if it doesn't exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

PORT_FLUX = "cDAQ1Mod1/ai0"
PORT_TC = "cDAQ1Mod4/ai0"  # Adjust based on 9213 wiring
PATH_OUTPUT = r'C:\Users\CertesAdmin\Documents\CONTENEUR'
LOG_INTERVAL = 60
# Example: If your sensor says 46.7 microvolts per W/m²
SENSITIVITY_CONSTANT = 46.7e-6
SAMPLE_RATE = 100  # Hz (Frequency)
SAMPLES_TO_READ = 100 # We read 1 second worth of data to average out noise

def run_acquisition():
    # 1. ASK USER FOR DATE STRING
    print("--- Setup ---")
    date_val = input("Enter the month-day-hour-minute (e.g., 05-22-15-28): ")

    # Construct the filename using the user input
    filename = f"flux_thermal_log_{date_val}.csv"
    output_file = os.path.join(PATH_OUTPUT, filename)

    # 1. INITIAL SETUP
    plt.ion()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Create empty line objects
    line1, = ax1.plot([], [], 'b-o', label='Heat Flux ($W/m^2$)')
    line2, = ax2.plot([], [], 'r-s', label='Temp (°C)')

    # Setup axis labels once
    ax1.set_ylabel("Heat Flux [W/m²]")
    ax1.legend(loc='upper left')
    ax2.set_ylabel("Temperature [°C]")
    ax2.set_xlabel("Time")
    ax2.legend(loc='upper left')
    plt.tight_layout()

    data_history = []

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(PORT_FLUX)
        task.ai_channels.add_ai_thrmcpl_chan(PORT_TC, thermocouple_type=ThermocoupleType.K)#according to Thermocouple type

        # --- DEFINING THE SAMPLE RATE HERE ---
        task.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=SAMPLES_TO_READ
        )

        last_log_time = 0
        print(f"--- ACQUISITION STARTED (Sampling @ {SAMPLE_RATE}Hz) ---")

        try:
            while True:
                current_time = time.time()

                if current_time - last_log_time >= LOG_INTERVAL:
                    # Start the burst
                    task.start()

                    # We read 100 samples (1 second of data at 100Hz)
                    # This acts as a low-pass filter to remove noise.
                    raw = task.read(number_of_samples_per_channel=SAMPLES_TO_READ, timeout=10.0)

                    # Stop the task so it's ready to be 'started' again next minute
                    task.stop()

                    # Average the 100 samples
                    avg_values = [np.mean(ch) for ch in raw]

                    flux = avg_values[0] / SENSITIVITY_CONSTANT
                    temp = avg_values[1]
                    ts = datetime.now().strftime("%m-%d %H:%M:%S")

                    data_history.append([ts, flux, temp])
                    last_log_time = current_time

                    print(f"[{ts}] Point #{len(data_history)} captured.")

                    # 2. UPDATE DATA WITHOUT CLEARING
                    df = pd.DataFrame(data_history, columns=['Time', 'Flux', 'Temp'])

                    # Update X and Y data for both lines
                    x_indices = np.arange(len(df))  # Using indices for stability
                    line1.set_data(x_indices, df['Flux'])
                    line2.set_data(x_indices, df['Temp'])

                    # Adjust the view limits so we can see the new points
                    ax1.relim()
                    ax1.autoscale_view()
                    ax2.relim()
                    ax2.autoscale_view()

                    # Update X-axis ticks to show timestamps
                    step = max(1, len(df) // 5)  # Show max 5 labels to avoid crowding
                    plt.xticks(x_indices[::step], df['Time'].iloc[::step], rotation=45)

                    # 3. FORCE REPAINT
                    fig.canvas.draw()
                    fig.canvas.flush_events()

                    # SAVE
                    df.to_csv(output_file, index=False, sep='\t')

                # Maintain the window heartbeat
                plt.pause(0.1)

        except KeyboardInterrupt:
            print("\nStopped by User.")
        finally:
            print(f"Final data saved to {output_file}")


if __name__ == "__main__":
    run_acquisition()