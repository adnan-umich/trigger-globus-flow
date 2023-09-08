# trigger-globus-flow

# Requirements
* Python >= 3.6
* Pipenv

# Pipenv Route Installation Instructions
1) `git clone https://github.com/adnan-umich/trigger-globus-flow.git`
2) `cd trigger-globus-flow`
3) `py -m pipenv install`

# Pipenv Route Installation Instructions
1) `git clone https://github.com/adnan-umich/trigger-globus-flow.git`
2) `cd trigger-globus-flow`
3) `virtualenv venv`
4) `source venv/bin/activate`
5) WINDOWS `. venv\Scripts\activate`
6) `pip install - requirements.txt`

# Configuration
Specified in the config.yaml file. Modify as needed.
  ```source_directory : 'C:\data'
  staging_directory : 'C:\Users\data\ready'
  time_difference_min : 5
  flow_uuid : 'xxxx-xxxx-xxxxxxx-xxxxxx'
  source_endpoint: 'xxxx-xxxx-xxxxxxx-xxxxxx'
  source_path : '/C/Users/data/ready/'
  destination_endpoint: ''xxxx-xxxx-xxxxxxx-xxxxxx''
  destination_path : '.'````