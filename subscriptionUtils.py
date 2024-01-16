# Copyright (c) 2023 Satellogic USA Inc. All Rights Reserved.
#
# This file is part of Spotlite.
#
# This file is subject to the terms and conditions defined in the file 'LICENSE',
# which is part of this source code package.

from time import sleep
import json
import geopandas as gpd
from shapely.geometry import shape
import os
import uuid
import smtplib
import json
import geojson
from datetime import datetime, timedelta
import config
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from requests import HTTPError
from selenium import webdriver
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Tuple, Dict, Optional, List, Type
from shapely.geometry import Polygon, Point, box
import logging
from spotlite import Spotlite, TaskingManager
import pandas as pd

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
subcDb = config.SUBSCRIPTIONS_FILE_PATH
password = config.EMAIL_PASSWORD
from_email = config.EMAIL_ADDRESS
period = config.SUBC_MON_FREQUENCY # In Minutes

Spotlite = Searcher(config.KEY_ID, config.KEY_SECRET)
visualizer = Visualizer()

def build_service():
    # flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    # creds = flow.run_local_server(port=0)

    # service = build('gmail', 'v1', credentials=creds)
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def load_subscriptions(input_subc_file_path=None):
    if input_subc_file_path != None:
        subc_path = input_subc_file_path
    else:
        subc_path = subcDb

    # Check if the file exists
    if not os.path.exists(subc_path):
        logger.error("Subscription DB not present.")
        return None  # Or handle the error as needed

    with open(subc_path, 'r') as f:
        data = json.load(f)
    return data

def save_subscriptions(data):
    with open(subcDb, 'w') as f:
        json.dump(data, f, indent=2)

def list_subscriptions():
    data = load_subscriptions()
    for sub in data['features']:
        subscription_id = sub['id']
        subscription_name = sub['properties']['subscription_name']
        emails = sub['properties']['emails']  # Accessing the list of emails
        polygon = sub['geometry']
        emails_str = ', '.join(emails) 
        print(f"ID: {subscription_id}, Name: {subscription_name}, \nEmails: {emails_str}, \nPolygon: {polygon}")

def add_subscription(user_emails: List[str], subscription_name: str, polygon: Polygon):  
    data = load_subscriptions()
    feature_collection = geojson.FeatureCollection(data['features'])

    new_feature = geojson.Feature(
        geometry=polygon,
        properties={
            'emails': user_emails,  # Storing multiple emails
            'subscription_name': subscription_name
        },
        id=str(len(feature_collection['features']) + 1)
    )

    feature_collection['features'].append(new_feature)
    save_subscriptions(feature_collection)

def delete_subscription(sub_id):
    data = load_subscriptions()
    updated_features = [feature for feature in data['features'] if feature['id'] != sub_id]
    data['features'] = updated_features
    save_subscriptions(data)

def delete_all_subscriptions(user_email):
    data = load_subscriptions()
    data[user_email] = []
    save_subscriptions(data)  # Adjusted argument

def add_subscription_from_file(user_email, name, geojson_file_path):
    with open(geojson_file_path, 'r') as f:
        geojson_data = json.load(f)
    polygon = geojson_data['features'][0]['geometry']['coordinates']
    add_subscription(user_email, name, polygon)

