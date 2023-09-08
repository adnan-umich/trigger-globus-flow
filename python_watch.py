import os
import time
import datetime
import uuid
import shutil
from globus_automate_client import create_flows_client


class FileRenamer:
    def __init__(self, directory, destination_directory):
        self.directory = directory
        self.destination_directory = destination_directory

    def rename_files(self):
        try:
            for filename in os.listdir(self.directory):
                file_path = os.path.join(self.directory, filename)

                try:
                    # Check if the file ends with .dat and doesn't have "PREFIX_" in its name
                    if filename.endswith(".dat") and "PREFIX_" not in filename:
                        # Get the modification time of the file in UTC
                        utc_now = datetime.datetime.utcnow()
                        modification_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(file_path))

                        # Calculate the time difference in seconds
                        time_difference = (utc_now - modification_time).total_seconds()

                        # If the file hasn't been modified for 5 seconds, rename it
                        if time_difference > 5:
                            # Generate a new name with a prefix
                            new_name = f"PREFIX_{filename}"

                            # If the new name already exists, append a unique prefix
                            while os.path.exists(os.path.join(self.directory, new_name)):
                                unique_prefix = str(uuid.uuid4())[:8]  # Generate a unique prefix
                                new_name = f"PREFIX_{unique_prefix}_{filename}"

                            new_path = os.path.join(self.directory, new_name)

                            # Rename the file
                            os.rename(file_path, new_path)
                            print(f"Renamed {filename} to {new_name}")

                except OSError as e:
                    print(f"Error processing file {filename}: {e}")
        except FileNotFoundError as e:
            print(f"Error: Directory not found - {self.directory}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


class FileMover:
    def __init__(self, source_directory, destination_directory):
        self.source_directory = source_directory
        self.destination_directory = destination_directory

    def move_files_with_prefix(self):
        try:
            # TODO: Ideally not have this in production.
            if not os.path.isdir(self.destination_directory):
                os.makedirs(self.destination_directory)

            for filename in os.listdir(self.source_directory):
                file_path = os.path.join(self.source_directory, filename)

                try:
                    # Check if the file has "PREFIX" in its name
                    if "PREFIX_" in filename:
                        destination_path = os.path.join(self.destination_directory, filename)

                        # If the destination file already exists, append a unique prefix
                        while os.path.exists(destination_path):
                            unique_suffix = str(uuid.uuid4())[:8]  # Generate a unique suffix
                            destination_path = os.path.join(
                                self.destination_directory,
                                f"{os.path.splitext(filename)[0]}_{unique_suffix}{os.path.splitext(filename)[1]}"
                            )

                        shutil.move(file_path, destination_path)
                        print(f"Moved {filename} to {destination_path}")
                        self.run_flow_basic()

                except Exception as e:
                    print(f"Error moving file {filename}: {e}")
        except FileNotFoundError as e:
            print(f"Error: Directory not found - {self.source_directory}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    @staticmethod
    def run_flow():
        fc = create_flows_client()

        # TODO: Specify the flow to run when triggered
        flow_id = "f37e5766-7b3c-4c02-92ee-e6aacd8f4cb8"
        flow_scope = fc.get_flow(flow_id).data["globus_auth_scope"]

        # TODO: Set a label for the flow run
        # Default includes the file name that triggered the run
        flow_label = "photonics-transfer"

        # TODO: Modify source collection ID
        # Source collection must be on the endpoint where this trigger code is running
        source_id = "f1c8b178-4dba-11ee-8142-15041d20ea55"

        # TODO: Modify destination collection ID
        # Destination must be a guest collection so permission can be set
        # Default is "Globus Tutorials on ALCF Eagle"
        destination_id = "29a00465-6aca-4312-acb9-d6003001d3b4"

        # TODO: Modify destination collection path
        # Update path to include your user name e.g. /automate-tutorial/dev1/
        destination_base_path = "/."

        # Get the directory where the triggering file is stored and
        # add trailing '/' to satisfy Transfer requirements for moving a directory

        source_path = os.path.join("/C/Users/Adnanzai/Documents/data/ready")

        # Get name of monitored folder to use as destination path
        # and for setting permissions

        # Add a trailing '/' to meet Transfer requirements for directory transfer
        destination_path = os.path.join(".")

        # Inputs to the flow
        flow_input = {
            "input": {
                "source": {
                    "id": source_id,
                    "path": source_path,
                },
                "destination": {
                    "id": destination_id,
                    "path": destination_path,
                }
            }
        }

        flow_run_request = fc.run_flow(
            flow_id=flow_id,
            flow_scope=None,
            flow_input=flow_input,
            label=flow_label,
            tags=["photonics-transfer"],
        )
        print(f"Transferring and sharing")

    @staticmethod
    def run_flow_basic():
        os.system("globus-automate flow run f37e5766-7b3c-4c02-92ee-e6aacd8f4cb8 --flow-input input.json --label adnan1")

if __name__ == "__main__":
    directory_to_watch = r"C:\Users\Adnanzai\Documents\data"
    destination_directory = r"C:\Users\Adnanzai\Documents\data\ready"
    file_renamer = FileRenamer(directory_to_watch, destination_directory)
    file_mover = FileMover(directory_to_watch, destination_directory)

    while True:
        try:
            file_renamer.rename_files()
            time.sleep(1)  # Check every 1 second for changes
            file_mover.move_files_with_prefix()
        except KeyboardInterrupt:
            print("Program terminated by user.")
            break
