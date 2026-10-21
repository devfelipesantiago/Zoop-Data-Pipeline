import logging
import os

import pandas as pd

DATA_REFERENCIA = pd.to_datetime("2024-06-15")


def transformar_silver():
    try:
        # Lógica para transformar os dados da Camada Bronze para a Camada Silver
        logging.info("Transformação para a Camada Silver iniciada.")
        os.makedirs("datalake/silver", exist_ok=True)

        # Leitura da Bronze
        df_pedido = pd.read_parquet("datalake/bronze/pedido.parquet")
        df_item = pd.read_parquet("datalake/bronze/pedido_item.parquet")
        df_cliente = pd.read_parquet("datalake/bronze/cliente.parquet")
        df_produto = pd.read_parquet("datalake/bronze/produto.parquet")

        # Regras de Qualidade 1: Rejeitar negativos e nulos
        df_item = df_item[(df_item["quantidade"] >= 0) & (df_item["valor_item"] >= 0)]
        df_pedido = df_pedido.dropna(subset=["id_cliente"])

        # Junção das tabelas (join)
        df_prata = (
            df_item.merge(df_pedido, on="id_pedido", how="left")
            .merge(df_cliente, on="id_cliente", how="left")
            .merge(df_produto, on="id_produto", how="left")
        )

        # Padronização de datas
        df_pedido["data_pedido"] = pd.to_datetime(df_pedido["data_pedido"])
        df_pedido["data_vencimento"] = pd.to_datetime(df_pedido["data_vencimento"])

        # Função para calcular dias de atraso (apenas para não pagos)
        def calcular_dias_atraso(row):
            if row["status_pagamento"] != "PAGO":
                delta = DATA_REFERENCIA - row["data_vencimento"]
                return max(0, delta.days)  # Retorna 0 se não houver atraso
            return 0

        df_prata["dias_atraso"] = df_prata.apply(calcular_dias_atraso, axis=1)

        # Função para derivar o status com base na data de referência
        def deriva_status(row):
            if row["status_pagamento"] == "PAGO":
                return "PAGO"
            elif DATA_REFERENCIA > row["data_vencimento"]:
                return "ATRASADO"
            else:
                return "EM_DIA"

        df_prata["status_derivado"] = df_prata.apply(deriva_status, axis=1)

        # Auditoria de divergências
        divergencias = df_prata[
            (df_prata["status_pagamento"] == "ABERTO")
            & (df_prata["status_derivado"] == "ATRASADO")
        ]
        if not divergencias.empty:
            logging.warning(
                f"Auditoria de Qualidade: {len(divergencias)} pedidos marcados como ABERTO estão ATRASADOS."
            )

        # Salvando o resultado na Camada Silver
        df_prata = df_prata.drop_duplicates()
        df_prata.to_parquet(
            "datalake/silver/dados_consolidados.parquet",
            index=False,
            engine="pyarrow",
        )

        logging.info("Camada Silver finalizada com sucesso.")
    except Exception as e:
        logging.info("Erro ao transformar os dados para a Camada Silver: %s", e)
