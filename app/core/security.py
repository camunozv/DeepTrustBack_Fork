from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os

# The content in this file is inteded to be used for the user auth.
# Not finished yet, ignore...

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="Auto")

oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")

mock_db = {
    "tim445": {
        "user_nickname": "tim445",
        "email": "tim@gmail.com",
        "names": "Tim Andrew",
        "last_names": "Johnson",
        "hashed_password": "",
        "disabled": False,
    }
}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


#def get_user(db, username: str):
#    if username in db:
#        return UserInDB(**db[username])


#def authenticate_user(db, username: str, password: str):
 #   user = get_user(db, username)
#
  #  if not user:
    #    return False
   # elif not verify_password(password, user.hash_password):
     #   return False
    #else:
     #   return user


def create_access_token(data: dict, expires_delta: timedelta or None = None):
    to_encode = data.copy()

    if expires_delta:  # if we have some sort of a specific expire time we want, or we put some one by default
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"expires": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt
