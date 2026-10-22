CREATE DATABASE IF NOT EXISTS `ZOOP_DW`
-- Dimensão Tempo (SCD Tipo 1 / Estática)
CREATE TABLE dim_tempo (
    sk_tempo INT PRIMARY KEY, -- Formato esperado: AAAAMMDD
    data DATE NOT NULL,
    ano INT NOT NULL,
    mes INT NOT NULL,
    trimestre INT NOT NULL,
    dia INT NOT NULL,
    dia_util BOOLEAN NOT NULL
);

-- Dimensão Produto (SCD Tipo 1)
CREATE TABLE dim_produto (
    sk_produto SERIAL PRIMARY KEY,
    cod_produto INT NOT NULL, -- Código natural vindo do OLTP
    nome_produto VARCHAR(100),
    categoria VARCHAR(50),
    preco_unitario DECIMAL(10,2)
);

-- Dimensão Cliente (SCD Tipo 2 - Controle de Histórico)
CREATE TABLE dim_cliente (
    sk_cliente SERIAL PRIMARY KEY,
    cod_cliente INT NOT NULL, -- Código natural vindo do OLTP
    nome VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    flag_vigencia BOOLEAN NOT NULL
);

-- Fato Vendas (Grão: uma linha por item de pedido)
CREATE TABLE fato_vendas (
    sk_cliente INT NOT NULL,
    sk_produto INT NOT NULL,
    sk_tempo INT NOT NULL,
    id_pedido INT NOT NULL, -- Mantido para rastreabilidade/linhagem
    quantidade INT NOT NULL,
    valor_item DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_fato_cliente FOREIGN KEY (sk_cliente) REFERENCES dim_cliente (sk_cliente),
    CONSTRAINT fk_fato_produto FOREIGN KEY (sk_produto) REFERENCES dim_produto (sk_produto),
    CONSTRAINT fk_fato_tempo FOREIGN KEY (sk_tempo) REFERENCES dim_tempo (sk_tempo)
);