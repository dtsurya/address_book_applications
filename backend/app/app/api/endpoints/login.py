
from fastapi import APIRouter, Depends, Form,requests
from sqlalchemy.orm import Session
from app.models import ApiTokens,User
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash,verify_password
from datetime import datetime
from app.utils import *
from sqlalchemy import or_

import random


router = APIRouter()
dt = str(int(datetime.utcnow().timestamp()))

#Check Token
@router.post("/check_token")
async def checkToken(*,db: Session = Depends(deps.get_db),
                      token: str = Form(...)):
    
    checkToken = db.query(ApiTokens).filter(ApiTokens.token == token,
                                           ApiTokens.status == 1).first()
    if checkToken:
        return {"status": 1,"msg": "Success."}
    else:
        return {"status": 0,"msg": "Failed."}


#1.Login
@router.post("/login")
async def login(*,db: Session = Depends(deps.get_db),
                authcode: str = Form(None),
                userName: str = Form(...),
                password: str = Form(...)
                ,device_id: str = Form(None),
                device_type: str = Form(...,description = "1-android,2-ios"),
                push_id: str = Form(None),
                ip: str = Form(None),resetKey: str = Form(None),
                otp: str = Form(None)):
    
    ip = ip
    if device_id:
        auth_text = device_id + str(userName)
    else:
        auth_text = userName
    
    user = deps.authenticate(db,username = userName,
                             password = password,
                           authcode = authcode,
                           auth_text = auth_text)
  
    if not user:
        return {"status": 0,"msg": "Invalid employee id or password."}
    
    else:
        key = None
        userId = user.id

        if otp:
            user.otp = otp
            user.reset_key = resetKey
            msg = f"YOUR OTP IS {otp}"
            send = await send_mail(receiver_email = user.email,
                                 message = msg)
            db.commit()
    
        else:
            
            key = ''
            char1 = '0123456789abcdefghijklmnopqrstuvwxyz'
            char2 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            characters = char1 + char2
            token_text = userId
            for i in range(0, 30):
                key += characters[random.randint(
                        0, len(characters) - 1)]
                
            delToken = db.query(ApiTokens).\
                filter(ApiTokens.user_id == user.id).update({'status': 0})

            addToken = ApiTokens(user_id = userId,
                                token = key,
                                created_at = datetime.now(settings.tz_IN),
                                renewed_at = datetime.now(settings.tz_IN),
                                validity = 1,
                                device_type = device_type,
                                device_id = device_id,
                                push_device_id = push_id,
                                device_ip = ip,
                                status = 1)
                    

            db.add(addToken)
            db.commit()

        if user.otpVerifiedStatus == 1:
            return {'status':1,
                    'token': key,
                    'msg': 'Successfully LoggedIn.',        
                    'userType': user.userType,
                    'userId': userId if userId else 0,
                    'userName': user.name,
                    "verifyStatus": user.otpVerifiedStatus,
                    "duration": 120,
                    'status': 1
                        # 'image':(f"{settings.BASE_DOMAIN}/{user.image}" 
                        #             if user.image !=None else 
                        #             f"{settings.BASE_DOMAIN}/file_mconnect/dummy.png") ,
                        
                    }
        else:
            return ({"status": 2,"msg": "You are not verified."}) #For not verified users
    
    
#2.Logout
@router.post("/logout")
async def logout(db: Session = Depends(deps.get_db),
                 token: str = Form(...)):

    user = deps.get_user_token(db = db,token = token)
    if user:
        check_token = db.query(ApiTokens).\
            filter(ApiTokens.token == token,ApiTokens.status == 1).first()

        if check_token:
            check_token.status = -1
            db.commit()
            return ({"status": 1,"msg": "Success."}) 
        else:
            return ({"status": 0,"msg": "Failed."})
    else:
        return ({"status":0,"msg":"Invalid user."})
    

#3.Otp Verification
"""After the Successful SignIn Then You want to Verify
so An otp is sended to your register then u want to verify here"""

@router.post("/otpVerification")

