# Zoop Data Pipeline — Do Transacional ao Analítico

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas)

Pipeline ETL end-to-end que resolve um problema real de separação entre ambiente operacional e analítico: extrair dados do banco transacional (OLTP), processar em um Data Lake local em camadas (Bronze → Silver → Gold) e carregar em um Data Warehouse dimensional (Star Schema) com controle de histórico via **SCD Tipo 2**.

---

## Problema de negócio

A **Zoop** (empresa fictícia) enfrentava um problema clássico: as consultas analíticas do time de dados rodavam diretamente no banco de produção, concorrendo com as transações operacionais e degradando a performance do sistema.

Além disso, os dados brutos apresentavam inconsistências:
- Registros com valores negativos de quantidade e valor
- Pedidos com `id_cliente` inexistente (integridade referencial quebrada)
- Clientes com cadastros duplicados
- Pedidos marcados como `ABERTO` com vencimento já ultrapassado

**Solução:** construir uma plataforma analítica local que separa o operacional do analítico, aplica regras de qualidade em cada etapa e disponibiliza dados confiáveis para consumo via DW.

---

## Arquitetura

```
CSV (dados brutos)
      │
      ▼
┌─────────────┐        ┌──────────────────────────────────────┐
│  PostgreSQL │        │           Data Lake (Parquet)        │
│    OLTP     │──────► │  Bronze  │  Silver   │     Gold      │
│  porta 5432 │  ETL   │  (raw)   │ (tratado) │  (agregado)   │
└─────────────┘        └──────────────────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  PostgreSQL DW  │
                              │   Star Schema   │
                              │   porta 5433    │
                              └─────────────────┘
```

| Camada     | Responsabilidade                                                                          |
| ---------- | ----------------------------------------------------------------------------------------- |
| **Bronze** | Ingestão literal — dados extraídos do OLTP sem transformação, preservados em Parquet      |
| **Silver** | Limpeza, deduplicação, tipagem, joins e regras de qualidade com log de auditoria          |
| **Gold**   | Agregação por mês e categoria — indicadores pré-calculados prontos para análise           |
| **DW**     | Modelo estrela com Surrogate Keys, FK entre fato e dimensões, SCD Tipo 2 na `dim_cliente` |

---

## Modelo dimensional (Star Schema)

```
                 dim_tempo
                     │
dim_produto ── fato_vendas ── dim_cliente (SCD Tipo 2)
```

### `fato_vendas`
Grão: uma linha por item de pedido.

| Campo        | Tipo    | Descrição                                             |
| ------------ | ------- | ----------------------------------------------------- |
| `sk_cliente` | INT     | FK → `dim_cliente` (versão vigente na data da compra) |
| `sk_produto` | INT     | FK → `dim_produto`                                    |
| `sk_tempo`   | INT     | FK → `dim_tempo` (formato YYYYMMDD)                   |
| `id_pedido`  | INT     | Chave natural para rastreabilidade                    |
| `quantidade` | INT     | Itens comprados                                       |
| `valor_item` | DECIMAL | Preço do item no momento da compra                    |

### `dim_cliente` — SCD Tipo 2
Mantém histórico de mudanças cadastrais (cidade, estado). A `fato_vendas` aponta sempre para a versão do cliente **vigente na data da compra**, garantindo análises históricas precisas.

| Campo                      | Tipo    | Descrição                                       |
| -------------------------- | ------- | ----------------------------------------------- |
| `sk_cliente`               | INT PK  | Surrogate Key                                   |
| `cod_cliente`              | INT     | Chave natural do OLTP                           |
| `nome`, `cidade`, `estado` | VARCHAR | Dados cadastrais                                |
| `valid_from`               | DATE    | Início da vigência                              |
| `valid_to`                 | DATE    | Fim da vigência (`9999-12-31` = registro atual) |
| `flag_vigencia`            | BOOLEAN | `True` se versão atual                          |

---

## ✅ Regras de qualidade (camada Silver)

Aplicadas em [`transform_silver.py`](src/transform_silver.py), com divergências registradas em [`logs/pipeline_execucao.log`](logs/pipeline_execucao.log):

1. **Rejeição de negativos** — remove registros com `quantidade < 0` ou `valor_item < 0`
2. **Integridade referencial** — descarta pedidos sem `id_cliente` rastreável
3. **Deduplicação** — remove duplicatas completas nos cadastros
4. **Auditoria de atrasos** — detecta e loga pedidos com status `ABERTO` e vencimento anterior à data de referência (`2024-06-15`), derivando o status correto `ATRASADO`

---

## Estrutura do projeto

```
projeto-final/
├── dados/                        # CSVs de entrada (simulam exportação do sistema)
│   ├── clientes.csv
│   ├── clientes_atualizacao.csv  # Mudanças cadastrais (input para SCD2)
│   ├── pedidos.csv
│   └── produtos.csv
├── datalake/
│   ├── bronze/                   # Dados brutos em Parquet
│   ├── silver/                   # Dados tratados em Parquet
│   └── gold/                     # Indicadores agregados em Parquet
├── logs/
│   └── pipeline_execucao.log     # Log de auditoria do pipeline
├── sql/
│   ├── 01_create_oltp.sql        # DDL do banco transacional
│   └── 02_create_dw.sql          # DDL do Data Warehouse
├── src/
│   ├── main.py                   # Orquestrador — executa toda a esteira
│   ├── extract.py                # Carga do OLTP + extração para Bronze
│   ├── transform_silver.py       # Limpeza, qualidade e joins (Silver)
│   ├── transform_gold.py         # Agregações de negócio (Gold)
│   └── load_dw.py                # Carga dimensional + SCD Tipo 2
├── docker-compose.yml            # Dois containers PostgreSQL (OLTP + DW)
└── requirements.txt
```

---

## Como executar

### Pré-requisitos
- [Docker e Docker Compose](https://www.docker.com/)
- Python 3.12+

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/SEU-USUARIO/zoop-data-pipeline.git
cd zoop-data-pipeline

# 2. Suba os dois bancos PostgreSQL (OLTP na 5432, DW na 5433)
docker compose up -d

# 3. Crie o ambiente virtual e instale as dependências
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. Execute toda a esteira de uma vez
python -m src.main
```

O pipeline executa na ordem: **OLTP → Bronze → Silver → Gold → DW (dimensões + SCD2)**.
Acompanhe a execução em tempo real no arquivo `logs/pipeline_execucao.log`.

---

## Stack utilizada

| Ferramenta     | Uso                                 |
| -------------- | ----------------------------------- |
| Python 3.12    | Linguagem principal                 |
| Pandas         | Transformações e qualidade de dados |
| PyArrow        | Leitura/escrita de Parquet          |
| SQLAlchemy     | Conexão com PostgreSQL              |
| psycopg2       | Driver PostgreSQL                   |
| Docker Compose | Infraestrutura local (OLTP + DW)    |
| PostgreSQL 16  | Banco transacional e analítico      |
