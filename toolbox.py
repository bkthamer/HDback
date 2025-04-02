from sqlalchemy import func
import models
from parametres import TAILLE_VIGNETTE, CAPTURE_INSTANT, PATH_MEDIA,PATH_CFG,FORMAT_VIDEO_Z3,FORMAT_VIDEO_Z2,FORMAT_VIDEO_Z1
from moviepy import VideoFileClip
from PIL import Image
import os
import sys
import subprocess
from monlogger import logme
from apihelice import obtain_list_media_sd, reload_playlist_sd
from ftplib import FTP
import shutil
    

"""
#Creation des formats video et de la vignette
def video_tools(media_ori,ref,db):
    logme.info("video_tools: demarrage du processus video_tools pour "+ media_ori)
    lib = media_ori.split(".")[0]
    db_result = db.query(models.TachePrepaVideo).filter(models.TachePrepaVideo.id == ref).first()
    if db_result is None:
        logme.error("video_tools: la tache "+ref+ " formats videos et vignette n'a pas ete trouve dans la base")
        return
    db_resultmedia= db.query(models.Media).filter(models.Media.libelle == lib).first()
    
    #Partie pour creer les differents formats videos   
    logme.debug("video_tools: demarrage du processus de mise au format de la video "+ media_ori)
    db_result.status = "en_cours"
    db_result.last_info = func.now()
    db.commit()
    chemin = os.path.join(PATH_MEDIA, media_ori)    
    command = [
        "ffmpeg","-i" ,chemin,
        "-c:v","libx264",
        "-preset","medium",
        "-filter_complex","[0:v]crop=min(iw\\,ih):min(iw\\,ih),scale=384:384,setsar=1[v2];[0:v]crop=ih:ih:(iw-ih)/2:(iw-ih)/2:0,scale =480:480,setsar=1[v1]",
        "-map","[v1]",
        "-profile:v:0","baseline",
        "-level:v:0","3.1",
        "-r:v:0","25",
        "-threads","12",
        "-c:a","copy",chemin.split(".")[0] + "Z3.mp4",
        "-map","[v2]",
        "-profile:v:1","baseline",
        "-level:v:1","4.2",
        "-r:v:1","25",
        "-threads","12",
        "-c:a","copy",chemin.split(".")[0] + "Z2.mp4"
        ]
    try:
        subprocess.run(command,check=True) #le check permet de lever l'exception
        logme.debug("video_tools: processus de creation des differents formats videos termine ")
    except:
        logme.warning("video_tools: Echec du processus de creation des differents formats videos")
        db_result.status = "echec"
        db_result.last_info = func.now()
        db.delete(db_resultmedia)
        video_clean_files(media_ori)
        db.commit()
        return
    
    #Partie pour creer la vignette 
    logme.debug("video_tools: demarrage du processus de creation de la vignette pour "+ media_ori)
    try:
        cheminfrom = chemin.split(".")[0] + "Z3.mp4"        
        clip = VideoFileClip(cheminfrom)
        temp = media_ori.split(".")[0]
        cheminto = os.path.join(PATH_MEDIA, temp + ".png")
        clip.save_frame(cheminto, CAPTURE_INSTANT)
        temp = Image.open(cheminto)
        temp.thumbnail(TAILLE_VIGNETTE)
        temp.save(cheminto)
        clip.close()
        temp.close()
        logme.debug("video_tools: processus de creation de la vignette termine avec success")    
    except:
        logme.warning("video_tools: Echec processus de creation de la vignette pour " + media_ori)        
        db_result.status = "echec"
        db_result.last_info = func.now()
        db.delete(db_resultmedia)
        video_clean_files(media_ori)
        db.commit()
        return
        
    db_result.status = "success"
    db_result.last_info = func.now()        
    db_resultmedia.ready = True
    db.commit()
    logme.info("video_tools: fin du processus video_tools pour "+ media_ori)
"""

