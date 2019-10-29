import os, shutil
from zipfile import PyZipFile, ZIP_STORED
from settings import *

root = os.path.dirname(os.path.realpath('__file__'))
mod_name = None

if __name__ == "__main__":
    mod_name = input("Type the name of your mod and hit enter or just hit enter to skip naming")
    src = os.path.join(root, 'Scripts')
    if not mod_name:
        mod_name=os.path.basename(os.path.normpath(os.path.dirname(os.path.realpath('__file__'))))
    
    mod_name = creator_name + '_' + mod_name
    ts4script = os.path.join(root, mod_name + '.ts4script')

    ts4script_mods = os.path.join(os.path.join(mods_folder), mod_name + '.ts4script')

    zf = PyZipFile(ts4script, mode='w', compression=ZIP_STORED, allowZip64=True, optimize=2)
    for folder, subs, files in os.walk(src):
        zf.writepy(folder)
    zf.close()
    shutil.copyfile(ts4script, ts4script_mods)