async def otpVerification(*,db: Session = Depends(deps.get_db),
                           otp: str = Form(...),
                           reset_key: str = Form(...),
                           verificationType:str = Form(None,
                            description = "1->credentials")):

    checkUser = db.query(User).\
        filter(User.status == 1,User.reset_key == reset_key).first()
    if checkUser:
        if otp == checkUser.otp:
            if checkUser.otp_verified_at <= datetime.now():

                checkUser.otp_verified = 1
                checkUser.reset_key = None
                checkUser.otp = None
                db.commit()
                if verificationType != str(2):
                    if not verificationType:
                        msg = f"Subject: Welcome\n\n YOU ARE VERIFIED"
                    elif verificationType == str(1):
                        msg = f"Subject:
                          Welcome Back\n\n YOUR USER NAME IS :
                          {checkUser.name}"
                

                    try:
                        send = await send_mail(
                            receiver_email = checkUser.email,
                            message = msg)
                    except:
                        return ({"status": 0,
                                "msg": 
                                "Can't connect to server . Try later."})
                return ({"status": 1,
                        "msg":
                     "Credential send to your email or mobile number."})
               
            else:
                return {"status": 0,"msg": "Time out."}
        else:
            return {"status": 0,"msg": "Otp not match."}
    else:
        return {"status": 0,"msg": "No user found."}
     

#4.change Password
""" This Api is for that Exception Case thus the User
Wants to Change their Password"""

@router.post("/changePassword")

async def changePassword(db: Session = Depends(deps.get_db),
                          token: str = Form(...)
                          ,old_password: str = Form(None),
                          new_password: str = Form(...),
                          repeat_password: str = Form(...)):

    user = deps.get_user_token(db = db,token = token)
    if user:
    
        if  verify_password(old_password,user.password):

            if new_password != repeat_password:
                return ({"status": 0,"msg": "Password is not match."})
            
            else:           
                user.password = get_password_hash(new_password)
                db.commit()

                return ({"status": 1,"msg": 
                         "Password successfully updated."})
        else:
            return ({"status": 0,"msg": "Current password is invalid."})
    else:  
        return ({"status": -1,"msg": "Login session expires"})
    
