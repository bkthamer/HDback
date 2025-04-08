from fastapi.responses import FileResponse, StreamingResponse
from monlogger import logme
from apscheduler.schedulers.background import BackgroundScheduler
from middleware import log_requests
from fastapi import FastAPI,HTTPException,Depends, UploadFile,BackgroundTasks,File,Form,Query,Body
from pydantic import BaseModel, EmailStr,Field, field_validator,IPvAnyAddress
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from typing import Annotated, List, Optional, Union
from basededonnee import SessionLocal,moteurbd
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import or_,and_,not_,func
from toolbox import video_tools,video_clean_files,config_file,Maj_Helice
from apihelice import to_start,to_veille,req_info,init,reload_playlist_sd,obtain_list_media_sd,add_file_sd,delete_file_sd,pushconfig_sd,disable_file_sd,enable_file_sd
import models
from models import MIP  # Ensure MIP is imported
import re
import shutil
import os
import uuid
import json
import subprocess
import sys
import jwt
from datetime import datetime, timedelta, date,timezone
from fastapi.security import OAuth2PasswordBearer
import smtplib
from email.mime.text import MIMEText

#Mise en place du dossier mediatheque si non existant
from parametres import VERSION,PATH_MEDIA,MIME_TYPES,PATH_CFG,PYCAV,HELICE_OLD_GEN,HELICE_GEN1,TRUST_WIFI_SSID,TRUST_WIFI_KEY,WIFI_SSID_HD,CFG_OLD,CFG_GEN1
os.makedirs(PATH_MEDIA, exist_ok=True)
os.makedirs(PATH_CFG, exist_ok=True)

VALID_MAC_ADDRESS = r"^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}$"
DEBUT_MAC_ADDRESS = r"^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:$"



ipo = FastAPI(title="API Helice Diffusion",version=VERSION)
logme.info("Demarrage de l'"+ ipo.title  + " " + ipo.version)

scheduler = BackgroundScheduler()
scheduler.start()


"""Ajout pour permettre de traiter des fct endpoint dans autres fichiers """
ipo.add_middleware(
    BaseHTTPMiddleware,
    dispatch=log_requests,
)


"""Partie securisation"""
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

origins = [
    "http://localhost:3000", 
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3000",  
]

ipo.add_middleware(    
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





"""Création du shéma de la base de donnée uniquement en création et ajout de table depuis le models.py"""

models.Base.metadata.create_all(bind=moteurbd)



"""Fonction ouverture fermeture de session de la base de donnée"""  
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

############################################# WEBSOCKET POUR TACHE EN ARRIERE PLAN ######################
#########################################################################################################

#########################################################################################################

"""modeles pydantic pour le corps des requetes"""
class Typemateriel(BaseModel):
    id: int = Field (default=None, description="id du typemateriel")
    libelle: str = Field (default=None, description="libelle du typemateriel")
    

########################### END POINT ######################

@ipo.get("/")
async def root():
    """Retourne un message de bienvenue """
    return {"message": "Bienvenue sur la racine du backend Hélice Diffusion by Ipocanp-2024"}

#################################### PROD REQUESTS ########################################
@ipo.get ("/nawan/list/full")
async def nawan_list_full(db:db_dependency):    
    #results= db.query(models.Materiel).join(models.Materiel.typemateriel).values(models.Materiel.hdref,models.Typemateriel.libelle)
    #results= db.query(models.Materiel,models.Materiel.typemateriel).join(models.Typemateriel).all()
    #results = db.query(models.Production).join(models.Materiel,models.Production.id == models.Materiel.id).join(models.Materiel.typemateriel).values(
    results = db.query(models.Production).join(models.Materiel,models.Production.hdref == models.Materiel.hdref).values(
        models.Materiel.typemateriel,
        models.Production.ref_infra,
        models.Production.ip,
        models.Production.bail,
        models.Production.lastchange,
        models.Materiel.hdref
        )
    resultlist = []
    for  typemateriel,ref_infra, ip, bail, lastchange, hdref in results:
        resultlist.append({'typemateriel':typemateriel,
                           'ref_infra':ref_infra,
                           'ip':ip,
                           'bail':bail,
                           'lastchange':lastchange,
                           'hdref':hdref})        
    return resultlist

@ipo.get ("/nawan/list/ready")
async def nawan_list_ready(db:db_dependency):    
    results = db.query(models.Production).join(models.Materiel,models.Production.hdref == models.Materiel.hdref).filter(
        and_(models.Production.ip != "0.0.0.0", models.Production.bail == True)).values(
        models.Materiel.typemateriel,
        models.Production.ref_infra,
        models.Production.ip,
        models.Production.bail,
        models.Production.lastchange,
        models.Materiel.hdref
        )
    resultlist = []
    for  typemateriel,ref_infra, ip, bail, lastchange, hdref in results:
        resultlist.append({'typemateriel':typemateriel,
                           'ref_infra':ref_infra,
                           'ip':ip,
                           'bail':bail,
                           'lastchange':lastchange,
                           'hdref':hdref})        
    return resultlist
   
@ipo.get ("/nawan/list/notready")
async def nawan_list_notready(db:db_dependency):    
    results = db.query(models.Production).join(models.Materiel,models.Production.hdref == models.Materiel.hdref).filter(
        or_(models.Production.ip == "0.0.0.0", models.Production.bail == False)).values(
        models.Materiel.typemateriel,
        models.Production.ref_infra,
        models.Production.ip,
        models.Production.bail,
        models.Production.lastchange,
        models.Materiel.hdref
        )
    resultlist = []
    for  typemateriel,ref_infra, ip, bail, lastchange, hdref in results:
        resultlist.append({'typemateriel':typemateriel,
                           'ref_infra':ref_infra,
                           'ip':ip,
                           'bail':bail,
                           'lastchange':lastchange,
                           'hdref':hdref})        
    return resultlist

class Patch_infra(BaseModel):
    ref_infra: str = Field (default="", description="ref_infra (Mac ou serialnumber suivant le cas)")
    new_ip: str = Field (default="0.0.0.0", description="Assignation d'une IP")
    new_bail: bool = Field (default=False, description="Etat du Bail")
@ipo.patch("/nawan/update")
async def nawan_update(newpatch_infra:Patch_infra,db:db_dependency):
    results = db.query(models.Production).filter(models.Production.ref_infra == newpatch_infra.ref_infra)
    ref_infra = results.first()
    if ref_infra is None: return {"message": "Not found"}
    results.update({"ip": newpatch_infra.new_ip, "bail": newpatch_infra.new_bail,"lastchange": func.now(),"lastchange_by": "nawan"},synchronize_session=False)
    db.commit()
    return {"message": "updated"}


class terminal(BaseModel):
    terminal_hdref: str = Field (default="", description="le hdref du terminal")
@ipo.patch("/materiel/lecteur/miseenprod")
async def miseenprod(newterminal:terminal,db:db_dependency):
    logme.debug("miseenprod: demarrage du processus de mise en production de lecteur de media")
    try:
        result=db.query(models.Materiel).filter(and_(models.Materiel.hdref == newterminal.terminal_hdref,models.Materiel.status !="en_service"))
        ref = result.first()
        if ref is None: return {"etat": "error", "message": "Ce materiel n'est pas disponible ou entrées à vérifier"}
        mac= ref.macadresse
        resultat = db.query(models.Production).filter(models.Production.ref_infra == mac)
        ref = resultat.first()
        if ref is not None: return {"etat": "error", "message": "Ce materiel est déjà affecté" }
        db.add(models.Production(ip="0.0.0.0",bail= 0,ref_infra = mac, lastchange = func.now(), lastchange_by ="HelDiff",hdref = newterminal.terminal_hdref))
        result.update({"status":"en_service","iptemp":"0.0.0.0"})
        db.commit()
        db_clean=db.query(models.Decouverte).filter(models.Decouverte.macadresse == mac).first()
        db.delete(db_clean)
        db.commit()
        
    except: 
        logme.error("miseenprod: Une erreur s'est produite lors de la mise en production de lecteur de media")
        return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }    
        
    logme.info("miseenprod:  mise en production de lecteur de media")
    return {"etat": "info", "message": "Nawan a été informé de l'ajout en production de ce lecteur de media"}

   

@ipo.patch("/materiel/routeur/miseenprod")
async def miseenprod(newterminal:terminal,db:db_dependency):
    logme.debug("miseenprod: demarrage du processus de mise en production du routeur")
    try:
        result=db.query(models.Materiel).filter(and_(models.Materiel.hdref == newterminal.terminal_hdref,models.Materiel.status !="en_service"))
        ref = result.first()
        if ref is None: return {"etat": "error", "message": "Ce routeur n'est pas disponible ou entrées à vérifier" }
        sn= ref.serialnumber 
        resultat = db.query(models.Production).filter(models.Production.ref_infra == sn)
        ref = resultat.first()
        if ref is not None: return {"etat": "error", "message": "Ce routeur est déjà affecté" }
        db.add(models.Production(ip="0.0.0.0",bail= 0,ref_infra = sn, lastchange = func.now(), lastchange_by ="HelDiff",hdref = newterminal.terminal_hdref))
        result.update({"status":"en_service","iptemp":"0.0.0.0"})
        db.commit()
        db_clean=db.query(models.Decouverte).filter(models.Decouverte.serialnumber == sn).first()
        db.delete(db_clean)
        db.commit()
        
    except:
        logme.error("miseenprod: Une erreur s'est produite lors de la mise en production de routeur")
        return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }    
    
    logme.info("miseenprod:  mise en production de routeur")    
    return {"etat": "info", "message": "Nawan a été informé de l'ajout en production de ce routeur"}
    
    

