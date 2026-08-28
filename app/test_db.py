from app.database.database import engine

try:
    connection = engine.connect()
    print("Banco conectado com sucesso!")
    connection.close()
except Exception as e:
    print(e)
