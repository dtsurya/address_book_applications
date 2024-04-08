from fastapi import APIRouter, Depends, Form,requests
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash,verify_password
from datetime import datetime
from app.utils import *
from sqlalchemy import or_,func

import random


router = APIRouter()

# Add
@router.post("/add_address")
async def add_address(db:Session=Depends(deps.get_db),name:str=Form(...),
                      latitude:str=Form(...),longitude:str=Form(...)):
    checkName = db.query(Address).filter(Address.name == name , Address.status==1).first()
    if checkName:
        return {"status":0,"msg":"Name already exists"}
    else:
        createNewData = Address(
            name = name,
            latitude=latitude,
            longitude = longitude,
            status = 1
        ) 
        db.add(createNewData)
        db.commit()
        return {"status":1,"msg":"Address added successfully"}
    
#List
@router.get("/gtelocation")
def gtelocation(*, db: Session = Depends(deps.get_db),user_latitude:str=Form(...),user_longitude:str=Form(...)):
    user_latitude="11.119926"
    user_longitude="77.336315"
    getLoca=db.query(Address).order_by(func.sqrt(
                    func.pow(69.1 * (Address.latitude - {user_latitude}), 2) +
                    func.pow(69.1 * ({user_longitude} - Address.longitude) * func.cos(Address.latitude / 57.3), 2))).all()
 
    return getLoca  

# Update Address
@router.post("/update_address")
def udateAddress(db: Session = Depends(deps.get_db),address_id:int=Form(...),name:str=Form(None),latitude:str=Form(None),longitude:str=Form(None)):
    # Check Address
    check_address=db.query(Address).filter(Address.id == address_id).first()
    
    if not check_address:
       return {"status":0,"msg":"Invalid Address"}
    # Update Address
    check_address.name = name
    check_address.latitude = latitude
    check_address.longitude = longitude
    db.commit()
    return {"status":1,"msg":"Updated Successfully"} 

# Delete Address
@router.post("/delete_address")
def deleteAddress(db: Session = Depends(deps.get_db),address_id:int=Form(...)):
    # Check Address
    check_address=db.query(Address).filter(Address.id == address_id).first()
    
    if not check_address:
       return {"status":0,"msg":"Invalid Address"}
    # Delete Address
    check_address.status = -1 # Status -1  means deleted
    db.commit()
    return {"status":1,"msg":"Deleted Successfully"}     

  