################################# DECOUVERTE ##########################################

class Decouverte(BaseModel):
    macadresse: Optional[str] = Field (default="no:no:no:no:no:no")
    serialnumber: Optional[str] = Field (default="")
    iptemp:str =Field (default="0.0.0.0",description ="ip temporaire")
    wifi:Optional[str] =Field (default="Non renseigné",description ="ip temporaire")
    
    @field_validator("macadresse")
    @classmethod
    def validate_macadresse(cls, value:str) -> str:
        if not re.match(VALID_MAC_ADDRESS, value,re.IGNORECASE):
           raise ValueError("Format Adresse mac invalide")
        return value
@ipo.post("/decouverte/add")
async def decouverte_add(newdecouverte:Decouverte,db:db_dependency):
    db_test = db.query(models.Decouverte).filter(or_(models.Decouverte.iptemp == newdecouverte.iptemp,and_(models.Decouverte.macadresse == newdecouverte.macadresse,
                                                      models.Decouverte.serialnumber == newdecouverte.serialnumber))).first()
    if db_test is not None:
        return {"message": "decouverte déjà existante"}
    
    db_decouverte = models.Decouverte(macadresse = newdecouverte.macadresse,
                                      serialnumber = newdecouverte.serialnumber,
                                      iptemp = newdecouverte.iptemp,
                                      wifi = newdecouverte.wifi)    
    db.add(db_decouverte)
    db.commit()
    return {"message": "decouverte ajoutée"}

@ipo.patch("/decouverte/updateip")
async def decouverte_upt(newdecouverte:Decouverte,db:db_dependency):
    result=db.query(models.Decouverte).filter(models.Decouverte.macadresse == newdecouverte.macadresse)
    ref = result.first()
    if ref is None : return{"message": "Oups pas de reference pour ce materiel"}
    result.update({"iptemp":newdecouverte.iptemp})
    db.commit()
    return {"message": "ip temporaire mise à jour"}

@ipo.post("/decouverte/searchbymac")
async def decouverte_sbm(newdecouverte:Decouverte,db:db_dependency):
    result=db.query(models.Decouverte).filter(models.Decouverte.macadresse == newdecouverte.macadresse)
    ref = result.first()
    if ref is None : return{"message": "NO-MAC"}
    return {"iptemp":ref.iptemp}
 
@ipo.get("/decouverte/list")
async def decouverte_list(db:db_dependency):
    results = db.query(models.Decouverte).all()
    return results

@ipo.get("/nawan/iee/list")
async def nawan_iee_list(db:db_dependency):
    results =db.query(models.Iee).all()
    return results

class Iee(BaseModel):
    iee: str = Field (description ="début des mac acceptables au format xx:xx:xx: ")
    @field_validator("iee")
    @classmethod
    def validate_iee(cls, value:str) -> str:
        if not re.match(DEBUT_MAC_ADDRESS, value,re.IGNORECASE):
           raise ValueError("Format debut de mac invalide")
        return value
        
@ipo.post("/nawan/iee/add")
async def nawan_iee_add(newiee:Iee,db:db_dependency):
    db_test = db.query(models.Iee).filter(models.Iee.iee == newiee.iee).first()
    if db_test is not None:
        return {"message": "iee deja existante"}
    db_iee = models.Iee(iee = newiee.iee)
    db.add(db_iee)
    db.commit()
    return {"message": "iee ajoutée"}

@ipo.delete("/nawan/iee/delete")
async def nawan_iee_delete(newiee:Iee,db:db_dependency):
    db_test = db.query(models.Iee).filter(models.Iee.iee == newiee.iee).first()
    if db_test is None:
        return {"message": "iee non existante"}
    db.delete(db_test)
    db.commit()
    return {"message": "iee supprimée"}


### POUR DEBUG OU DEV SEULEMENT ###
@ipo.get("/initialise/valeur/test")
async def initialise_valeur_test( db:db_dependency):
    models.Base.metadata.drop_all(bind=moteurbd)
    models.Base.metadata.create_all(bind=moteurbd)
    #exemple de decouverte
    db.add(models.Iee(iee = "2c:c3:e6:"))
    db.add(models.Iee(iee = "90:97:d5:"))
    db.add(models.Iee(iee = "c0:e7:bf:"))
    
     
    
    #exemple de typemateriel
    db.add(models.Typemateriel(libelle = "HeliceZH1"))
    db.add(models.Typemateriel(libelle = "HeliceZH1p"))
    db.add(models.Typemateriel(libelle = "HeliceZH2"))
    db.add(models.Typemateriel(libelle = "HeliceZH3"))
    db.add(models.Typemateriel(libelle = "HeliceZH3p"))
    db.add(models.Typemateriel(libelle = "RouteurAR617"))    
    db.commit()
    #exemple de materiel
    db.add(models.Decouverte(macadresse = "aa:aa:aa:aa:aa:aa",serialnumber = "aaaaa",iptemp = "0.0.0.1"))
    db.add(models.Decouverte(macadresse = "ab:ab:ab:aa:aa:aa",serialnumber = "bbbbb",iptemp = "0.0.0.0",wifi = "cléwifiRout"))
      
    db.add(models.Materiel(macadresse = "5c:e7:47:0b:72:de",serialnumber = "2S22B00117089B",hdref = "MRPat",status = "en_stock",typemateriel = "RouteurAR617",wifi = "Hel87Diff$$"))
    db.add(models.Materiel(macadresse = "2c:c3:e6:8b:a6:3a",serialnumber = "sn-bb",hdref = "MHPat",status = "en_stock",typemateriel = "HeliceZH3p"))

    db.commit()
    #exemple de client
    db.add(models.Client(societe = "SAS IPOCANP LABO",enseigne = "IPOCANP",nomcontact = "Nom1",prenomcontact = "Patrick",emailcontact = "email1@email.fr",telephonecontact = "00000001",adresse = "adresse1",ville = "ville1",codepostal = "24001"))
    db.add(models.Client(societe ="SAS NAWAN LABO",enseigne = "NAWAN",nomcontact = "Nom2",prenomcontact = "David",emailcontact = "email2@email.fr",telephonecontact = "00000002",adresse = "adresse2",ville = "ville2",codepostal = "24002"))
    db.commit()
    #exemple de categorie
    db.add(models.Categorie(nom = "Divers"))
    db.commit()
    #exemple de media
    #db.add(models.Media(libelle = "check",description = "Description1",categorie_id = 1))
  
    db.commit()
   
    
   
    
    return {"message": "valeur test initialisée"}
    
###TYPEMATERIEL###
@ipo.post("/add/typemateriel")
async def add_typemateriel(newtypemateriel:Typemateriel, db:db_dependency):
    db_typemateriel = models.Typemateriel(libelle = newtypemateriel.libelle)                                        
    #db_typemateriel = models.Typemateriel(**newtypemateriel.model_dump())
    db.add(db_typemateriel)
    db.commit()
    return {"message": "created", "id":db_typemateriel.id, "libelle":db_typemateriel.libelle}

@ipo.get("/typemateriel/list")
async def list_typemateriels(db:db_dependency):
    return db.query(models.Typemateriel).order_by(models.Typemateriel.libelle.asc()).all()

@ipo.delete("/typemateriel/delete")
async def delete_typemateriels(newtypemateriel:Typemateriel,db:db_dependency):
    db_typemateriel = db.query(models.Typemateriel).filter(or_(models.Typemateriel.id == newtypemateriel.id,models.Typemateriel.libelle == newtypemateriel.libelle)).first()
    if db_typemateriel is None:        
        return {"message": "not found", "libelle":newtypemateriel.libelle}
    else:
        db.delete(db_typemateriel)
        db.commit()
        return {"message": "deleted", "id":db_typemateriel.id, "libelle":db_typemateriel.libelle}

@ipo.patch("/typemateriel/update")
async def patch_typemateriels(newtypemateriel:Typemateriel,db:db_dependency):
    for db_typemateriel in db.query(models.Typemateriel):
        if db_typemateriel.id == newtypemateriel.id:
            db_typemateriel.libelle = newtypemateriel.libelle
            db.commit()
            return {"message": "updated", "id":db_typemateriel.id, "libelle":db_typemateriel.libelle}
    if db_typemateriel is None:        
        return {"message": "not found", "libelle":newtypemateriel.libelle}

#########################################  MATERIEL     ######################################
class Materiel(BaseModel): 
    id: int = Field(default=None, description="id du materiel")   
    macadresse: str = Field(default=None, description="Adresse mac de l'équipemet - A renseigner au format AA:BB:CC:DD:EE:FF")
    serialnumber: str = Field(default=None, description="Numero de série fournisseur du produit  .")
    hdref: str = Field(default=None, description="Référence chez Helice Diffusion")
    status: str =Field(default=None, description="liste de choix en_stock, en_maintenance, en_service")
    typemateriel: str =Field(default=None, description="type de materiel")
    wifi: Optional[str] =Field(default=None, description="wifi")
    iptemp: Optional[str] =Field(default=None, description="ip temporaire")
    
    @field_validator("macadresse")
    @classmethod
    def validate_macadresse(cls, value:str) -> str:
        if not re.match(VALID_MAC_ADDRESS, value,re.IGNORECASE):
           raise ValueError("Format Adresse mac invalide")
        return value

