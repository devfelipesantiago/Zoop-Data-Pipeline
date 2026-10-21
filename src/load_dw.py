import pandas as pd
import logging
from sqlalchemy import create_engine

engine_dw = create_engine("postgresql+psycopg2://zoop:zoop123@localhost:5432/zoop_dw")


def carregar_dimensoes_e_fatos():
    logging.info("Iniciando carga inicial do Data Warehouse...")
    try:
        df_prata = pd.read_parquet("datalake/prata/dados_consolidados.parquet")

        # --- DIMENSÃO TEMPO ---
        dim_tempo = (
            pd.to_datetime(df_prata["data_pedido"])
            .drop_duplicates()
            .to_frame(name="data")
            .sort_values("data")
            .reset_index(drop=True)
        )
        dim_tempo["sk_tempo"] = dim_tempo["data"].dt.strftime("%Y%m%d").astype(int)
        dim_tempo["ano"] = dim_tempo["data"].dt.year
        dim_tempo["mes"] = dim_tempo["data"].dt.month
        dim_tempo["trimestre"] = dim_tempo["data"].dt.quarter
        dim_tempo["dia"] = dim_tempo["data"].dt.day
        dim_tempo["dia_util"] = dim_tempo["data"].dt.dayofweek < 5
        # Carga na tabela dim_tempo
        dim_tempo.to_sql(
            "dim_tempo", con=engine_dw, if_exists="append", index=False, method="multi"
        )

        # --- DIMENSÃO PRODUTO ---
        dim_produto = (
            df_prata[["id_produto", "nome_produto", "categoria", "preco_unitario"]]
            .drop_duplicates(subset=["id_produto"])
            .copy()
        )
        # Gerando Surrogate Keys localmente
        dim_produto.insert(0, "sk_produto", range(1, len(dim_produto) + 1))
        dim_produto = dim_produto.rename(columns={"id_produto": "cod_produto"})
        # Carga na tabela dim_produto
        dim_produto.to_sql(
            "dim_produto", con=engine_dw, if_exists="append", index=False
        )

        # --- DIMENSÃO CLIENTE (Carga Inicial SCD2) ---
        dim_cliente = (
            df_prata[["id_cliente", "nome", "cidade", "estado"]]
            .drop_duplicates(subset=["id_cliente"])
            .copy()
        )
        # Renomeando o código natural para 'cod_cliente'
        dim_cliente = dim_cliente.rename(columns={"id_cliente": "cod_cliente"})
        # Gerando Surrogate Keys localmente
        dim_cliente.insert(0, "sk_cliente", range(1, len(dim_cliente) + 1))
        # Adicionando colunas de controle (SCD Tipo 2)
        dim_cliente["valid_from"] = pd.to_datetime("1900-01-01")
        dim_cliente["valid_to"] = pd.to_datetime("9999-12-31")
        dim_cliente["flag_vigencia"] = True
        # Carga na tabela dim_cliente
        dim_cliente.to_sql(
            "dim_cliente", con=engine_dw, if_exists="append", index=False
        )

        # --- FATO VENDAS ---
        df_fato = df_prata.copy()
        df_fato["sk_tempo"] = (
            pd.to_datetime(df_fato["data_pedido"]).dt.strftime("%Y%m%d").astype(int)
        )

        # Lookups para buscar as SKs
        df_fato = df_fato.merge(
            dim_produto[["sk_produto", "cod_produto"]],
            left_on="id_produto",
            right_on="cod_produto",
            how="inner",
        )

        # Lookup com Dim Cliente trazendo valid_from e valid_to para garantir histórico exato
        dim_cliente_dw = pd.read_sql(
            "SELECT sk_cliente, cod_cliente, valid_from, valid_to FROM dim_cliente",
            con=engine_dw,
        )

        # Lookup Dimensão Cliente (trazendo sk_cliente com base no cod_cliente)
        df_fato = df_fato.merge(
            dim_cliente_dw, left_on="id_cliente", right_on="cod_cliente", how="inner"
        )
        # Filtrando apenas os registros que estão dentro do período de vigência do cliente
        df_fato = df_fato[
            (
                pd.to_datetime(df_fato["data_pedido"])
                >= pd.to_datetime(df_fato["valid_from"])
            )
            & (
                pd.to_datetime(df_fato["data_pedido"])
                <= pd.to_datetime(df_fato["valid_to"])
            )
        ]

        fato_vendas = df_fato[
            [
                "sk_cliente",
                "sk_produto",
                "sk_tempo",
                "id_pedido",
                "quantidade",
                "valor_item",
            ]
        ]

        # Carga na tabela fato_vendas
        fato_vendas.to_sql(
            "fato_vendas", con=engine_dw, if_exists="append", index=False
        )
        logging.info("Carga do DW (Star Schema) concluída.")
    except Exception as e:
        logging.error(f"Erro durante a carga do DW: {e}")


def processar_scd2_clientes():
    logging.info("Aplicando atualizações cadastrais (SCD Tipo 2)...")
    try:
        # Lendo o arquivo que simula mudanças cadastrais posteriores
        df_updates = pd.read_csv("dados/clientes_atualizacao.csv")
        dim_cliente = pd.read_sql("SELECT * FROM dim_cliente", con=engine_dw)

        novos_registros = []

        for _, row in df_updates.iterrows():
            cod = row["id_cliente"]
            data_atu = pd.to_datetime(row["data_atualizacao"])

            # 1. Encontrar o registro antigo no DataFrame em memória e fechar a vigência
            idx_antigo = dim_cliente.index[
                (dim_cliente["cod_cliente"] == cod)
                & (dim_cliente["flag_vigencia"] == True)
            ].tolist()
            if idx_antigo:
                dim_cliente.at[idx_antigo[0], "valid_to"] = data_atu
                dim_cliente.at[idx_antigo[0], "flag_vigencia"] = False

            # 2. Criar a nova versão do registro
            novo_registro = {
                "sk_cliente": dim_cliente["sk_cliente"].max()
                + len(novos_registros)
                + 1,
                "cod_cliente": cod,
                "nome": row["nome"],
                "cidade": row["cidade"],
                "estado": row["estado"],
                "valid_from": data_atu,
                "valid_to": pd.to_datetime("9999-12-31"),
                "flag_vigencia": True,
            }
            novos_registros.append(novo_registro)

        # Adicionando as novas linhas ao DataFrame
        if novos_registros:
            dim_cliente = pd.concat(
                [dim_cliente, pd.DataFrame(novos_registros)], ignore_index=True
            )

        # Atualizando o banco de dados com a tabela completa de clientes (SCD2)
        dim_cliente.to_sql(
            "dim_cliente", con=engine_dw, if_exists="replace", index=False
        )
        logging.info("Histórico de clientes atualizado.")
    except Exception as e:
        logging.error(f"Erro durante a atualização de clientes (SCD2): {e}")
