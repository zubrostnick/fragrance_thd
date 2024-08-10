"""
Combines multiple CSV files into a single CSV file.
It logs the process, allowing users to select the CSV files for merging through a file dialog,
and generates a uniquely named output file while keeping track of the logs in a specified directory
"""


import pandas as pd
import os
import glob
from datetime import datetime
from tkinter import Tk
from tkinter.filedialog import askopenfilenames

def create_log_file(log_directory):
    # Ensure the log directory exists
    os.makedirs(log_directory, exist_ok=True)
    # Create a log file with a unique name based on the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = os.path.join(log_directory, f"log_{timestamp}.txt")
    with open(log_file, 'w') as log:
        log.write(f"Log file created on {datetime.now()}\n")
    return log_file


def log_info(log_file, message):
    with open(log_file, 'a') as log:
        log.write(f"{datetime.now()}: {message}\n")


def generate_output_file_name(directory, base_name="combined_file"):
    i = 1
    while True:
        output_file = os.path.join(directory, f"{base_name}_{i}.csv")
        if not os.path.exists(output_file):
            print(output_file)
            return output_file
        i += 1


def combine_csv_files(log_directory):
    directory_path = os.getcwd()
    # Use glob to get a list of all csv files in the directory
    # csv_files = glob.glob(os.path.join(directory_path, '*.csv')) # Finds all csvs in a folder automatically

    # Create a new log file for this run
    log_file = create_log_file(os.path.join(directory_path, log_directory))

    Tk().withdraw()  # Close the root window
    csv_files = askopenfilenames(filetypes=[("CSV files", "*.csv")], title="Select CSV files for merging") # allows csv files we want to combine
    if not csv_files:
        print("No files selected.")
        return

    combined_df = pd.DataFrame()
    total_instances = 0

    log_info(log_file, "Starting CSV combination process.")
    for csv_file in csv_files:
        try:
            data = pd.read_csv(csv_file)
            combined_df = pd.concat([combined_df, data], ignore_index=True)
            total_instances += data.shape[0]
            log_info(log_file, f"Successfully combined {csv_file} with {data.shape[0]} rows")
        except Exception as e:
            log_info(log_file, f"Error combining {csv_file}: {e}")

    # Save the combined dataframe to the output file
    output_file = generate_output_file_name(os.path.join(directory_path, "combined files"))
    # Ensure the log directory exists
    os.makedirs(os.path.join(directory_path, "combined files"), exist_ok=True)
    print(f"Success! Output: {output_file}, logs: {log_file}")

    log_info(log_file, f"Successfully saved combined CSV to {output_file}. Total size - {total_instances} {combined_df.shape[0]}")


if __name__ == "__main__":
    # Specify the directory containing the csv files
    log_dir = 'logs'
    combine_csv_files(log_dir)