@ipo.post("/materiel/add")
async def add_materiel(newmateriel:Materiel,db:db_dependency):
    if ((newmateriel.typemateriel not in HELICE_OLD_GEN and newmateriel.typemateriel not in HELICE_GEN1)or(newmateriel.iptemp[:10] == PYCAV) ) :
        if newmateriel.typemateriel in HELICE_OLD_GEN or newmateriel.typemateriel in HELICE_GEN1: newmateriel.status = "en_migration"
        try:
            logme.debug("add_materiel: on essaye d'inscrire un materiel hors helice dans le stock")
            db_materiel = models.Materiel(macadresse = newmateriel.macadresse,
                                  serialnumber = newmateriel.serialnumber,
                                  hdref = newmateriel.hdref,
                                  status = newmateriel.status,
                                  typemateriel = newmateriel.typemateriel,
                                  wifi = newmateriel.wifi,
                                  iptemp = newmateriel.iptemp)
            db.add(db_materiel)
            db.commit()            
        except Exception as detail:
            logme.error(f"add_materiel: Echec de l'inscription d'un materiel dans le stock - {detail}" )
            return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }
        logme.info("add_materiel: ok inscription materiel dans le stock avec hdref "+ newmateriel.hdref)
        return {"etat": "success", "message":"OK Nouveau Materiel enregistré sans configuration "}
    
    #creation du fichier de configuration temporaire pour les helices NON PYCAV
    if newmateriel.iptemp[:10] != PYCAV:
        logme.debug("add_materiel: on demande l'ajout d'une helice NON PYCAV dans stock")
        if newmateriel.typemateriel in HELICE_GEN1 : setupname = CFG_GEN1
        elif newmateriel.typemateriel in HELICE_OLD_GEN : setupname = CFG_OLD
        else: 
            logme.error("add_materiel: Ne correspond pas à un  type de materiel attendu "+ newmateriel.typemateriel)
            return {"etat": "error", "message": "Une erreure s'est produite verifier le type de materiel" }
        
        generation =  config_file(TRUST_WIFI_SSID,TRUST_WIFI_KEY,newmateriel.hdref)
        if not generation : 
            return {"etat": "error", "message": "Une erreure s'est produite dans la generation du fichier config" }
        else:         
            pousseconfig = pushconfig_sd(newmateriel.iptemp,newmateriel.hdref,setupname)
            if not pousseconfig :
                return {"etat": "error", "message": "Une erreure s'est produite dans l'envoi du fichier config" }
            else:
                try:
                    logme.debug("add_materiel: on essaye d'inscrire l'helice  NON PYCAV dans le stock")
                    db_materiel = models.Materiel(macadresse = newmateriel.macadresse,
                                  serialnumber = newmateriel.serialnumber,
                                  hdref = newmateriel.hdref,
                                  status = newmateriel.status,
                                  typemateriel = newmateriel.typemateriel,
                                  wifi = newmateriel.wifi,
                                  iptemp = newmateriel.iptemp)
                    db.add(db_materiel)
                    db.commit()            
                except Exception as detail:
                    logme.error(f"add_materiel: Echec de l'inscription de l'helice NON PYCAV dens le stock - {detail}")
                    return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }
                logme.info("add_materiel: ok inscription materiel helice NON PYCAV dans le stock avec hdref "+ newmateriel.hdref)
                return {"etat": "success", "message":"OK Nouveau Materiel enregistré avec configuration injectée "}
 

@ipo.get("/materiel/list")
async def list_materiels(db:db_dependency):
    return db.query(models.Materiel).order_by(models.Materiel.status.desc()).all()

@ipo.get("/routeurstock/list")
async def list_routeurstock(db:db_dependency):
    return db.query(models.Materiel).filter(and_(models.Materiel.status =="en_stock"),(models.Materiel.typemateriel=="RouteurAR617")).all()

@ipo.get("/lecteurstock/list")
async def list_lecteurstock(db:db_dependency):
    return db.query(models.Materiel).filter(and_(models.Materiel.status =="en_stock"),(models.Materiel.typemateriel!="RouteurAR617")).all()

@ipo.get("/lecteurmigration/list")
async def list_lecteurmig(db:db_dependency):
    return db.query(models.Materiel).filter(and_(models.Materiel.status =="en_migration"),(models.Materiel.typemateriel!="RouteurAR617")).all()

@ipo.post("/materiel/globalsearch/{search}")
async def globalsearch_materiel(search: str,db:db_dependency):
    #toto= db.query(models.Typemateriel).join(models.Materiel).filter(or_(models.Materiel.macadresse.contains(search) ,models.Materiel.serialnumber.contains(search),models.Materiel.hdref.contains(search),models.Materiel.status.contains(search))).order_by(models.Materiel.macadresse.desc()).all()
    toto= db.query(models.Materiel).filter(or_(models.Materiel.macadresse.contains(search) ,models.Materiel.serialnumber.contains(search),models.Materiel.hdref.contains(search),models.Materiel.status.contains(search))).order_by(models.Materiel.macadresse.desc()).all()
    return toto

################################################## CLIENT ############################################
class Client(BaseModel):
    id : int = Field(default=None, description="id du client")
    societe : str = Field(default=None, description="société du client")
    enseigne : str = Field(default=None, description="enseigne du client")
    nomcontact : str = Field(default=None, description="nom du contact")
    prenomcontact : str = Field(default=None, description="prenom du contact")
    emailcontact : EmailStr = Field(default=None, description="email du contact")
    telephonecontact : str = Field(default=None, description="telephone du contact")
    adresse : str = Field(default=None, description="adresse du client")
    ville : str = Field(default=None, description="ville du client")
    codepostal : int = Field(default=None, description="code postal du client")
    

@ipo.post("/client/add")
async def add_client(newclient:Client,db:db_dependency):
    try:
        db_client = models.Client(societe = newclient.societe,
                              enseigne = newclient.enseigne,
                              nomcontact = newclient.nomcontact,                              
                              prenomcontact = newclient.prenomcontact,
                              emailcontact = newclient.emailcontact,
                              telephonecontact = newclient.telephonecontact,
                              adresse = newclient.adresse,
                              ville = newclient.ville,
                              codepostal = newclient.codepostal)
        db.add(db_client)
        db.commit()
    except: return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }
    
    return {"etat": "success", "message":"OK Nouveau Client enregistré"}
@ipo.get("/client/list")
async def client_list(db:db_dependency):
    return db.query(models.Client).order_by(models.Client.societe.desc()).all()


###SITE###
class Site(BaseModel):
    id : Optional[int] = Field(default=None, description="id du site")
    nomsite : str = Field(default=None, description="nom du site")
    adresse : Optional[str] = Field(default=None, description="adresse du site")
    ville : Optional[str] = Field(default=None, description="ville du site")
    codepostal : Optional[int] = Field(default=None, description="code postal du site")
    client_id : Optional[int] = Field(default=None, description="id du client")
    routeur_hdref : str = Field(default=None, description="hdref du routeur")
    site_wifi: Optional[str] = Field(default=None, description="wifi du site")

@ipo.post("/site/add")
async def add_site(newsite:Site,db:db_dependency):
    db_materiel = db.query(models.Materiel).filter(models.Materiel.hdref == newsite.routeur_hdref).first()    
    
    #On met en base le site
    try:
        db_prod = db.query(models.Production).filter(models.Production.ref_infra == db_materiel.serialnumber).first()
        if db_prod is not None: return {"etat": "error", "message": "Ce materiel est deja en production" }
        db_site = models.Site(nomsite = newsite.nomsite,
                              adresse = newsite.adresse,
                              ville = newsite.ville,
                              codepostal = newsite.codepostal,
                              client_id = newsite.client_id,
                              routeur_hdref= newsite.routeur_hdref,
                              site_wifi = db_materiel.wifi)
        db.add(db_site)
        db.commit()
        logme.debug ("add_site: Nouveau Site: " + newsite.nomsite + " enregistré dans la base avec routeur "+ newsite.routeur_hdref)
    except:
        logme.error ("add_site: Echec de l'inscription du site "+ newsite.nomsite + "avec routeur "+ newsite.routeur_hdref )
        return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }
    
    if db_materiel.iptemp[:10] != PYCAV:
        # On met à jour le status du routeur dans materiel et ip à 0.0.0.0 et on met en production le routeur
        try:
            
            db_materiel.iptemp = "0.0.0.0"
            db_materiel.status = "en_service"
            db.add(models.Production(ip="0.0.0.0",bail= 0,ref_infra = db_materiel.serialnumber, lastchange = func.now(), lastchange_by ="HelDiff",hdref = db_materiel.hdref))
            db.commit()
            result = db.query(models.Decouverte).filter(models.Decouverte.serialnumber == db_materiel.serialnumber).first()
            db.delete(result)
            db.commit()
            logme.debug ("add_site: mise à jour du status du routeur  et ip temporaire et mise en production et efface decouverte "+ newsite.routeur_hdref)
            
        except:
            logme.error ("add_site: Echec mise à jour du status du routeur  et ip temporaire et mise en production  "+ newsite.routeur_hdref)
            return {"etat": "error", "message": "Contacter l'administrateur" }
        
        return {"etat": "success", "message":"Le site est maintenant lié avec un routeur mis en production"}
    
    else:
        #On met à jour le status du routeur dans materiel
        try:
            db_materiel.status = "en_migration"
            db.commit()
            logme.debug ("add_site: mise à jour du status du routeur  en migration "+ newsite.routeur_hdref)
        except:
            logme.error ("add_site: Echec mise à jour du status du routeur  en migration  "+ newsite.routeur_hdref)
            return {"etat": "error", "message": "Contacter l'administrateur routeur migration" }
    
        return {"etat": "info", "message":"Le site est crée avec un routeur Ex-Pycav, dans l'attente d'une affectation d'hélice celuici reste en migration" }

