import os
if not os.path.exists("build"):
    os.mkdir("build")
os.system("sphinx-build source build")
