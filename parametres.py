#VERSION
VERSION = "0.2.1"
# A SECURISER PAR LA SUITE avec dotenv
#URL_BASEDEDONNEE = 'mariadb+mariadbconnector://apiHD:Adefinir@localhost:3306/hdapplication'

URL_BASEDEDONNEE = 'mariadb+mariadbconnector://root:@localhost:3306/hdapplication3'


# Taille des vignettes en pixels qui sont crées automatiquement à l'ajout d'un média
TAILLE_VIGNETTE = (128, 128)
# Instant de capture dans le media pour créer la vignette (en seconde)
CAPTURE_INSTANT = 2
# Chemin de la médiatheque
PATH_MEDIA = "mediatheque"
# Chemin des fichiers de conf helice
PATH_CFG = "cfghelice"
# Port des commandes pour les hélices
PORT_CMD_HELICE = 9910
# type mine autorisé pour les médias
MIME_TYPES = ["video/mp4", "video/x-matroska", "video/webm", "video/avi", "video/x-flv", "video/quicktime", "video/x-msvideo", "video/x-ms-wmv", "video/x-mpeg", "video/mpeg"]
#adresse reservée pour ancien reseau pycav
PYCAV = "192.168.97"
# Helice old generation avec fichier de config nommé network_config
HELICE_OLD_GEN = ["HeliceZH1p", "HeliceZH3p"]
CFG_OLD = "network_config"
# Felice generation 1 helice diffusion avec fichier de config nommé network.cfg
HELICE_GEN1 = ["HeliceZH1", "HeliceZH2", "HeliceZH3"]
CFG_GEN1 = "network.cfg"
# Helice format video 
FORMAT_VIDEO_Z1 = ["HeliceZH1", "HeliceZH1p"]
FORMAT_VIDEO_Z2 = ["HeliceZH2"]
FORMAT_VIDEO_Z3 = ["HeliceZH3", "HeliceZH3p"]
# parametre des wifi
TRUST_WIFI_SSID="TrustHeliceDiffusion"
TRUST_WIFI_KEY="Hel87Diff$$"

WIFI_SSID_HD="HeliceDiffusion"