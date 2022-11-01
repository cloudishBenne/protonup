"""Constant Values"""
import os
CONFIG_FILE = (os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')) + '/protonup/config.ini'
DEFAULT_INSTALL_DIR = os.path.expanduser('~/.steam/root/compatibilitytools.d/')
DEFAULT_LUTRIS_INSTALL_DIR =  (os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')) + '/lutris/runners/wine/' 
TEMP_DIR = '/tmp/protonup/'
PROTONGE_URL = 'https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases'
WINEGE_URL = 'https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases'
BUFFER_SIZE = 65536  # Work with 64 kb chunks
