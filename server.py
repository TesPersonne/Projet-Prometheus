import socket
import pygame
import threading
import numpy as np

# Configuration du serveur
HOST = "0.0.0.0"
PORT = 4444
FICHIER_FINAL = "lidar_scan.obj"

# Configuration Pygame
WIDTH, HEIGHT = 1800, 1600
BACKGROUND_COLOR = (0, 0, 0)
POINT_COLOR = (255, 255, 0)
SCALE = 500
FOV = 90

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rendu 3D - Lidar")
all_points = []

# Variables de caméra
camera_pos = np.array([0.0, 0.0, -5.0])
camera_angle = np.array([0.0, 0.0])
SPEED = 0.5
SENSITIVITY = 0.02

running_measurement = False
client_socket = None

def send_command(command):
    """Envoie une commande au client si connecté."""
    if client_socket:
        try:
            client_socket.sendall(command.encode() + b'\n')
            print(f"📡 Commande envoyée : {command}")
        except BrokenPipeError:
            print("⚠ Client déconnecté, impossible d'envoyer la commande.")

"""def handle_client(sock):
    
    global all_points, running_measurement, client_socket
    client_socket = sock
    print("✅ Client connecté")
    
    try:
        with open(FICHIER_FINAL, "w") as f:
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                lines = data.decode().strip().split("\n")
                for line in lines:
                    parts = line.split()
                    if len(parts) == 4 and parts[0] == "v":
                        _, x, y, z = parts
                        f.write(line + "\n")
                        all_points.append(np.array([float(x), float(y), float(z)]))
                    else:
                        print(f"⚠ Ligne ignorée (format invalide) : {line}")
    except Exception as e:
        print(f"❌ Erreur : {e}")
    finally:
        print("❌ Client déconnecté")
        sock.close()
        client_socket = None"""
    
def handle_client(sock):
    global all_points, running_measurement, client_socket
    client_socket = sock
    print("✅ Client connecté")
    
    try:
        with open(FICHIER_FINAL, "w") as f:
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                lines = data.decode().strip().split("\n")
                for line in lines:
                    parts = line.split()
                    if len(parts) == 4 and parts[0] == "v":
                        _, x, y, z = parts
                        x, y, z = float(x), float(y), float(z)

                        # Rotation de 90° vers la droite autour de l'axe Z
                        x_rot = -y #y
                        y_rot =  x #-x

                        f.write(f"v {x_rot} {y_rot} {z}\n")
                        all_points.append(np.array([x_rot, y_rot, z]))
                    else:
                        print(f"⚠ Ligne ignorée (format invalide) : {line}")
    except Exception as e:
        print(f"❌ Erreur : {e}")
    finally:
        print("❌ Client déconnecté")
        sock.close()
        client_socket = None


def start_server():
    """Démarre le serveur TCP."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"🟢 Serveur en écoute sur {HOST}:{PORT}")
    
    while True:
        client, _ = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

def transform_points():
    """Transforme les points pour la caméra."""
    transformed = []
    for point in all_points:
        relative_pos = point - camera_pos
        rot_x = np.array([
            [1, 0, 0],
            [0, np.cos(camera_angle[0]), -np.sin(camera_angle[0])],
            [0, np.sin(camera_angle[0]), np.cos(camera_angle[0])]
        ])
        rot_y = np.array([
            [np.cos(camera_angle[1]), 0, np.sin(camera_angle[1])],
            [0, 1, 0],
            [-np.sin(camera_angle[1]), 0, np.cos(camera_angle[1])]
        ])
        transformed_point = rot_y @ (rot_x @ relative_pos)
        if transformed_point[2] > 0:
            transformed.append(transformed_point)
    return transformed

def display_3d():
    """Affiche les points reçus en 3D avec Pygame et permet de se déplacer."""
    global running_measurement, all_points, camera_pos, camera_angle
    running = True
    clock = pygame.time.Clock()
    
    while running:
        screen.fill(BACKGROUND_COLOR)
        keys = pygame.key.get_pressed()
        
        # Déplacement caméra
        if keys[pygame.K_z]:
            camera_pos[2] += SPEED
        if keys[pygame.K_s]:
            camera_pos[2] -= SPEED
        if keys[pygame.K_q]:
            camera_pos[0] -= SPEED
        if keys[pygame.K_d]:
            camera_pos[0] += SPEED
        if keys[pygame.K_a]:
            camera_pos[1] -= SPEED
        if keys[pygame.K_e]:
            camera_pos[1] += SPEED
        
        transformed_points = transform_points()
        """
        for point in transformed_points:
            x2d = int(WIDTH / 2 + point[0] * SCALE / point[2])
            y2d = int(HEIGHT / 2 - point[1] * SCALE / point[2])
            pygame.draw.circle(screen, POINT_COLOR, (x2d, y2d), 2)
        """
        for point in transformed_points:
    # Vérifie si la coordonnée z est suffisamment grande pour éviter la division par zéro
            if point[2] > 0:
                x2d = int(WIDTH / 2 + point[0] * SCALE / point[2])
                y2d = int(HEIGHT / 2 - point[1] * SCALE / point[2])

                # Vérifie si les coordonnées sont valides
                if 0 <= x2d < WIDTH and 0 <= y2d < HEIGHT:
                    pygame.draw.circle(screen, POINT_COLOR, (x2d, y2d), 2)

        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    running_measurement = not running_measurement
                    if not running_measurement:
                        all_points.clear()
                    send_command("start" if running_measurement else "stop")
        
            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[0]:
                    dx, dy = event.rel
                    camera_angle[1] += dx * SENSITIVITY
                    camera_angle[0] += dy * SENSITIVITY
        
        clock.tick(60)
    
    pygame.quit()

# Lancement des threads
threading.Thread(target=start_server, daemon=True).start()
display_3d()