#5.reSendOtp
@router.post("/resendOtp")
async def resendOtp(db: Session = Depends(deps.get_db),
                     resetKey: str = Form(...)):

    getUser = db.query(User).\
        filter(User.reset_key == resetKey,User.status == 1).first()
    
    if getUser:
        (otp, reset,
         created_at, 
         expireTime, 
         expireAt, otpValidUpto) = deps.get_otp()
        resetKey = reset+"@ghgkhdfkjh@trhghgu"
        otp = "123456"
        getUser.otp = otp
        getUser.reset_key = resetKey
        getUser.otpExpireAt = expireAt
        db.commit()

        msg = (f"THANKS FOR CHOOSING OUR 
               SERVICE YOUR SIX DIGIT OTP PIN IS {otp}")
        try:
            send = await send_mail(receiver_email = getUser.email,
                                   message = msg)
            return ({"status": 1,"msg": "OTP sended to your email",
                 "reset_key": resetKey,
                 "expire_at": expireAt,"otp": otp})
        except:
            return {"status":0,"msg":"Email not proper."}
        
    return ({"status": 0,"msg": "Non User Found"})


# 6. FORGOT PASSWORD

@router.post('/forgotPassword')
async def forgotPassword(db: Session = Depends(deps.get_db),    
                                    email: str = Form(None)):
    
    user = db.query(User).filter(User.userType == 1,
                                 or_(User.email == email,
                                     User.phone == email,
                                     User.alternativeNumber == email),
                                  User.status == 1)
    checkUser = user.first()
    if checkUser:
        
        if checkUser.email :
            (otp, reset, created_at,
            expire_time, expire_at,
                otp_valid_upto) = deps.get_otp()
        
            otp="123456"
            message = f'''Your  OTP for Reset Password is : {otp}'''
            reset_key = f'{reset}{checkUser.id}DTEKRNSSHPT'
    
            user = user.update({'otp': otp,
                                'reset_key': reset_key,
                                'otpExpireAt': expire_at})
            db.commit()

            mblNo = f'+91{checkUser.mobile}'
            try:
                send = await send_mail(receiver_email = checkUser.email,
                                       message = message)
                return ({'status': 1,'reset_key': reset_key,
                        'msg': 
                        f'An OTP message has been sent to {checkUser.email}.',
                        'remaining_seconds': otp_valid_upto})
            except Exception as e:
                print("EXCEPTION: ",e)
                return {'status': 0,'msg': 'Unable to send the Email.'}

        else:
            return({'status': 0,
                     'msg': 
      "Email address not found. Contact administrator for assistance."} )

    else:
        return({'status':0,'msg':'Sorry. The requested account not found'})
    
 
    
@router.post("/signupUser")
async def signupUser(db: Session = Depends(deps.get_db),
                      name: str = Form(...),
                      email: str = Form(...),
                      mobileNumber: str = Form(...),
                      alternativeNumber: str = Form(None),
                      password: str = Form(...)):

    getUser = db.query(User).filter(User.status == 1,
                                    User.otpVerifiedStatus == 1)
        
    if mobileNumber:
            checkMobileNumber = getUser.\
                filter(or_(User.phone == mobileNumber,
                        User.alternativeNumber == mobileNumber))
    
            if checkMobileNumber:
                return {"status": 0,
                        "msg": "Mobile number already exists."}
                
    if alternativeNumber and mobileNumber :

        if alternativeNumber == mobileNumber:
                return {"status": 0,
                        "msg":
                "Mobile number and alternative mobile number are same."}
        else:
            checkAlternativeNumber = getUser.\
                filter(or_(User.phone == alternativeNumber,
                       User.alternativeNumber == mobileNumber))
            
            if checkAlternativeNumber:
                return {"status": 0,"msg": "Mobile number already exists!"}
            
        if email:
            getEmail = getUser.\
                filter(User.email == email).first()
            if getEmail:
                return {"status": 0,
                        "msg": "Email already exist!"}
        
        alternative_mobile_no = (alternative_mobile_no 
                               if alternative_mobile_no else None)
        pwd=password
        if pwd:
            password = get_password_hash(pwd)
        else:
            return {"status": 0,"msg": "Password not matched!"}
        

        (otp, reset, created_at,
          expire_time, expire_at,
            otp_valid_upto) = deps.get_otp()
        
        otp = "123456"
        reset_key1 = f'{reset}TnrTkd10jf1998J7u20I@'
  
        msg = f"Subject: Welcome to Mconnect Family\n\n Your otp  is {otp}   Stay Connected With MConnect."
        send = await send_mail(receiver_email = email,message = msg)
        
        createUser = User(email = email,
                          userType = 1,
                          name = name,
                        phone = mobileNumber,
                        alternativeNumber = alternativeNumber,
                        contact_person = name,
                        created_at = datetime.now(settings.tz_IN),
                        status = 1,password = password,
                        otp = otp,
                        otpVerifiedStatus = 0,
                        otpExpireAt = expire_at,
                        reset_key = reset_key1)

        db.add(createUser)
        db.commit()  


        return ({"status": 1,"reset_key": reset_key1,
                 "duration": 120,
                 "msg": f"An OTP message has been sent to {email}"})
    
# @router.post("/createEmployee")
# async def createEmployee(db: Session = Depends(deps.get_db),
#                          username: str = Form(...),
#                          password: str = Form(...)):
#     """Create Employee"""
#     password = password.strip()
#     createNewEmployee = User(
#         name = username,
#         password = get_password_hash(password),
#         userType =1,
#         otpVerifiedStatus =1
#     )
#     db.add(createNewEmployee)
#     db.commit()
#     return {"status": 1,"msg": "success"}


      
# @router.post("/createAuthCode")
# async def createAuthCode(username: str = Form(...)):
#     security.check_authcode(username,username)