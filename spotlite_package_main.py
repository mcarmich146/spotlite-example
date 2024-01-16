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
from geopy.geocoders import Nominatim
import re
from spotlite import Spotlite, TaskingManager
# from subscriptionUtils import load_subscriptions, list_subscriptions, add_subscription, delete_subscription

# application imports
import config
# from satellogicUtils import get_lat_long_from_place, ensure_dir
from satellogicTaskingAPI import gather_task_inputs

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
        print("7. Run Subscription Monitor.")
        print("8. Dump Footprints.")
        print("9. Satellite Tasking Menu.")
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

            save_and_animate = input("Save and Animate (y/n)?: ").lower() or "y" # apply this to every aoi.
            spotlite.create_tile_stack_animation(points, width, start_date, end_date, save_and_animate)

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
        elif user_choice == '7': # Run Subscription Monitor.
            spotlite.monitor_subscriptions_for_captures()
        elif user_choice == '8': # Dump capture footprints for AOI and time range
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
        elif user_choice == '9': # Manage Taskings.
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
        
        elif user_choice == 'q': # Q for quit
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
            continue

if __name__ == "__main__":
    main()
