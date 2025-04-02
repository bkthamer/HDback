from basededonnee import Base
from sqlalchemy import Boolean,Column,Integer,String,DateTime,Text,Table,ForeignKey,TIMESTAMP,JSON,Enum,UniqueConstraint,CheckConstraint, Uuid,PrimaryKeyConstraint,Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON


############################# DRAFT TABLES COMPTES USER ET SECURISATION ############################
utilisateur_roles = Table(
    "t_utilisateur_roles",
    Base.metadata,
    Column("utilisateur_id", Integer, ForeignKey("t_utilisateurs.id")),
    Column("role_id", Integer, ForeignKey("t_roles.id"))
)

role_permissions = Table(
    "t_role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("t_roles.id")),
    Column("permission_id", Integer, ForeignKey("t_permissions.id"))
)

utilsateur_permissions = Table(
    "t_utilisateur_permissions",
    Base.metadata,
    Column("utilisateur_id", Integer, ForeignKey("t_utilisateurs.id")),
    Column("permission_id", Integer, ForeignKey("t_permissions.id"))
)

utilisateur_groupes = Table(
    "t_utilisateur_groupes",
    Base.metadata,
    Column("utilisateur_id", Integer, ForeignKey("t_utilisateurs.id")),
    Column("groupe_id", Integer, ForeignKey("t_groupes.id"))
)

class Utilisateur(Base): 
    __tablename__ = "t_utilisateurs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    login = Column(String(30), nullable=False, unique=True,index=True)   
    nom = Column(String(30), nullable=False)    
    prenom = Column(String(30), nullable=False)
    password = Column(String(30), nullable=False)   
    email = Column(String(30), nullable=False,unique=True,index=True)
    roles = relationship("Role", secondary=utilisateur_roles, back_populates="utilisateurs")
    permissions = relationship("Permission", secondary=utilsateur_permissions, back_populates="utilisateurs")
    groupes = relationship("Groupe", secondary=utilisateur_groupes, back_populates="utilisateurs")     
    
