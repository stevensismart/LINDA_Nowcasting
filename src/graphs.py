import collections
import datetime
import os
from subprocess import Popen, PIPE, STDOUT

import folium
import numpy as np
import pandas as pd
from branca.element import Template, MacroElement
from cartopy import crs as ccrs
from folium.plugins import FloatImage
from folium.plugins import MeasureControl
from folium.plugins import MiniMap
from matplotlib import colors
from matplotlib import pyplot as plt
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from tqdm import tqdm

from src.assets import build_close_locations, ppf_estimates, locations
from src.tools import map_settings, add_gif


def generate_coordinates(window_size, lat_min, lat_max, lon_min, lon_max):
    lat = [e / 100 for e in range(int(lat_max * 100), int(lat_min * 100), -(window_size))]
    lon = [e / 100 for e in range(int(lon_min * 100), int(lon_max * 100), window_size)]
    return lon, lat


def generate_est_texts(save_path):
    # Get the name of the files
    file_names = {os.path.getmtime(os.path.join(save_path, 'img', f)): os.path.join(save_path, 'img', f) for f in
                  os.listdir(os.path.join(save_path, 'img')) if
                  os.path.isfile(os.path.join(save_path, 'img', f)) and f.endswith('png')}
    od = collections.OrderedDict(sorted(file_names.items()))
    od = [od[_key][-16:-4] for _key in list(od)]
    od = [f'{_key[8:10]}:{_key[10:]} {_key[4:6]}/{_key[6:8]}/{_key[:4]} EST' for _key in od]
    return od



def generate_gif(save_path):
    # photos = [os.path.join(save_path,'img',e) for e in os.listdir(os.path.join(save_path,'img')) if e.endswith('.png')]
    # photos.sort()
    cmd = ["convert", "-delay", '100', '-colors', '16', '-fuzz', '2%', '-loop', '0', '-dispose', 'background',
           '$(ls -1', os.path.join(save_path, 'img', '*.png'), '| sort -V)',
           os.path.join(save_path, 'img', 'mrms.gif')]
    cmd = ' '.join(cmd)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read()
    print(output)


def save_figs(nowcast_linda, save_path, window_size, modified_shape):
    if not modified_shape:
        lat_min = 20
        lat_max = 55
        lon_min = -130
        lon_max = -60
    else:
        # Generate the lon couples
        lon_couples = [(e, (-130 + (e / 100))) for e in range(7000)]
        lat_couples = [(e, (55 - (e / 100))) for e in range(3500)]
        # Select the coordinates for longitude
        lon_min = [e for e in lon_couples if e[0] == modified_shape[0][0]]
        lon_min = lon_min[0][1]
        lon_max = [e for e in lon_couples if e[0] == modified_shape[0][1]]
        lon_max = lon_max[0][1]
        # Select the coordinates for latitude
        lat_max = [e for e in lat_couples if e[0] == modified_shape[1][0]]
        lat_max = lat_max[0][1]
        lat_min = [e for e in lat_couples if e[0] == modified_shape[1][1]]
        lat_min = lat_min[0][1]

    lon, lat = generate_coordinates(window_size, lat_min, lat_max, lon_min, lon_max)

    # Boundaries of map: [western lon, eastern lon, southern lat, northern lat]
    domain = [lon_min, lon_max, lat_min, lat_max]

    lon_ticks = [-81, -73, -64]
    lat_ticks = [36, 38, 41, 44]

    for _date in tqdm(list(nowcast_linda), desc="Generating layers ..."):
        fig = plt.figure(figsize=(11, 8))
        ax = plt.axes(projection=ccrs.PlateCarree())

        map_settings(ax, lon_ticks, lat_ticks, domain)

        bar = 'rainbow'  # Color map for colorbar and plot
        max_color = 'darkred'  # Color for Rad data > 1
        # Plotting settings for AOD data
        color_map = plt.get_cmap(bar)
        color_map.set_over(max_color)

        levels = [round(e / 14, 2) for e in range(15)]
        norm = colors.BoundaryNorm(levels, len(levels))
        aod = nowcast_linda[_date]
        aod[aod <= 0.0699] = None
        pcm = ax.contourf(lon, lat, nowcast_linda[_date], norm=norm, levels=levels, extend='both',
                          colors=('#606060', '#67627D', '#5F5B8E', '#4B67AB',
                                  '#4A9BAC', '#56B864', '#91CE4E', '#D0DB45',
                                  '#DBB642', '#DB9D48', '#DB7B50', '#D15F5E',
                                  '#B43A66', '#93164E', '#541029'))
        fig.patch.set_visible(False)
        ax.axis('off')
        file_res = 1200
        minute = '{:02d}'.format(_date.minute)
        hour = '{:02d}'.format(_date.hour)
        day = '{:02d}'.format(_date.day)
        month = '{:02d}'.format(_date.month)
        year = _date.year
        name = os.path.join(save_path, 'img', f'MRMS{year}{month}{day}{hour}{minute}.png')
        fig.savefig(name, bbox_inches='tight', dpi=file_res, pad_inches=0)


