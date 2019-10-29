import os, multiprocessing, time, subprocess, re, sys
import fnmatch, shutil, io
from zipfile import PyZipFile, ZIP_STORED
from Utilities.unpyc3 import decompile
from settings import *

delay_time = 480  # Time to close threads in seconds

ea_folder = 'EA'
if not os.path.exists(ea_folder):
    os.mkdir(ea_folder)

gameplay_folder_data = os.path.join(game_folder, 'Data', 'Simulation', 'Gameplay')
gameplay_folder_game = os.path.join(game_folder, 'Game', 'Bin', 'Python')

script_package_types = ['*.zip', '*.ts4script']

def extract_folder(ea_folder, gameplay_folder):
    for root, dirs, files in os.walk(gameplay_folder):
        for ext_filter in script_package_types:
            for filename in fnmatch.filter(files, ext_filter):
                

def worker(name):
    print(name)

def run_workers():
    pool = multiprocessing.Pool()

    pool.close()
    pool.join()

def main():
    extract_folder(ea_folder,gameplay_folder_data)
    extract_folder(ea_folder,gameplay_folder_game)
    input()
    run_workers()

if __name__ == "__main__":
    main()