from sqlalchemy import create_engine, MetaData, Table, Column, Numeric,insert, Integer, VARCHAR, update, text, delete 
from sqlalchemy.engine import result
# Erstelle eine Engine, die auf deine Datenbank verweist
engine = create_engine('sqlite:///:memory:', echo=True)

# initialize the Metadata Object 
meta = MetaData(bind=engine) 
MetaData.reflect(meta) 

books = Table( 
    'books', meta, 
    Column('book_id', Integer, primary_key=True), 
    Column('book_price', Numeric), 
    Column('genre', VARCHAR), 
    Column('book_name', VARCHAR) 
) 
  
meta.create_all(engine) 
books_table = meta.tables["books"]
conn = engine.connect()
conn.execute(books_table, {"book_price":10, "genre": "test", "book_name": "hi"})
Bae