@ipo.get("/site/list")
async def site_list(db:db_dependency):
    return db.query(models.Site).order_by(models.Site.nomsite.desc()).all()

@ipo.get("/site/list/byclient/{client_id}")
async def site_list_byclient(client_id:int,db:db_dependency):
    return db.query(models.Site).filter(models.Site.client_id == client_id).order_by(models.Site.nomsite.desc()).all()


@ipo.get("/site/list/migration")
async def site_list_mi(db:db_dependency):
    return db.query(models.Site).join(models.Materiel).filter(and_(models.Site.routeur_hdref == models.Materiel.hdref),models.Materiel.status == "en_migration").all()
###PDV###
class Groupdv(BaseModel):
    id : int = Field(default=None, description="id du groupdv")
    libelle : str = Field(default=None, description="nom du groupdv")
    description : str = Field(default=None, description="description du groupdv")
    

@ipo.post("/add/groupdv")
async def add_groupdv(newgroupdv:Groupdv,db:db_dependency):
    db_groupdv = models.Groupdv(libelle = newgroupdv.libelle,
                                description = newgroupdv.description)
    db.add(db_groupdv)
    db.commit()
    
    return {"message": "created", "id":db_groupdv.id, "nom":db_groupdv.libelle}





###################################################  MEDIATHEQUE #####################################################
class Souscategorie(BaseModel):
    id : int = Field(default=None, description="id de la souscategorie")
    nom : str = Field(default=None, description="nom de la souscategorie")
    categorie_id : int = Field(default=None, description="id de la categorie")

@ipo.post("/add/souscategorie/mediatheque")
async def add_souscategorie(newsouscategorie:Souscategorie,db:db_dependency):
    db_souscategorie = models.Souscategorie(nom = newsouscategorie.nom,
                                            categorie_id = newsouscategorie.categorie_id)
    db.add(db_souscategorie)
    db.commit()
    return {"message": "created", "id":db_souscategorie.id, "nom":db_souscategorie.nom}



class Categorie(BaseModel):
    id : int = Field(default=None, description="id de la categorie")
    nom : str = Field(default=None, description="nom de la categorie")   
 
@ipo.get("/media/cat/list")
async def media_cat_list(db:db_dependency):
    return db.query(models.Categorie).order_by(models.Categorie.nom.asc()).all()

@ipo.post("/media/cat/add")
async def add_categorie(newcategorie:Categorie,db:db_dependency):
    db_categorie = models.Categorie(nom = newcategorie.nom)
    db.add(db_categorie)
    db.commit()
   
    



class Subcategorie(BaseModel):
    id : int = Field(default=None, description="id de la subcategorie")
    nom : str = Field(default=None, description="nom de la categorie")
    id_cat : int = Field(default=None, description="id de la categorie")
    
@ipo.post("/media/subcat/listbycat")
async def media_subcat_listbycat(cat:Categorie,db:db_dependency):
    return db.query(models.Souscategorie).filter(models.Souscategorie.categorie_id == cat.id).order_by(models.Souscategorie.nom.desc()).all()

@ipo.get("/media/subcat/list")
async def media_subcat_list(db:db_dependency):
    return db.query(models.Souscategorie).order_by(models.Souscategorie.nom.desc()).all()
    
@ipo.post("/media/subcat/add")
async def add_categorie(newsubcategorie:Subcategorie,db:db_dependency):
    db_subcategorie = models.Souscategorie(nom = newsubcategorie.nom,categorie_id = newsubcategorie.id_cat,)
    db.add(db_subcategorie)
    db.commit()
    


class Media(BaseModel):
    id : Optional[int] = Field(default=None, description="id du media")
    libelle : str = Field(default="Oups", description="source du media")    
    description : Optional[str]= Field(default="Aucune description", description="description du media")
    categorie_id : Optional[int] = Field(default= 1, description="id de la categorie")
    souscategorie_id : Optional[int] = Field(default=None, description="id de la souscategorie")


@ipo.post("/mediatheque/media/add")
async def add_media(
    tache_arriereplan: BackgroundTasks,
    db: db_dependency,
    new_upload_file: UploadFile,
    owner_id: Optional[Union[int, str]] = Query(None),  
    newmedia: Media = Depends()
):
    
    if isinstance(owner_id, str) and owner_id.lower() in ["null", "none", ""]:
        owner_id = None
    elif owner_id is not None and isinstance(owner_id, str):
        try:
            owner_id = int(owner_id)
        except ValueError:
            return {"etat": "error", "message": "Format de owner_id incorrect"}
    
    db_media = db.query(models.Media).filter(models.Media.libelle == newmedia.libelle).first()
    if db_media is not None:
        return {"etat": "error", "message": "Ce nom est déjà utilisé"}

    # Vérification du type Mime...
    try:
        logme.debug("check le format du fichier soumis:" + new_upload_file.content_type)
        if new_upload_file.content_type not in MIME_TYPES:
            return {"etat": "error", "message": "Le fichier ne semble pas être un média conforme"}
    except:
        return {"etat": "error", "message": "Echec test de compatibilité du fichier"}

    # Enregistrement du fichier...
    try:
        media_ori = newmedia.libelle + ".ori"
        destpath = os.path.join(PATH_MEDIA, media_ori)
        with open(destpath, "wb") as buffer:
            shutil.copyfileobj(new_upload_file.file, buffer)
    except:
        return {"etat": "error", "message": "Une erreur s'est produite lors du téléchargement"}

    # Création du média en base
    try:
        db_media = models.Media(
            libelle=newmedia.libelle,
            description=newmedia.description,
            categorie_id=newmedia.categorie_id,
            souscategorie_id=newmedia.souscategorie_id,
            owner_id=owner_id  # owner_id peut être None
        )
        db.add(db_media)
        db.commit()
    except:
        return {"etat": "error", "message": "Une erreur s'est produite vérifier les entrées"}

    # Lancement de la tâche en arrière-plan
    ref = uuid.uuid4()
    qui = "username"
    db_tache = models.TachePrepaVideo(
        id=ref,
        soumis_par=qui,
        type_tache="preparation vignette",
        titre=newmedia.libelle,
        sourcename=new_upload_file.filename,
        owner_id=owner_id
    )
    db.add(db_tache)
    db.commit()
    tache_arriereplan.add_task(video_tools, media_ori, ref, db)

    return {"etat": "info", "message": "Création de la vignette en cours. Veuillez patienter quelques instants avant d'utiliser ce nouveau média."}

@ipo.get("/media/taches/list")
async def media_taches_list(db:db_dependency):
    return db.query(models.TachePrepaVideo).all()

@ipo.delete("/mediatheque/media/del")
async def del_media(oldmedia:Media,db:db_dependency):
    logme.debug("Demande de suppression du media: "+oldmedia.libelle)
    result=db.query(models.Media).filter(models.Media.libelle == oldmedia.libelle).first()
    if result is None : return{"etat": "error", "message": "Ce media n'a pas été trouvé"}
    db.delete(result)
    db.commit()
    try :
       media_ori=oldmedia.libelle+".ori"
       video_clean_files(media_ori)
       return {"etat": "success", "message":f"Le media {oldmedia.libelle} a bien été supprimé"}
    except: return {"etat": "error", "message": "Une erreure s'est produite lors de l'effacement du media"}
     

@ipo.get("/mediatheque/list")
async def list_mediatheque(db:db_dependency):
    return db.query(models.Media).order_by(models.Media.libelle.asc()).all()

class FiltreMedia(BaseModel):
    cat_id : Optional[int] = Field(default=None, description="id categorie du media")
    subcat : Optional[int] = Field(default=None, description="id souscategorie du media")
@ipo.post ("/media/filtre")
async def filtre_media(newfiltre:FiltreMedia,db:db_dependency):
    if newfiltre.subcat is None : return db.query(models.Media).filter(models.Media.categorie_id == newfiltre.cat_id).order_by(models.Media.libelle.asc()).all()
    else : return db.query(models.Media).filter(models.Media.categorie_id == newfiltre.cat_id).filter(models.Media.souscategorie_id == newfiltre.subcat).order_by(models.Media.libelle.asc()).all()