def most_frequent(List):
    return max(set(List), key=List.count)


def likelihood(list):
    return (most_frequent(list), round(list.count(most_frequent(list)) / len(list), 2) * 100)


def build_likelihoods(nowcast_linda, closest_locs):
    nowcast_linda = {_time: np.nan_to_num(nowcast_linda[_time]) for _time in list(nowcast_linda)}
    boxplot, locs = {e: {} for e in list(closest_locs)}, {e: {} for e in list(closest_locs)}
    for location in list(locs):
        boxplot[location] = locs[location] = {_time: [abs(round(e, 2)) for e in list(
            nowcast_linda[_time][:, closest_locs[location][0], closest_locs[location][1]])] for _time in
                                              list(nowcast_linda)}
        locs[location] = {_time: likelihood(locs[location][_time]) for _time in list(locs[location])}
    return locs, boxplot


def make_precip_historic(precip, _timestep, closest_locs):
    res = {}
    for location in list(closest_locs):
        res[location] = [(_timestep - datetime.timedelta(minutes=precip.shape[0] * 10 - e * 10),
                          round(precip[e, closest_locs[location][0], closest_locs[location][1]], 2)) for e in
                         range(precip.shape[0] - 6, precip.shape[0])]
    res = {e: pd.DataFrame(res[e]).rename({0: 'date', 1: 'precip'}, axis=1).set_index(['date']) for e in list(res)}
    return res


