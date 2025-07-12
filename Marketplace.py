import socket
import threading
import json
import time
import requests
from flask import Flask, jsonify
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

estadoMarketplace = True
listaProdutos = []
dicionarioProdutos = {}
listaCategorias = []
stockMarketplace = []


def getProdutoresREST():
    urlGestor = "http://193.136.11.170:5001/"
    lista = requests.get(f"{urlGestor}/produtor")
    if lista.status_code == 200:
        novaLista = []
        for produtor in lista.json():
            produtor["tipo"] = "rest"
            novaLista.append(produtor)
        return novaLista
    else:
        print("Erro ao obter lista Produtores:", lista.status_code, lista.json())


def getProdutoresSocket(listaSubscricao):
    for i in range(3):
        listaSubscricao.append({"nome": f"{1 + i}", "porta": 1026 + i, "ip": '127.0.0.1', "tipo": 'socket'})
    return listaSubscricao


def inputNumero(texto):
    valor = input(texto)
    while not valor.isnumeric():
        valor = input(f"Valor invalido\nIntroduza novo valor: ")
    return int(valor)


def inputTextoLista(lista, texto):
    texto = input(texto)
    while texto not in lista and texto != '0':
        texto = input(f"Valor invalido\nIntroduza novo valor: ")
    return texto