@ipo.get("/mediatheque/vignette/{vignette_name}")
async def get_vignette(vignette_name: str):
    # Renvoyer l'image dans la réponse
    vignette_name = vignette_name + ".png"
    vignette_path = os.path.join(PATH_MEDIA, vignette_name)
    if os.path.exists(vignette_path):
        return FileResponse(vignette_path, media_type="image/png")
    else:
        logme.warning(f"Probleme de chargement de l'image {vignette_name}")
        return {"etat": "info", "message": f"Probleme de chargement de l'image {vignette_name}"}
    
    
@ipo.get("/mediatheque/video/{video_name}")
async def get_video(video_name: str):
    video_name = video_name + "Z3.mp4"
    video_path = os.path.join(PATH_MEDIA, video_name)
    def video_stream():
        with open(video_path, "rb") as video_file:
            yield from video_file

    if os.path.exists(video_path):
        return StreamingResponse(video_stream(), media_type="video/mp4")
    else:
        logme.warning(f"Probleme de chargement de la video pour previsualiser {video_name}")
        return {"etat": "info", "message": f"Probleme de chargement de la video pour previsualiser {video_name}"}
         

###################################### HELICE ###################################""

@ipo.get("/terminal/etat/{terminal_hdref}")
async def etat_terminal(terminal_hdref: str,db:db_dependency):
    req=db.query(models.Production).filter(models.Production.hdref == terminal_hdref)
    res=req.first()
    if res is None : return "gray"
    ip = res.ip
    if ip == "0.0.0.0" : return "blue"
    if (os.system("ping -c 1 " +ip)) != 0 : return "red"
    else : return "green"

class RemoteHelice(BaseModel):
    hdref:str
    ordre: str #start,veille,reload,info,listsd,addmedia,delmedia
    libelle: Optional [str]= Field(default=None)
    fichier: Optional [str]= Field(default=None)
@ipo.post("/helice/remote")
async def remote(newremotehelice:RemoteHelice,db:db_dependency):
    msg ="Commade non disponible"
    req=db.query(models.Production).filter(models.Production.hdref == newremotehelice.hdref)
    res=req.first()
    if res is None : return {"message":"cette hélice n'est pas en production"}
    if res.ip == "0.0.0.0" : return {"message":"cette hélice n'a pas d'IP"}
    if res.bail == 0 : return {"message":"cette hélice n'a pas de bail valide"}
    ip = res.ip
    osy = sys.platform
    if osy != "win32" : 
        if (os.system("ping -c 1 " +ip)) != 0 : return {"message":"cette hélice ne répond pas "}
    match newremotehelice.ordre:
        case "start":
            msg = to_start(ip)
        case "veille":
            msg = to_veille(ip)
        case "info":
            msg = req_info(ip)
        case "raz":
            msg = init(ip)
        case "reload":
            msg = reload_playlist_sd(ip)
        case "listsd":
            msg = obtain_list_media_sd(ip)
        case "addmedia":
            msg = add_file_sd(ip,newremotehelice.libelle)
        case "delmedia":
            msg = delete_file_sd(ip,newremotehelice.fichier)
        case "disablemedia":
            msg = disable_file_sd(ip, newremotehelice.fichier)
        case "enablemedia":
            msg = enable_file_sd(ip, newremotehelice.fichier)    
        case _: return msg
    return(msg)
        
class migration(BaseModel):
    hdref_helice: str
    id_site: int
    hdref_pdv: str
    emplacement: Optional[str]= Field(default=None)
    multimig: bool = Field (default=False, description="Autres helices devant migrer sur même site")
@ipo.post("/pycav/migration")
async def pycav_migration(newmigration:migration,db:db_dependency):
    db_pdv = db.query(models.Pdv).filter (models.Pdv.pdv_hdref == newmigration.hdref_pdv).first()
    if db_pdv is not None:
        return {"etat": "error", "message": "Le nom est déjà utilisé" }
    logme.debug("pycav_migration: demarrage du processus de migration pycav")    
    jointure=db.query(models.Materiel,models.Site).join(models.Site,models.Materiel.hdref==models.Site.routeur_hdref).filter(models.Site.id==newmigration.id_site)
    resultats = jointure.all()
    json_resultats = []
    for resultat in resultats:
        json_resultat = {
            'wifi': resultat.Materiel.wifi,
            "hdref_routeur": resultat.Site.routeur_hdref}
        json_resultats.append(json_resultat)
    wifikey = json_resultats[0]["wifi"]
    routeur = json_resultats[0]["hdref_routeur"]
    terminal = db.query(models.Materiel).filter(models.Materiel.hdref == newmigration.hdref_helice).first()
    if terminal.typemateriel in HELICE_OLD_GEN : 
        setupname = CFG_OLD
    else :
        setupname = CFG_GEN1
    if (os.system("ping -c 1 " +terminal.iptemp)) != 0 :
        logme.warning("pycav_migration: impossible de se connecter à l'helice")
        return {"etat": "error", "message": "Impossible de se connecter à l'helice"}
    generation = config_file(WIFI_SSID_HD,wifikey,newmigration.hdref_helice)
    if not generation : 
        return {"etat": "error", "message": "Une erreure s'est produite dans la generation du fichier config" }
    pousseconfig = pushconfig_sd(terminal.iptemp,newmigration.hdref_helice,setupname)
    if not pousseconfig :
        return {"etat": "error", "message": "Une erreure s'est produite dans l'envoi du fichier config" }
    # On peut pousser le routeur en production
    if newmigration.multimig == False :
        return {"etat": "success", "message":"L'hélice a été reconfigurée"}
    try:
        db_materiel = db.query(models.Materiel).filter(models.Materiel.hdref == routeur).first() 
        db_materiel.iptemp = "0.0.0.0"
        db_materiel.status = "en_service"
        db.add(models.Production(ip="0.0.0.0",bail= 0,ref_infra = db_materiel.serialnumber, lastchange = func.now(), lastchange_by ="HelDiff",hdref = db_materiel.hdref))
        result = db.query(models.Decouverte).filter(models.Decouverte.serialnumber == db_materiel.serialnumber).first()
        db.delete(result)
        db.commit()
        logme.debug ("pycav_migration: mise à jour du status du routeur  et init ip temporaire et mise en production et efface decouverte sn: "+ db_materiel.serialnumber)
            
    except:
        logme.error ("pycav_migration: Echec mise à jour du status du routeur  et init ip temporaire et mise en production et efface decouverte sn: "+ db_materiel.serialnumber)
        return {"etat": "error", "message": "Contacter l'administrateur" }
        
    return {"etat": "success", "message":"L'hélice a été reconfigurée et le routeur a été migré vers la production"}
    
    
    
class Pdv(BaseModel):
    id : Optional[int] = Field(default=None, description="id du pdv")
    pdv_hdref : Optional [str] = Field(default=None, description="nom du pdv par hd")
    materiel_hdref : Optional [str] = Field(default=None, description="hdref du materiel")
    emplacement : Optional [str]= Field(default=None, description="dans la vitrine")
    site_id : Optional[int] = Field(default=None, description="id du site")
    
@ipo.post("/pdv/setuphelice")
async def pdv_setuphelice(newpdv:Pdv,db:db_dependency):
    db_pdv = db.query(models.Pdv).filter (models.Pdv.pdv_hdref == newpdv.pdv_hdref).first()
    if db_pdv is not None:
        return {"etat": "error", "message": "Le nom est déjà utilisé" }
    logme.debug("pdv_setuphelice: demarrage du processus du setup helice pour pdv")
    db_site = db.query(models.Site).filter (models.Site.id == newpdv.site_id).first()  
    terminal = db.query(models.Materiel).filter(models.Materiel.hdref == newpdv.materiel_hdref).first()
    if terminal.typemateriel in HELICE_OLD_GEN : 
        setupname = CFG_OLD
    else :
        setupname = CFG_GEN1
    if (os.system("ping -c 1 " +terminal.iptemp)) != 0 : 
        logme.warning("pdv_setuphelice: impossible de se connecter à l'helice")
        return {"etat": "error", "message": "Impossible de se connecter à l'helice"}
    generation = config_file(WIFI_SSID_HD,db_site.site_wifi,newpdv.materiel_hdref)
    if not generation : 
        return {"etat": "error", "message": "Une erreure s'est produite dans la generation du fichier config" }
    pousseconfig = pushconfig_sd(terminal.iptemp,newpdv.materiel_hdref,setupname)
    if not pousseconfig :        
        return {"etat": "error", "message": "Une erreure s'est produite dans l'envoi du fichier config" }
   
    return {"etat": "success", "message":"L'hélice a été reconfigurée"}
 
@ipo.post("/pdv/add")
async def add_pdv(newpdv:Pdv,db:db_dependency):
    try:
        db_pdv = models.Pdv(pdv_hdref = newpdv.pdv_hdref,
                        materiel_hdref = newpdv.materiel_hdref,
                        emplacement = newpdv.emplacement,
                        site_id = newpdv.site_id)
        db.add(db_pdv)
        db.commit()
    except: return {"etat": "error", "message": "Une erreure s'est produite vérifier les entrées" }
    
    return {"etat": "success", "message":"OK Nouveau Point de diffusion enregistré"}