def video_tools(media_ori, ref, db):
    logme.info("video_tools: démarrage du processus video_tools pour " + media_ori)
    
    
    base_name, ext = os.path.splitext(media_ori)
    
    
    if shutil.which("ffmpeg") is None:
        logme.error("video_tools: ffmpeg n'est pas trouvé dans le PATH. Veuillez l'installer ou l'ajouter au PATH.")
        return

   
    db_result = db.query(models.TachePrepaVideo).filter(models.TachePrepaVideo.id == ref).first()
    if db_result is None:
        logme.error("video_tools: la tâche " + str(ref) + " formats vidéos et vignette n'a pas été trouvée dans la base")
        return
    db_resultmedia = db.query(models.Media).filter(models.Media.libelle == base_name).first()
    
    
    logme.debug("video_tools: démarrage du processus de mise au format de la vidéo " + media_ori)
    db_result.status = "en_cours"
    db_result.last_info = func.now()
    db.commit()
    
    
    chemin = os.path.join(PATH_MEDIA, media_ori)
    
    
    if not os.path.exists(chemin):
        logme.error("video_tools: Le fichier vidéo spécifié n'existe pas : " + chemin)
        db_result.status = "echec"
        db_result.last_info = func.now()
        db.delete(db_resultmedia)
        db.commit()
        return
    
    
    output1 = os.path.join(PATH_MEDIA, base_name + "Z3.mp4")
    output2 = os.path.join(PATH_MEDIA, base_name + "Z2.mp4")
    
    
    filter_complex = (
        "[0:v]crop=min(iw\\,ih):min(iw\\,ih),scale=384:384,setsar=1[v2];"
        "[0:v]crop=ih:ih:(iw-ih)/2:(iw-ih)/2:0,scale=480:480,setsar=1[v1]"
    )
    
    
    command = [
        "ffmpeg",
        "-i", chemin,
        "-c:v", "libx264",
        "-preset", "medium",
        "-filter_complex", filter_complex,
        
        "-map", "[v1]",
        "-profile:v:0", "baseline",
        "-level:v:0", "3.1",
        "-r:v:0", "25",
        "-threads", "12",
        "-c:a", "copy",
        output1,
        
        "-map", "[v2]",
        "-profile:v:1", "baseline",
        "-level:v:1", "4.2",
        "-r:v:1", "25",
        "-threads", "12",
        "-c:a", "copy",
        output2
    ]
    
    try:
        subprocess.run(command, check=True)
        logme.debug("video_tools: processus de création des différents formats vidéos terminé")
    except Exception as e:
        logme.warning("video_tools: Échec du processus de création des différents formats vidéos : " + str(e))
        db_result.status = "echec"
        db_result.last_info = func.now()
        db.delete(db_resultmedia)
        video_clean_files(media_ori)
        db.commit()
        return

    
    logme.debug("video_tools: démarrage du processus de création de la vignette pour " + media_ori)
    try:
        clip = VideoFileClip(output1)
        vignette_file = os.path.join(PATH_MEDIA, base_name + ".png")
        clip.save_frame(vignette_file, CAPTURE_INSTANT)
        img = Image.open(vignette_file)
        img.thumbnail(TAILLE_VIGNETTE)
        img.save(vignette_file)
        clip.close()
        img.close()
        logme.debug("video_tools: processus de création de la vignette terminé avec succès")
    except Exception as e:
        logme.warning("video_tools: Échec du processus de création de la vignette pour " + media_ori + " : " + str(e))
        db_result.status = "echec"
        db_result.last_info = func.now()
        db.delete(db_resultmedia)
        video_clean_files(media_ori)
        db.commit()
        return

    
    db_result.status = "success"
    db_result.last_info = func.now()
    db_resultmedia.ready = True
    db.commit()
    logme.info("video_tools: fin du processus video_tools pour " + media_ori)

def video_clean_files(media_ori):
    logme.debug("video_clean_files: demarrage du processus de nettoyage des fichiers pour "+ media_ori )
    chemin = os.path.join(PATH_MEDIA, media_ori)
    nb = 0
    if os.path.exists(chemin):
        os.remove(chemin)
        nb+=1
    if os.path.exists(chemin.split(".")[0] + "Z2.mp4"):
        os.remove(chemin.split(".")[0] + "Z2.mp4")
        nb+=1
    if os.path.exists(chemin.split(".")[0] + "Z3.mp4"):
        os.remove(chemin.split(".")[0] + "Z3.mp4")
        nb+=1
    if os.path.exists(chemin.split(".")[0] + ".png"):
        os.remove(chemin.split(".")[0] + ".png")
        nb+=1
    return logme.info("video_clean_files: fin du processus de nettoyage de "+ str(nb) + " fichier(s) pour "+ media_ori )
            
def config_file(ssid,clewifi,nom):
    logme.debug("config_file: demarrage du processus de creation du fichier config pour helice")
    try :
        cheminsource=  "cfgmodel"
        chemindestination= os.path.join(PATH_CFG, nom)
    
        with open (cheminsource, "r") as f:
            contenu = f.readlines()
        contenu.append("STA_SSID=" + ssid + "\n")    
        contenu.append("STA_AUTH_KEY=" + clewifi + "\n")
        contenu.append("DEVICE_NAME=" + nom + "\n")
        with open (chemindestination, "w") as f:
            f.writelines(contenu)
        logme.info("config_file: fin du processus de creation du fichier config pour helice")
        
    except Exception as detail:
        logme.error("config_file: Echec du processus de creation du fichier config pour helice "+ detail)
        return False
    return True 