def send_email(to_email, subject, body, folium_html_path=None, plotly_html_path=None):
    service = build_service()
    
    # Create a MIMEMultipart message
    msg = MIMEMultipart()
    msg['bcc'] = to_email
    msg['subject'] = subject

    # Attach the body text
    msg.attach(MIMEText(body, 'html'))

    # # Attach the tiles image
    # if folium_png_path:
    #     with open(folium_png_path, 'rb') as img:
    #         mime_img = MIMEImage(img.read())
    #         mime_img.add_header('Content-ID', 'TilesMap')  # The image ID should match the one used in the body
    #         mime_img.add_header("Content-Disposition", "attachment", filename="tiles_map.png")
    #         msg.attach(mime_img)
        
    # # Attach the cloud image
    # if plotly_png_path:
    #     with open(plotly_png_path, 'rb') as img:
    #         mime_img = MIMEImage(img.read())
    #         mime_img.add_header('Content-ID', 'CloudMap')  # The image ID should match the one used in the body
    #         mime_img.add_header("Content-Disposition", "attachment", filename="cloud_map.png")
    #         msg.attach(mime_img)
    
    # Attach the HTML map
    if folium_html_path:
        with open(folium_html_path, 'r') as f:
            mime_html = MIMEText(f.read(), 'html')
            mime_html.add_header("Content-Disposition", "attachment", filename="tiles_map.html")
            msg.attach(mime_html)

    # Attach the Cloud HTML map   
    if plotly_html_path:
        with open(plotly_html_path, 'r', encoding='utf-8') as f:
            mime_html = MIMEText(f.read(), 'html')
            mime_html.add_header("Content-Disposition", "attachment", filename="cloud_cover_heatmap.html")
            msg.attach(mime_html)

    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    create_message = {'raw': raw_msg}

    try:
        message = (service.users().messages().send(userId="me", body=create_message).execute())
        logger.warning(f'Sent message to {to_email}, Message Id: {message["id"]}')
    except HTTPError as error:
        logger.error(f'An error occurred: {error}')
        message = None

def format_email_body_subject(subscription_name, sorted_aggregated_df):
    email_body = f"""
    <html>
        <body>
            <p>Dear Subscriber,</p>
            <p>We are excited to inform you that new imagery has been found in your subscription area: {subscription_name}.</p>
            <p>Here are the details of the new images - {len(sorted_aggregated_df)} New Captures:</p>
            <ul>
    """
    # Iterate over rows in the sorted_aggregated_df DataFrame
    for index, row in sorted_aggregated_df.iterrows():
        # Extract data from each row
        outcome_id = row['outcome_id']
        actual_capture_date = row['capture_date']
        cloud_cover_percentage = int(row['mean_cloud_cover'])  # Assuming mean_cloud_cover is in decimal form

        # Format the date if it's a datetime object
        if isinstance(actual_capture_date, datetime):
            actual_capture_date = actual_capture_date.strftime('%Y-%m-%d %H:%M:%S UTC')

        # Append information to the email body
        email_body += f"<li>Capture Date: {actual_capture_date}, Outcome ID: {outcome_id}, Cloud Cover: {cloud_cover_percentage}%</li>"

    email_body += """
            </ul>
            <p>Thank you for choosing our service!</p>
            <p>Best Regards From Your Team At Satellogic.</p>
            <p></p>
            <p>Note: to open the attached html map of the images you must download the file first.</p>
        </body>
    </html>
    """

    email_subject = f"DoNotReply - New Satellogic Imagery - {subscription_name}"
    return email_body, email_subject


def check_and_notify():
    data = load_subscriptions()
    for feature in data['features']:
        user_emails = feature['properties']['emails']  # Now we have a list
        subscription_name = feature['properties']['subscription_name']
        
        geojson_polygon = feature['geometry']
        shapely_polygon = shape(geojson_polygon)  # Convert GeoJSON to Shapely Polygon
        minx, miny, maxx, maxy = shapely_polygon.bounds  # Get the bounding box coordinates
        aoi = box(minx, miny, maxx, maxy) 

        foundTiles, _, sorted_aggregated_df, tiles_path_html, cloud_path_html = check_archive(aoi, period, subscription_name)  # adjusted to receive gdf_grouped
        if foundTiles == True:
            email_body, email_subject= format_email_body_subject(subscription_name, sorted_aggregated_df)
            to_emails = ', '.join(user_emails)  # Join all emails into a single string
            send_email(to_emails, email_subject, email_body, tiles_path_html, cloud_path_html)
        else:
            logger.error(f"No Images Found In This Search Polygon.")

