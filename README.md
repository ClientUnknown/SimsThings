# SimsThings

Just messing around with modding The Sims 4.

# Decompiler
I decided to enhance the decompiler script going around with multiprocessing, this should (depending on the system) make decompiling the files MUCH faster, around 45 seconds on my Ryzen 3800x

decompile_all_multi.py can be used with Python 3.7.5 to decompile game files locally.

settings.py must always be within the same directory as Python script that is calling it.

# NOTE
You will need Python (3.7.5 to be safe) installed to run these files.

If you want to decompile Sims 4's Python scripts just follow these steps:
  Place settings.py, decompile_all_multi.py, and Utilities in the same directory
  Open a terminal in the working directory and type "py decompile_all_multi.py" without the quotations to run the script
  Don't be worried if you see some files failing to decompile, haven't found a way around that
  Once done you'll have a folder called EA in your working directory with all the decompiled python files
  
 compile_mod.py is run the same way but Utilities is not needed, be sure to run The Sims 4 BEFORE trying to compile a mod.
 
 settings.py contains fields that need to be filled out.
