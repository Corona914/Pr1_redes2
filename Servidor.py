import socket
import os
import multiprocessing
from multiprocessing import Lock
import json
import shutil
from datetime import datetime
from fpdf import FPDF

# Configuración del servidor
HOST = '0.0.0.0'
DIRECTORIO = 'ftp_storage'
PRODUCTOS_FILE = 'productos.json'
ARCHIVO_USUARIOS = 'usuarios.txt'

# Crear directorio y archivo de usuarios si no existen
if not os.path.exists(DIRECTORIO):
    os.makedirs(DIRECTORIO)

if not os.path.exists(ARCHIVO_USUARIOS):
    with open(ARCHIVO_USUARIOS, 'w') as f:
        pass

lock = Lock()

# ---------------- Funciones de gestión de usuarios ----------------
def cargar_usuarios():
    """Carga los usuarios del archivo en un diccionario."""
    usuarios = {}
    try:
        with open(ARCHIVO_USUARIOS, 'r') as f:
            for linea in f:
                if ':' in linea:
                    usuario, contraseña = linea.strip().split(':')
                    usuarios[usuario] = contraseña
    except FileNotFoundError:
        pass
    return usuarios


def guardar_usuario(usuario, contraseña):
    """Guarda un nuevo usuario con la protección de lock."""
    usuarios = cargar_usuarios()
    if usuario in usuarios:
        return False
    with lock:
        with open(ARCHIVO_USUARIOS, 'a') as f:
            f.write(f"{usuario}:{contraseña}\n")
    return True


def safe_join(base, *paths):
    """Une rutas y asegura que la ruta final esté dentro de 'base'."""
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(os.path.abspath(base)):
        raise Exception("Acceso fuera del directorio permitido.")
    return final_path


def enviar_archivo(conn, relative_path):
    """Envía un archivo al cliente usando una ruta relativa."""
    try:
        ruta_archivo = safe_join(DIRECTORIO, relative_path)
    except Exception:
        return False

    if not os.path.exists(ruta_archivo) or not os.path.isfile(ruta_archivo):
        return False

    try:
        with open(ruta_archivo, 'rb') as archivo:
            while chunk := archivo.read(1024):
                conn.sendall(chunk)
            conn.sendall(b'EOF')  # Marca de fin de archivo
        return True
    except:
        return False


def recibir_archivo(conn, target_path):
    """Recibe el contenido de un archivo y lo guarda en target_path."""
    try:
        with lock:
            with open(target_path, 'wb') as archivo:
                while True:
                    datos = conn.recv(1024)
                    if not datos:
                        break
                    if datos.endswith(b'EOF'):
                        archivo.write(datos[:-3])
                        break
                    archivo.write(datos)
        return True
    except Exception as e:
        print(f"Error al recibir archivo: {e}")
        return False


