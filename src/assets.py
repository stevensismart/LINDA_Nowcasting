from typing import List, Tuple

ppf_estimates = {
    'Newark Liberty International Airport': [(5, 105, 114, 126), (10, 116, 127, 140), (50, 139, 154, 169)],
    'John F. Kennedy International Airport': [(5, 73, 93, 120), (10, 108, 140, 182), (50, 140, 191, 263)],
    'LaGuardia Airport': [(5, 92, 116, 146), (10, 108, 137, 172), (50, 139, 187, 249)],
    'Teterboro Airport': [(5, 105, 116, 127), (10, 117, 129, 141), (50, 141, 157, 172)],
    'Holland Tunnel NJ': [(5, 93, 121, 154), (10, 112, 142, 181), (50, 143, 193, 261)],
    'Holland Tunnel NY': [(5, 93, 121, 154), (10, 112, 142, 181), (50, 143, 193, 261)],
    'Lincoln Tunnel NY': [(5, 97, 122, 154), (10, 113, 143, 181), (50, 144, 194, 261)],
    'Lincoln Tunnel NJ': [(5, 96, 122, 155), (10, 111, 142, 183), (50, 142, 193, 263)],
    'Port Newark': [(5, 104, 114, 126), (10, 116, 127, 140), (50, 139, 154, 169)],
    'Port Elizabeth': [(5, 105, 114, 126), (10, 116, 127, 140), (50, 139, 154, 169)],
    'Port Jersey and Greenville Yards': [(5, 105, 115, 127), (10, 117, 128, 141), (50, 140, 156, 171)],
    'Brooklyn Piers - Redhook Container Terminal': [(5, 94, 121, 155), (10, 110, 142, 182), (50, 141, 192, 263)],
    '65th Street Intermodal Terminal': [(5, 94, 121, 156), (10, 109, 142, 184), (50, 141, 192, 264)],
    'Howland Hook Marine Terminal': [(5, 93, 122, 158), (10, 109, 143, 187), (50, 141, 195, 272)],
    'Newark Penn and Harrison Stations': [(5, 104, 114, 126), (10, 116, 127, 139), (50, 139, 154, 168)],
    'Harrison Car Equipment Facility': [(5, 104, 114, 125), (10, 116, 127, 139), (50, 139, 153, 168)],
    'Tracks: NJ Turnpike & Passaic River': [(5, 104, 114, 125), (10, 116, 127, 139), (50, 139, 154, 169)],
    'Tracks: Hackensack River West': [(5, 104, 114, 125), (10, 116, 127, 139), (50, 139, 154, 169)],
    'Tracks: Hackensack River East': [(5, 105, 115, 126), (10, 116, 127, 140), (50, 140, 155, 170)],
    'Grove St Exchange Place & Newport Stations': [(5, 96, 121, 153), (10, 112, 142, 181), (50, 143, 193, 261)],
    'Hoboken and Caisson 1 Vent Building': [(5, 96, 121, 153), (10, 112, 142, 181), (50, 143, 193, 261)],
    'Morton Street Ventilation Shaft': [(5, 96, 122, 154), (10, 112, 142, 181), (50, 143, 193, 261)]
}

locations = {
    'Newark Liberty International Airport': (40.6895354, -74.1766511),
    'John F. Kennedy International Airport': (40.6413153, -73.780327),
    'LaGuardia Airport': (40.7769311, -73.8761546),
    'Teterboro Airport': (40.8507, -74.0604),
    'Holland Tunnel NJ': (40.7288767, -74.0332389),
    'Holland Tunnel NY': (40.7262, -74.0115),
    'Lincoln Tunnel NY': (40.7611867, -74.0056528),
    'Lincoln Tunnel NJ': (40.767361, -74.020661),
    'Port Newark': (40.6904455648776, -74.14725337358634),
    'Port Elizabeth': (40.67556507203779, -74.15398066049917),
    'Port Jersey and Greenville Yards': (40.67119681965079, -74.07374978629467),
    'Brooklyn Piers - Redhook Container Terminal': (40.68544360119133, -74.00929539171405),
    '65th Street Intermodal Terminal': (40.64286612748238, -74.03017774095771),
    'Howland Hook Marine Terminal': (40.637345286285544, -74.18618361613548),
    'Newark Penn and Harrison Stations': (40.7393148985097, -74.15834047688615),
    'Harrison Car Equipment Facility': (40.738939239040015, -74.13678212844397),
    'Tracks: NJ Turnpike & Passaic River': (40.73813317267604, -74.11492499661831),
    'Tracks: Hackensack River West': (40.73876686519661, -74.09453382263837),
    'Tracks: Hackensack River East': (40.73825919404139, -74.0744008941495),
    'Grove St Exchange Place & Newport Stations': (40.722140786726946, -74.037003279267),
    'Hoboken and Caisson 1 Vent Building': (40.73505312572795, -74.03008512166838),
    'Morton Street Ventilation Shaft': (40.7322970762522, -74.01100843753662)
}

def closest(lst, K):
    return lst[min(range(len(lst)), key=lambda i: abs(lst[i] - K))]


def build_close_locations(window_size, modified_shape : Tuple[tuple]  = None):
    if not modified_shape:
        lat_min = 20
        lat_max = 55
        lon_min = -130
        lon_max = -60
    else:
        # Generate the lon couples
        lon_couples = [(e,(-130+(e/100))) for e in range(7000)]
        lat_couples = [(e,(55-(e/100))) for e in range(3500)]
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



    lat = [e / 100 for e in range(int(lat_max * 100), int(lat_min * 100), -(window_size))]
    lon = [e / 100 for e in range(int(lon_min * 100), int(lon_max * 100), window_size)]

    closest_loc = {e: (lat.index(closest(lat, locations[e][0])), lon.index(closest(lon, locations[e][1]))) for e in
                   list(locations)}

    return closest_loc