def Maj_Helice(helice_ref,list_media,ref,db):
    logme.debug("Maj_Helice: demarrage du processus de mise à jour de l'hélice "+ helice_ref +" ref " + str(ref) + " list des media " + str(list_media))
    # Partie1 On va chercher l'ip de l'hélice et on test si elle est accessible, son type pour format video
    osy = sys.platform
       
    try:
        status = "En_cours"
        cause = ""
        ext=""
        request_ip = db.query(models.Production).filter(models.Production.hdref == helice_ref)
        result=request_ip.first()
        if result is None or result.ip == "0.0.0.0" :
            status = "echec"
            cause = "no_ip"
            logme.warning("Maj_Helice: impossible de trouver une ip pour l'hélice ou pas encore en service "+ helice_ref)
            
        
        if  osy != "win32" and status != "echec" :
            if os.system("ping -c 1 " +result.ip) != 0 :
                logme.warning("Maj_Helice: l'hélice n'est pas en ligne "+ helice_ref + " ip " + result.ip)
                status = "echec"
                cause = "disconnected"
        
        if status != "echec" :
            ip = result.ip
            request_mat = db.query(models.Materiel).filter(models.Materiel.hdref == helice_ref)
            result=request_mat.first()
            if result.typemateriel in FORMAT_VIDEO_Z1 : ext="Z1.mp4"    
            elif result.typemateriel in FORMAT_VIDEO_Z2 : ext="Z2.mp4"
            elif result.typemateriel in FORMAT_VIDEO_Z3 : ext="Z3.mp4"
            logme.debug("Maj_Helice: partie 1 OK "+ helice_ref +" termine avec ip: " + ip + " status: " + status + " cause: " + cause +" ext: " + ext)
            db_tache = db.query(models.TacheMaJHelice).filter(models.TacheMaJHelice.id == ref).first()
            db_tache.status = status
            db_tache.last_info = func.now()            
            db.commit()
        
        if status == "echec" :  
            db_tache = db.query(models.TacheMaJHelice).filter(models.TacheMaJHelice.id == ref).first()
            db_tache.status = status
            db_tache.last_info = func.now()
            db_tache.cause = cause
            db_tache.tentatives += 1
            db.commit()
            return
                            
    except: 
        logme.error("Maj_Helice: Echec partie1 pour la tache mise à jour helice "+ helice_ref)
        return      
   
    # Partie 2 On va recuperer la liste des fichiers actuel_sd, on compare avec la nouvelle et on ajoute ceux qui sont manquants
    logme.debug ("debut de la partie 2 pour la tache mise à jour helice "+ helice_ref)
    
    try:
        actuel_sd = obtain_list_media_sd(ip)
        list_media_select = {i + ext for i in set(list_media)}    
        list_media_add = list_media_select - actuel_sd
        list_media_del = actuel_sd - list_media_select
        logme.debug("list_media select: " + str(list_media_select))
        logme.debug("list_media_add: " + str(list_media_add))
        logme.debug("list_media_del: " + str(list_media_del))
        
        if len(list_media_add) > 0 :
            for elt in list_media_add:
                origine = os.path.join(PATH_MEDIA,elt)
                with FTP(ip) as ftp_helice:
                    ftp_helice.cwd('sd_card')
                    with open(origine, 'rb') as f:
                        ftp_helice.storbinary(f"STOR {elt}", f)
        
        
        if len(list_media_del) > 0 :
            for elt in list_media_del:
                with FTP(ip) as ftp_helice:            
                    ftp_helice.cwd('sd_card')
                    ftp_helice.delete(elt)
        
        reload_playlist_sd(ip)
        status = "success"        
        db_tache.status = status
        db_tache.last_info = func.now()
        db_tache.tentatives += 1
        db.commit()
        logme.debug("Maj_Helice: partie 2 et finalisation de la tache mise à jour helice "+ helice_ref +" OK ")
        
    except: 
        logme.error("Maj_Helice: Echec partie2 pour la tache mise à jour helice "+ helice_ref)
        status = "echec"        
        db_tache.status = status
        db_tache.last_info = func.now()
        db_tache.cause = "download fail"
        db_tache.tentatives += 1
        db.commit()
        return

   
    
  