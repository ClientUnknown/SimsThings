from Utilities import extract_folder
from settings import *

ea_folder = 'EA'
if not os.path.exists(ea_folder):
    os.mkdir(ea_folder)

gameplay_folder_data = os.path.join(game_folder, 'Data', 'Simulation', 'Gameplay')
gameplay_folder_game = os.path.join(game_folder, 'Game', 'Bin', 'Python')

extract_folder(ea_folder,gameplay_folder_data)
extract_folder(ea_folder,gameplay_folder_game)

input()