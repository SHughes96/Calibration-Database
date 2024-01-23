# Calibration Database

Welcome to the WEAVE calibration database repository!
This contains the scripts I built to process, ingest, and recall entries from the WEAVE fibre positioner log files to improve its ability to accurately place optical fibres.

The processing of the logfiles in process_logfile.py is a prototype with many exception cases as the instrument is still undergoing development. This script was made to quickly grab the required information and has not been optimised. 
It is currently being reformatted to use machine code directly due to the complexity of the logfiles, with additional information being tracked from the instrument over time, resulting in changes to the logfile structure.

## Overview

**create_database.py**
Initialise the class fibre_database to create a local database, which contains three tables, one for each movement type being tracked. These are referred to as 'Move', 'Park', and 'Unpark'.
Methods:
- create_tables()
- add_move()
- check_count()
- update_move()
- count_all_moves()
- evaluate_logfile()
- get_attribute()
- scrub_fibre_entries()

**process_logfile.py**
The log_extraction class extracts the fibre movement information from an individual log file and formats the data to be ingested by the database_entry class into the local database fibre_moves.db

Methods:

Class log_extraction
- extract_fibres_moved()
- find_move_info()
- updated_find_timestamps_and_positions()

Class database_entry:
- add_fibre_move_entries()
- evaluate_logfile()
- add_entries_both_plates()
