# Copyright (c) 2023 Satellogic USA Inc. All Rights Reserved.
#
# This file is part of Spotlite.
#
# This file is subject to the terms and conditions defined in the file 'LICENSE',
# which is part of this source code package.

# standard library imports
from datetime import datetime
from pathlib import Path
import os

# third-party imports
import webbrowser
import tkinter as tk
from tkinter import filedialog
import logging
from dateutil.relativedelta import relativedelta
from PIL import ImageFont
import pandas as pd
import geopandas as gpd
import folium
from geopy.geocoders import Nominatim
import re
from spotlite import Spotlite
from segment_images import Segmenter

# application imports
import config

def get_lat_long_from_place(place):
    # The regex below matches a pattern like '-34.2355, 19.2157'
    lat_long_pattern = re.compile(r'^-?\d+\.\d+,\s*-?\d+\.\d+$')
    if lat_long_pattern.match(place):
        # If the input matches the lat-long pattern, split it into lat and long
        lat, lon = map(float, place.split(','))
        return lat, lon
    else:
        geolocator = Nominatim(user_agent="ZXCVBGFDSAaasdfg12413415")
        location = geolocator.geocode(place)
        lat, lon = location.latitude, location.longitude

    return lat, lon

def _get_font() -> ImageFont:
    """Returns either a specified font or falls back to the default font."""
    try:
        font_path = config.FONT_PATH

        # if path exists
        if Path(font_path).is_file():
            logging.info("using custom font: '%s'", font_path)
            enlarged_font_size = 100
            font = ImageFont.truetype(font_path, enlarged_font_size)

        else:
            logging.info("specified font path not found: '%s'", font_path)
            raise AttributeError

    except AttributeError:
        logging.info("using default font.")
        font = ImageFont.load_default()

    return font

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def main():
    # Make Sure All The Directories Are Present
    ensure_dir("log")
    ensure_dir("images")
    ensure_dir("maps")
    ensure_dir("invalid_outcome_ids")
    ensure_dir("search_results")
    ensure_dir("points_to_monitor")

    # Setup Logging
    now = datetime.now().strftime("%d-%m-%YT%H%M%S")
    logging.basicConfig(filename=f"log/UserApp-{now}.txt", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # Add StreamHandler to log to console as well
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logging.getLogger().addHandler(console)

    place = ""

    # print(f"Keys: {config.KEY_ID}, {config.KEY_SECRET}")
    spotlite = Spotlite(config.KEY_ID, config.KEY_SECRET)

    while True:
        print("\nOptions:")
        print("1. Search And Animate Site.")
        print("2. Create Cloud Free Basemap.")
        print("3. Create Heatmap Of Collection Age.")
        print("4. Create Heatmap Of Imagery Depth.")
        print("5. Create Heatmap Of Cloud Cover.")
        print("6. Download Tiles For BBox.")
        print("7. Download Specific Image Id (Outcome_Id)")
        print("8. Run Subscription Monitor.")
        print("9. Dump Footprints.")
        print("10. Satellite Tasking Menu.")
        print("11. Extract Objects.")
        print("q. For Quit...")

        user_choice = input("Enter your choice: ")
        if user_choice == '1':
            use_geojson = input("Do you have a geojson POINT file (y/n)?: ").lower()

            if use_geojson == 'y':
                # Open the file dialog to select the GeoJSON file
                root = tk.Tk()
                root.withdraw()
                geojson_filepath = filedialog.askopenfilename(title="Select GeoJSON file",
                                                            filetypes=[("GeoJSON files", "*.geojson")])
                if geojson_filepath:
                    logging.info(f"GeoJSON file selected: {geojson_filepath}")
                    tiles_gdf = gpd.read_file(geojson_filepath)
                    points = [{'lat': row.geometry.y, 'lon': row.geometry.x} for index, row in tiles_gdf.iterrows()]
                else:
                    logging.warning("No file selected. Please try again.")
                    # Optionally, add logic to re-prompt the user or handle this situation
                    break
            else:
                place = input(f"Enter the place name or lat,lon in dec. deg.: ")
                lat, lon = get_lat_long_from_place(place)
                points = [{'lat': lat, 'lon': lon}]

            # Set the Bbox width
            width = float(input("Provide search box width (km):"))

            # Get the current date and calculate the date one month prior
            now = datetime.now()
            one_month_ago = now - relativedelta(months=1)

            # Format the dates to string (YYYY-MM-DD)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')

            start_date = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            end_date = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            logging.info(f"Date Range For Search: {start_date} - {end_date}")

            save_and_animate = input("Save and Animate (y/n)? [n]: ").lower() or "n" # apply this to every aoi.
            spotlite.create_tile_stack_animation(points, width, start_date, end_date, save_and_animate)

            # extract_objects = input("Extract Objects (y/n)? [n]: ").lower() or "n"


        elif user_choice == '2': # Create Cloud Free Tile Basemap - Works but seem like non-sense?
            logging.warning("Create Cloud Free Tile Basemap.")
            # Open the file dialog to select the GeoJSON file
            logging.warning("Provide geojson polygon file.")
            root = tk.Tk()
            root.withdraw()
            geojson_filepath = filedialog.askopenfilename(title="Select GeoJSON file",
                                                        filetypes=[("GeoJSON files", "*.geojson")])
            if geojson_filepath:
                logging.info(f"GeoJSON file selected: {geojson_filepath}")
                tiles_gdf = gpd.read_file(geojson_filepath)
                search_aoi = tiles_gdf.iloc[0].geometry.__geo_interface__
            else:
                logging.warning("No geojson file!")
                break

            # Format the dates to string (YYYY-MM-DD)
            # Get the current date and calculate the date one month prior
            now = datetime.utcnow()
            one_month_ago = now - relativedelta(months=1)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
            search_start_date_str = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            search_end_date_str = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            logging.warning(f"Date Range For Search: {search_start_date_str} - {search_end_date_str}")

            spotlite.create_cloud_free_basemap(search_aoi, search_start_date_str, search_end_date_str)

        elif user_choice == '3': # Create heatmap of imagery age.
            # Open the file dialog to select the GeoJSON file
            print("Provide geojson polygon file.")
            root = tk.Tk()
            root.withdraw()
            geojson_filepath = filedialog.askopenfilename(title="Select GeoJSON file",
                                                        filetypes=[("GeoJSON files", "*.geojson")])
            if geojson_filepath:
                logging.info(f"GeoJSON file selected: {geojson_filepath}")
                tiles_gdf = gpd.read_file(geojson_filepath)
                search_aoi = tiles_gdf.iloc[0].geometry.__geo_interface__
            else:
                logging.warning("No geojson file!")
                break

            # Format the dates to string (YYYY-MM-DD)
            # Get the current date and calculate the date one month prior
            now = datetime.utcnow()
            one_month_ago = now - relativedelta(months=1)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
            search_start_date_str = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            search_end_date_str = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            logging.warning(f"Date Range For Search: {search_start_date_str} - {search_end_date_str}")

            spotlite.create_age_heatmap(search_aoi, search_start_date_str, search_end_date_str)

        elif user_choice == '4': # Create Heatmap for Stack Depth
            logging.warning("Create Heatmap Of Depth Of Stack.")
            # Open the file dialog to select the GeoJSON file
            logging.warning("Provide geojson polygon file.")
            root = tk.Tk()
            root.withdraw()
            geojson_filepath = filedialog.askopenfilename(title="Select GeoJSON file",
                                                        filetypes=[("GeoJSON files", "*.geojson")])
            if geojson_filepath:
                logging.info(f"GeoJSON file selected: {geojson_filepath}")
                tiles_gdf = gpd.read_file(geojson_filepath)
                search_aoi = tiles_gdf.iloc[0].geometry.__geo_interface__
            else:
                logging.warning("No geojson file!")
                break

            # Format the dates to string (YYYY-MM-DD)
            # Get the current date and calculate the date one month prior
            now = datetime.utcnow()
            one_month_ago = now - relativedelta(months=1)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
            search_start_date_str = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            search_end_date_str = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            logging.warning(f"Date Range For Search: {search_start_date_str} - {search_end_date_str}")

            spotlite.create_count_heatmap(search_aoi, search_start_date_str, search_end_date_str)

        elif user_choice == '5': # Create for heat map for cloud cover for latest tiles.
            # Open the file dialog to select the GeoJSON file
            print("Provide geojson polygon file.")
            root = tk.Tk()
            root.withdraw()
            geojson_filepath = filedialog.askopenfilename(title="Select GeoJSON file",
                                                        filetypes=[("GeoJSON files", "*.geojson")])
            if geojson_filepath:
                logging.info(f"GeoJSON file selected: {geojson_filepath}")
                input_gdf = gpd.read_file(geojson_filepath)
                search_aoi = input_gdf.iloc[0].geometry.__geo_interface__
            else:
                logging.warning("No geojson file!")
                break

            # Format the dates to string (YYYY-MM-DD)
            # Get the current date and calculate the date one month prior
            now = datetime.utcnow()
            one_month_ago = now - relativedelta(months=1)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
            search_start_date_str = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            search_end_date_str = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            logging.warning(f"Date Range For Search: {search_start_date_str} - {search_end_date_str}")

            spotlite.create_cloud_heatmap(search_aoi, search_start_date_str, search_end_date_str)

            continue
        
        
        elif user_choice == '6': # Download Tiles For BBox
            place = input(f"Enter the place name or lat,lon in dec. deg.: ")
            lat, lon = get_lat_long_from_place(place)
            points = [{'lat': lat, 'lon': lon}]

            # Set the Bbox width
            width = float(input("Provide search box width (km):"))

            # Get the current date and calculate the date one month prior
            now = datetime.now()
            one_month_ago = now - relativedelta(months=1)

            # Format the dates to string (YYYY-MM-DD)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')

            start_date = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            end_date = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            logging.info(f"Date Range For Search: {start_date} - {end_date}")

            output_dir = None
            spotlite.download_tiles(points, width, start_date, end_date, output_dir)

        elif user_choice == '7': # Download Tiles For Specific Image Id 
            outcome_id = input(f"Provide Image Outcome_ID: ") or None
            output_dir = input("Provide custom output directory. [images/OutcomeId_<outcome_id>_<date>]") or None
            if outcome_id is None:
                logging.warning(f"No Image Id (Outcome_ID) Provided.  Sample Format: 28c202d1-291f-47dd-b59f-1e68159f1147--200217")
            
            now = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')

            if output_dir is None:
                output_dir = f"images/OutcomeId_{outcome_id}_{now}"
            spotlite.download_image(outcome_id, output_dir)
            continue

        elif user_choice == '8': # Run Subscription Monitor.
            # period = input("Enter Minutes Between Monitoring Runs [Return for Default]: ") or "240"
            # period_int = int(period)
            spotlite.monitor_subscriptions_for_captures()
        elif user_choice == '9': # Dump capture footprints for AOI and time range
            # Open the file dialog to select the GeoJSON file
            print("Provide search geojson polygon file.")
            root = tk.Tk()
            root.withdraw()
            geojson_filepath = filedialog.askopenfilename(title="Select GeoJSON file",
                                                        filetypes=[("GeoJSON files", "*.geojson")])
            if geojson_filepath:
                logging.info(f"GeoJSON file selected: {geojson_filepath}")
                input_gdf = gpd.read_file(geojson_filepath)
                search_aoi = input_gdf.iloc[0].geometry.__geo_interface__
            else:
                logging.warning("No geojson file!")
                break

            # Format the dates to string (YYYY-MM-DD)
            # Get the current date and calculate the date one month prior
            now = datetime.utcnow()
            one_month_ago = now - relativedelta(months=1)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
            search_start_date_str = input("Enter start date (YYYY-MM-DD, UTC) or press enter for 1 month ago: ") or one_month_ago_str
            search_end_date_str = input("Enter end date (YYYY-MM-DD, UTC or press enter for now: ") or end_date_str

            spotlite.save_footprints(search_aoi, search_start_date_str, search_end_date_str)
            
            continue
        elif user_choice == '10': # Manage Taskings.
            while True:
                print("Manage Taskings:")
                print("1. Create New Tasking Via API") 
                print("2. Check Status For TaskID ") 
                print("3. Cancel Task For TaskID") 
                print("4. Query and Download Image For ScenesetID") 
                print("5. Check Client Config.") 
                print("6. Search Products By Status.") 
                print("7. Check Available Product List.") 
                print("8. List Captures For TaskID.") 
                print("9. Monitor Taskings For Delivery.")
                print("q. Back to main menu.")
                sub_choice = input("Enter your choice: ")

                if sub_choice == '1':  # Create new tasking via API

                    task_params = gather_task_inputs()

                    tasking_df = spotlite.tasking_manager.create_new_tasking(task_params)
                    print(f"Tasking Result: {tasking_df}")
                    continue
                elif sub_choice == '2': # Check status of task
                    task_id = input("Enter Task Id: ")
                    print(f"Status: {spotlite.tasking_manager.task_status(task_id)}")
                    continue
                elif sub_choice == '3': # cancel_task
                    task_id = input("Enter Task Id: ")
                    print(f"Status: {spotlite.tasking_manager.cancel_task(task_id)}")
                    continue
                elif sub_choice == '4': # query_and_download_image
                    scene_set_id = input("Enter SceneSetID?: ")
                    download_dir = input("Target Relative Download Directory? (images):") or None
                    print(f"Downloaded Image Filename: {spotlite.tasking_manager.download_image(scene_set_id, download_dir)}")
                    continue
                elif sub_choice == '5': # Check Client Config
                    print(f"Client Config: {spotlite.tasking_manager.check_account_config()}")
                elif sub_choice == '6': # Search products by status.
                    status = input("Provide Status To Query [ALL]: ") or ""
                    df = spotlite.tasking_manager.query_tasks_by_status(status)
                    pd.set_option('display.max_rows', None)  # Show all rows
                    pd.set_option('display.max_columns', None)  # Show all columns
                    pd.set_option('display.width', None)  # Auto-detect the display width

                    print(f"Product Columns: {df.columns}")
                    print(f"Products Result: {df}")
                elif sub_choice == '7': # Check available products list.
                    df = spotlite.tasking_manager.query_available_tasking_products()
                    print(f"Availble Products: \n{df}")
                elif sub_choice == '8': # Check captures for task_id
                    task_id = input("Provide task_id: ")
                    if task_id:
                        response_json = spotlite.tasking_manager.capture_list(task_id)
                        if response_json is not None and 'capture_id' in response_json.columns:
                            for idx, row in response_json.iterrows():
                                print(f"Capture ID: {row['capture_id']}, Start: {row['start']}, Satellite: {row['satellite_name']}, Status: {row['status']}")
                        else:
                            print("No results found or error in API call.")
                    continue
                elif sub_choice == '9': # Run a monitor service to track when ordered imagery arrives and send an email to the user.
                    # This runs as a service until it fails or is cancelled.
                    check_interval_min = (input(f"How many minutes between checks? [10min]: ")) or 10
                    check_interval_sec = check_interval_min
                    spotlite.tasking_manager.monitor_task_status(check_interval_sec)
                    continue
                elif sub_choice == 'q': # Return to main menu
                    break
                else:
                    print("Invalid Choice.")
                    continue

        elif user_choice == '11': # Extract Objects
            place = input(f"Enter the place name or lat,lon in dec. deg.: ")
            lat, lon = get_lat_long_from_place(place)
            points = [{'lat': lat, 'lon': lon}]

            # Set the Bbox width
            width = float(input("Provide search box width (km):"))

            # Get the current date and calculate the date one month prior
            now = datetime.now()
            one_month_ago = now - relativedelta(months=1)

            # Format the dates to string (YYYY-MM-DD)
            end_date_str = now.strftime('%Y-%m-%d')
            one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')

            start_date = input("Enter start date (YYYY-MM-DD) or press enter for 1 month ago: ") or one_month_ago_str
            end_date = input("Enter end date (YYYY-MM-DD) or press enter for now: ") or end_date_str
            prompt = input(f"Enter Prompt For Search (short text string): ") or None
            if prompt is None:
                logging.error(f"Prompt is invalid: {prompt}")
                continue

            box_threshold = input("Box_Threshold [0.24]: ?") or 0.24
            text_threshold = input("Text_Threshold [0.24]: ?") or 0.24

            logging.info(f"Date Range For Search: {start_date} - {end_date}")

            output_dir = None
            tiles_filename_list = spotlite.download_tiles(points, width, start_date, end_date, output_dir)

            logging.warning(f"tiles_filename_list: {tiles_filename_list}")
            box_threshold_float = float(box_threshold)
            text_threshold_float = float(text_threshold)
            segmenter = Segmenter(box_threshold_float, text_threshold_float)
            for filename in tiles_filename_list:
                segmenter.segment_image(filename, prompt)

        elif user_choice == 'q': # Q for quit
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
            continue



def map_desired_tasking_location(lat, lon):
    # Create map and add task location
    mp = folium.Map(location=[lat, lon], tiles="CartoDB dark_matter", zoom_start=13)
    folium.Marker([lat, lon]).add_to(mp)

    # Save the map to an HTML file
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    map_filename = f'images/Tasking_Map_{now}.html'
    os.makedirs(os.path.dirname(map_filename), exist_ok=True)
    mp.save(map_filename)

    # Open the HTML file in the default web browser
    webbrowser.open('file://' + os.path.realpath(map_filename))

def validate_date_range(date_range_str):
    try:
        # Split the date_range_str into start_date_str and end_date_str
        start_date_str, end_date_str = date_range_str.split()

        # Parse the date strings into datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%SZ')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%SZ')

        # Check that the start date is before the end date
        if start_date >= end_date:
            print("Start date must be before end date.")
            return False
        return True
    except ValueError as ve:
        print(f"Invalid date format: {ve}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def validate_coordinates(value):
    try:
        float_value = float(value)
        return -180 <= float_value <= 180
    except ValueError:
        return False

def validate_expected_age(value):
    pattern = re.compile(r"(\d+ days, \d{2}:\d{2}:\d{2})")
    return bool(pattern.match(value))

def validate_date(value):
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
        return True
    except ValueError:
        return False


def get_input(prompt, validation_func=None, default_value=None):
    while True:
        user_input = input(prompt + f" (Default: {default_value}): ") or default_value
        if validation_func and not validation_func(user_input):
            print("Invalid input, please try again.")
        else:
            return user_input

def gather_task_inputs():
    # Gather inputs from the user or allow for defaults
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    project_name = get_input("Enter the project name:", default_value=f"API_Testing")
    task_name = get_input("Enter the task name:", default_value=f"API_Task_{now}")

    product = int(get_input("Enter the product number (169):", validation_func=lambda x: x.isdigit(), default_value="169"))
    max_captures = int(get_input("Enter the maximum number of captures (1):", validation_func=lambda x: x.isdigit(), default_value="1"))
    expected_age = get_input("Enter the expected age (7 days, 00:00:00):", validation_func=validate_expected_age, default_value="7 days, 00:00:00")

    print("Enter the target coordinates (lat/long, dec deg):")
    lat_lon = input("Enter the latitude and longitude (format: lat,lon): ")
    lat, lon = map(float, lat_lon.split(','))  # This will split the input string into lat and lon, and convert them to floats

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')  # Get the current UTC date and time in the desired format
    one_month_later = (datetime.utcnow() + relativedelta(months=1)).strftime('%Y-%m-%dT%H:%M:%SZ')  # Get the date and time one month later in the desired format

    # start_date = get_input("Enter the capture window start(YYYY-MM-DDThh:mm:ssZ):", validation_func=validate_date, default_value=now)
    # end_date = get_input("Enter the capture window end (YYYY-MM-DDThh:mm:ssZ):", validation_func=validate_date, default_value=one_month_later)

    # Set a default date range
    default_date_range = f"{now} {one_month_later}"

    date_input = get_input(
        f"Enter the capture window start and end (format: {default_date_range}):",
        validation_func=validate_date_range,  # You'll need to define this function
        default_value=default_date_range
    )

    # Split the input into start and end dates
    start_date, end_date = date_input.split()

    task = {
        "project_name": project_name,
        "task_name": task_name,
        "product": product,
        "max_captures": max_captures,
        "expected_age": expected_age,
        "target": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "start": start_date,
        "end": end_date
    }
    print(task)
    map_desired_tasking_location(lat, lon)
    return task

if __name__ == "__main__":
    main()
