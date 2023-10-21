import datetime
from typing import Tuple

import typer

from src.grabber import download_latest_mrms, load_latest_mrms
from src.graphs import save_figs, generate_gif, generate_map, graph_builder
from src.model import nowcast
from src.system_functions import keep_latest_mrms, save_to_github, keep_latest_images
from src.tools import timed_nowcast, timed_excedance
import time


class Caster:
    def __init__(self, save_path: str, nb_observations: int = 30, nb_forecasts: int = 12, window_size=4, modified_shape = None):
        # Get saving path containing both img and data folder
        self.save_path = save_path
        # Get time
        self.minute = '{:02d}'.format(datetime.datetime.now().minute)
        self.hour = '{:02d}'.format(datetime.datetime.now().hour)
        self.day = '{:02d}'.format(datetime.datetime.now().day)
        self.month = '{:02d}'.format(datetime.datetime.now().month)
        self.year = datetime.datetime.now().year
        # Target url to load mrms from
        self.url = f'https://mtarchive.geol.iastate.edu/{self.year}/{self.month}/{self.day}/mrms/ncep/PrecipRate/'
        self.n_url = None
        if datetime.datetime.now().hour > 20:
            n_day = '{:02d}'.format((datetime.datetime.now()+datetime.timedelta(days=1)).day)
            n_month = '{:02d}'.format((datetime.datetime.now()+datetime.timedelta(days=1)).month)
            n_year = (datetime.datetime.now()+datetime.timedelta(days=1)).year
            # Traget url for the next day
            self.n_url = f'https://mtarchive.geol.iastate.edu/{n_year}/{n_month}/{n_day}/mrms/ncep/PrecipRate/'
        # Get the number of observations to download
        self.nb_observations = nb_observations
        # Get the window size
        self.window_size = window_size
        # Get the number of window times ahead
        self.nb_forecasts = nb_forecasts
        # Retrieve shape
        self.modified_shape = modified_shape

    def __call__(self, *args, **kwargs):
        # Download latest mrms data with a number of opservations equal to nb_observations
        download_latest_mrms(self.url,self.n_url, self.save_path, self.nb_observations)
        # Delete the old mrms file and keep only the ones we need
        keep_latest_mrms(self.save_path, self.nb_observations)
        # Load the mrms files
        precip, last_timestep = load_latest_mrms(self.save_path, self.window_size, self.modified_shape)
        # Compute the nowcasting
        excedance, nowcast_linda = nowcast(precip, nb_forecasts=self.nb_forecasts, threshold=1)
        # Build teh graphs
        nowcast_linda = timed_nowcast(nowcast_linda, last_timestep)
        graph_builder(save_path=self.save_path, nowcast_linda=nowcast_linda, window_size=self.window_size, modified_shape=self.modified_shape, precip=precip)
        # Generate time for each step
        excedance = timed_excedance(excedance, last_timestep)
        # Save the figures
        save_figs(excedance, self.save_path, self.window_size, self.modified_shape)
        # Keep the latest images
        keep_latest_images(self.save_path, self.nb_forecasts)
        # Generate the gif
        generate_gif(self.save_path)
        # Generate map
        generate_map(self.save_path, self.nb_forecasts, window_size=self.window_size, modified_shape=self.modified_shape)
        # To github
        save_to_github(
            save_path=self.save_path,
            hour=self.hour,
            minute=self.minute,
            month=self.month,
            day=self.day,
            year=self.year
        )


def main(save_path: str = typer.Option(None), nb_observations: int = typer.Option(None),
         nb_forecasts: int = typer.Option(None),
         window_size: int = typer.Option(None)):
    start = time.time()
    modified_shape = None
    caster = Caster(save_path, nb_observations, nb_forecasts, window_size, modified_shape)
    caster()
    print("############################\nNowcasting done .. Time taken :", time.time() - start)


if __name__ == '__main__':
    typer.run(main)
