import socket
import time

# Configuration du serveur
SERVER_IP = "192.168.1.7"  # Modifie si nécessaire
SERVER_PORT = 4444
OBJ_FILE = "lidar_scan.obj"  # Nom de ton fichier OBJ existant

# Connexion au serveur
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))
print("✅ Connecté au serveur.")

# Lecture et envoi du fichier OBJ
with open(OBJ_FILE, "r") as f:
    for line in f:
        if line.startswith("v "):
            client_socket.sendall(line.encode())
            time.sleep(0.01)  # Simule un envoi progressif comme un vrai LIDAR

print("✅ Données envoyées avec succès.")
client_socket.close()