# ---------------- Productos de la tienda ----------------
def cargar_productos():
    if not os.path.exists(PRODUCTOS_FILE):
        productos = [
            {"id": 1, "nombre": "Laptop HP Pavilion", "marca": "HP", "tipo": "Computadora", "precio": 12000, "stock": 5},
            {"id": 2, "nombre": "Mouse Logitech MX Master 3", "marca": "Logitech", "tipo": "Accesorio", "precio": 1800, "stock": 20},
            {"id": 3, "nombre": "Monitor Samsung Odyssey G5", "marca": "Samsung", "tipo": "Pantalla", "precio": 7500, "stock": 10},
            {"id": 4, "nombre": "Teclado Redragon Kumara K552", "marca": "Redragon", "tipo": "Accesorio", "precio": 700, "stock": 15},
            {"id": 5, "nombre": "Tablet Lenovo Tab P11", "marca": "Lenovo", "tipo": "Tablet", "precio": 4500, "stock": 8},
            {"id": 6, "nombre": "MacBook Air M3", "marca": "Apple", "tipo": "Computadora", "precio": 24500, "stock": 7},
            {"id": 7, "nombre": "Audifonos Sony WH-1000XM5", "marca": "Sony", "tipo": "Audio", "precio": 6500, "stock": 18},
            {"id": 8, "nombre": "Webcam Logitech C920", "marca": "Logitech", "tipo": "Accesorio", "precio": 1500, "stock": 25},
            {"id": 9, "nombre": "Impresora Epson EcoTank L3250", "marca": "Epson", "tipo": "Impresora", "precio": 4200, "stock": 12},
            {"id": 10, "nombre": "Disco Duro Externo Seagate 2TB", "marca": "Seagate", "tipo": "Almacenamiento", "precio": 1300, "stock": 30},
            {"id": 11, "nombre": "Smartwatch Garmin Forerunner 55", "marca": "Garmin", "tipo": "Accesorio", "precio": 3800, "stock": 9},
            {"id": 12, "nombre": "iPhone 16 Pro", "marca": "Apple", "tipo": "Celular", "precio": 28500, "stock": 10},
            {"id": 13, "nombre": "Tarjeta de Video NVIDIA RTX 4070", "marca": "NVIDIA", "tipo": "Componente PC", "precio": 11500, "stock": 6},
            {"id": 14, "nombre": "Monitor Gamer LG UltraGear 27 pulgadas", "marca": "LG", "tipo": "Pantalla", "precio": 6800, "stock": 11},
            {"id": 15, "nombre": "Bocina Bluetooth JBL Flip 6", "marca": "JBL", "tipo": "Audio", "precio": 2600, "stock": 22},
            {"id": 16, "nombre": "Consola Xbox Series X", "marca": "Microsoft", "tipo": "Consola", "precio": 11000, "stock": 9},
            {"id": 17, "nombre": "SSD Interno Samsung 980 Pro 1TB", "marca": "Samsung", "tipo": "Almacenamiento", "precio": 1900, "stock": 28},
            {"id": 18, "nombre": "Router WiFi 6 TP-Link Archer AX55", "marca": "TP-Link", "tipo": "Accesorio", "precio": 1600, "stock": 15},
            {"id": 19, "nombre": "Drone DJI Mini 3", "marca": "DJI", "tipo": "Dron", "precio": 10500, "stock": 7},
            {"id": 20, "nombre": "Silla Gamer Corsair T3 Rush", "marca": "Corsair", "tipo": "Accesorio", "precio": 5500, "stock": 13}
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
    """Genera un ticket en formato PDF y devuelve los datos del ticket en un diccionario."""
    total = sum(p['precio'] for p in carrito)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ticket_data = {
        "usuario": usuario,
        "fecha": fecha,
        "productos": [{"nombre": p['nombre'], "precio": p['precio']} for p in carrito],
        "total": total
    }

    pdf = FPDF()
    pdf.add_page()

    # Título
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 10, 'Ticket de Compra', 0, 1, 'C')
    pdf.ln(10)

    # Información del cliente
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Usuario: {usuario}", 0, 1, 'L')
    pdf.cell(0, 8, f"Fecha: {fecha}", 0, 1, 'L')
    pdf.ln(5)

    # Encabezado tabla
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(130, 10, 'Producto', 1, 0, 'C')
    pdf.cell(60, 10, 'Precio', 1, 1, 'C')

    # Productos
    pdf.set_font('Arial', '', 12)
    for item in carrito:
        nombre_producto = item['nombre'].encode('latin-1', 'replace').decode('latin-1')
        precio_producto = f"${item['precio']:.2f}"
        pdf.cell(130, 10, nombre_producto, 1, 0)
        pdf.cell(60, 10, precio_producto, 1, 1, 'R')

    # Total
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(130, 12, 'TOTAL', 1, 0, 'R')
    pdf.cell(60, 12, f"${total:.2f}", 1, 1, 'R')

    # Guardar PDF
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_ticket = f"ticket_{usuario}_{timestamp}.pdf"
    pdf.output(nombre_ticket)

    print(f"Ticket generado: {nombre_ticket}")
    return ticket_data


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


# ---------------- Inicio del servidor ----------------
def iniciar_servidor():
    """Inicia el servidor FTP y crea un proceso para cada cliente."""
    while True:
        try:
            puerto = int(input("Ingresa el puerto en el que deseas iniciar el servidor: "))
            if puerto < 1024 or puerto > 65535:
                print("Por favor elige un puerto entre 1024 y 65535.")
                continue
            break
        except ValueError:
            print("Ingresa un número válido para el puerto.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, puerto))
        s.listen()
        print(f"Servidor FTP escuchando en {HOST}:{puerto}...")

        while True:
            conn, addr = s.accept()
            proceso = multiprocessing.Process(
                target=manejar_cliente,
                args=(conn, addr),
                daemon=True
            )
            proceso.start()


if __name__ == "__main__":
    iniciar_servidor()
