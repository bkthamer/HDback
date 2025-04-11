import socket
from parametres import PORT_CMD_HELICE,PATH_MEDIA,PATH_CFG
from ftplib import FTP , error_perm
import os
from monlogger import logme
import gzip
import io


filetoignore={'System Volume Information'}

def decode_helice(reponse):
    reponse_lenght = len(reponse)    
    if reponse[0]== 126 and reponse[reponse_lenght-1] == 127:
        reponse_lenght = len(reponse)
        data_lenght = int.from_bytes(reponse[1:4], 'little')
        reponse= reponse[6:data_lenght+6]
        reponse=str(reponse.decode("UTF-8"))
        x=reponse.split("&")
        res=dict()
        for i in x:
            a=i[:i.index("=")]
            b=i[i.index("=")+1:]
            res[a]=b
        #res=json.dumps(res)
        print(res)    
        return res
    else: return  {"error":"pas de message retourné"}
    
    # Commande sortie de veille d'une helice
def to_start(ip):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as helcmd :
        helcmd.connect((ip, PORT_CMD_HELICE))
        helcmd.send(b'\x7e\x07\x00\x00\x00\x0dPower=1\x7f')
        reponse = helcmd.recv(4096)        
        result= decode_helice(reponse)
        return result

    
def check_vpn_connection():
    # Cette fonction vérifie si le client VPN est connecté en analysant l'interface réseau
    try:
        # Remplace cette logique pour vérifier l'interface réseau TAP-Windows ou toute autre interface utilisée
        vpn_ip = "192.168.16.12"  # L'IP locale attribuée par OpenVPN
        socket.create_connection((vpn_ip, 1194), timeout=5)  # Tester la connexion avec OpenVPN
        return True
    except socket.error:
        return False

def decode_helice(data):
    # Ton code de décodage des données ici
    return data.decode('utf-8')  # Exemple simple de décodage

# Commande de mise en veille (faux stop) helice
def to_veille(ip):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as helcmd :
        helcmd.connect((ip, PORT_CMD_HELICE))
        helcmd.send(b'\x7e\x07\x00\x00\x00\x0dPower=0\x7f')
        reponse = helcmd.recv(4096)        
        result= decode_helice(reponse)
        return result

# Commande pour obtenir info live helice
def req_info(ip):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as helcmd :
        helcmd.connect((ip, PORT_CMD_HELICE))
        helcmd.send(bytes.fromhex('7E 00 00 00 00 01 7F'))
        reponse = helcmd.recv(4096)
        result = decode_helice(reponse)    
        return result
    
# Commande init d'une helice
def init(ip):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as helcmd :
        helcmd.connect((ip, PORT_CMD_HELICE))
        helcmd.send(bytes.fromhex('7E 00 00 00 00 6D 7F'))
        reponse = helcmd.recv(4096)
        return reponse

# Reload la playlist interne avec les fichiers sur sd      
def reload_playlist_sd(ip): 
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as helcmd :
        helcmd.connect((ip, PORT_CMD_HELICE))
        helcmd.send(bytes.fromhex('7E 00 00 00 00 05 7F'))
        reponse = helcmd.recv(4096)
        return reponse

#Récupère la liste des fichiers sur la SD format set
def obtain_list_media_sd(ip):
    with FTP(ip) as ftp_helice:
        ftp_helice.cwd('sd_card')
        filepresent = set(ftp_helice.nlst())
        filepresent = filepresent - filetoignore
        return filepresent

#Envoyer un fichier sur la SD UNIQUE ET SUR Z3 Phase1 et reloading
def add_file_sd(ip,libelle):
    print(libelle)
    fichier = libelle + "Z3.mp4"
    origine = os.path.join(PATH_MEDIA,fichier)
    print(origine)
    if os.path.isfile(origine):
        try:
            with FTP(ip) as ftp_helice:
                ftp_helice.cwd('sd_card')
                with open(origine, 'rb') as f:
                    ftp_helice.storbinary(f"STOR {fichier}", f)
        except:
            return{"message":"fichier non envoyé"}
    else:
        return{"message":"fichier non trouvé"}
    
    reload_playlist_sd(ip)
    return{"message":"fichier envoyé"}

