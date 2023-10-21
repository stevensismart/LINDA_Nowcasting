import os
import subprocess
from git import Repo
from subprocess import Popen, PIPE, STDOUT


def keep_latest_mrms(save_path, nb_observations):
    # # make the vid
    files = {os.path.getmtime(os.path.join(save_path, 'data', f)): os.path.join(save_path, 'data', f) for f in
             os.listdir(os.path.join(save_path, 'data')) if
             os.path.isfile(os.path.join(save_path, 'data', f)) and f.endswith('grib2')}
    if len(files) > nb_observations:
        file_times = [e for e in list(files)]
        file_times.sort()
        files_to_keep = file_times[-nb_observations:]
        files_to_delete = [e for e in file_times if e not in files_to_keep]
        for _file in files_to_delete:
            subprocess.check_call(["rm", files[_file]])


def keep_latest_images(save_path, nb_forecasts):
    # # make the vid
    files = {os.path.getmtime(os.path.join(save_path, 'img', f)): os.path.join(save_path, 'img', f) for f in
             os.listdir(os.path.join(save_path, 'img')) if
             os.path.isfile(os.path.join(save_path, 'img', f)) and f.endswith('png')}
    file_times = [e for e in list(files)]
    file_times.sort()
    if len(file_times) > nb_forecasts:
        files_to_keep = file_times[-nb_forecasts:]
        files_to_delete = [e for e in file_times if e not in files_to_keep]
        for _file in files_to_delete:
            subprocess.check_call(["rm", files[_file]])


def save_to_github(save_path, hour, minute, month, day, year):
    if os.path.isdir(os.path.join(save_path, 'blackhawk70.github.io')):
        subprocess.check_call(['rm', '-rf', os.path.join(save_path, 'blackhawk70.github.io')])
    full_local_path = os.path.join(save_path, "blackhawk70.github.io")
    username = "blackhawk70"
    password = "ghp_B0m60W###yBm"
    password = password.replace('#','')
    remote = f"https://{username}:{password}@github.com/blackhawk70/blackhawk70.github.io.git"
    Repo.clone_from(remote, full_local_path)
    repo = Repo(full_local_path)

    cmd = ["mv", os.path.join(save_path, "index.html"), os.path.join(save_path, "blackhawk70.github.io", "index.html")]
    cmd = " ".join(cmd)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read()
    print(output)
    cmd = ["cp", '-r',os.path.join(save_path, "graphs/*"), os.path.join(save_path, "blackhawk70.github.io/", 'graphs/')]
    cmd = " ".join(cmd)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read()
    print(output)

    repo.git.add(all=True)
    repo.index.commit(f"{hour}:{minute} {month}/{day}/{year}")
    # repo.index.commit(f"test")
    repo = Repo(full_local_path)
    origin = repo.remote(name="origin")
    origin.push()
    subprocess.check_call(['rm', '-rf', 'blackhawk70.github.io'])
    print('done !')
