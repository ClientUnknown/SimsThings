import sys, subprocess, os, time, multiprocessing
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui
import settings
import decompile_all_multi

class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.title = "Sims 4 Decompiler"
        self.left = 200
        self.top = 200
        self.width = 640
        self.height = 480

        self.curr_settings = settings.Settings()
        self.curr_decompiler = decompile_all_multi.SimsDecompiler()

        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.get_creator_name()
        self.get_game_folder()
        self.run_decompile_all_multi()

        #self.run_decompiler()

        self.show()

    def get_creator_name(self):
        creator_name, ok_pressed = QtWidgets.QInputDialog.getText(self, "Creator's Name","Your Creator Name:", QtWidgets.QLineEdit.Normal, "")
        if ok_pressed and creator_name != "":
            self.curr_settings.set_creator_name(creator_name)

    def get_game_folder(self):
        self.curr_settings.set_game_folder(str(os.path.abspath(QtWidgets.QFileDialog.getExistingDirectory(self, "Select directory with sims.exe"))))

    def run_decompiler(self):
        button = QtWidgets.QPushButton("Run")

        button.clicked.connect(self.run_decompile_all_multi())
        button.show()

    def run_decompile_all_multi(self):
        self.curr_decompiler.gameplay_folder_data = os.path.join(self.curr_settings.game_folder, "Data", "Simulation", "Gameplay")
        self.curr_decompiler.gameplay_folder_game = os.path.join(self.curr_settings.game_folder, "Game", "Bin", "Python")

        #alert = QtWidgets.QMessageBox()
        #alert.setText("Now running the decompiler...")
        #alert.exec_()

        start_time = time.time()

        self.curr_decompiler.fill_queue(self.curr_decompiler.gameplay_folder_data)
        self.curr_decompiler.fill_queue(self.curr_decompiler.gameplay_folder_game)
        
        for i in range(4):
            proc = multiprocessing.Process(target=self.curr_decompiler.worker())
            self.curr_decompiler.processes.append(proc)
            proc.start()
        for proc in self.curr_decompiler.processes:
            proc.join()

        print("This run took %f seconds" % (time.time()-start_time))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())