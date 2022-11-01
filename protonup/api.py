"""ProtonUp-ng API"""
import os
import shutil
from configparser import ConfigParser
import tarfile
import requests
from .utilities import download, sha512sum, readable_size
from .constants import CONFIG_FILE, PROTONGE_URL, WINEGE_URL
from .constants import TEMP_DIR, DEFAULT_INSTALL_DIR, DEFAULT_LUTRIS_INSTALL_DIR


def fetch_data(tag, lutris=False) -> dict:
    """
    Fetch ProtonGE release information from github
    Return Type: dict {str, str}
    Content(s):
        'version', date', 'download', 'size', 'checksum'
    """
    if lutris:
        pkg_format = 'tar.xz'
        url = WINEGE_URL + (f'/tags/{tag}' if tag else '/latest')
    else:
        pkg_format = 'tar.gz'
        url = PROTONGE_URL + (f'/tags/{tag}' if tag else '/latest')
        
    data = requests.get(url).json()
    if 'tag_name' not in data:
        return None  # invalid tag

    values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
    for asset in data['assets']:
        if asset['name'].endswith('sha512sum'):
            values['checksum'] = asset['browser_download_url']
        elif asset['name'].endswith(pkg_format):
            values['download'] = asset['browser_download_url']
            values['size'] = asset['size']
    return values


def fetch_releases(count=100, lutris=False) -> list:
    """
    List ProtonGE releases on Github
    Return Type: list[str]
    """
    tags = []
    for release in requests.get((PROTONGE_URL if not lutris else WINEGE_URL) + "?per_page=" + str(count)).json():
        tags.append(release['tag_name'])
    tags.reverse()
    
    return tags


def install_directory(target=None, lutris=False) -> str:
    """
    Custom install directory
    Return Type: str
    """
    config = ConfigParser()

    if not os.path.exists(CONFIG_FILE):
        # Return defaults
        if target == None:
            return DEFAULT_LUTRIS_INSTALL_DIR if lutris else DEFAULT_INSTALL_DIR
        
        # Create config if it doesn't exist
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    
    # Make sure config file has all settings        
    config.read(CONFIG_FILE)
    if not config.has_section('protonup'):
        config.add_section('protonup')
    if not config.has_option('protonup', 'installdir'):
        config.set('protonup', 'installdir', DEFAULT_INSTALL_DIR)
    if not config.has_option('protonup', 'lutris_installdir'):
        config.set('protonup', 'lutris_installdir', DEFAULT_LUTRIS_INSTALL_DIR)
    
    if target is not None:
        # Return install dir
        if target == 'get':
            if not lutris:
                return os.path.expanduser(config['protonup']['installdir']) 
            else:
                return os.path.expanduser(config['protonup']['lutris_installdir'])

        # Set install dir
        if target.lower() == 'default':
            if lutris:
                target = DEFAULT_LUTRIS_INSTALL_DIR
            else:
                target = DEFAULT_INSTALL_DIR
        if not target.endswith('/'):
            target += '/'
        if lutris:
            config['protonup']['lutris_installdir'] = target
        else:
            config['protonup']['installdir'] = target

        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        
        return target

    # Return config
    if not lutris: 
        return os.path.expanduser(config['protonup']['installdir'])
    return os.path.expanduser(config['protonup']['lutris_installdir'])


def installed_versions(lutris=False) -> list:
    """
    List of proton installations
    Return Type: list[str]
    """
    installdir = install_directory(lutris=lutris)
    versions_found = []

    if os.path.exists(installdir):
        folders = os.listdir(installdir)
        # Find names of directories with proton
        versions_found = [folder for folder in folders if os.path.exists(installdir + '/' + folder + "/proton" if not lutris else "/bin/wine")]
    
    return versions_found


def get_proton(version=None, yes=True, dl_only=False, output=None, lutris=False) -> None:
    """Download and (optionally) install Proton"""
    installdir = install_directory(lutris=lutris)
    data = fetch_data(tag=version, lutris=lutris)
    if not data or 'download' not in data:
        if not yes:
            print('[ERROR] invalid tag / binary not found')
        return False
    if not lutris:
    # fixes new naming scheme ##################
        if not version or version.startswith('GE-'):
            installdir += data['version']
        else:
            installdir += 'Proton-' + data['version']
    ############################################
    else:
        # old naming scheme  
        if not version.startswith('GE'):
            # LoL naming scheme
            if not version.endswith('LoL'):
                installdir += 'lutris-ge-' + data['version'].replace('-GE', '') + '-x86_64'
            else:
                installdir += 'lutris-ge-lol-' + data['version'].replace('-GE', '').replace('-LoL', '') + '-x86_64'
        # current naming scheme
        else:
            installdir += 'lutris-' + data['version'] + '-x86_64'
    checksum_dir = installdir + '/sha512sum'
    source_checksum = requests.get(data['checksum']).text if 'checksum' in data else None
    local_checksum = open(checksum_dir).read() if os.path.exists(checksum_dir) else None

    # Check if it already exist
    if os.path.exists(installdir) and not dl_only:
        if local_checksum and source_checksum:
            if local_checksum in source_checksum:
                if not yes:
                    # fixes new naming scheme #####################################
                    if not version or version.startswith('GE-'):
                        print(f"[INFO] {data['version']} already installed")
                    else:
                        print(f"[INFO] Proton-{data['version']} already installed")
                    ###############################################################
                    print("[INFO] No hotfix found")
                return
            elif not yes:
                print("[INFO] Hotfix available")
        else:
            if not yes:
                # fixes new naming scheme #####################################
                if not version or version.startswith('GE-'):
                    print(f"[INFO] {data['version']} already installed")
                else:
                    print(f"[INFO] Proton-{data['version']} already installed")
                ###############################################################
            return

    # Confirmation
    if not yes:
        # fixes new naming scheme ##############################
        if not version or version.startswith('GE-'):
            print(f"Ready to download {data['version']}")
        else:
            print(f"Ready to download Proton-{data['version']}")
        print(f"\nSize      : {readable_size(data['size'])}",
              f"\nPublished : {data['date']}")
        ########################################################
        if input("Continue? (Y/n): ") not in ['y', 'Y', '']:
            return

    # Prepare Destination
    destination = output if output else (os.getcwd() if dl_only else TEMP_DIR)
    if not destination.endswith('/'):
        destination += '/'
    destination += data['download'].split('/')[-1]
    destination = os.path.expanduser(destination)

    # Download
    if not download(url=data['download'], destination=destination, show_progress=not yes):
        if not yes:
            print("[ERROR] Download failed")
        return

    download_checksum = sha512sum(destination)
    if source_checksum and (download_checksum not in source_checksum):
        if not yes:
            print("[ERROR] Checksum verification failed")
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        return

    # Installation
    if not dl_only:
        if os.path.exists(installdir):
            shutil.rmtree(installdir)
        tarfile.open(destination, ("r:gz" if not lutris else "r:xz")).extractall(install_directory(lutris=lutris))
        if not yes:
            print('[INFO] Installed in: ' + installdir)
        open(checksum_dir, 'w').write(download_checksum)
    elif not yes:
        print('[INFO] Downloaded to: ' + destination)

    # Clean up
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


def remove_proton(version=None, lutris=False) -> bool:
    """Uninstall existing proton installation"""
    # fixes new naming scheme ###################
    if version and not version.startswith("GE-"):
        version = "Proton-" + version
    #############################################
    target = install_directory(lutris=lutris) + version
    if os.path.exists(target):
        shutil.rmtree(target)
        return True
    return False
