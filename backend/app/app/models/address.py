from sqlalchemy import  Column, Integer, String, DateTime, ForeignKey,TEXT,DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import TINYINT

from app.db.base_class import Base

class Address(Base):
    __tablename__="address"
    id = Column(Integer,primary_key=True)
    name = Column(String(255))
    latitude = Column(DECIMAL(11,7))
    longitude = Column(DECIMAL(11,7))
    status = Column(TINYINT)

    