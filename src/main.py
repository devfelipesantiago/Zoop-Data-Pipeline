import os
import logging
from src.extract import extrair_bronze, carregar_oltp
from src.transform_silver import transformar_silver
from src.transform_gold import transformar_gold
from src.load_dw import carregar_dimensoes_e_fatos, transformar_scd2_clientes

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/pipeline_execucao.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def executar_pipeline():
    logging.info("--- INICIANDO PIPELINE ZOOP ---")

    try:
        # 1. OLTP e Bronze
        carregar_oltp()
        extrair_bronze()

        # 2. Silver e Gold
        transformar_silver()
        transformar_gold()

        # 3. Data Warehouse Dimensional
        carregar_dimensoes_e_fatos()
        transformar_scd2_clientes()

        logging.info("--- PIPELINE FINALIZADO COM SUCESSO ---")

    except Exception as e:
        logging.error("--- PIPELINE FALHOU: %s ---", e)
        raise


if __name__ == "__main__":
    executar_pipeline()
