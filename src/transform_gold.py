import pandas as pd
import os
import logging


def transformar_gold():
    logging.info("Iniciando agregação para a Camada gold...")
    try:
        os.makedirs("datalake/gold", exist_ok=True)

        df_silver = pd.read_parquet("datalake/silver/dados_consolidados.parquet")

        # Criando coluna de ano-mês para agrupamento
        df_silver["ano_mes"] = df_silver["data_pedido"].dt.to_period("M").astype(str)
        df_silver["faturamento_total"] = (
            df_silver["quantidade"] * df_silver["valor_item"]
        )

        # Calculando valor em atraso apenas para os pedidos derivados como ATRASADOS
        df_silver["valor_em_atraso"] = df_silver.apply(
            lambda r: (
                r["faturamento_total"] if r["status_derivado"] == "ATRASADO" else 0
            ),
            axis=1,
        )

        # Agregação por mês e categoria
        df_gold = (
            df_silver.groupby(["ano_mes", "categoria"])
            .agg(
                faturamento_total=("faturamento_total", "sum"),
                quantidade_vendida=("quantidade", "sum"),
                valor_em_atraso=("valor_em_atraso", "sum"),
            )
            .reset_index()
        )

        # Salvando o resultado na Camada gold
        df_gold.to_parquet(
            "datalake/gold/indicadores_mes_categoria.parquet",
            engine="pyarrow",
            index=False,
        )
        logging.info("Camada gold gerada com sucesso.")
    except Exception as e:
        logging.error("Erro ao gerar a Camada gold: %s", e)
