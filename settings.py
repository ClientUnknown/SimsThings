import os

#creator_name = 'Xpherion'
#mods_folder = os.path.expanduser(
#    os.path.join('~', 'Documents', 'Electronic Arts', 'The Sims 4', 'Mods')
#)

#game_folder = os.path.join('D:', os.sep, 'Origin', 'The Sims 4')

class Settings():
    def __init__(self):
        self.creator_name = ""
        self.mods_folder = os.path.expanduser(os.path.join('~', 'Documents', 'Electronic Arts', 'The Sims 4', 'Mods'))
        self.game_folder = ""

    def set_creator_name(self, creator_name):
        self.creator_name = creator_name

    def set_mods_folder(self, mods_folder):
        self.mods_folder = mods_folder

    def set_game_folder(self, game_folder):
        self.game_folder = game_folder

    def get_creator_name(self):
        return self.creator_name
    
    def get_mods_folder(self):
        return self.mods_folder

    def get_game_folder(self):
        return self.game_folder