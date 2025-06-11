from app import app, db
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import pandas as pd

# Configurações - SUBSTITUA 'suasenha' pela sua senha real
sqlite_db = 'sqlite:///jogadores.db'
postgres_db = 'postgresql://postgres:beststyle.99@localhost:5432/jogadores_db'

# Criar engines
engine_sqlite = create_engine(sqlite_db)
engine_postgres = create_engine(postgres_db)

# Criar banco PostgreSQL se não existir
if not database_exists(postgres_db):
    create_database(postgres_db)

# 1. Criar estrutura no PostgreSQL usando o contexto da aplicação
with app.app_context():
    # Configurar a URI do banco de dados para PostgreSQL temporariamente
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_DATABASE_URI'] = postgres_db
    
    # Criar todas as tabelas
    db.create_all()
    
    # Restaurar a URI original
    app.config['SQLALCHEMY_DATABASE_URI'] = original_uri

# 2. Migrar os dados de cada tabela
tables = ['jogador', 'jogo', 'rodada']

for table in tables:
    print(f'\nMigrando tabela {table}...')
    try:
        # Ler dados do SQLite
        df = pd.read_sql_table(table, engine_sqlite)
        print(f"Registros encontrados: {len(df)}")
        
        # Escrever no PostgreSQL
        df.to_sql(table, engine_postgres, if_exists='append', index=False, method='multi')
        print(f"Tabela {table} migrada com sucesso!")
    except Exception as e:
        print(f"Erro ao migrar tabela {table}: {str(e)}")

print('\nMigração concluída com sucesso!')