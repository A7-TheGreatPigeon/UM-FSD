import threading
import time
import random
import requests
import psutil
import socket
import json
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding

app = Flask(__name__)



informacaoProdutor = {}
estadoProdutor = True
listaProdutos = []
listaCategorias = {  "Fruta": ["Figo", "Pera", "Castanha", "Banana", "Morango", "Manga", "Uva", "Kiwi", "Laranja", "Maca"],
                    "Ferramentas": ["Alicate", "Espatula", "Martelo", "Medidor", "Macete", "Aparafusadora", "Pa", "Tesoura", "Serrote", "Machado"],
                    "Livros": ["A Divina Comedia", "Os Lusiadas", "Memorial do Convento", "Mensagem", "A Guarda Branca"],
                    "Roupa": ["Camisola", "Casaco", "T-Shirt", "Calcas", "Saia", "Par de Meias"],
                    "Computadores": ["Acer", "Lenovo", "Dell", "Apple", "ASUS"],
                    "Smartphones": ["Apple", "Oppo", "Xiaomi", "Samsung", "Honor", "Nokia"],
                    "Filmes": ["Capitao Falcao", "Balas e Bolinhos", "Minions", "A Ressaca", "Gaiola Dourada"],
                    "Sapatos": ["Botas", "Sapatilhas", "Salto-Alto", "Chinelos", "Pantufas", "Sandalias"]}


def obterIpVpn():
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address.startswith('10.8.0'):
                return addr.address
            

def atualizarCertificado(novoCertificado):
    global certificado
    certificado = novoCertificado


def publicarProdutor(informacaoProdutor):
    urlGestor = "http://193.136.11.170:5001/"
    while True:
        lista = requests.post(f"{urlGestor}/produtor_certificado", json=informacaoProdutor)
        if lista.status_code == 200:
            print("A informação de um produtor foi atualizada com sucesso")
            atualizarCertificado(lista.text)
        elif lista.status_code == 201:
            print("O novo produtor foi registado com sucesso")
            atualizarCertificado(lista.text)
        else:
            print("O pedido não foi bem executado, por isso o servidor não foi capaz de executar com sucesso.")
        time.sleep(110)


def postProdutor():
    global estadoProdutor, key
    
    enderecoIP = str(obterIpVpn())
    if enderecoIP == "None":
        print("Produtor não conectado à rede ou IP não é 10.8.0.x")
        estadoProdutor = False
        return
    
    informacaoProdutor["ip"] = str(obterIpVpn())
    informacaoProdutor["nome"] = input("Nome do produtor: ")
    informacaoProdutor["porta"] = int(input("Porta: "))

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    chavePublica = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    informacaoProdutor["pubKey"] = chavePublica.decode()

    threading.Thread(target=publicarProdutor, args=(informacaoProdutor,)).start()
    

def gerarAssinaturaCertificado(mensagem):
    global certificado, key
    
    if isinstance(mensagem, list) or isinstance(mensagem, dict):
        mensagem = json.dumps(mensagem).encode('utf-8')
    elif isinstance(mensagem, str):
        mensagem = mensagem.encode('utf-8')

    assinatura = key.sign(
        mensagem,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return assinatura.decode('cp437'), certificado


@app.route("/secure/categorias", methods=['GET'])
def getCategorias():
    lista = []
    for produto in listaProdutos:
        if produto["categoria"] not in lista:
            lista.append(produto["categoria"])

    assinatura, certificado = gerarAssinaturaCertificado(lista)
    return {"assinatura": assinatura, "certificado": certificado, "mensagem": lista}, 200


@app.route("/secure/produtos", methods=['GET'])
def getProdutosCategoria():
    produtos = []
    categoria = request.args.get('categoria')
    for produto in listaProdutos:
        if produto["categoria"] == categoria:
            produtos.append(produto)
    if len(produtos) != 0:
        status_code = 200
    else:
        produtos = '1: Categoria Inexistente'
        status_code = 404

    assinatura, certificado = gerarAssinaturaCertificado(produtos)
    return {"assinatura": assinatura, "certificado": certificado, "mensagem": produtos}, status_code


@app.route("/secure/comprar/<produto>/<quantidade>/", methods=['POST'])
def comprarProduto(produto, quantidade):
    encontrou = False
    for produtoDaLista in listaProdutos:
        if produtoDaLista["produto"] == produto:
            if int(quantidade) <= produtoDaLista["quantidade"]:
                produtoDaLista["quantidade"] -= int(quantidade)
                if produtoDaLista["quantidade"] == 0:
                    listaProdutos.remove(produtoDaLista)
                status_code = 200
                mensagem = "Produtos comprados"
            else:
                status_code = 404
                mensagem = "Quantidade indisponivel"
            encontrou = True
    if not encontrou:
        status_code = 404
        mensagem = "Produto inexistente"
    assinatura, certificado = gerarAssinaturaCertificado(mensagem)
    return {"assinatura": assinatura, "certificado": certificado, "mensagem": mensagem}, status_code


def produtosNaLista():
    listaDeProdutos = []
    for produto in listaProdutos:
        listaDeProdutos.append(produto["produto"])
    return listaDeProdutos
    

def criarStock():                                                                           
    while estadoProdutor:                                                                   
        for categoria, items in listaCategorias.items():                                    
            itemsSelecionados = random.sample(items, random.randint(1, len(items)))
            for produto in itemsSelecionados:
                if produto in produtosNaLista():
                    for prod in listaProdutos:
                        if prod["produto"] == produto:
                            prod["quantidade"] += random.randint(1, 5)
                else:
                    listaProdutos.append({"categoria": categoria, "preco": random.randint(1, 3), "produto": produto, "quantidade": random.randint(1, 5)})
        time.sleep(60)                                                                     


postProdutor()
if estadoProdutor:
    threading.Thread(target=criarStock, args=()).start()
    if __name__ == '__main__':
        app.run(host=informacaoProdutor["ip"], port=informacaoProdutor["porta"], debug=False, use_reloader=False)