from logging.handlers import RotatingFileHandler
import sys 
import logging

logme=logging.getLogger("monlogger")
logme.setLevel(logging.DEBUG)

# Format des logs
formatterstream = logging.Formatter('%(levelname)s:    %(message)s')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Definition des handlers
monstream_handler = logging.StreamHandler(sys.stdout)
monstream_handler.setLevel(logging.DEBUG)
#monfile_handler = logging.FileHandler("ipo.log")
monfile_handler=RotatingFileHandler('ipo.log', maxBytes=2*1024*1024, backupCount=3)
monfile_handler.setLevel(logging.DEBUG)

# Appliquer le format aux handlers
monstream_handler.setFormatter(formatterstream)
monfile_handler.setFormatter(formatter)

# Ajouter les handlers au logger
logme.addHandler(monstream_handler)
logme.addHandler(monfile_handler)