def delete_file_sd(ip,fichier):
    print(fichier)
    try:
        with FTP(ip) as ftp_helice:
            ftp_helice.cwd('sd_card')
            ftp_helice.delete(fichier )
            
    except:
        return{"message":"fichier non supprimé"}
    return{"message":"fichier supprimé"}
                
def pushconfig_sd(ip,hdref,setupname):
    logme.debug("config_sd: Demarrage du processus  de l'envoi du fichier de configuration")
    origine = os.path.join(PATH_CFG,hdref)
    if os.path.isfile(origine):
        try:
            with FTP(ip) as ftp_helice:
                ftp_helice.cwd('sd_card')
                with open(origine, 'rb') as f:
                    ftp_helice.storbinary(f"STOR {setupname}", f)
        except Exception as detail:
            logme.error(f"pushconfig_sd: Echec de l'envoi du fichier de configuration - {detail} " )
            return False
    else:
        logme.error("config_sd: le fichier de config n'existe pas")
        return False
    
    #Ici effacer le fichier review ok
    logme.info("config_sd: Succes de l'envoi du fichier de configuration")
    return True

def disable_file_sd(ip, fichier):
    try:
        with FTP(ip) as ftp_helice:
            ftp_helice.cwd('sd_card')
            
            ftp_helice.rename(fichier, f'dis/{fichier}')
        return {"message": "Fichier déplacé dans le dossier dis"}
    except Exception as e:
        return {"message": f"Erreur de désactivation: {str(e)}"}

def enable_file_sd(ip, fichier):
    try:
        base_name = os.path.basename(fichier)
        
        with FTP(ip) as ftp_helice:
            
            ftp_helice.cwd('/sd_card')
            
            if base_name.lower() == "dis":
                
                try:
                    ftp_helice.cwd("dis")
                except Exception as e:
                    return {"message": f"Dossier 'dis' introuvable: {str(e)}"}

                try:
                    file_list = ftp_helice.nlst()
                except Exception as e:
                    return {"message": f"Erreur lors de la lecture du dossier 'dis': {str(e)}"}
                finally:
                    
                    ftp_helice.cwd("..")
                
                
                try:
                    root_files = ftp_helice.nlst()
                    for fname in root_files:
                        if fname.lower().endswith(".mp4"):
                            try:
                                ftp_helice.delete(fname)
                                print(f"Fichier supprimé: {fname}")
                            except Exception as e:
                                print(f"Erreur lors de la suppression de {fname}: {str(e)}")
                except Exception as e:
                    print(f"Erreur lors de la lecture de la racine: {str(e)}")
                
                moved_files = []
                
                for fname in file_list:
                    if fname.lower().endswith(".mp4"):
                        source = f"dis/{fname}"
                        destination = fname
                        try:
                            
                            try:
                                ftp_helice.size(destination)
                                
                                continue
                            except Exception:
                                pass
                            
                            
                            ftp_helice.rename(source, destination)
                            moved_files.append(fname)
                        except Exception as e:
                            print(f"Erreur pour {fname}: {str(e)}")
                
                reload_playlist_sd(ip)
                return {"message": f"Fichiers restaurés: {', '.join(moved_files)}" if moved_files else "Aucun fichier à restaurer."}

            else:
                source = f"dis/{base_name}"
                destination = base_name
                try:
                    ftp_helice.size(source)
                except Exception:
                    return {"message": f"Fichier {base_name} introuvable dans 'dis'."}

                try:
                    ftp_helice.size(destination)
                    return {"message": f"Le fichier {base_name} existe déjà."}
                except Exception:
                    pass
                
                ftp_helice.rename(source, destination)
                reload_playlist_sd(ip)
                return {"message": f"Fichier {base_name} restauré."}

    except Exception as e:
        return {"message": f"Erreur: {str(e)}"}
