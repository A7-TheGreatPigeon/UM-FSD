import socket
import threading
import time
import json
import random


class ProdutorSocket:
    def __init__(self, porta):
        self.__estadoProdutor = True
        self.__listaProdutos = []
        self.__listaCategorias = {"Fruta": ["Figo", "Pera", "Castanha", "Banana", "Morango", "Manga", "Uva", "Kiwi", "Laranja", "Maca"],
                            "Ferramentas": ["Alicate", "Espatula", "Martelo", "Medidor", "Macete", "Aparafusadora", "Pa", "Tesoura", "Serrote", "Machado"],
                            "Livros": ["A Divina Comedia", "Os Lusiadas", "Memorial do Convento", "Mensagem", "A Guarda Branca"],
                            "Roupa": ["Camisola", "Casaco", "T-Shirt", "Calcas", "Saia", "Par de Meias"],
                            "Computadores": ["Acer", "Lenovo", "Dell", "Apple", "ASUS"],
                            "Smartphones": ["Apple", "Oppo", "Xiaomi", "Samsung", "Honor", "Nokia"],
                            "Filmes": ["Capitao Falcao", "Balas e Bolinhos", "Minions", "A Ressaca", "Gaiola Dourada"],
                            "Sapatos": ["Botas", "Sapatilhas", "Salto-Alto", "Chinelos", "Pantufas", "Sandalias"]}
        
        threading.Thread(target=self.criarStock, args=()).start()              
        threading.Thread(target=self.setSocket, args=(porta,)).start()                


    def getEstadoProdutor(self):
        return self.__estadoProdutor
    
    def getListaCategorias(self):
        return self.__listaCategorias
    
    def getListaProdutos(self):
        return self.__listaProdutos
    

    def setSocket(self, porta):                                            
        s = socket.socket()                                               
        s.bind(('', porta))
        print("Socket associado")
        s.listen(5)
        while self.getEstadoProdutor():
            c, addr = s.accept()
            threading.Thread(target=self.ligacaoComMarketplace, args=(c,)).start()


    def ligacaoComMarketplace(self, c):
        try:
            match c.recv(1024).decode():
                case '1':
                    c.send(json.dumps(self.getCategorias()).encode())
                    print("Categorias socket enviadas")
                case '2':
                    c.send(".".encode())
                    categoria = c.recv(1024).decode()
                    c.send(json.dumps(self.getProdutosCategoria(categoria)).encode())
                    print("Produtos socket enviados")
                case '3':
                    c.send(".".encode())
                    produto = c.recv(1024).decode()
                    c.send(".".encode())
                    quantidade = c.recv(1024).decode()
                    c.send(self.comprarProduto(produto, quantidade).encode())
                    print(f"Produto {produto} socket comprado(s)")
        finally:
            return


    def getCategorias(self):
        lista = []
        for produto in self.getListaProdutos():
            if produto["categoria"] not in lista:
                lista.append(produto["categoria"])
        return lista


    def getProdutosCategoria(self, categoria):
        produtos = []
        for produto in self.getListaProdutos():
            if produto["categoria"] == categoria:
                produtos.append(produto)
        return produtos
    

    def comprarProduto(self, produto, quantidade):
        lock.acquire()
        for produtoDaLista in self.getListaProdutos():
            if produtoDaLista["produto"] == produto:
                if int(quantidade) <= produtoDaLista["quantidade"]:
                    produtoDaLista["quantidade"] -= int(quantidade)
                    if produtoDaLista["quantidade"] == 0:
                        self.getListaProdutos().remove(produtoDaLista)
                    lock.release()
                    return "Sucesso: Produtos comprados"
                else:
                    lock.release()
                    return "2: Quantidade indisponivel"
        lock.release()
        return "1: Produto inexistente"


    def produtosNaLista(self):
        listaDeProdutos = []
        for produto in self.getListaProdutos():
            listaDeProdutos.append(produto["produto"])
        return listaDeProdutos

    def criarStock(self):                                                                                  
        while self.getEstadoProdutor():                                                                   
            for categoria, items in self.getListaCategorias().items():                                  
                itemsSelecionados = random.sample(items, random.randint(1, len(items)))
                for produto in itemsSelecionados:
                    if produto in self.produtosNaLista():
                        for prod in self.getListaProdutos():
                            if prod["produto"] == produto:
                                prod["quantidade"] += random.randint(1, 5)
                    else:
                        self.getListaProdutos().append({"produto": produto, "quantidade": random.randint(1, 5), "preco": random.randint(1, 3), "categoria": categoria})
            time.sleep(60)   

lock = threading.RLock()

ProdutorSocket(1026)
ProdutorSocket(1027)