import pandas as pd
import os
import logging


def transformar_ouro():
    logging.info("Iniciando agregação para a Camada Ouro...")
    try:
        os.makedirs("datalake/ouro", exist_ok=True)

        df_prata = pd.read_parquet("datalake/prata/dados_consolidados.parquet")

        # Criando coluna de ano-mês para agrupamento
        df_prata["ano_mes"] = df_prata["data_pedido"].dt.to_period("M").astype(str)
        df_prata["faturamento_total"] = df_prata["quantidade"] * df_prata["valor_item"]

        # Calculando valor em atraso apenas para os pedidos derivados como ATRASADOS
        df_prata["valor_em_atraso"] = df_prata.apply(
            lambda r: (
                r["faturamento_total"] if r["status_derivado"] == "ATRASADO" else 0
            ),
            axis=1,
        )

        # Agregação por mês e categoria
        df_ouro = (
            df_prata.groupby(["ano_mes", "categoria"])
            .agg(
                faturamento_total=("faturamento_total", "sum"),
                quantidade_vendida=("quantidade", "sum"),
                valor_em_atraso=("valor_em_atraso", "sum"),
            )
            .reset_index()
        )

        # Salvando o resultado na Camada Ouro
        df_ouro.to_parquet(
            "datalake/ouro/indicadores_mes_categoria.parquet",
            engine="pyarrow",
            index=False,
        )
        logging.info("Camada Ouro gerada com sucesso.")
    except Exception as e:
        logging.error("Erro ao gerar a Camada Ouro: %s", e)
