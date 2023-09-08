import os
import time
import datetime
import uuid
import shutil
import json
import yaml
from globus_automate_client import create_flows_client


class FileRenamer:
    def __init__(self):
        try:
            with open("config.yaml", 'r', encoding="utf-8") as f:
                data = yaml.load(f, yaml.Loader)
                self.source_directory = data['source_directory']
                self.staging_directory = data['staging_directory']
                self.time_difference_min = data['time_difference_min']
        except FileNotFoundError:
                print("Error: The specified YAML file does not exist.")
        except yaml.YAMLError as e:
            print(f"Error: YAML parsing error - {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def rename_files(self):
        try:
            for filename in os.listdir(self.source_directory):
                file_path = os.path.join(self.source_directory, filename)

                try:
                    # Check if the file ends with .dat and doesn't have "PREFIX_" in its name
                    if filename.endswith(".dat") and "DONE_" not in filename:
                        # Get the modification time of the file in UTC
                        utc_now = datetime.datetime.utcnow()
                        modification_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(file_path))

                        # Calculate the time difference in seconds
                        time_difference = (utc_now - modification_time).total_seconds()

                        # If the file hasn't been modified for 5 seconds, rename it
                        if time_difference > self.time_difference_min:
                            # Generate a new name with a prefix
                            new_name = f"DONE_{filename}"

                            # If the new name already exists, append a unique prefix
                            while os.path.exists(os.path.join(self.source_directory, new_name)):
                                unique_prefix = str(uuid.uuid4())[:8]  # Generate a unique prefix
                                new_name = f"DONE_{unique_prefix}_{filename}"

                            new_path = os.path.join(self.source_directory, new_name)

                            # Rename the file
                            os.rename(file_path, new_path)
                            print(f"Renamed {filename} to {new_name}")

                except OSError as e:
                    print(f"Error processing file {filename}: {e}")
        except FileNotFoundError as e:
            print(f"Error: Directory not found - {self.source_directory}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


class FileMover:
    def __init__(self):
        try:
            with open("config.yaml", 'r', encoding="utf-8") as f:
                data = yaml.load(f, yaml.Loader)
                self.source_directory = data['source_directory']
                self.staging_directory = data['staging_directory']
                self.time_difference_min = data['time_difference_min']
                self.source_endpoint = data['source_endpoint']
                self.source_path = data['source_path']
                self.destination_endpoint = data['destination_endpoint']
                self.destination_path = data['destination_path']
                self.flow_uuid = data['flow_uuid']
        except FileNotFoundError:
            print("Error: The specified YAML file does not exist.")
        except yaml.YAMLError as e:
            print(f"Error: YAML parsing error - {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def move_files_with_prefix(self):
        try:
            # TODO: Ideally not have this in production.
            if not os.path.isdir(self.staging_directory):
                os.makedirs(self.staging_directory)

            for filename in os.listdir(self.source_directory):
                file_path = os.path.join(self.source_directory, filename)

                try:
                    # Check if the file has "PREFIX" in its name
                    if "DONE_" in filename:
                        # Each move gets a unique directory inside destination_directory, to avoid race conditions that
                        # can result in data loss
                        path_unique_suffix = str(uuid.uuid4())[:8]  # Generate a unique suffix

                        if not os.path.isdir(os.path.join(self.staging_directory,path_unique_suffix)):
                            os.makedirs(os.path.join(self.staging_directory,path_unique_suffix))

                        destination_path = os.path.join(os.path.join(self.staging_directory,path_unique_suffix), filename)

                        # If the destination file already exists, append a unique prefix
                        while os.path.exists(destination_path):
                            unique_suffix = str(uuid.uuid4())[:8]  # Generate a unique suffix
                            destination_path = os.path.join(
                                os.path.join(self.staging_directory,path_unique_suffix),
                                f"{os.path.splitext(filename)[0]}_{unique_suffix}{os.path.splitext(filename)[1]}"
                            )

                        shutil.move(file_path, destination_path)
                        print(f"Moved {filename} to {destination_path}")
                        self.run_flow_basic(path_unique_suffix)

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

    def run_flow_basic(self, path_unique_suffix):
        _source_path = f"{self.source_path}{path_unique_suffix}"
        # Inputs to the flow
        flow_input = f'{{"source": {{"id": "{self.source_endpoint}","path": "{_source_path}",}},"destination": {{"id": "{self.destination_endpoint}","path": "{self.destination_path}"}}}}'
        flow_input = json.dumps(flow_input)
        globus_command = f"globus-automate flow run {self.flow_uuid} --flow-input {flow_input} --label photonics-data-move"
        print(self.source_endpoint)
        print(self.source_path)
        print(self.destination_endpoint)
        print(self.destination_path)
        print(_source_path)
        print(flow_input)
        os.system(globus_command)


if __name__ == "__main__":
    # Instantiate required class objects
    file_renamer = FileRenamer()
    file_mover = FileMover()

    while True:
        try:
            file_renamer.rename_files()
            time.sleep(1)  # Check every 1 second for changes
            file_mover.move_files_with_prefix()
        except KeyboardInterrupt:
            print("Program terminated by user.")
            break