def validarCertificado(certificado):
    with open("manager_public_key.pem", "rb") as f:
        chavePublica = serialization.load_pem_public_key(f.read())
    try:
        chavePublica.verify(
            certificado.signature,
            certificado.tbs_certificate_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        return False


def validarAssinatura(mensagem):
    chavePublica = load_pem_x509_certificate(mensagem["certificado"].encode()).public_key()

    if isinstance(mensagem["mensagem"], list) or isinstance(mensagem["mensagem"], dict):
        mensagem["mensagem"] = json.dumps(mensagem["mensagem"]).encode('utf-8')
    elif isinstance(mensagem["mensagem"], str):
        mensagem["mensagem"] = mensagem["mensagem"].encode('utf-8')
    try:
        chavePublica.verify(
            mensagem["assinatura"].encode("cp437"),
            mensagem["mensagem"],
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        return False


def getCategoriasRest(ligacao):
    try:
        global listaCategorias
        produtos = requests.get(f"http://{ligacao['ip']}:{ligacao['porta']}/categorias", timeout=1)
        if produtos.status_code == 200:
            for produto in produtos.json():
                if produto not in listaCategorias:
                    listaCategorias.append(produto)
    finally:
        return
    

def getCategoriasRestSecure(ligacao):
    try:
        global listaCategorias
        produtos = requests.get(f"http://{ligacao['ip']}:{ligacao['porta']}/secure/categorias", timeout=1)
        if produtos.status_code == 200:
            if validarCertificado(load_pem_x509_certificate(produtos.json()["certificado"].encode())):
                if validarAssinatura(produtos.json()):
                    for produto in produtos.json()["mensagem"]:
                        if produto not in listaCategorias:
                            listaCategorias.append(produto)
    finally:
        return
    

def getCategoriasSocket(ligacao):
    try:
        global listaCategorias
        s = socket.socket()
        s.settimeout(1)
        s.connect((ligacao["ip"], ligacao["porta"]))
        s.send("1".encode())
        produtos = json.loads(s.recv(2048).decode())
        for produto in produtos:
            if produto not in listaCategorias:
                listaCategorias.append(produto)
        print("Categorias Socket recebidas")
    finally:
        return


def getProdutosCategoriaRest(ligacao, categoria):
    try:
        global listaProdutos
        produtos = requests.get(f"http://{ligacao['ip']}:{ligacao['porta']}/produtos", {'categoria': categoria}, timeout=1)
        for produto in produtos.json():
            encontrou = True
            for produtoDaLista in listaProdutos:
                if produto["produto"] == produtoDaLista["produto"]:
                    encontrou = False
                    produtoDaLista["quantidade"] += produto["quantidade"]
            if encontrou and produtos.status_code == 200:                                                       
                listaProdutos.append(produto)
    finally:
        return
    

def getProdutosCategoriaRestSecure(ligacao, categoria):
    try:
        global listaProdutos
        produtos = requests.get(f"http://{ligacao['ip']}:{ligacao['porta']}/secure/produtos", {'categoria': categoria}, timeout=1)
        if produtos.status_code == 200:
            if validarCertificado(load_pem_x509_certificate(produtos.json()["certificado"].encode())):
                if validarAssinatura(produtos.json()):
                    for produto in produtos.json()["mensagem"]:
                        encontrou = True
                        for produtoDaLista in listaProdutos:
                            if produto["produto"] == produtoDaLista["produto"]:
                                encontrou = False
                                produtoDaLista["quantidade"] += produto["quantidade"]
                        if encontrou and produtos.status_code == 200:                                                       
                            listaProdutos.append(produto)
    finally:
        return
    

def getProdutosCategoriaSocket(ligacao, categoria):
    try:
        global listaProdutos
        s = socket.socket()
        s.settimeout(1)
        s.connect((ligacao["ip"], ligacao["porta"]))
        print(f"Marketplace conectado ao socket {ligacao["nome"]}")
        s.send("2".encode())
        confirmacao = s.recv(1024).decode()
        s.send(categoria.encode())
        produtos = json.loads(s.recv(2048).decode())
        for produto in produtos:
            encontrou = True
            for produtoDaLista in listaProdutos:
                if produto["produto"] == produtoDaLista["produto"]:
                    encontrou = False
                    produtoDaLista["quantidade"] += produto["quantidade"]
            if encontrou:                                                       
                listaProdutos.append(produto)
    finally:
        return


def listarProdutosDisponiveis(listaSubscricao):
    if len(listaSubscricao) != 0:
        global listaCategorias, listaProdutos
        listaCategorias.clear()
        listaProdutos.clear()
        listaThreads = []

        for ligacao in listaSubscricao:
            if ligacao["tipo"] == "rest":
                if ligacao["secure"] == 0:
                    x = threading.Thread(target=getCategoriasRest, args=(ligacao,))
                elif ligacao["secure"] == 1:
                    x = threading.Thread(target=getCategoriasRestSecure, args=(ligacao,))
            if ligacao["tipo"] == "socket":
                x = threading.Thread(target=getCategoriasSocket, args=(ligacao,))
            x.start()
            listaThreads.append(x)

        for x in listaThreads:
            x.join()
        
        print(f"\nCategorias disponiveis: ")
        for categoria in listaCategorias:
            print(f"{categoria}")

        texto = inputTextoLista(listaCategorias, "Categoria a escolher: ")
        if texto != '0':

            listaThreads = []

            for ligacao in listaSubscricao:
                if ligacao["tipo"] == "rest":
                    if ligacao["secure"] == 0:
                        x = threading.Thread(target=getProdutosCategoriaRest, args=(ligacao, texto,))
                    elif ligacao["secure"] == 1:
                        x = threading.Thread(target=getProdutosCategoriaRestSecure, args=(ligacao, texto,))
                if ligacao["tipo"] == "socket":
                    x = threading.Thread(target=getProdutosCategoriaSocket, args=(ligacao, texto,))
                x.start()
                listaThreads.append(x)

            for x in listaThreads:
                x.join()

            if len(listaProdutos) != 0:
                    texto = f"\nProduto".ljust(18)
                    print(f"{texto}  Q")
                    for produto in listaProdutos:
                        texto = ""
                        texto = f"{produto['produto'].ljust(18, '-')} {produto['quantidade']} "
                        print(texto)
            else:
                print("Categoria sem produtos disponiveis")


def listarProdutores(listaSubscricao):
    if len(listaSubscricao) != 0:
        print("")
        for produtor in listaSubscricao:
            texto = ""
            texto += f"Produtor: {produtor['nome']}".ljust(30)
            texto += f"IP: {produtor['ip']}".ljust(20)
            texto += f"Porta: {produtor['porta']}".ljust(15)
            if produtor["tipo"] == "rest":
                if produtor["secure"] == 1:
                    texto += f"Tipo: {produtor['tipo']}Secure"
                else:
                    texto += f"Tipo: {produtor['tipo']}"
            else:
                texto += f"Tipo: {produtor['tipo']}"
            print(texto)


def addProdutosCategoriaRest(ligacao, categoria):
    try:
        global dicionarioProdutos
        produtos = requests.get(f"http://{ligacao['ip']}:{ligacao['porta']}/produtos", {'categoria': categoria}, timeout=1)
        if produtos.status_code == 200:
            for nome, lista in dicionarioProdutos.items():
                if nome == ligacao["nome"]:
                    for produto in produtos.json():
                        lista.append(produto)
                    return
            dicionarioProdutos[ligacao["nome"]] = produtos.json()
    finally:
        return


def addProdutosCategoriaRestSecure(ligacao, categoria):
    try:
        global dicionarioProdutos
        produtos = requests.get(f"http://{ligacao['ip']}:{ligacao['porta']}/secure/produtos", {'categoria': categoria}, timeout=1)
        if produtos.status_code == 200:
            if validarCertificado(load_pem_x509_certificate(produtos.json()["certificado"].encode())):
                if validarAssinatura(produtos.json()):
                    for nome, lista in dicionarioProdutos.items():
                        if nome == ligacao["nome"]:
                            for produto in produtos.json()["mensagem"]:
                                lista.append(produto)
                            return
                    dicionarioProdutos[ligacao["nome"]] = produtos.json()["mensagem"]
    finally:
        return
    

def addProdutosCategoriaSocket(ligacao, categoria):
    try:
        global dicionarioProdutos
        s = socket.socket()
        s.settimeout(1)
        s.connect((ligacao["ip"], ligacao["porta"]))
        s.send("2".encode())
        confirmacao = s.recv(1024).decode()
        s.send(categoria.encode())
        produtos = json.loads(s.recv(2048).decode())

        for nome, lista in dicionarioProdutos.items():
            if nome == ligacao["nome"]:
                for produto in produtos:
                    lista.append(produto)
                return
        dicionarioProdutos[ligacao["nome"]] = produtos
    finally:
        return

def verPrecoPorProdutor(listaSubscricao):
    if len(listaSubscricao) != 0:
        global listaCategorias, dicionarioProdutos
        listaCategorias.clear()
        dicionarioProdutos.clear()
        
        listaThreads = []

        for ligacao in listaSubscricao:
            if ligacao["tipo"] == "rest":
                if ligacao["secure"] == 0:
                    x = threading.Thread(target=getCategoriasRest, args=(ligacao,))
                elif ligacao["secure"] == 1:
                    x = threading.Thread(target=getCategoriasRestSecure, args=(ligacao,))
            if ligacao["tipo"] == "socket":
                x = threading.Thread(target=getCategoriasSocket, args=(ligacao,))
            x.start()
            listaThreads.append(x)

        for x in listaThreads:
            x.join()

        if len(listaCategorias) != 0:

            listaThreads = []

            for ligacao in listaSubscricao:
                for categoria in listaCategorias:
                    if ligacao["tipo"] == "rest":
                        if ligacao["secure"] == 0:
                            x = threading.Thread(target=addProdutosCategoriaRest, args=(ligacao, categoria,))
                        elif ligacao["secure"] == 1:
                            x = threading.Thread(target=addProdutosCategoriaRestSecure, args=(ligacao, categoria,))
                    if ligacao["tipo"] == "socket":
                        x = threading.Thread(target=addProdutosCategoriaSocket, args=(ligacao, categoria,))
                    x.start()
                    listaThreads.append(x)

            for x in listaThreads:
                x.join()
        

        nomeProdutos = []
        nomeProdutores = []

        for nome, lista in dicionarioProdutos.items():
            for produto in lista:
                if produto["produto"] not in nomeProdutos:
                    nomeProdutos.append(produto["produto"])
            nomeProdutores.append(nome)


        espaco = 20                                                             
        stringProdutor = f"Produtor".ljust(espaco)
        stringQuantidadePreco = f"Item".ljust(espaco)
        stringDivisao = f"".ljust(espaco, '-')
        for nome in nomeProdutores:
            espaco += 14
            stringProdutor = f"{stringProdutor}|      {nome}".ljust(espaco)
            stringQuantidadePreco = f"{stringQuantidadePreco}|   Q     €".ljust(espaco)
            stringDivisao = f"{stringDivisao.ljust(espaco, '-')}"
        print(f"{stringProdutor}\n{stringQuantidadePreco}\n{stringDivisao}")


        for nomeProduto in nomeProdutos:                                    
            espaco = 20
            texto = f"{nomeProduto}"
            for id, produtor in dicionarioProdutos.items():            
                encontrou = False
                for produto in produtor:                            
                    if produto["produto"] == nomeProduto:
                        texto = f"{texto.ljust(espaco)}|   {produto['quantidade']}".ljust(espaco + 9) 
                        texto = f"{texto} {produto['preco']} "
                        espaco += 14
                        encontrou = True
                if not encontrou:
                    texto = f"{texto.ljust(espaco)}|   {'0'}".ljust(espaco + 9) 
                    texto = f"{texto} {'Ind'} "
                    espaco += 14
            print(texto)


def comprarAoProdutor(listaSubscricao):
    if len(listaSubscricao) != 0:

        listarProdutores(listaSubscricao)

        nomeProdutores = []

        for subscricao in listaSubscricao:
            nomeProdutores.append(subscricao["nome"])

        texto = inputTextoLista(nomeProdutores, "Produtor a conectar: ")

        if texto != '0':
            for produtor in listaSubscricao:
                if produtor["nome"] == texto:
                    global listaCategorias, dicionarioProdutos, stockMarketplace
                    listaCategorias.clear()
                    dicionarioProdutos.clear()

                    if produtor["tipo"] == "rest":
                        if produtor["secure"] == 0:
                            getCategoriasRest(produtor)
                        elif produtor["secure"] == 1:
                            getCategoriasRestSecure(produtor)
                    if produtor["tipo"] == "socket":
                        getCategoriasSocket(produtor)

                    if len(listaCategorias) != 0:

                        listaThreads = []

                        for categoria in listaCategorias:
                            if produtor["tipo"] == "rest":
                                if produtor["secure"] == 0:
                                    x = threading.Thread(target=addProdutosCategoriaRest, args=(produtor, categoria,))
                                elif produtor["secure"] == 1:
                                    x = threading.Thread(target=addProdutosCategoriaRestSecure, args=(produtor, categoria,))
                            if produtor["tipo"] == "socket":
                                x = threading.Thread(target=addProdutosCategoriaSocket, args=(produtor, categoria,))
                            x.start()
                            listaThreads.append(x)

                        for x in listaThreads:
                            x.join()


                        nomeProdutos = []

                        print("Produtos disponiveis: ")                                     
                        for nome, produtos in dicionarioProdutos.items():
                            for produto in produtos:
                                texto = ""
                                texto = f"{produto['produto'].ljust(18, '-')} {produto['quantidade']} "
                                texto = f"{texto.ljust(21, '-')} {produto['preco']}€"
                                print(texto)
                                nomeProdutos.append(produto["produto"])

                        produtoAComprar = inputTextoLista(nomeProdutos, "Produto a comprar: ")
                        if produtoAComprar != '0':
                            quantidadeAComprar = inputNumero("Quantidade a comprar: ")
                            if quantidadeAComprar != 0:
                                    if produtor["tipo"] == "rest":
                                        if produtor["secure"] == 0:
                                            statusCompra = requests.get(f"http://{produtor['ip']}:{produtor['porta']}/comprar/{produtoAComprar}/{quantidadeAComprar}", timeout=1) 
                                            print(statusCompra.text)
                                        elif produtor["secure"] == 1:
                                            statusCompra = requests.post(f"http://{produtor['ip']}:{produtor['porta']}/secure/comprar/{produtoAComprar}/{quantidadeAComprar}", timeout=1)
                                            print(statusCompra.json()["mensagem"])
                                        
                                        valido = True
                                        if produtor["secure"] == 1:
                                            valido = False
                                            if validarCertificado(load_pem_x509_certificate(statusCompra.json()["certificado"].encode())):
                                                if validarAssinatura(statusCompra.json()):
                                                    valido = True

                                        if statusCompra.status_code == 200:
                                            if valido:
                                                for produto in stockMarketplace:
                                                    if produtoAComprar == produto["produto"]:
                                                        produto["quantidade"] += quantidadeAComprar
                                                        return

                                                for nome, produtos in dicionarioProdutos.items():
                                                    for produto in produtos:
                                                        if produtoAComprar == produto["produto"]:
                                                            stockMarketplace.append({"produto": produtoAComprar, "quantidade": quantidadeAComprar,  "preco": produto["preco"], "taxa": 0})
                                                            return

                                    if produtor["tipo"] == "socket":
                                        s = socket.socket()
                                        s.settimeout(1)
                                        s.connect((produtor["ip"], produtor["porta"]))
                                        s.send("3".encode())
                                        confirmacao = s.recv(1024).decode()
                                        s.send(produtoAComprar.encode())
                                        confirmacao = s.recv(1024).decode()
                                        s.send(str(quantidadeAComprar).encode())
                                        mensagem = s.recv(1024).decode()
                                        print(mensagem)
                                        if mensagem == "Sucesso: Produtos comprados":

                                            for produto in stockMarketplace:
                                                if produtoAComprar == produto["produto"]:
                                                    produto["quantidade"] += quantidadeAComprar
                                                    return

                                            for nome, produtos in dicionarioProdutos.items():
                                                for produto in produtos:
                                                    if produtoAComprar == produto["produto"]:
                                                        stockMarketplace.append({"produto": produtoAComprar, "quantidade": quantidadeAComprar,  "preco": produto["preco"], "taxa": 0})
                                                        return
                    else:
                        print("Produtor indisponivel")    


def verStockMarketplace(taxa):
    global stockMarketplace
    if len(stockMarketplace) != 0:
        print("Produtos disponiveis: ")
        for produto in stockMarketplace:
            texto = ""
            texto = f"{produto['produto'].ljust(18, '-')} {produto['quantidade']} "
            if taxa:
                texto = f"{texto.ljust(21, '-')} {produto['preco']}€"
                texto = f"{texto.ljust(24)} {produto['taxa']}%"
            else:
                texto = f"{texto.ljust(21, '-')} {produto['preco'] * (1 + (produto['taxa'] / 100)):.2f}€"
            print(texto)
    else:
        print(f"Stock vazio")


def alterarTaxa():
    global stockMarketplace
    verStockMarketplace(True)
    if len(stockMarketplace) != 0:

        nomeProdutos = []
        for produto in stockMarketplace:
            nomeProdutos.append(produto["produto"])

        texto = inputTextoLista(nomeProdutos, "Produto: ")
        if texto != '0':
            novaTaxa = inputNumero("Nova taxa: ")

            for produto in stockMarketplace:
                if produto["produto"] == texto:
                    produto["taxa"] = novaTaxa
                    return


def interface():
    global estadoMarketplace
    while estadoMarketplace:
        print("")
        print(f"1 - Listar produtos disponiveis por categoria")
        print(f"2 - Comprar a um produtor")
        print(f"3 - Ver preco de cada produtor")
        print(f"4 - Lista produtores")
        print(f"5 - Ver stock Marketplace")
        print(f"6 - Alterar taxa do produto")
        print(f"0 - Sair")
        opcao = inputNumero("Opcao: ")
        listaSubscricao = getProdutoresREST()
        listaSubscricao = getProdutoresSocket(listaSubscricao)
        match opcao:
            case 1:
                listarProdutosDisponiveis(listaSubscricao)

            case 2:
                comprarAoProdutor(listaSubscricao)

            case 3:
                verPrecoPorProdutor(listaSubscricao)

            case 4:
                listarProdutores(listaSubscricao)

            case 5:
                verStockMarketplace(False)

            case 6:
                alterarTaxa()

            case 0:
                estadoMarketplace = False

            case _:
                print(f"Opção invalida\n")

interface()