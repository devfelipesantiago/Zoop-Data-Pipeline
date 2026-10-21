CREATE DATABASE IF NOT EXISTS `ZOOP_OLTP`
-- Criação da tabela de Clientes
CREATE TABLE cliente (
    id_cliente INT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    data_nascimento DATE
);

-- Criação da tabela de Produtos
CREATE TABLE produto (
    id_produto INT PRIMARY KEY,
    nome_produto VARCHAR(100) NOT NULL,
    categoria VARCHAR(50),
    preco_unitario DECIMAL(10,2)
);

-- Criação da tabela de Pedidos
CREATE TABLE pedido (
    id_pedido INT PRIMARY KEY,
    id_cliente INT NOT NULL,
    data_pedido DATE NOT NULL,
    status_pagamento VARCHAR(20) NOT NULL,
    data_vencimento DATE NOT NULL,
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
);

-- Criação da tabela de Itens do Pedido (Chave primária composta)
CREATE TABLE pedido_item (
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    valor_item DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id_pedido, id_produto),
    CONSTRAINT fk_item_pedido FOREIGN KEY (id_pedido) REFERENCES pedido (id_pedido),
    CONSTRAINT fk_item_produto FOREIGN KEY (id_produto) REFERENCES produto (id_produto)
);