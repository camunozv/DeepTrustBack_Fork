from pydantic import BaseModel


class Token(BaseModel):
    access_token:str
    token_type: str

class TokenData(BaseModel):
    user_name:str or None = None

class User(BaseModel):
    user_nickname:str
    email:str or None = None
    names: str or None = None
    last_names: str or None = None
    disabled: bool or None = None
        
class UserInDB(User):
    hash_password:str