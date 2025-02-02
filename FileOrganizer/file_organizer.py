import os 
import shutil

source = "C:/Users/admin/Desktop/Projects/Automation/test.py"
destination = "C:/Users/admin/Desktop/Projects/Automation/FileOrganizer/test.py"

shutil.copy(source, destination)

os.remove(source)