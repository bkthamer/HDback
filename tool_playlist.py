from ftplib import FTP
import os
import sys

from sqlalchemy import func
from apihelice import reload_playlist_sd
import models
from monlogger import logme
from parametres import FORMAT_VIDEO_Z1, FORMAT_VIDEO_Z2, FORMAT_VIDEO_Z3, PATH_MEDIA

# A partir de l'id de la playlist récupérer la liste des media de cette playlist
def get_list_media(playlist_id,db):
    list_media = []
    results = db.query(models.Media).join(models.MIP, models.Media.id == models.MIP.mip_media_id).filter(models.MIP.mip_playlist_id == playlist_id).all()
    for item in results:
        list_media.append(item.libelle)  
    return list_media

# A partir de l'id de la playlist récupérer la liste des pdv (materiel hdref) de cette playlist
def get_list_cible(playlist_id,db):
    list_cible = [] 
    results = db.query(models.Pdv).join(models.PIP, models.Pdv.id == models.PIP.pip_pdv_id).filter(models.PIP.pip_playlist_id == playlist_id).all()
    for item in results:
        list_cible.append(item.materiel_hdref)
    return list_cible

#Activer la playlist sur l'hélice en envoyant les fichiers sur l'hélice (sans controle d'existence sur sd)
def activate_pl_to_helice(helice_ref,list_media,ref,db):
    logme.debug("try to activate_pl_to_helice" + helice_ref +" ref " + str(ref) + " list des media " + str(list_media))
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
            logme.warning("try to activate_pl_to_helice: impossible de trouver une ip pour l'hélice ou pas encore en service "+ helice_ref)
            
        
        if  osy != "win32" and status != "echec" :
            if os.system("ping -c 1 " +result.ip) != 0 :
                logme.warning("try to activate_pl_to_helice: l'hélice n'est pas en ligne "+ helice_ref + " ip " + result.ip)
                status = "echec"
                cause = "disconnected"
        
        db_tache = db.query(models.TacheMaJHelice).filter(models.TacheMaJHelice.id == ref).first()
        
        if status != "echec" :
            ip = result.ip
            request_mat = db.query(models.Materiel).filter(models.Materiel.hdref == helice_ref)
            result=request_mat.first()
            if result.typemateriel in FORMAT_VIDEO_Z1 : ext="Z1.mp4"    
            elif result.typemateriel in FORMAT_VIDEO_Z2 : ext="Z2.mp4"
            elif result.typemateriel in FORMAT_VIDEO_Z3 : ext="Z3.mp4"

        
        if status == "echec" :  
            db_tache = db.query(models.TacheMaJHelice).filter(models.TacheMaJHelice.id == ref).first()
            db_tache.status = status
            db_tache.last_info = func.now()
            db_tache.cause = cause
            db_tache.tentatives += 1
            db.commit()
            return
                            
    except: 
        logme.error("try to activate_pl_to_helice: Partie1 "+ helice_ref)
        return      
   
    # Partie 2 On ajoute les media de la playlist sur l'hélice    
    
    try:
        
        list_media_add = [item + ext for item in list_media]
   
        if len(list_media_add) > 0 :
            for elt in list_media_add:
                origine = os.path.join(PATH_MEDIA,elt)
                with FTP(ip) as ftp_helice:
                    ftp_helice.cwd('sd_card')
                    with open(origine, 'rb') as f:
                        ftp_helice.storbinary(f"STOR {elt}", f)        

        
        
        reload_playlist_sd(ip)
        status = "success"
        db_tache.status = status
        db_tache.last_info = func.now()
        db_tache.tentatives += 1
        db.commit()
 
        
        
    except:
        logme.error("try to activate_pl_to_helice: Echec partie2 pour la tache mise à jour helice "+ helice_ref)
        status = "echec"        
        db_tache.status = status
        db_tache.last_info = func.now()
        db_tache.cause = "download fail"
        db_tache.tentatives += 1
        db.commit()
        return