class Role(Base): 
    __tablename__ = "t_roles"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    libelle = Column(String(30), index=True, nullable=False, unique=True)
    utilisateurs= relationship("Utilisateur", secondary=utilisateur_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class Permission(Base): 
    __tablename__ = "t_permissions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    libelle = Column(String(30), index=True, nullable=False, unique=True)
    utilisateurs = relationship("Utilisateur", secondary=utilsateur_permissions, back_populates="permissions")
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
class Groupe(Base): 
    __tablename__ = "t_groupes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    libelle = Column(String(30), index=True, nullable=False, unique=True)
    utilisateurs = relationship("Utilisateur", secondary=utilisateur_groupes, back_populates="groupes")

class Droitlog(Base):
    __tablename__ = "t_droitlogs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    utilisateur_id = Column(Integer, ForeignKey("t_utilisateurs.id"))
    type_modification = Column(String(50))
    detail_modification = Column(JSON)
    date_modification = Column(TIMESTAMP,server_default=func.now())                            
    utilisateur = relationship("Utilisateur")

############################### TABLES PRODUCTIONS PARTAGE NAWAN ##############################
class Production(Base):
    __tablename__ = "t_productions"
    id = Column(Integer, primary_key=True,autoincrement=True)
    hdref = Column(String(20),index=True,unique=True)
    ref_infra = Column(String(30),index=True,unique=True)
    ip = Column(String(16),default="0.0.0.0")
    bail= Column(Boolean, default=False)
    lastchange = Column(TIMESTAMP,server_default=func.now())
    lastchange_by = Column(String(10))
    
class Iee(Base):
    __tablename__ = "t_iees"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    iee  = Column(String(9),nullable=False, unique=True)

############################## TABLES MATERIELS ##############################
class Decouverte(Base):
    __tablename__ = "t_decouvertes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    macadresse   = Column(String(17))
    serialnumber = Column(String(30))
    iptemp = Column(String(16),default="0.0.0.0",unique=True)
    notified = Column(TIMESTAMP,server_default=func.now())
    wifi = Column(String(20),default="Non renseigné")
    

class Typemateriel(Base):
    __tablename__ = "t_typemateriels"
    id = Column(Integer, primary_key=True, index=True)
    libelle = Column(String(30), index=True, nullable=False, unique=True)
    
    materiels = relationship("Materiel", back_populates="typemateriel_id")
    
class Materiel(Base):
    __tablename__ = "t_materiels"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    macadresse   = Column(String(17), index=True, nullable=False, unique=True)
    serialnumber = Column(String(30))
    hdref = Column(String(20), index=True, nullable=False, unique=True)
    status = Column(Enum('en_stock', 'en_maintenance', 'en_service','en_migration', name='typestatus'),default='en_stock')
    iptemp = Column(String(16),default="0.0.0.0")
    typemateriel = Column(String(30), ForeignKey("t_typemateriels.libelle"))
    wifi = Column(String(20),default="Non renseigné")
    simref = Column(String(20),default="Non renseigné")
    
    typemateriel_id = relationship("Typemateriel", back_populates="materiels")
    
class Cartesim(Base):
    __tablename__ = "t_cartesims"
    simref = Column(String(30), index=True, nullable=False, primary_key=True)
    active = Column(Boolean, default=False)
    disponible = Column(Boolean, default=False)
    
    
    
############################## TABLES MEDIAS ##############################
class Categorie(Base):
    __tablename__ = "t_categories"
    id = Column(Integer, primary_key=True)
    nom = Column(String(50), unique=True, nullable=False)
    
    souscategories = relationship("Souscategorie", back_populates="categorie")
    medias = relationship("Media", back_populates="categorie")

class Souscategorie(Base):
    __tablename__ = "t_souscategories"
    id = Column(Integer, primary_key=True)
    nom = Column(String(50), nullable=False)
    categorie_id = Column(Integer, ForeignKey("t_categories.id"))
    
    categorie = relationship("Categorie", back_populates="souscategories")
    medias = relationship("Media", back_populates="souscategorie")
    

       

class Media(Base):
    __tablename__ = "t_medias"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    libelle = Column(String(50), nullable=False,index=True,unique=True)
    description = Column(String(255),default = "Aucune description")
    ready = Column(Boolean, default=False)   
    categorie_id = Column(Integer, ForeignKey("t_categories.id"))
    souscategorie_id = Column(Integer, ForeignKey("t_souscategories.id"))
    owner_id = Column(Integer, ForeignKey("t_users.id_user"), nullable=True)
    
    categorie = relationship("Categorie", back_populates="medias")
    souscategorie = relationship("Souscategorie", back_populates="medias")
    
    playlists = relationship("Playlist",secondary="t_mip", back_populates="medias")
    #ajouté 
    mip_entries = relationship("MIP", back_populates="media") 
   
    


 
############################### TABLES CLIENTS SITES ############################## 
class Client(Base):
    __tablename__ = "t_clients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    societe = Column(String(50),nullable=False,index=True,default="Non renseigné")
    enseigne = Column(String(50),default="Non renseigné")
    nomcontact = Column(String(30),nullable=False,index=True)
    prenomcontact = Column(String(30),nullable=False)
    emailcontact = Column(String(50))
    telephonecontact = Column(String(10))
    adresse = Column(String(50))
    ville = Column(String(30))
    codepostal = Column(Integer)
    
    sites = relationship("Site", back_populates="client") 
        
    __table_args__ = (
        UniqueConstraint('societe', 'nomcontact','prenomcontact','adresse', name='contrainte_client'),
        CheckConstraint("(telephonecontact IS NOT NULL) OR (emailcontact IS NOT NULL)", name='contrainte_contact')
    )
    
class Site(Base):
    __tablename__ = "t_sites"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nomsite = Column(String(50),nullable=False,unique=True,index=True,default="Non renseigné")
    adresse = Column(String(50))
    ville = Column(String(30))
    codepostal = Column(String(5),nullable=False)
    client_id = Column(Integer, ForeignKey("t_clients.id"),nullable=False)
    routeur_hdref = Column(String(20), ForeignKey("t_materiels.hdref"),nullable=False,unique=True)
    site_wifi = Column(String(20),default="NR")
    
    client = relationship("Client", back_populates="sites")
    pdvs = relationship("Pdv", back_populates="site")

 ############################### TABLES GROUPEPDV PDV ##############################    
 


class Pdv(Base):
    __tablename__ = "t_pdvs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pdv_hdref = Column(String(20),unique=True, index =True,nullable= False)
    materiel_hdref = Column(String(20), ForeignKey("t_materiels.hdref"),unique=True,nullable=False)
    emplacement = Column(String (50))    
    site_id = Column(Integer, ForeignKey("t_sites.id"),nullable=False)
    
    site = relationship("Site", back_populates="pdvs")
   
    


    
 #################### TABLES TACHES ############################"
 
class TachePrepaVideo(Base):
    __tablename__ = "t_tacheprepavideos"
    id = Column(Uuid, primary_key=True, index=True)
    date_soumission = Column(TIMESTAMP,server_default=func.now())
    soumis_par = Column(String(50))
    type_tache = Column(String(50))
    titre = Column(String(50))
    sourcename = Column(String(50))    
    last_info = Column(TIMESTAMP)
    status = Column(String(20),default="Non demarrée")
    owner_id = Column(Integer , nullable=True)

class TacheMaJHelice(Base):
    __tablename__ = "t_tachemajhelices"
    id = Column(Uuid, primary_key=True, index=True)
    date_soumission = Column(TIMESTAMP,server_default=func.now())
    soumis_par = Column(String(50))
    list_media = Column(JSON)
    helice_hdref = Column(String(20))
    tentatives = Column(Integer)
    cause = Column(String(20))
    last_info = Column(TIMESTAMP)
    status = Column(String(20),default="En_cours")

class User(Base):
    __tablename__ = "t_users"

    id_user = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=True)
    site_id = Column(Integer, ForeignKey("t_sites.id"), nullable=True)

    def __repr__(self):
        return f"<User(id_user={self.id_user}, email={self.email}, role={self.role}, site_id={self.site_id})>"
    

