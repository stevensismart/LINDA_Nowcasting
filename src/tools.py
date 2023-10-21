import datetime

import folium
import numpy as np
import requests
from PIL import Image, ImageChops
from bs4 import BeautifulSoup
from cartopy import crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter


def trim(img):
    border = Image.new(img.mode, img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, border)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        img = img.crop(bbox)
    return np.array(img)


def read_img(name):
    img = Image.open(name)
    img = trim(img)
    return img


def add_gif(m, name, gif_file, bounds, flag):
    feature_group = folium.FeatureGroup(name=name, show=flag)
    image_overlay = folium.raster_layers.ImageOverlay(gif_file, bounds=bounds, opacity=0.5, pixelated=True,
                                                      origin="lower", )
    feature_group.add_child(image_overlay)
    feature_group.add_to(m)


def listFD(url):
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith('gz')]


def map_settings(ax, lon_ticks, lat_ticks, domain):
    # Set up and label the lat/lon grid
    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.set_extent(domain, crs=ccrs.PlateCarree())


def timed_excedance(nowcast_linda, last_timestep):
    return {last_timestep + datetime.timedelta(minutes=10 * (e + 1)): nowcast_linda[e, :, :] for e in
            range(nowcast_linda.shape[0])}


def timed_nowcast(nowcast_linda, last_timestep):
    return {last_timestep + datetime.timedelta(minutes=10 * (e + 1)): nowcast_linda[:, e, :, :] for e in
            range(nowcast_linda.shape[1])}