def graph_builder(save_path, nowcast_linda, window_size, modified_shape, precip):
    if not os.path.exists(os.path.join(save_path, 'graphs')):
        os.makedirs(os.path.join(save_path, 'graphs'))
    closest_locs = build_close_locations(window_size, modified_shape)
    likelihoods, boxplot_data = build_likelihoods(nowcast_linda, closest_locs)
    timed_history = make_precip_historic(precip, list(nowcast_linda)[0], closest_locs)
    for location in list(likelihoods):
        # Build likelihood dataframe
        tmp_df = pd.DataFrame(likelihoods[location]).T.rename({0: 'precip', 1: 'likelihood'}, axis=1)
        tmp_df.index = pd.to_datetime(tmp_df.index)
        result = timed_history[location].reset_index()
        tmp_df = tmp_df.reset_index()

        # # TODO: remove the following
        # import random
        # tmp_df['precip'] = tmp_df['precip'].map(lambda x: x + random.randint(50, 120))
        tmp_df['cumul'] = tmp_df['precip'].cumsum()

        # Build boxplot fataframe
        bx_plt = pd.DataFrame(
            [(_time, _val) for _time in list(boxplot_data[location]) for _val in boxplot_data[location][_time]]).rename(
            {0: 'date', 1: 'precip_ens'}, axis=1)
        # fig.show()

        # Create customized tooltip text field
        hover_text = []
        for index, row in tmp_df.iterrows():
            hover_text.append((f'<b>{location}</b><br><br>' +
                               f"Precipitation value: {row['precip']} mm/h<br>" +
                               f"Likelihood: {int(row['likelihood'])}%<br>"
                               ))
        tmp_df['text'] = hover_text

        # # TODO : remove the following:
        # result['precip'] = result['precip'].map(lambda x: x + random.randint(50,100))

        # Create the figure
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{}, {}],
                   [{"colspan": 2}, None]],
            subplot_titles=("Boxplot of different ensemble predictions",
                            "Nowcast precipitation accumulation", "Latest and nowcasted precipitation values"))

        fig.add_trace(  # Add a bar chart to the figure
            go.Bar(
                x=tmp_df['index'],
                y=tmp_df['precip'],
                name=f"Nowcasted Precipitation value (mm/h)",
                # text=tmp_df['text'],
                hovertext=tmp_df['text'],  # Pass the 'text' column to the hoverinfo parameter to customize the tooltip

            ),
            row=2, col=1)

        fig.add_trace(  # Add a bar chart to the figure
            go.Bar(
                x=result['date'],
                y=result['precip'],
                name=f"Estimated Precipitation value (mm/h)",
                # text=tmp_df['text'],
                # hovertext=tmp_df['text'],  # Pass the 'text' column to the hoverinfo parameter to customize the tooltip

            ),
            row=2, col=1)

        fig.add_vline(x=tmp_df['index'][0], line_width=1, line_dash="dash", line_color="green")
        fig.add_vrect(x0=tmp_df['index'][0], x1=tmp_df.iloc[-1, 0] + datetime.timedelta(minutes=10),
                      annotation_text=f"Nowcast", annotation_position="top left",
                      annotation=dict(font_size=12, font_family="Times New Roman", font_color='green'),
                      fillcolor="green", opacity=0.15, line_width=1)
        fig.add_trace(
            go.Scatter(x=tmp_df['index'], y=tmp_df['cumul'], name=f"Cumulative precipitation (mm)", fillcolor='green'),
            row=1, col=2)

        _colors = {5: 'tomato',
                   10: 'red',
                   50: 'maroon'}
        for zone in ppf_estimates[location]:
            fig.add_shape(go.layout.Shape(type="line",
                                          yref="paper",
                                          xref="x",
                                          x0=tmp_df['index'][0],
                                          y0=zone[2],
                                          x1=tmp_df.iloc[-1, 0] + datetime.timedelta(minutes=10),
                                          y1=zone[2],
                                          # line=dict(color="RoyalBlue", width=3),),
                                          line=dict(color=_colors[zone[0]], width=2, dash='dash'), ),
                          row=1,
                          col=2)

        # for zone in ppf_estimates[location]:
        #     # if max(tmp_df['precip']) + 35 > zone[2]:
        #     fig.add_hline(y=zone[2], line_width=1, line_dash="dash", line_color="red")
        #     fig.add_hrect(y0=zone[2] - 10, y1=zone[2] + 11,
        #                   annotation_text=f"{zone[0]}-year Return Period", annotation_position="top left",
        #                   annotation=dict(font_size=12, font_family="Times New Roman", font_color='Black'),
        #                   fillcolor="red", opacity=0, line_width=1)

        for _time in list(boxplot_data[location]):
            fig.append_trace(
                go.Box(x=[_time for e in range(40)], y=list(bx_plt.set_index('date').loc[_time, :]['precip_ens']),
                       marker_color='green', showlegend=False),
                row=1, col=1
            )

        fig.update_layout(
            hoverlabel_bgcolor='#FFFFFF',  # Change the background color of the tooltip to light gray
            title_text=f"Precipitation nowcast value\nof {location}",  # Add a chart title
            title_font_family="Times New Roman",
            title_font_size=20,
            title_font_color="darkblue",  # Specify font color of the title
            title_x=0.5,  # Specify the title position
            xaxis=dict(
                tickfont_size=10,
                tickangle=270,
                showgrid=True,
                zeroline=True,
                showline=True,
                showticklabels=True,
                # dtick="M1",  # Change the x-axis ticks to be monthly
                # tickformat="%b\n%Y"
            ),
            # showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )

            # yaxis_title='Precipitation value',
            # yaxis2_title='Ensemble Prediction',
        )
        for zone in ppf_estimates[location]:
            fig.add_annotation(x=tmp_df['index'][0] + datetime.timedelta(minutes=5),
                               y=zone[2] + 10,
                               text=f'{zone[0]}-year return period',
                               showarrow=False,
                               row=1, col=2)

        fig.write_html(os.path.join(save_path, "graphs", str(location) + ".html"), include_plotlyjs="cdn",
                       full_html=False)