class Demande(Base):
    __tablename__ = "t_demandes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sujet = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    date = Column(DateTime, server_default=func.now())
    image = Column(String(255), nullable=True)
    email = Column(String(100), nullable=False)


class Playlist(Base):
    __tablename__ = "t_playlists"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    libelle = Column(String(50), nullable=False,index=True,unique=True)
    description = Column(String(255),default = "Aucune description") 
    proprietaire = Column(Integer)
    status= Column(Boolean,default=False)
    
    medias = relationship("Media", secondary="t_mip", back_populates="playlists")
    grilles = relationship("Grille", back_populates="playlist")
    #ajouté
    mip_entries = relationship("MIP", back_populates="playlist")


class Grille(Base):
    __tablename__ = "t_grille"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("t_playlists.id"), nullable=False)
    helice_hdref = Column(String(17),ForeignKey("t_materiels.hdref"), nullable=False)
    start_date = Column(DateTime,nullable=False)
    end_date = Column(DateTime, nullable=False)
    media_ids = Column(JSON, nullable=False)
    
    playlist = relationship("Playlist", back_populates="grilles")
    materiel = relationship("Materiel")
    
    
    
class MIP(Base):
    __tablename__ = "t_mip"
    mip_media_id= Column(Integer, ForeignKey("t_medias.id"))
    mip_playlist_id=Column(Integer, ForeignKey("t_playlists.id"))
    mip_add_by = Column(String(50))
    mip_add_date = Column(TIMESTAMP,server_default=func.now())
        
    __table_args__ = (PrimaryKeyConstraint('mip_media_id', 'mip_playlist_id',name='contrainte_mip'),)

    media = relationship("Media", back_populates="mip_entries")
    playlist = relationship("Playlist", back_populates="mip_entries")
    
class PIP(Base):
    __tablename__ = "t_pip"
    pip_playlist_id= Column(Integer, ForeignKey("t_playlists.id"))
    pip_pdv_id=Column(Integer, ForeignKey("t_pdvs.id"))
    pip_add_by =Column(String(50))
    pip_add_date = Column(TIMESTAMP,server_default=func.now())
    
    __table_args__ = (PrimaryKeyConstraint('pip_playlist_id', 'pip_pdv_id',name='contrainte_pip'),)