@ipo.get("/pdv/list/bysite/{site_id}")
async def pdv_list_bysite(site_id:int,db:db_dependency):
    return db.query(models.Pdv).filter(models.Pdv.site_id == site_id).all()

@ipo.get("/helices/op/list")
async def helice_op_list(db:db_dependency):
    return db.query(models.Materiel).filter(and_(models.Materiel.status == "en_service",models.Materiel.typemateriel.contains("Helice") )).order_by(models.Materiel.hdref.desc()).all()



class Suppdv(BaseModel):
    pdv_hdref: str
    mat_hdref:str
@ipo.delete("/pdv/delete")
async def pdv_del(newpdv:Suppdv,db:db_dependency):
    logme.debug("pdv_del: Process pour effacer le pdv "+ newpdv.pdv_hdref)
    try:
        db_prod=db.query(models.Production).filter(models.Production.hdref == newpdv.mat_hdref).first()
        if db_prod is not None:
            db.delete(db_prod)
            db.commit()
        db_pdv=db.query(models.Pdv).filter(models.Pdv.pdv_hdref == newpdv.pdv_hdref).first()
        db.delete(db_pdv)
        db.commit()
        db_mat=db.query(models.Materiel).filter(models.Materiel.hdref == newpdv.mat_hdref).first()
        db.delete(db_mat)
        db.commit()
        logme.info("pdv_del: Ok fin du process effacer pdv "+newpdv.pdv_hdref)
        return {"etat":"success", "message":"Point de diffusion effacé, materiel retiré de la base (Nécessite une nouvelle découverte pour réutilisation, la référence peut être réunitilisée)"}
    except:
        logme.error("pdv_del: Echec du process d'effacement pdv")
        return {"etat":"error","message":"Echec du retrait du point de diffusion"}
  
    

class Supsite(BaseModel):
    site_id :int
    mat_hdref:str
@ipo.delete("/site/delete")
async def site_del(newsite:Supsite,db:db_dependency):
    db_site = db.query(models.Site).filter(models.Site.id == newsite.site_id).first()
    site_href = db_site.nomsite
    logme.debug("site_del: Process pour effacer site : "+ site_href + " avec site id: " + str(newsite.site_id))
    try:
        db_pdv=db.query(models.Pdv).filter(models.Pdv.site_id == newsite.site_id).first()
        if db_pdv is not None:
            logme.info("site_dev: Le site ne peut pas etre effacer, des pdv sont associés")
            return {"etat":"error","message":"Impossible d'effacer le site avant retrait des pdv associés"}
        db_prod=db.query(models.Production).filter(models.Production.hdref == db_site.routeur_hdref).first()
        if db_prod is not None:
            db.delete(db_prod)
            db.commit()
            db.delete(db_site)
        db.commit()
        db_mat= db.query(models.Materiel).filter(models.Materiel.hdref == newsite.mat_hdref).first()
        db_mat.status="en_stock"
        db.commit()
        logme.info("site_dev: Ok le site a été effacé "+ site_href)
        return {"etat":"success", "message":"Le site à été effacé et le routeur mis en stock"}
    except:
        logme.error("site_del: Echec du process d'effacement du site")
        return {"etat":"error","message":"Echec du retrait du site"}
    
    
###### TACHE ARRIERE PLAN MAJ HELICE ######
class HeliceMedia(BaseModel):
    hdref : str
    listmedia : List
@ipo.post("/helice/majmedia")
async def helice_majmedia(tache_fond:BackgroundTasks,newmaj:HeliceMedia,db:db_dependency):
    ref= uuid.uuid4()
    qui = "username"
    try:
        db_tache = models.TacheMaJHelice(id = ref,
                            soumis_par = qui,
                            list_media = newmaj.listmedia,
                            helice_hdref = newmaj.hdref,
                            last_info = func.now(),
                            tentatives =0,
                            status = "Demande"
                          )
        db.add(db_tache)
        db.commit() 
           
        tache_fond.add_task(Maj_Helice,newmaj.hdref,newmaj.listmedia,ref,db)
        return {"etat": "info", "message": "Votre demande a bien été enregistrée"}
                
    except:
        logme.error("echec du lancement de la tache mise à jour helice "+ newmaj.hdref)
        return {"etat": "error", "message": "Echec de la demande, veuillez contacter l'administrateur" }


    
@ipo.get("/helice/taches/maj/list")
async def helice_taches(db:db_dependency):
    return db.query(models.TacheMaJHelice).all()


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="L'email de l'utilisateur")
    password: str = Field(..., min_length=6, description="Le mot de passe de l'utilisateur")
    role: Optional[str] = "user"  # Défini "user" comme valeur par défaut

    class Config:
        orm_mode = True

@ipo.post("/creer_compte")
async def creer_compte(user: UserCreate, db: Session = Depends(get_db)):
    # Vérifier si l'email existe déjà
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Hasher le mot de passe
    hashed_password = pwd_context.hash(user.password)
    
    # Créer un nouvel utilisateur
    new_user = models.User(email=user.email, password=hashed_password, role=user.role)
    
    # Ajouter et enregistrer l'utilisateur dans la base de données
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"msg": "Compte créé avec succès"}
    
SECRET_KEY = "ma_clé_secrète"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class UserLogin(BaseModel):
    email: str
    password: str


