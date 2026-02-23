import nidaqmx
from nidaqmx.constants import AcquisitionType, ThermocoupleType
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime

# --- Configuration ---
SENSORS = ['Window']
PORT_FLUX = "cDAQ1Mod1/ai0"
PORT_TC = "cDAQ1Mod2/ai0:5"  # Adjust based on 9213 wiring
LOG_INTERVAL = 60
# Example: If your sensor says 50 microvolts per W/m²
# Sensitivity = 50e-6 V/(W/m²)
SENSITIVITY_CONSTANT = 50e-6

plt.style.use('ggplot')
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 8))
data_history = []


def run_acquisition():
    # Use 'with' to ensure the task is closed properly
    with nidaqmx.Task() as task:
        # Add Heat Flux (Voltage)
        task.ai_channels.add_ai_voltage_chan(PORT_FLUX, name_to_assign_to_channel="Flux")
        # Add 6 Thermocouples (Temperature)
        task.ai_channels.add_ai_thrmcpl_chan(PORT_TC, thermocouple_type=ThermocoupleType.K)

        task.start()
        print(f"Acquisition started. Sampling every {LOG_INTERVAL}s.")
        print("Close the plot window to stop and save data.")

        try:
            while plt.fignum_exists(fig.number):
                # Read a small burst of samples (e.g., 10) to get a stable average
                raw = task.read(number_of_samples_per_channel=10)
                avg_values = [np.mean(channel_data) for channel_data in raw]

                # CONVERSION: Flux = Voltage / Sensitivity
                voltage_raw = avg_values[0]
                heat_flux_converted = voltage_raw / SENSITIVITY_CONSTANT

                # Timestamp and store
                now = datetime.now()
                # Update the log entry with the converted value
                entry = [now, heat_flux_converted] + avg_values[1:]
                data_history.append(entry)

                # Create DataFrame for plotting
                df = pd.DataFrame(data_history, columns=['Time', 'HeatFlux_Wm2'] + SENSORS)

                # Refresh Plot
                ax1.clear()
                ax2.clear()

                # Heat Flux Plot (Upper)
                ax1.plot(df['Time'], df['HeatFlux_Wm2'], marker='o', color='tab:blue', label='Heat Flux ($W/m^2$)')
                ax1.legend(loc='upper left')
                ax1.set_ylabel("Heat Flux ($W/m^2$)")
                ax1.set_title("Real-time Thermal Monitoring")

                # Temperature Plot (Lower)
                for s in SENSORS:
                    ax2.plot(df['Time'], df[s], marker='s', label=s)

                ax2.set_ylabel("Temperature (°C)")
                ax2.set_xlabel("Time")
                ax2.legend(loc='lower left', ncol=3, fontsize='x-small')

                plt.draw()
                plt.pause(0.1)  # Brief pause for GUI update

                # Wait for the next minute
                time.sleep(LOG_INTERVAL)

        except KeyboardInterrupt:
            print("\nManual stop detected.")
        finally:
            task.stop()
            # Save final results to CSV
            if data_history:
                final_df = pd.DataFrame(data_history, columns=['Time', 'HeatFlux_Wm2'] + SENSORS)
                final_df.to_csv("thermal_acquisition_log.csv", index=False)
                print(f"Data saved with calibrated units'. Total points: {len(data_history)}")


if __name__ == "__main__":
    run_acquisition()