def check_archive(aoi_box: Polygon, period: int, subsription_name: str):   
    # Create the search window in UTC 
    end_date = datetime.utcnow()  # Current date and time in UTC
    start_date = end_date - timedelta(minutes=period)  
    # start_date = end_date - timedelta(weeks=1)

    # Formatting dates to string as your `search_archive` might expect string input
    str_start_date = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    str_end_date = end_date.strftime('%Y-%m-%dT%H:%M:%S')
    logger.warning(f"\nSearching: {subsription_name} \nPeriod: {start_date.strftime('%Y-%m-%d %H:%M:%S UTC')} and {end_date.strftime('%Y-%m-%d %H:%M:%S UTC')} \nAOI: {aoi_box}")
    tiles_gdf, num_tiles, num_captures = searcher.search_archive(aoi_box, str_start_date, str_end_date)

    logging.warning(f"Search complete! Num Tiles: {num_tiles}, Num Captures: {num_captures}")
    
    # If no tiles found then return False.
    if num_tiles == 0:
        return False, 0, None, None, None  # adjusted to return 0 and None for consistency
    
    grouped = searcher.group_by_outcome_id(tiles_gdf)

    # Aggregate data: Get the first capture_date and outcome_id, and mean cloud cover for each group
    aggregated_data = []
    for outcome_id, group in grouped:
        capture_date = group.iloc[0]['capture_date']
        cloud_cover_mean = group['eo:cloud_cover'].mean()
        aggregated_data.append({'outcome_id': outcome_id, 
                                'capture_date': capture_date, 
                                'mean_cloud_cover': cloud_cover_mean})

    # Create a DataFrame from the aggregated data
    aggregated_df = pd.DataFrame(aggregated_data)

    # Sort the DataFrame by capture_date in descending order
    sorted_aggregated_df = aggregated_df.sort_values(by='capture_date', ascending=False)

    # Create the map
    lat, lon = compute_centroid(aoi_box) 

    points_list = [Point(lon, lat)]

    aois_list = [aoi_box]
    
    folium_map = visualizer.create_folium_map(points_list, aois_list)

    animation_filename = None
    
    # Create filenames with the current datetime
    current_datetime_str = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')
    folium_map_path_html = f"maps/Tiles_{current_datetime_str}.html"
    cloud_map_path_html = f"maps/Cloud_{current_datetime_str}.html"

    folium_map = visualizer.update_map_with_footprints(folium_map, tiles_gdf, animation_filename, aoi_box)  
    cloud_map = visualizer.cloud_heatmap(tiles_gdf)

    # Save the folium map
    folium_map.save(folium_map_path_html)

    # Save the cloud map as HTML
    cloud_map.write_html(cloud_map_path_html)


    # Save the map as an image
    # map_image_path_html = f'maps/folium-map-for-email.html'
    # map_image_path_png = f'maps/folium-map-for-email.png'
    # folium_map.save(map_image_path_html)
    # save_screen_shot(map_image_path_html, map_image_path_png, False)

    # cloud_map_path_html = f'maps/cloud-map-for-email.html'
    # cloud_map_path_png = f'maps/cloud-map-for-email.png'
    # cloud_map.write_html(cloud_map_path_html)
    # # cloud_map.write_image(cloud_map_path_png)
    # save_screen_shot(cloud_map_path_html, cloud_map_path_png, True)
                
    return True, len(tiles_gdf), sorted_aggregated_df, folium_map_path_html, cloud_map_path_html
    

def save_screen_shot(input_html_file_path, output_png_file_path, is_cloud):
    options = webdriver.ChromeOptions()
    # Disabling 3D APIs as per the solution found for WebGL error
    # options.add_argument('--disable-3d-apis')
    options.add_argument('headless')
    with webdriver.Chrome(options=options) as driver:
        driver.get(f'file:///{os.path.abspath(input_html_file_path)}')  # Provide absolute path with file:///
        sleep(5)
        
        if is_cloud == True:
            # Set zoom
            driver.execute_script("document.body.style.zoom='70%'")
            # Get the dimensions of the body and the window
            body_width = driver.execute_script("return document.body.scrollWidth")
            body_height = driver.execute_script("return document.body.scrollHeight")
            window_width = driver.execute_script("return window.innerWidth")
            window_height = driver.execute_script("return window.innerHeight")

            # Calculate center position
            center_x = (body_width - window_width) // 2
            center_y = (body_height - window_height) // 2

            # Scroll to center
            driver.execute_script(f"window.scrollTo({center_x}, {center_y})")
        driver.save_screenshot(output_png_file_path)

def compute_centroid(aoi_polygon):
    polygon_shape = shape(aoi_polygon)
    centroid = polygon_shape.centroid
    return centroid.y, centroid.x 
