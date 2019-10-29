import fnmatch
import os
from zipfile import PyZipFile, ZIP_STORED

import shutil

import io
from Utilities.unpyc3 import decompile
import fnmatch
import os


def decompile_dir(rootPath):
    pattern = '*.pyc'
    for root, dirs, files in os.walk(rootPath):
        for filename in fnmatch.filter(files, pattern):
            p = str(os.path.join(root, filename))
            try:
                py = decompile(p)
                with io.open(p.replace('.pyc', '.py'), 'w', encoding='utf-8') as output_py:
                    for statement in py.statements:
                        output_py.write(str(statement) + '\r')
                print(p)
            except Exception as ex:
                print("FAILED to decompile %s" % p)


script_package_types = ['*.zip', '*.ts4script']


def extract_subfolder(root, filename, ea_folder):
    src = os.path.join(root, filename)
    dst = os.path.join(ea_folder, filename)
    if src != dst:
        shutil.copyfile(src, dst)
    zip = PyZipFile(dst)
    out_folder = os.path.join(ea_folder, os.path.splitext(filename)[0])
    zip.extractall(out_folder)
    decompile_dir(out_folder)
    pass


def extract_folder(ea_folder, gameplay_folder):
    for root, dirs, files in os.walk(gameplay_folder):
        for ext_filter in script_package_types:
            for filename in fnmatch.filter(files, ext_filter):
                extract_subfolder(root, filename, ea_folder)


def compile_module(creator_name, root, mods_folder,mod_name=None):
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