def generate_map(save_path, nb_forecasts, window_size, modified_shape):
    od = generate_est_texts(save_path)
    _url = 'https://server.arcgisonline.com/ArcGIS/rest/services/Specialty/DeLorme_World_Base_Map/MapServer/tile/{z}/{y}/{x}'

    m = folium.Map([40.749044, -73.983306],
                   # tiles='cartodbdark_matter',
                   tiles='cartodbpositron',
                   zoom_start=8,
                   min_zoom=5,
                   max_zoom=14,
                   prefer_canvas=True,
                   max_bounds=True
                   )

    #     folium.LayerControl(collapsed=False).add_to(m)

    url = (
        "MRMS.png"
    )
    FloatImage(url, bottom=80, left=5).add_to(m)

    template = """
        {% macro html(this, kwargs) %}
       <!doctype html>
    <html lang="en">
         <!doctype html>
    <html lang="en">
    <head>
            <meta charset="UTF-8">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document</title>


        </head>
        <body>




      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>jQuery UI Draggable - Default functionality</title>
      <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">
      <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
      <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
      <script>
      $( function() {
        $( "#maplegend" ).draggable({
                        start: function (event, ui) {
                            $(this).css({
                                right: "auto",
                                top: "auto",
                                bottom: "auto"
                            });
                        }
                    });
    });
      </script>
    <div id='maplegend' class='maplegend' 
        style='position: absolute; z-index:9999;
         border-radius:0px; padding: 10px; font-size:14px; right: 21px; bottom: 20px;'>
          <span  valign="middle"; align="center"; style="background-color: transparent ; color: black;font-weight: bold; font-size: 180%; " id="txt" ></span>
    <div class='legend-scale'>
      <ul class='legend-labels'>


           <li><span valign="middle"; align="center"; style="background: rgb(255, 255, 255); color: rgb(0, 0, 0);font-weight: bold; font-size: 100%;">  Prob  </span></li>
         <li><span valign="middle"; align="center"; style="background: rgba(255, 0, 0); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">  1  </span></li>
         <li><span valign="middle"; align="center"; style="background: rgba(225, 90, 0); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">  0.92  </span></li>
             <li><span valign="middle"; align="center"; style="background:  rgba(234, 162, 62, 0.87); color: rgb(0, 0, 0);font-weight: bold; font-size: 120%;">  0.85  </span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(255,255,0); color: rgb(0, 0, 0);font-weight: bold; font-size: 120%;">0.77</span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(193, 229, 60, 0.87); color: rgb(0, 0, 0);font-weight: bold; font-size: 120%;">0.69</span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(153, 220, 69, 0.87); color: rgb(0, 0, 0);font-weight: bold; font-size: 120%;">0.62</span></li>
        <li><span valign="middle"; align="center";  style="background: rgba(69, 206, 66, 0.87); color: rgb(0, 0, 0);font-weight: bold; font-size: 120%;">0.54</span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(78, 194, 98, 0.87); color: rgb(0, 0, 0);font-weight: bold; font-size: 120%;">0.46</span></li>
        <li><span valign="middle"; align="center";  style="background: rgba(71, 177, 139, 0.87); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">0.38</span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(64, 160, 180, 0.87); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">0.31</span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(67, 105, 196, 0.75); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">0.23</span></li>
        <li><span valign="middle"; align="center"; style="background: rgba(79, 87, 183, 0.58); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">0.15</span></li>
        <li><span valign="middle"; align="center";  style="background: rgba(82, 71, 141, 0); color: rgb(255, 255, 255);font-weight: bold; font-size: 120%;">0</span></li>
      </ul>
    </div>
    </div>
    <script>
        let titles = """ + f"""{[e for e in od]}""" + """;
        let currentIndex = 1;
        let text = document.getElementById('txt');



        setTimeout(function () {

        setInterval(() => {

           text.innerHTML= titles[currentIndex];   

           currentIndex++;
        """ + f"if (currentIndex === {nb_forecasts})" + """
            currentIndex = 0;

        }, 1000)

      }, 400)


        </script>
    </body>
    </html>
    <style type='text/css'>
      .maplegend .legend-title {
        text-align: left;
        margin-bottom: 5px;
        font-weight: bold;
        font-size: 100%;
        }
      .maplegend .legend-scale ul {
        margin: 0;
        margin-bottom: 5px;
        padding: 0;
        float: right;
        list-style: none;
        }
      .maplegend .legend-scale ul li {
        font-size: 80%;
        list-style: none;
        margin-left: 0;
        line-height: 18px;
        margin-bottom: 2px;
        }
      .maplegend ul.legend-labels li span {
        display: block;
        float: left;
        height: 16px;
        width: 30px;
        margin-right: 5px;
        margin-left: 0;
        border: 1px solid #999;
        }
      .maplegend .legend-source {
        font-size: 80%;
        color: #777;
        clear: both;
        }
      .maplegend a {
        color: #777;
        }
    /*////*/
        body{
                    background: #000;
                }
            /*h1{ 
                text-align: center;
                font-size: 24pt;
                background-color: transparent;
                color: white;

                }*/

    </style>
        {% endmacro %}"""

    macro = MacroElement()
    macro._template = Template(template)

    m.get_root().add_child(macro)

    if not modified_shape:
        lat_min = 19
        lat_max = 54
        lon_min = -129
        lon_max = -59
    else:
        # Generate the lon couples
        lon_couples = [(e, (-130 + (e / 100))) for e in range(7000)]
        lat_couples = [(e, (55 - (e / 100))) for e in range(3500)]
        # Select the coordinates for longitude
        lon_min = [e for e in lon_couples if e[0] == modified_shape[0][0]]
        lon_min = lon_min[0][1]
        lon_max = [e for e in lon_couples if e[0] == modified_shape[0][1]]
        lon_max = lon_max[0][1]
        # Select the coordinates for latitude
        lat_max = [e for e in lat_couples if e[0] == modified_shape[1][0]]
        lat_max = lat_max[0][1]
        lat_min = [e for e in lat_couples if e[0] == modified_shape[1][1]]
        lat_min = lat_min[0][1]

    # folium.TileLayer(_url, attr='Tiles &copy; Esri &mdash; Copyright: &copy;2012 DeLorme', name='DeLorme').add_to(m)m.add_child(colormap)
    add_gif(m, 'MRMS', os.path.join(save_path, 'img', 'mrms.gif'), [[lat_min, lon_min], [lat_max, lon_max]], True)

    minimap = MiniMap(toggle_display=True, position="bottomleft")
    m.add_child(minimap)
    m.add_child(MeasureControl())

    # # Add location markers
    # for loc in list(locations):
    #     html = """
    #     <iframe src=\"""" + os.path.join('graphs', loc + '.html') + """\" width="850" height="500"  frameborder="0">
    #     """
    #
    #     popup = folium.Popup(folium.Html(html, script=True))
    #     folium.Marker(location=[locations[loc][0], locations[loc][1]],
    #                   popup=popup, icon=folium.Icon(icon='home', prefix='fa')).add_to(m)

    for loc in list(locations):
        html = """
        <iframe src=\"""" + os.path.join('graphs', loc + '.html') + """\" width="850" height="500"  frameborder="0">    
        """

        popup = folium.Popup(folium.Html(html, script=True))
        folium.Marker(location=[locations[loc][0], locations[loc][1]],
                      popup=popup, icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

    # os.system(f'rm *.grib2')
    # os.system(f'rm *.nc')
    print('saving map...')
    m.fit_bounds((lat_max, lon_max), (lat_min, lon_min))
    m.save(os.path.join(save_path, "index.html"))
