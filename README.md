# spotlite-example - Example code showing how to use Satellogic "spotlite" package to interact with the Archive API.

## PURPOSE:
This app is intended to exercise the API in a demo centric way
that allows the user to follow their predicted user CONOPS lifecycle (below).

The inspiration for this package came from the Life Cycle Steps (based on the [TCPED](https://www.dhs.gov/sites/default/files/publications/FactSheet%20TCPED%20Process%20Analysis%202016.12.12%20FINAL_1_0.pdf) life cycle):
1. User enters place name or lat/long for search
2. Search the archive for tiles and visualize them.
3. Access the full resolution Rapid Response products
4. Animate tiles time sequence for context and change monitoring
5. Order different product formats
6. Create new subscription areas to monitor for images coming in
7. Analyze tiles to extract analytics/information/intelligence
8. Create new tasking activities for high priority POIs
9. Repeat

## MAIN FUNCTION ACTIVITIES

The main functions provided in the spotlite_main.py are captured below.

The menus are:

Options:
1. Search And Animate Site.
2. Create Cloud Free Basemap.
3. Create Heatmap Of Collection Age.
4. Create Heatmap Of Imagery Depth.
5. Create Heatmap Of Cloud Cover.
6. Download Tiles For BBox.
7. Run Subscription Monitor.
8. Dump Footprints.
8. Satellite Tasking Menu.
q. For Quit...

## INSTALLATION

The user of this app needs to run the python script within a setup environment.
You will need to setup the environment in a virtual environment:

### Linux Installation

#### Install GDAL with brew

```bash
brew update
brew upgrade
brew install gdal
brew doctor
```

### Setup virtualenv

```bash
python -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
```

### Windows installation

Conda is required.  Ensure it is installed on your machine, then perform the following.

```bash
conda env create -f envionment.yaml
```

### Install Spotlite

You can use pip to install the Spotlite distribution.

```bash
pip install spotlite
```

## HOW TO RUN APPLICATION

Then you can run the app menu.

```bash
python ./spotlite_package_main.py
```

You follow the prompts from there.  Some functions are more mature than others.
Search and Animate Site, Create Heatmaps, Download Tiles and Dump Footprints are my favorite.

Other services in this app that need to be started and left running in your terminal for them
to work for you in the background.

Capture Subscription Monitoring Service - This service runs in the background and searches on a periodic basis for imagery captured in 
the last period and creates an email notification with map of the images so you can find the new imagery and copy paste references to the images by clicking on the markers and copying the text from the popup.  Use the option: 7. Run Subscription Monitor.

## config.py file contents

Place at root dir and replace the KEY_ID and KEY_SECRET with your credentials obtained from Satellogic.

```bash
# Define your configurations here, for example:
KEY_ID = "GetFromSatellogic"
KEY_SECRET = "GetFromSatellogic"
```
