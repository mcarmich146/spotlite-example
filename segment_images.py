# Copyright (c) 2023 Satellogic USA Inc. All Rights Reserved.
#
# This is a BETA Class that uses LangSAM to extract objects from images.
#
# This file is subject to the terms and conditions defined in the file 'LICENSE',
# which is part of this source code package.

from datetime import datetime
import leafmap
from samgeo.text_sam import LangSAM
import logging
from PIL import Image
import rasterio


logger = logging.getLogger(__name__)
tiles_gdf = None
    
class Segmenter:
    def __init__(self, box_threshold=0.24, text_threshold=0.24):
        # Assigning default values to instance attributes
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self._param = None  # Initialize _param for the property

    @property
    def param(self):
        return self._param

    @param.setter
    def param(self, value):
        self._param = value


    def segment_image(self, image_filename: str, text_prompt: str) -> leafmap:
        image_pil, lat, lon = self.open_geotiff_as_pil(image_filename)
        
        m = leafmap.Map(center=[lat, lon], zoom=14)  # Customize your map
        m.add_basemap("SATELLITE")  # Add more layers as needed

        logging.warning("Segment_Image Called.")
        
        m.layers[-1].visible = False
        m.add_raster(image_filename, layer_name="Image")

        sam = LangSAM()
        box_threshold = self.box_threshold
        text_threshold = self.text_threshold

        logging.warning(f"Calling Predict: {image_filename}, {text_prompt}, {box_threshold}, {text_threshold}.")
        sam.predict(image_pil, text_prompt, box_threshold, text_threshold)
        logging.warning("Predict Returned.")

        # Set the filenames
        now = datetime.now().strftime("%Y%m%dT%H%M%S")
        segmentation_raster_filename = f"analytics/segmentation_{now}.tif"
        # segmentation_shape_filename = f"analytics/segmentation_{now}.shp"
        output_html_filename = f"analytics/map_visualization_{now}.html"
        sam.show_anns(
            cmap='viridis',
            add_boxes=True,
            box_color='r',
            alpha=0.8,
            title=f"Automatic Segmentation of {text_prompt}",
            blend=True,
            output=segmentation_raster_filename,
        )

        logging.warning(f"Segmentation File Saved: {segmentation_raster_filename}")

        ## Save The Map ##
        # Save the map to the HTML file
        m.to_html(outfile=output_html_filename)

        logging.warning(f"Final Output: {output_html_filename}")

    def open_geotiff_as_pil(self, geoTIFF_path: str) -> Image.Image:
        with rasterio.open(geoTIFF_path) as src:
            # Get dimensions of the image
            width, height = src.width, src.height
            
            # Calculate the center pixel
            center_x, center_y = width // 2, height // 2
            
            # Convert the center pixel to geographic coordinates (longitude, latitude)
            lon, lat = src.xy(center_y, center_x)
            
            # For simplicity, this example assumes the GeoTIFF is 8-bit and has 3 bands (RGB).
            # Satellogic L1B (Quickview are indeed 8-bit, but are four band)
            red, green, blue = src.read([1, 2, 3])

            # Combine the bands into an RGB image (PIL expects the data in the opposite order).
            pil_image = Image.merge("RGB", [Image.fromarray(band) for band in [red, green, blue]])

        return pil_image, lat, lon