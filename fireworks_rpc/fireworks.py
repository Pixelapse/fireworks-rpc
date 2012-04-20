import fnmatch
import os
import os.path

FIREWORKS_EXE = None

# Try to find Fireworks
adobe_dir = os.path.expandvars(r'%PROGRAMFILES(x86)%\Adobe')

try:
  fireworks_dir = fnmatch.filter(os.listdir(adobe_dir), 'Adobe Fireworks CS[5-9]')[0]
  fireworks_exe = os.path.join(adobe_dir, fireworks_dir, 'Fireworks.exe')
  
  if os.path.exists(fireworks_exe):
    FIREWORKS_EXE = fireworks_exe
except:
  pass

def set_fireworks_path(path):
  global FIREWORKS_EXE
  FIREWORKS_EXE = path

def kill_fireworks():
  os.system("taskkill /im Fireworks.exe /f")
  
def start_fireworks():
  os.startfile(FIREWORKS_EXE)

def restart_fireworks():
  kill_fireworks()
  start_fireworks()