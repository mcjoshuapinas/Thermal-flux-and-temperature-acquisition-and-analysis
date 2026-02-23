import nidaqmx
from nidaqmx.constants import AcquisitionType, ThermocoupleType
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

# --- PATH CONFIGURATION ---
# Get the absolute path of the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define relative paths for data input and results output
# This ensures the code works on any computer without modification
output_directory = os.path.join(BASE_DIR, "output")

# Create the output directory automatically if it doesn't exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)


# --- Configuration ---
SENSORS = ['Window']
PORT_FLUX = "cDAQ1Mod1/ai0"
PORT_TC = "cDAQ1Mod2/ai0"  # Adjust based on 9213 wiring
LOG_INTERVAL = 60
# Example: If your sensor says 50 microvolts per W/m²
# Sensitivity = 50e-6 V/(W/m²)
SENSITIVITY_CONSTANT = 47.6e-6

plt.style.use('ggplot')
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 8))
data_history = []


def run_acquisition():
    # Use 'with' to ensure the task is closed properly
    with nidaqmx.Task() as task:
        # Add Heat Flux (Voltage)
        task.ai_channels.add_ai_voltage_chan(PORT_FLUX, name_to_assign_to_channel="Flux")
        # Add Thermocouples (Temperature)
        task.ai_channels.add_ai_thrmcpl_chan(PORT_TC, thermocouple_type=ThermocoupleType.K)

        task.start()
        print(f"Acquisition started. Sampling every {LOG_INTERVAL}s.")
        print("Close the plot window to stop and save data.")

        try:
            while plt.fignum_exists(fig.number):
                # 1. Read a small burst of samples (e.g., 10) to get a stable average
                raw = task.read(number_of_samples_per_channel=10)
                avg_values = [np.mean(channel_data) for channel_data in raw]

                # 2. CONVERSION: Flux = Voltage / Sensitivity
                voltage_raw = avg_values[0]
                heat_flux_converted = voltage_raw / SENSITIVITY_CONSTANT
                # TEMPERATURE
                window_temperature = avg_values[1]
                # 3. Create the row
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = [now, heat_flux_converted, window_temperature]

                # 4. Create DataFrame for plotting
                data_history.append(entry)
                pd.DataFrame([entry], columns=columns).to_csv(output_file, mode='a', header=False, index=False)

                # 5. Plotting (Now only plotting one temperature line)
                df = pd.DataFrame(data_history, columns=columns)
                ax1.clear()
                ax2.clear()
                ax1.set_title("Real-time Thermal Monitoring")
                ax1.plot(df['Time'], df['HeatFlux_Wm2'], color='tab:blue', label='Thermal Flux ($W/m^2$)')
                ax2.plot(df['Time'], df['Window'], color='tab:red', label='Window Temperature (°C)')

                # Temperature Plot (Lower)
                for s in SENSORS:
                    ax2.plot(df['Time'], df[s], marker='s', label=s)

                ax2.set_ylabel("Temperature (°C)")
                ax2.set_xlabel("Time")
                ax2.legend(loc='lower left', ncol=3, fontsize='x-small')
                ax1.legend()
                ax2.legend()
                plt.draw()
                plt.pause(0.1)
                # Wait for the next minute
                time.sleep(LOG_INTERVAL)

        except KeyboardInterrupt:
            print("\nManual stop detected.")
        finally:
            task.stop()
            # Save final results to CSV
            if data_history:
                final_df = pd.DataFrame(data_history, columns=columns)
                output_file = os.path.join(output_directory, "thermal_acquisition_log.csv")
                final_df.to_csv(output_file, index=False, sep='\t', encoding='utf-8')
                print(f"Data saved with calibrated units'. Total points: {len(data_history)}")


if __name__ == "__main__":
    run_acquisition()