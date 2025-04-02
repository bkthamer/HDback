from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker  
from sqlalchemy.ext.declarative import declarative_base
from parametres import URL_BASEDEDONNEE

#URL_BASEDEDONNEE = 'mariadb+mariadbconnector://apiHD:Adefinir@localhost:3306/hdapplication'

moteurbd = create_engine(URL_BASEDEDONNEE)
SessionLocal= sessionmaker(autocommit=False,autoflush=False,bind=moteurbd)
Base = declarative_base()
