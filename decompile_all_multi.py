import os, multiprocessing, time, re, sys, threading
import fnmatch, shutil, io
from zipfile import PyZipFile, ZIP_STORED
from Utilities.unpyc3 import decompile
from settings import *

delay_time = 5.0  # Time to close a process in seconds
processes = []  # Keep track of the processes with a list

ea_folder = 'EA'
if not os.path.exists(ea_folder):
    os.mkdir(ea_folder)

gameplay_folder_data = os.path.join(game_folder, 'Data', 'Simulation', 'Gameplay')
gameplay_folder_game = os.path.join(game_folder, 'Game', 'Bin', 'Python')

script_package_types = ['*.zip', '*.ts4script']

def decompile_dir(p):
    try:
        py = decompile(p)
        with io.open(p.replace('.pyc', '.py'), 'w', encoding='utf-8') as output_py:
            for statement in py.statements:
                output_py.write(str(statement) + '\r')
    except Exception as ex:
        print("Failed to decompile %s" % p)

def fill_queue(q, curr_folder):
    for root, dirs, files in os.walk(curr_folder):
        for ext_filter in script_package_types:
            for filename in fnmatch.filter(files, ext_filter):
                src = os.path.join(root, filename)
                dst = os.path.join(ea_folder, filename)
                if src != dst:
                    shutil.copyfile(src, dst)
                zip = PyZipFile(dst)
                out_folder = os.path.join(ea_folder, os.path.splitext(filename)[0])
                zip.extractall(out_folder)
                q.put(out_folder)

def worker(q):
    filename = None
    while not q.empty():
        if not filename:
            filename = q.get()
        else:
            break
    
    grand_children = []
    pattern = '*.pyc'
    for root, dirs, files in os.walk(filename):
        for filename in fnmatch.filter(files, pattern):
            p = str(os.path.join(root, filename))
            thrd = threading.Thread(target=decompile_dir, args=(p,))
            grand_children.append(thrd)
            thrd.start()
    for thrd in grand_children:
        thrd.join(delay_time)

def run_workers(q):
    print("Spooling up workers...")
    for i in range(4):
        proc = multiprocessing.Process(target=worker, args=(q,))
        processes.append(proc)
        proc.start()
    for proc in processes:
        proc.join()

def main():
    start_time = time.time()

    q = multiprocessing.Manager().Queue()
    fill_queue(q,gameplay_folder_data)
    fill_queue(q,gameplay_folder_game)
    run_workers(q)

    end_time = time.time()

    print("This run took %f seconds" % (end_time-start_time))

    input("Hit enter to close")

if __name__ == "__main__":
    main()