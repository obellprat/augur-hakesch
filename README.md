# augur-hakesch
Augur-Hakesch is an AUGUR application for river discharge calculations based on the Swiss HAKESCH method after re-calibration on selected catchments and new precipitation climatology from the Swiss Federal Office of Meteorology and Climatology. 

# installation
## local installation and developement
The local developement process for Augur-Hakesch is based on Task ([https://taskfile.dev/]). After git checkout run
    pip install go-task-bin

Next download the example dem / dir from online sources to /src/api/data and build the frontend. For this ust call
    task init

To run it locally
    task dev

and the app is accessible on http://localhost:8000 (it needs to start some minutes)