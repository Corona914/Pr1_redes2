import socket
import json


def enviar(sock, mensaje):
    sock.sendall(mensaje.encode('utf-8'))


def recibir(sock):
    data = sock.recv(4096)
    try:
        return json.loads(data.decode('utf-8'))
    except:
        return data.decode('utf-8')


def registro(sock):
    user = input("Nuevo usuario: ")
    pwd = input("Contraseña: ")
    enviar(sock, f"REGISTRO {user} {pwd}")
    print(">>", recibir(sock))


def login(sock):
    user = input("Usuario: ")
    pwd = input("Contraseña: ")
    enviar(sock, f"LOGIN {user} {pwd}")
    resp = recibir(sock)
    print(">>", resp)
    return resp == "AUTENTIFICACION_EXITOSA"


def buscar(sock):
    termino = input("Buscar por nombre o marca: ")
    enviar(sock, f"BUSCAR {termino}")
    resp = recibir(sock)
    if isinstance(resp, list):
        for p in resp:
            print(f"[{p['id']}] {p['nombre']} - {p['marca']} - ${p['precio']} (stock {p['stock']})")
    else:
        print(resp)


def listar(sock):
    tipo = input("Tipo de producto (Computadora, Accesorio, Pantalla, Tablet, Audio, Impresora, "
                 "Almacenamiento, Componente PC, Consola): ")
    enviar(sock, f"LISTAR {tipo}")
    resp = recibir(sock)
    if isinstance(resp, list):
        for p in resp:
            print(f"[{p['id']}] {p['nombre']} - {p['marca']} - ${p['precio']} (stock {p['stock']})")
    else:
        print(resp)


def agregar(sock):
    pid = input("ID del producto a agregar: ")
    enviar(sock, f"AGREGAR {pid}")
    print(">>", recibir(sock))


def eliminar(sock):
    pid = input("ID del producto a eliminar del carrito: ")
    enviar(sock, f"ELIMINAR {pid}")
    print(">>", recibir(sock))


def ver_carrito(sock):
    enviar(sock, "CARRITO")
    resp = recibir(sock)
    if isinstance(resp, list) and resp:
        total = sum(p['precio'] for p in resp)
        for p in resp:
            print(f"[{p['id']}] {p['nombre']} - ${p['precio']}")
        print(f"Total: ${total}")
    else:
        print("Carrito vacío.")


def finalizar(sock):
    enviar(sock, "FINALIZAR")
    resp = recibir(sock)
    if isinstance(resp, dict):
        print("\n--- TICKET ---")
        print(f"Usuario: {resp['usuario']}")
        print(f"Fecha: {resp['fecha']}")
        print("Productos:")
        for p in resp['productos']:
            print(f" - {p['nombre']} - ${p['precio']}")
        print(f"Total: ${resp['total']}\n")
    else:
        print(resp)

def mostrar_todos(sock):
    enviar(sock, "MOSTRAR_TODOS")
    resp = recibir(sock)
    if isinstance(resp, list):
        print("\n--- TODOS LOS PRODUCTOS DISPONIBLES ---")
        for p in resp:
            print(f"[{p['id']}] {p['nombre']} - {p['marca']} - {p['tipo']} - ${p['precio']} (stock {p['stock']})")
    else:
        print(resp)


def main():
    host = input("IP del servidor: ")
    port = int(input("Puerto del servidor: "))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        print("Conectado al servidor de tienda.")

        # Autenticación
        while True:
            print("\n1. Registrarse")
            print("2. Iniciar sesión")
            op = input("> ")
            if op == "1":
                registro(sock)
            elif op == "2":
                if login(sock):
                    break
            else:
                print("Opción inválida")

        # Menú principal
        # Menú principal
        while True:
            print("\n--- MENÚ ---")
            print("1. Buscar producto")
            print("2. Listar por tipo")
            print("3. Agregar al carrito")
            print("4. Ver carrito")
            print("5. Eliminar del carrito")
            print("6. Finalizar compra")
            print("7. Salir")
            print("8. Mostrar todos los productos")  # 🔹 Nueva opción

            op = input("> ")
            if op == "1":
                buscar(sock)
            elif op == "2":
                listar(sock)
            elif op == "3":
                agregar(sock)
            elif op == "4":
                ver_carrito(sock)
            elif op == "5":
                eliminar(sock)
            elif op == "6":
                finalizar(sock)
            elif op == "7":
                enviar(sock, "EXIT")
                print(recibir(sock))
                break
            elif op == "8":
                mostrar_todos(sock)  # 🔹 Llama la nueva función
            else:
                print("Opción inválida.")


if __name__ == "__main__":
    main()
