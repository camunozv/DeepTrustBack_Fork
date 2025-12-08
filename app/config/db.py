from sqlalchemy import create_engine, MetaData

# This function allows to connect to a data base;
# with the required credentials, we just have to enter
# the URL. Since sqlalchemy allows us to interact with the
# data base, we also need some tools for hanlding the login
# to the data base and so on.
engine = create_engine("mysql+pymysql://root:Whistleblower11@localhost:3306/workshopdb")

meta = MetaData()

conn = engine.connect()