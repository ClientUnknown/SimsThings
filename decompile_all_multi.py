import os, multiprocessing, time, re, sys, threading
import fnmatch, shutil, io
from zipfile import PyZipFile, ZIP_STORED
from Utilities.unpyc3 import decompile

class SimsDecompiler():
    def __init__(self):
        self.delay_time = 2.0
        self.processes = []
        self.ea_folder = "EA"
        self.gameplay_folder_data = ""
        self.gameplay_folder_game = ""
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

    def fill_queue(self, curr_folder):
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
                    self.q.put(out_folder)

    def worker(self):
        filename = None
        if not filename:
            filename = self.q.get()

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