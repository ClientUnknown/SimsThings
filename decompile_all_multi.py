import os, multiprocessing, time, re, sys, threading
import fnmatch, shutil, io
from zipfile import PyZipFile, ZIP_STORED
from Utilities.unpyc3 import decompile
#import settings

class SimsDecompiler():
    def __init__(self):
        self.delay_time = 5.0
        self.processes = []
        self.ea_folder = "EA"
        self.gameplay_folder_data = ""#os.path.join(curr_settings.game_folder, 'Data', 'Simulation', 'Gameplay')
        self.gameplay_folder_game = ""#os.path.join(curr_settings.game_folder, 'Game', 'Bin', 'Python')
        self.script_package_types = ["*.zip", "*.ts4script"]
        self.q = multiprocessing.Manager().Queue()

        if not os.path.exists(self.ea_folder):
            os.mkdir(self.ea_folder)

    def decompile_dir(self, p):
        try:
            py = decompile(p)
            with io.open(p.replace(".pyc",  ".py"), "w", encoding="utf-8") as output_py:
                for statement in py.statements:
                    output_py.write(str(statement) + "\r")
        except Exception as ex:
            print("Failed to decompile %s" % p)

    def fill_queue(self, q, curr_folder):
        for root, dirs, files in os.walk(curr_folder):
            for ext_filter in self.script_package_types:
                for filename in fnmatch.filter(files, ext_filter):
                    src = os.path.join(root, filename)
                    dst = os.path.join(self.ea_folder, filename)
                    if src != dst:
                        shutil.copyfile(src, dst)
                    zip = PyZipFile(dst)
                    out_folder = os.path.join(self.ea_folder, os.path.splitext(filename)[0])
                    zip.extractall(out_folder)
                    q.put(out_folder)

    def worker(self, q):
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
                thrd = threading.Thread(target=self.decompile_dir, args=(p,))
                grand_children.append(thrd)
                thrd.start()
        for thrd in grand_children:
            thrd.join(self.delay_time)

    def run_workers(self, q):
        print("Spooling up workers...")
        for i in range(4):
            proc = multiprocessing.Process(target=self.worker, args=(q,))
            self.processes.append(proc)
            proc.start()
        for proc in self.processes:
            proc.join()

    def execute_decompiler(self):
        start_time = time.time()
        
        self.fill_queue(self.q, self.gameplay_folder_data)
        self.fill_queue(self.q, self.gameplay_folder_game)

        print("Queue filled")

        self.run_workers(self.q)

        end_time = time.time()

        print("This run took %f seconds" % (end_time-start_time))
        input("Hit enter to close")