@ipo.post("/login")
async def login(user: UserLogin, db: db_dependency):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    
    if not db_user or not pwd_context.verify(user.password, db_user.password):  
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    
    access_token = create_access_token(data={"sub": db_user.email, "role": db_user.role , "site_id": db_user.site_id})
    return {"access_token": access_token, "token_type": "bearer"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        site_id: str = payload.get("site_id")
        if email is None or role is None:
            raise credentials_exception
        return {"email": email, "role": role , "site_id": site_id}
    except jwt.PyJWTError:
        raise credentials_exception


@ipo.get("/protected_route")
async def protected_route(current_user: str = Depends(get_current_user)):
    return {"message": f"Bonjour, {current_user['email']}! Vous avez le rôle {current_user['role']} {current_user['site_id']} ."}


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

@ipo.put("/update_user")
async def update_user(user_update: UserUpdate, db: db_dependency, current_user: dict = Depends(get_current_user)):
    db_user = db.query(models.User).filter(models.User.email == current_user['email']).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    
    if user_update.email:
       
        existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        db_user.email = user_update.email
    
   
    if user_update.password:
        db_user.password = pwd_context.hash(user_update.password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"msg": "Informations mises à jour avec succès"}


@ipo.get("/users")
async def get_users(db:db_dependency):
    return db.query(models.User).all()

@ipo.get("/pdv")
async def get_pdv(db:db_dependency):
    return db.query(models.Pdv).all()


class SiteAssignment(BaseModel):
    email: str  
    site_id: int     

@ipo.put("/admin/assign_site")
async def assign_site_admin(
    site_assignment: SiteAssignment,
    db: db_dependency,
     
):
   
    
    
    db_user = db.query(models.User).filter(models.User.email == site_assignment.email).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    
    db_user.site_id = site_assignment.site_id  
    db.commit()
    db.refresh(db_user)

    return {"msg": f"Le site ID {site_assignment.site_id} a été assigné à {db_user.email} avec succès"}

@ipo.get("/sites")
async def get_sites(db:db_dependency):
    return db.query(models.Site).all()

class PingRequest(BaseModel):
    ip_address: str

@ipo.post("/ping")
async def ping_ip(request: PingRequest):
    """
    Effectue un ping sur l'adresse IP reçue dans le body.
    Retourne {"success": True} si le ping reçoit une réponse, sinon {"success": False}.
    """
    try:
        ip_address = request.ip_address

        
        if sys.platform == "win32":
            command = ["ping", "-n", "1", ip_address]
        else:
            command = ["ping", "-c", "1", ip_address]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Vérifie le code retour de la commande
        return {"success": result.returncode == 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class HdrefRequest(BaseModel):
    hdref: str

@ipo.post("/get_ip")
async def get_ip_by_hdref(request: HdrefRequest, db: Session = Depends(get_db)):
    production = db.query(models.Production).filter(models.Production.hdref == request.hdref).first()
    
    if not production:
        raise HTTPException(status_code=404, detail="HDREF non trouvé")
    
    return {"ip": production.ip}


class DemandeCreate(BaseModel):
    sujet: str
    description: str
    image: Optional[str] = None  

    class Config:
        orm_mode = True

class DemandeResponse(DemandeCreate):
    id: int
    date: datetime

if not os.path.exists("images"):
    os.makedirs("images")


@ipo.post("/ajoutdemande", response_model=DemandeResponse)
async def creer_demande(
    sujet: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(None),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    # Dossier où stocker les images (chemin absolu)
    IMAGES_FOLDER = r"C:\Users\Cybertek.tn\Desktop\PFE\HDback-main\images"
    
    # S'assurer que le dossier existe
    if not os.path.exists(IMAGES_FOLDER):
        os.makedirs(IMAGES_FOLDER)
    
    file_location = None
    if image:
        # Générer un nom de fichier unique
        image_filename = f"{uuid.uuid4().hex}_{image.filename}"
        # Chemin complet pour sauvegarder le fichier
        file_path = os.path.join(IMAGES_FOLDER, image_filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())
        # Stocker le chemin absolu dans la base de données
        file_location = file_path
    
    new_demande = models.Demande(
        sujet=sujet,
        description=description,
        image=file_location,  # Enregistre le chemin absolu de l'image
        email=email
    )
    
    db.add(new_demande)
    db.commit()
    db.refresh(new_demande)
    return new_demande

images = os.path.abspath("images")
ipo.mount("/images", StaticFiles(directory=images), name="images")


@ipo.get("/demandes")
async def get_demandes(db: Session = Depends(get_db)):
    return db.query(models.Demande).all()


@ipo.get("/users/count")
async def get_users_count(db: db_dependency):
    count = db.query(models.User).count()
    return {"total_users": count}

@ipo.get("/site/count")
async def get_users_count(db: db_dependency):
    count = db.query(models.Site).count()
    return {"total_sites": count}


@ipo.get("/helices/count")
async def get_users_count(db: db_dependency):
    count = db.query(models.Production).count()
    return {"total_helices": count}


@ipo.get("/media")
async def get_media(db: db_dependency):
    results = (
        db.query(models.Media, models.Categorie.nom.label("categorie_nom"))
          .join(models.Categorie, models.Media.categorie_id == models.Categorie.id)
          .all()
    )
    media_list = []
    for media, categorie_nom in results:
        media_data = media.__dict__.copy()
        media_data["categorie_nom"] = categorie_nom
        media_list.append(media_data)
    return media_list


class UserEmailRequest(BaseModel):
    email: str

@ipo.post("/get_user_id")
async def get_user_id(request: UserEmailRequest, db: db_dependency):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return {"user_id": user.id_user}


@ipo.get("/categories_all")
async def get_categories_all(db: db_dependency):
    return db.query(models.Categorie).all()


@ipo.get("/souscategorie_all")
async def get_souscategorie_all(db: db_dependency):
    return db.query(models.Souscategorie).all()

class UserEmail(BaseModel):
    email: str

@ipo.post("/count_media_by_id_user")
async def count_helice_by_id_user(request: UserEmail, db: db_dependency):
    user_id_response = await get_user_id(request, db)
    user_id = user_id_response["user_id"]
    count = db.query(models.Media).filter(models.Media.owner_id == user_id).count()
    return {"total_media": count}

@ipo.post("/nombre_demande")
async def get_demande_by_user(request : UserEmail  ,db: db_dependency):
    count = db.query(models.Demande).filter(models.Demande.email == request.email).count()
    return {"total_demande": count}



###############################################################PLAYLIST APPROCHE#####################################################





class HeureMinute(BaseModel):
    heure: int
    minute: int
    
class Sch(BaseModel):
    sch_id:int
    sch_playlist_id : int
    sch_start_date : date  # '2014-05-31'
    sch_end_date : date   # '2014-05-31'
    sch_day_of_week : List[int]   # 0 = Lundi, 1 = Mardi, 2 = Mercredi, 3 = Jeudi, 4 = Vendredi, 5 = Samedi, 6 = Dimanche  [0,1,2,3,4,5,6]
    sch_hour_start : HeureMinute  #{"heure": 24, "minute": 60}
    sch_hour_end : HeureMinute  #{"heure": 24, "minute": 60}


class Playlist(BaseModel):
    pl_id: int 
    pl_libelle : Optional[str] = None
    pl_description : Optional[str] = None
    pl_proprietaire : Optional[int] = None
    pl_status : Optional[bool]  = None


#Methode pour creer une playlist
@ipo.post("/playlist/add")
async def add_playlist(newplaylist:Playlist,db:db_dependency):
    try:
        db.add(models.Playlist(libelle = newplaylist.pl_libelle,description = newplaylist.pl_description,
                           proprietaire = newplaylist.pl_proprietaire,status =False))
        db.commit()
        logme.info("add_playlist: Nouvelle playlist enregistrée sous id : "+ str(newplaylist.pl_id))
        return {"etat": "success", "message": "Playlist ajoutée"}
    except:
        logme.error("add_playlist: Une erreur s'est produite lors de l'ajout de la playlist "+ newplaylist.pl_libelle)
        return {"etat": "error", "message": "Une erreur s'est produite lors de l'ajout de la playlist"}
    


    

@ipo.delete("/playlist/delete")
async def delete_playlist(delplaylist: Playlist, db: db_dependency):
    try:
        db.query(models.Grille).filter(models.Grille.playlist_id == delplaylist.pl_id).delete()
        db.query(models.MIP).filter(models.MIP.mip_playlist_id == delplaylist.pl_id).delete()
        db.query(models.PIP).filter(models.PIP.pip_playlist_id == delplaylist.pl_id).delete()
        db.query(models.Playlist).filter(models.Playlist.id == delplaylist.pl_id).delete()
        
        db.commit()
        logme.info(f"Playlist {delplaylist.pl_id} supprimée avec succès")
        return {"etat": "success", "message": "Playlist supprimée"}

    except Exception as e:
        logme.error(f"Erreur suppression playlist {delplaylist.pl_id}: {str(e)}")
        return {"etat": "error", "message": f"Erreur de suppression: {str(e)}"}

class Mip(BaseModel):
    list_media_id : list
    del_media_id : list
    mip_playlist_id : int
    mip_add_by : str

#Methode pour mettre à jour les medias d'une playlist (ajout ou/et suppression)
@ipo.post("/playlist/majmedia")
async def pl_maj_media(newmip:Mip,db:db_dependency):
    try:
        for media_id in newmip.list_media_id:
            db.merge(models.MIP(mip_media_id = media_id,mip_playlist_id = newmip.mip_playlist_id,mip_add_by = newmip.mip_add_by))
        for media_id in newmip.del_media_id:
            db.query(models.MIP).filter(and_(models.MIP.mip_media_id == media_id,models.MIP.mip_playlist_id == newmip.mip_playlist_id)).delete()
        db.commit()
        logme.info("pl_add_media: Ajout du  des media "+ str(newmip.list_media_id)+ " ou Suppression " +(str(newmip.del_media_id))+ " dans playlist "+ str(newmip.mip_playlist_id))
        return {"etat": "success", "message": "Ajout ou suppression du media dans la playlist"}
    except:
        logme.error("pl_add_media: Une erreur lors de l'ajout ou Suppression du media "+ str(media_id)+" dans playlist "+ str(newmip.mip_playlist_id))
        return {"etat": "error", "message": "Une erreur s'est produite lors de l'ajout ou suppression du media dans playlist"}



class Pip(BaseModel):
    list_pdv_id : list
    del_pdv_id : list
    pip_playlist_id : int
    pip_add_by : str

#Methode pour mettre à jour les pdv associés à d'une playlist (ajout ou/et suppression)
@ipo.post("/playlist/majpdv")
async def pl_maj_pdv(newpip:Pip,db:db_dependency):
    try:
        for pdv_id in newpip.list_pdv_id:
            db.merge(models.PIP(pip_pdv_id = pdv_id,pip_playlist_id = newpip.pip_playlist_id,pip_add_by = newpip.pip_add_by))
        for pdv_id in newpip.del_pdv_id:
            db.query(models.PIP).filter(and_(models.PIP.pip_pdv_id == pdv_id,models.PIP.pip_playlist_id == newpip.pip_playlist_id)).delete()
        db.commit()
        logme.info("pl_maj_pdv: Ajout du  des pdv "+ str(newpip.list_pdv_id)+ " ou Suppression " +(str(newpip.del_pdv_id))+ " dans playlist "+ str(newpip.pip_playlist_id))
        return {"etat": "success", "message": "Ajout ou suppression associations pdv dans la playlist"}
    except:
        logme.error("pl_maj_pdv: Une erreur lors de l'ajout ou Suppression du pdv"+ str(pdv_id)+" dans playlist "+ str(newpip.pip_playlist_id))
        return {"etat": "error", "message": "Une erreur s'est produite lors de l'ajout ou suppression association pdv dans playlist"}

#Methode pour lister les playlists 
@ipo.get("/playlist/list")
async def list_playlist(db:db_dependency):
    return db.query(models.Playlist).all()

class Mip(BaseModel):
    list_media_id : list
    mip_playlist_id : int
    mip_add_by : str

@ipo.post("/playlist/addmedia")
async def pl_add_media(newmip:Mip,db:db_dependency):
    try:
        for media_id in newmip.list_media_id:
            print(media_id)
            db.merge(models.MIP(mip_media_id = media_id,mip_playlist_id = newmip.mip_playlist_id,mip_add_by = newmip.mip_add_by))
        db.commit()
        logme.info("pl_add_media: Ajout du ou des media "+ str(newmip.list_media_id)+" dans playlist "+ str(newmip.mip_playlist_id))
        return {"etat": "success", "message": "Ajout du media dans la playlist"}
    except:
        logme.error("pl_add_media: Une erreur lors de l'ajout du media "+ str(media_id)+" dans playlist "+ str(newmip.mip_playlist_id))
        return {"etat": "error", "message": "Une erreur s'est produite lors de l'ajout du media dans playlist"}
    

@ipo.get("/playlist/listmedia/{playlist_id}")
async def list_media(playlist_id:int,db:db_dependency):
    return db.query(models.Media).join(models.MIP, models.Media.id == models.MIP.mip_media_id).filter(models.MIP.mip_playlist_id == playlist_id).all()



class Pip(BaseModel):
    pip_playlist_id: int
    pip_pdv_id: int
    pip_add_by: str = None
    
@ipo.post("/playlist/addpdv")
async def pl_add_pdv(newpip:Pip,db:db_dependency):
    try:
        db.add(models.PIP(playlist_id = newpip.pip_playlist_id,pdv_id = newpip.pip_pdv_id))
        db.commit()
        logme.info("pl_add_pdv: Ajout de la playlist "+ str(newpip.pip_playlist_id)+" dans le pdv "+ str(newpip.pip_pdv_id))
        return {"etat": "success", "message": "Ajout de la playlist dans le pdv"}
    except:
        logme.error("pl_add_pdv: Une erreur lors de l'ajout de la playlist "+ str(newpip.pip_playlist_id)+" dans le pdv "+ str(newpip.pip_pdv_id))
        return {"etat": "error", "message": "Une erreur s'est produite lors de l'ajout de la playlist dans pdv"}



#Methode pour ajouter une planification à une playlist
@ipo.post("/playlist/addsch")
async def pl_add_sch(newsch:Sch,db:db_dependency):
    try:
        db.add(models.Grille(playlist_id = newsch.sch_playlist_id,start_date = newsch.sch_start_date,end_date = newsch.sch_end_date,
                          day_of_week = newsch.sch_day_of_week,hour_start = newsch.sch_hour_start,
                          hour_end = newsch.sch_hour_end))
        db.commit()
        logme.info("pl_add_sch: Ajout de la planification "+ str(newsch.sch_id)+" pour la playlist "+ str(newsch.sch_playlist_id))
        return {"etat": "success", "message": "Ajout de la planification pour la playlist"}
    except:
        logme.error("pl_add_sch: Une erreur lors de l'ajout de la planification "+ str(newsch.sch_id)+" dans la playlist "+ str(newsch.sch_playlist_id))
        return {"etat": "error", "message": "Une erreur s'est produite lors de l'ajout de la planification dans playlist"}



## pour memoire   sched.add_job(job_function, 'cron',start_date='2014-05-01', day_of_week='0,6', hour=5, minute=30, end_date='2014-05-30')

@ipo.get("/playlist/list")
async def pl_list(db:db_dependency):
    return db.query(models.Playlist).all()


@ipo.get("/playlist/mip")
async def pl_mip(db:db_dependency):
    return db.query(models.MIP).all()

@ipo.get("/playlist/on/{playlist_id}")
async def pl_on(tache_fond:BackgroundTasks,playlist_id:int,db:db_dependency):
    # obtenir la liste des hélices et des medias de la playlist
    try : list_media= get_list_media(playlist_id,db)
    except: logme.error("pl_on: Une erreur la liste  des medias de la playlist "+ str(playlist_id))
    try : list_cible= get_list_cible(playlist_id,db)
    except: logme.error("pl_on: Une erreur la liste  des cibles de la playlist "+ str(playlist_id))
    qui = "username"
    for cible in list_cible:
        ref= uuid.uuid4()
        db_tache = models.TacheMaJHelice(id = ref,
                            soumis_par = qui,
                            list_media = list_media,
                            helice_hdref = cible,
                            last_info = func.now(),
                            tentatives =0,
                            status = "Demande"
                          )
        db.add(db_tache)
        db.commit() 
        tache_fond.add_task(activate_pl_to_helice,cible,list_media,ref,db)
    
    return {"list_media":list_media,"list_cible":list_cible}



from models import PIP, Playlist, Pdv, Media 




class PIPResponse(BaseModel):
    playlist: dict
    pdv: dict
    medias: List[dict]
    added_by: str
    added_date: datetime




@ipo.get("/pip", response_model=List[PIPResponse])
def get_pip_details(db: Session = Depends(get_db)):
    results = []
    
    
    pip_entries = db.query(PIP).all()
    
    for pip in pip_entries:
      
        playlist = db.query(Playlist).filter(Playlist.id == pip.pip_playlist_id).first()
        
       
        pdv = db.query(Pdv).filter(Pdv.id == pip.pip_pdv_id).first()
        
       
        medias = db.query(Media).join(MIP).filter(MIP.mip_playlist_id == playlist.id).all()
        
        
        results.append({
            "playlist": {
                "id": playlist.id,
                "libelle": playlist.libelle,
                "description": playlist.description
            },
            "pdv": {
                "id": pdv.id,
                "pdv_hdref": pdv.pdv_hdref,
                "emplacement": pdv.emplacement
            },
            "medias": [{
                "id": media.id,
                "libelle": media.libelle,
                "description": media.description
            } for media in medias],
            "added_by": pip.pip_add_by,
            "added_date": pip.pip_add_date
        })
    
    return results




'''

class PlaylistResponse(BaseModel):
    id: int
    libelle: str
    description: str
    proprietaire: int
    status: bool

    class Config:
        orm_mode = True

class MediaResponse(BaseModel):
    id: int
    libelle: str
    description: str
    ready: bool
    categorie_id: int
    souscategorie_id: int
    owner_id: Optional[int] = None  

    class Config:
        orm_mode = True

class MIPResponse(BaseModel):
    mip_add_by: Optional[str] = None  
    mip_add_date: datetime
    media: MediaResponse
    playlist: PlaylistResponse

    class Config:
        orm_mode = True


@ipo.get("/mip", response_model=List[MIPResponse])
def get_mip_entries(db: Session = Depends(get_db)):
    return db.query(MIP)\
        .join(MIP.media)\
        .join(MIP.playlist)\
        .options(
            contains_eager(MIP.media),
            contains_eager(MIP.playlist)
        )\
        .all()
    
    return mip_entries



  



class HeureMinute(BaseModel):
    heure: int
    minute: int

class GrilleBase(BaseModel):
    playlist_id: int
    helice_hdref: str
    start_date: datetime
    end_date: datetime
    media_ids: List[int]

class GrilleCreate(GrilleBase):
    pass

class Grille(GrilleBase):
    id: int
    
    class Config:
        orm_mode = True




@ipo.post("/grille/add", response_model=Grille)
async def add_grille(grille: Grille, db: Session = Depends(get_db)):
    new_grille = models.Grille(**grille.dict())
    db.add(new_grille)
    db.commit()
    db.refresh(new_grille)
    return new_grille


async def delete_scheduled_media(hdref: str, media_ids: List[int], db: Session):
    try:
        medias = db.query(models.Media).filter(models.Media.id.in_(media_ids)).all()
        filenames = [media.libelle + ".Z3.mp4" for media in medias]

        for filename in filenames:
            await remote(models.RemoteHelice(
                hdref=hdref,
                ordre="delmedia",
                fichier=filename
            ), db)

        db.query(models.Grille).filter(
            models.Grille.helice_hdref == hdref,
            models.Grille.end_date <= datetime.now(timezone.utc)
        ).delete()
        db.commit()

    except Exception as e:
        print(f"Erreur suppression automatique: {str(e)}")





async def add_scheduled_media(hdref: str, media_ids: list[int], db: Session):
    try:
        medias = db.query(models.Media).filter(models.Media.id.in_(media_ids)).all()
        if not medias:
            raise Exception("Aucun média trouvé")
            
    
        existing_files = await remote(models.RemoteHelice(
            hdref=hdref,
            ordre="listsd"
        ), db)
        
        for file in existing_files:
            await remote(models.RemoteHelice(
                hdref=hdref,
                ordre="delmedia",
                fichier=file
            ), db)

        
        for media in medias:
            await remote(models.RemoteHelice(
                hdref=hdref,
                ordre="addmedia",
                libelle=media.libelle
            ), db)

    except Exception as e:
        print(f"Erreur d'ajout programmé: {str(e)}")
        raise

@ipo.post("/programmer-playlist", response_model=Grille)
async def programmer_playlist(
    grille: GrilleCreate,
    db: Session = Depends(get_db)
):
    now_utc = datetime.now(timezone.utc)
    
    
    start_date_utc = grille.start_date.astimezone(timezone.utc)
    end_date_utc = grille.end_date.astimezone(timezone.utc)

    
    if start_date_utc >= end_date_utc:
        raise HTTPException(400, "La date de fin doit être ultérieure à la date de début")
    
    min_start_date = now_utc + timedelta(seconds=10)
    if start_date_utc <= min_start_date:
        raise HTTPException(400, f"La date de début doit être au moins 10 secondes dans le futur (actuellement: {now_utc})")

    
    medias = db.query(models.Media).filter(models.Media.id.in_(grille.media_ids)).all()
    if len(medias) != len(grille.media_ids):
        raise HTTPException(404, "Un ou plusieurs médias introuvables")

    
    db_grille = models.Grille(**grille.dict())
    db.add(db_grille)
    
    try:
        db.commit()
        db.refresh(db_grille)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erreur base de données: {str(e)}")

    
    scheduler.add_job(
        add_scheduled_media,
        'date',
        run_date=start_date_utc,
        args=[grille.helice_hdref, grille.media_ids, db]
    )

    scheduler.add_job(
        lambda: delete_scheduled_media(grille.helice_hdref, grille.media_ids, db),
        'date',
        run_date=end_date_utc
    )

    return db_grille
'''    