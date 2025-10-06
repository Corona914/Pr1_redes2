import socket
import os
import json
import multiprocessing
from multiprocessing import Lock
from datetime import datetime

# ---------------- CONFIGURACIÓN ----------------
HOST = '0.0.0.0'
PRODUCTOS_FILE = 'productos.json'
USUARIOS_FILE = 'usuarios.txt'

lock = Lock()

# ---------------- FUNCIONES DE ARCHIVOS ----------------
def cargar_usuarios():
    usuarios = {}
    if not os.path.exists(USUARIOS_FILE):
        return usuarios
    with open(USUARIOS_FILE, 'r') as f:
        for linea in f:
            if ':' in linea:
                usuario, contraseña = linea.strip().split(':')
                usuarios[usuario] = contraseña
    return usuarios

def guardar_usuario(usuario, contraseña):
    usuarios = cargar_usuarios()
    if usuario in usuarios:
        return False
    with lock:
        with open(USUARIOS_FILE, 'a') as f:
            f.write(f"{usuario}:{contraseña}\n")
    return True

def cargar_productos():
    if not os.path.exists(PRODUCTOS_FILE):
        productos = [
            {"id": 1, "nombre": "Laptop HP", "marca": "HP", "tipo": "Computadora", "precio": 12000, "stock": 5},
            {"id": 2, "nombre": "Mouse Logitech", "marca": "Logitech", "tipo": "Accesorio", "precio": 350, "stock": 20},
            {"id": 3, "nombre": "Monitor Samsung", "marca": "Samsung", "tipo": "Pantalla", "precio": 3000, "stock": 10},
            {"id": 4, "nombre": "Teclado Redragon", "marca": "Redragon", "tipo": "Accesorio", "precio": 700, "stock": 15},
            {"id": 5, "nombre": "Tablet Lenovo", "marca": "Lenovo", "tipo": "Tablet", "precio": 4500, "stock": 8}
        ]
        guardar_productos(productos)
    else:
        with open(PRODUCTOS_FILE, 'r') as f:
            productos = json.load(f)
    return productos

def guardar_productos(productos):
    with lock:
        with open(PRODUCTOS_FILE, 'w') as f:
            json.dump(productos, f, indent=4)

# ---------------- FUNCIONES DE TIENDA ----------------
def buscar_producto(termino):
    productos = cargar_productos()
    return [p for p in productos if termino.lower() in p['nombre'].lower() or termino.lower() in p['marca'].lower()]

def listar_por_tipo(tipo):
    productos = cargar_productos()
    return [p for p in productos if tipo.lower() == p['tipo'].lower()]

def agregar_al_carrito(carrito, producto_id):
    productos = cargar_productos()
    for p in productos:
        if p['id'] == producto_id:
            if p['stock'] <= 0:
                return "SIN_EXISTENCIAS"
            p['stock'] -= 1
            carrito.append(p)
            guardar_productos(productos)
            return "AGREGADO"
    return "NO_ENCONTRADO"

def eliminar_del_carrito(carrito, producto_id):
    for i, p in enumerate(carrito):
        if p['id'] == producto_id:
            carrito.pop(i)
            productos = cargar_productos()
            for prod in productos:
                if prod['id'] == producto_id:
                    prod['stock'] += 1
                    guardar_productos(productos)
                    break
            return "ELIMINADO"
    return "NO_ENCONTRADO"

def generar_ticket(carrito, usuario):
    total = sum(p['precio'] for p in carrito)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ticket = {
        "usuario": usuario,
        "fecha": fecha,
        "productos": [{"nombre": p['nombre'], "precio": p['precio']} for p in carrito],
        "total": total
    }
    nombre_ticket = f"ticket_{usuario}_{datetime.now().strftime('%H%M%S')}.json"
    with open(nombre_ticket, 'w') as f:
        json.dump(ticket, f, indent=4)
    return ticket

# ---------------- MANEJO DE CLIENTES ----------------
def manejar_cliente(conn, addr):
    carrito = []
    usuario_actual = None
    try:
        with conn:
            print(f"Conexión establecida con {addr}")

            while True:
                solicitud = conn.recv(4096).decode('utf-8')
                if not solicitud:
                    break

                partes = solicitud.strip().split(' ')
                comando = partes[0].upper()

                # ---------- REGISTRO / LOGIN ----------
                if comando == "REGISTRO":
                    _, user, pwd = partes
                    if guardar_usuario(user, pwd):
                        conn.sendall(b'REGISTRO_EXITOSO')
                    else:
                        conn.sendall(b'USUARIO_YA_EXISTE')

                elif comando == "LOGIN":
                    _, user, pwd = partes
                    usuarios = cargar_usuarios()
                    if user in usuarios and usuarios[user] == pwd:
                        usuario_actual = user
                        conn.sendall(b'AUTENTIFICACION_EXITOSA')
                    else:
                        conn.sendall(b'AUTENTIFICACION_FALLIDA')

                # ---------- BÚSQUEDA ----------
                elif comando == "BUSCAR":
                    termino = " ".join(partes[1:])
                    resultado = buscar_producto(termino)
                    conn.sendall(json.dumps(resultado).encode())

                # ---------- LISTAR ----------
                elif comando == "LISTAR":
                    tipo = " ".join(partes[1:])
                    resultado = listar_por_tipo(tipo)
                    conn.sendall(json.dumps(resultado).encode())

                # ---------- AGREGAR AL CARRITO ----------
                elif comando == "AGREGAR":
                    try:
                        producto_id = int(partes[1])
                        res = agregar_al_carrito(carrito, producto_id)
                        conn.sendall(res.encode())
                    except:
                        conn.sendall(b'ERROR_FORMATO')

                # ---------- ELIMINAR DEL CARRITO ----------
                elif comando == "ELIMINAR":
                    try:
                        producto_id = int(partes[1])
                        res = eliminar_del_carrito(carrito, producto_id)
                        conn.sendall(res.encode())
                    except:
                        conn.sendall(b'ERROR_FORMATO')

                # ---------- MOSTRAR CARRITO ----------
                elif comando == "CARRITO":
                    conn.sendall(json.dumps(carrito).encode())

                # ---------- FINALIZAR COMPRA ----------
                elif comando == "FINALIZAR":
                    if not carrito:
                        conn.sendall(b'CARRITO_VACIO')
                    else:
                        ticket = generar_ticket(carrito, usuario_actual or "anonimo")
                        carrito.clear()
                        conn.sendall(json.dumps(ticket).encode())

                elif comando == "EXIT":
                    conn.sendall(b'DESCONECTADO')
                    break

                else:
                    conn.sendall(b'COMANDO_NO_RECONOCIDO')

    except Exception as e:
        print(f"Error con cliente {addr}: {e}")
    finally:
        print(f"Conexión con {addr} cerrada")

# ---------------- INICIO DEL SERVIDOR ----------------
def iniciar_servidor():
    puerto = int(input("Ingresa el puerto en el que deseas iniciar el servidor: "))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, puerto))
        s.listen()
        print(f"Servidor de tienda escuchando en {HOST}:{puerto}")
        while True:
            conn, addr = s.accept()
            proceso = multiprocessing.Process(target=manejar_cliente, args=(conn, addr), daemon=True)
            proceso.start()

if __name__ == "__main__":
    iniciar_servidor()
