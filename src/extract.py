import pandas as pd
import os
import logging
from sqlalchemy import create_engine

# Conexão com o banco OLTP
DATABASE_URI = "postgresql+psycopg2://zoop:zoop123@localhost:5432/zoop_oltp"
engine_oltp = create_engine(DATABASE_URI, echo=False, future=True)


def carregar_oltp():
    logging.info("Iniciando carga transacional (OLTP)...")

    # Lendo os CSVs da pasta 'dados/'
    df_clientes = pd.read_csv("dados/clientes.csv")
    df_produtos = pd.read_csv("dados/produtos.csv")
    df_pedidos_brutos = pd.read_csv("dados/pedidos.csv")

    # Tratamento 1: Deduplicar produtos mantendo a primeira ocorrência
    df_produtos = df_produtos.drop_duplicates(subset=["id_produto"], keep="first")

    # Tratamento 2: Derivar tabelas pedido e pedido_item a partir de pedidos.csv (Normalização)
    df_pedidos = df_pedidos_brutos[
        [
            "id_pedido",
            "id_cliente",
            "data_pedido",
            "status_pagamento",
            "data_vencimento",
        ]
    ].drop_duplicates()
    df_pedido_item = df_pedidos_brutos[
        ["id_pedido", "id_produto", "quantidade", "valor_item"]
    ]

    # Carga no PostgreSQL (OLTP)
    try:
        df_clientes.to_sql("cliente", con=engine_oltp, if_exists="append", index=False)
        df_produtos.to_sql("produto", con=engine_oltp, if_exists="append", index=False)
        df_pedidos.to_sql("pedido", con=engine_oltp, if_exists="append", index=False)
        df_pedido_item.to_sql(
            "pedido_item", con=engine_oltp, if_exists="append", index=False
        )
        logging.info("Carga OLTP finalizada.")
    except Exception as e:
        logging.info("Erro ao carregar os dados no PostgreSQL: %s", e)


def extrair_bronze():
    logging.info("Iniciando extração para a Camada Bronze...")
    os.makedirs("datalake/bronze", exist_ok=True)

    tabelas = ["cliente", "produto", "pedido", "pedido_item"]
    try:
        for tabela in tabelas:
            df = pd.read_sql(f"SELECT * FROM {tabela}", con=engine_oltp)
            # Salvando como vieram do OLTP em formato Parquet
            df.to_parquet(
                f"datalake/bronze/{tabela}.parquet", engine="pyarrow", index=False
            )

        logging.info("Camada Bronze gerada com sucesso.")
    except Exception as e:
        logging.info("Erro ao extrair dados para a Camada Bronze: %s", e)
