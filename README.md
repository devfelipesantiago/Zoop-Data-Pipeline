# Zoop Data Pipeline: Do Transacional ao Analítico

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Pandas](https://img.shields.io/badge/Pandas-Data_Processing-150458?logo=pandas)

## 📌 Sobre o Projeto
Este projeto simula um cenário real da empresa **Zoop**, onde as consultas analíticas estavam a onerar o banco de dados transacional (OLTP) de produção.

Para resolver o problema, foi desenvolvida uma **plataforma analítica local end-to-end**, que extrai os dados brutos (sujos e duplicados), processa-os através de um **Data Lake em camadas (Bronze, Prata e Ouro)** utilizando o formato colunar Parquet, e disponibiliza-os num **Data Warehouse Dimensional (Star Schema)**. O projeto inclui o tratamento rigoroso de qualidade de dados e a implementação de histórico de clientes via **SCD (Slowly Changing Dimension) Tipo 2**.

---

## ⚙️ Arquitetura da Solução

1. **OLTP (PostgreSQL):** Banco relacional normalizado (3NF) simulando o ambiente de produção da Zoop.
2. **Data Lake (Local/Parquet):**
   * **Bronze:** Ingestão literal (raw data) extraída do OLTP.
   * **Prata:** Limpeza, deduplicação, cruzamentos, tipagem e regras de qualidade (Data Quality).
   * **Ouro:** Tabelas agregadas focadas no negócio (indicadores sumarizados).
3. **Data Warehouse (PostgreSQL):** Modelagem dimensional em Star Schema com Surrogate Keys, separando fatos e dimensões para consultas OLAP eficientes.

---

## 🚀 Como Executar o Projeto

Todo o pipeline foi construído para rodar localmente, sem custos com nuvem, utilizando contentores Docker.

### Pré-requisitos
* [Docker e Docker Compose](https://www.docker.com/)
* [Python 3.12+](https://www.python.org/)
* Git

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/SEU-USUARIO/zoop-data-pipeline.git](https://github.com/SEU-USUARIO/zoop-data-pipeline.git)
   cd zoop-data-pipeline
   ```

2. **Suba a infraestrutura de Bancos de Dados:**
   Serão instanciados dois bancos isolados na sua máquina (OLTP na porta 5432 e DW na porta 5433 para evitar conflitos).
   ```bash
   docker-compose up -d
   ```

3. **Configure o Ambiente Virtual e Instale as Dependências:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Execute o Orquestrador Principal:**
   O script executará toda a esteira (OLTP -> Bronze -> Prata -> Ouro -> DW).
   ```bash
   python src/main.py
   ```

---

## 📖 Catálogo de Dados (Data Warehouse)

O banco de dados analítico (`banco_dw`) foi estruturado num modelo estrela contendo as seguintes tabelas:

### `dim_cliente` (SCD Tipo 2)
Armazena os clientes com controle de histórico de mudanças cadastrais (cidade e estado).

| Campo           | Tipo      | Descrição                                                             |
| :-------------- | :-------- | :-------------------------------------------------------------------- |
| `sk_cliente`    | `INT`     | Surrogate Key e Chave Primária da dimensão.                           |
| `cod_cliente`   | `INT`     | Chave natural (ID) oriunda do banco transacional.                     |
| `nome`          | `VARCHAR` | Nome completo do cliente.                                             |
| `cidade`        | `VARCHAR` | Cidade de residência.                                                 |
| `estado`        | `VARCHAR` | Sigla do Estado (UF).                                                 |
| `valid_from`    | `DATE`    | Data de início de vigência desta versão do cadastro.                  |
| `valid_to`      | `DATE`    | Data de fim de vigência desta versão (`9999-12-31` se atual).         |
| `flag_vigencia` | `BOOLEAN` | `True` se o registo é a versão atual, `False` se é registo histórico. |

### `dim_produto`
Catálogo de produtos únicos.

| Campo            | Tipo      | Descrição                                               |
| :--------------- | :-------- | :------------------------------------------------------ |
| `sk_produto`     | `INT`     | Surrogate Key e Chave Primária.                         |
| `cod_produto`    | `INT`     | Chave natural (ID_Produto) vinda do banco transacional. |
| `nome_produto`   | `VARCHAR` | Nome descritivo do produto.                             |
| `categoria`      | `VARCHAR` | Categoria na qual o produto se enquadra.                |
| `preco_unitario` | `DECIMAL` | Preço unitário base de tabela.                          |

### `dim_tempo`
Dimensão de calendário derivada das datas dos pedidos.

| Campo       | Tipo      | Descrição                                                |
| :---------- | :-------- | :------------------------------------------------------- |
| `sk_tempo`  | `INT`     | Surrogate Key em formato numérico YYYYMMDD.              |
| `data`      | `DATE`    | Data correspondente do calendário.                       |
| `mes`       | `INT`     | Mês do ano da transação.                                 |
| `trimestre` | `INT`     | Trimestre correspondente (1 a 4).                        |
| `dia_util`  | `BOOLEAN` | `True` para dias de semana, `False` para fins de semana. |

### `fato_vendas`
Tabela transacional granular ao nível de item do pedido.

| Campo        | Tipo      | Descrição                                                       |
| :----------- | :-------- | :-------------------------------------------------------------- |
| `sk_cliente` | `INT`     | FK apontando para a versão correta do cliente na `dim_cliente`. |
| `sk_produto` | `INT`     | FK apontando para o item na `dim_produto`.                      |
| `sk_tempo`   | `INT`     | FK apontando para a data da compra na `dim_tempo`.              |
| `id_pedido`  | `INT`     | Código natural do pedido para auditoria e rastreio.             |
| `quantidade` | `INT`     | Quantidade de itens comprados.                                  |
| `valor_item` | `DECIMAL` | Preço fechado daquele item no momento exato da compra.          |

---

## 🔗 Linhagem de Dados (Data Lineage)

O fluxo do indicador `faturamento_total` percorre o seguinte caminho, desde o transacional até à visualização no DW:

1. **Origem (OLTP):** Os dados físicos `quantidade` e `valor_item` nascem nas transações inseridas na tabela normalizada `pedido_item` no PostgreSQL.
2. **Camada Bronze:** Extraídos sem transformações para o ficheiro `pedido_item.parquet` preservando a estrutura original.
3. **Camada Prata:** Durante os cruzamentos lógicos (Join), calcula-se em memória o indicador base `faturamento_total = quantidade * valor_item`.
4. **Camada Ouro:** O faturamento é materializado e pré-agregado por `ano_mes` e `categoria` no ficheiro `indicadores_mes_categoria.parquet`.
5. **Data Warehouse (Analítico):** As grandezas base (`quantidade` e `valor_item`) são armazenadas na `fato_vendas`. Isso permite que os relatórios recalculem o faturamento de forma fatiada, cruzando livremente com atributos de clientes, localização e produtos.

---

## 🛡️ Regras de Qualidade Aplicadas

Durante o processamento da Camada Prata (`transform_silver.py`), o pipeline aplica regras de negócio para garantir a higienização dos dados. Discrepâncias geram logs de auditoria na pasta `/logs`:

1. **Remoção de Negativos:** Rejeição de registos inválidos contendo valores de `quantidade < 0` ou `valor_item < 0`.
2. **Integridade Referencial:** Identificação e exclusão de pedidos órfãos, registados sem um `id_cliente` rastreável no catálogo de clientes.
3. **Deduplicação Oficial:** Remoção de duplicidades completas nos cadastros.
4. **Auditoria de Atrasos (Log):** Validação temporal utilizando a data de referência **15/06/2024**. O sistema deteta se o sistema transacional mantém o status "ABERTO" para compras cuja data de vencimento é anterior à referência, registando a divergência em log como um apontamento analítico de status "ATRASADO".