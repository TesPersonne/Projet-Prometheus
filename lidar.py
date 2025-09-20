import numpy as np
import serial
import struct
import socket
from enum import Enum

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
SERIAL_PORT = "/dev/ttyUSB0"
SERVER_IP = "REDACTED"
SERVER_PORT = 4444
MEASUREMENTS_PER_PLOT = 480
MEASUREMENT_LENGTH = 12
MESSAGE_FORMAT = "<xBHH" + "HB" * MEASUREMENT_LENGTH + "HHB"
PACKET_LENGTH = 47

State = Enum("State", ["SYNC0", "SYNC1", "SYNC2", "LOCKED", "UPDATE_PLOT"])

# Connexion au serveur
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))
print("✅ Connecté au serveur.")

# Connexion au LIDAR
lidar_serial = serial.Serial(SERIAL_PORT, 230400, timeout=0.5)
z_position = 0.0
scan_data = []
state = State.SYNC0
measurements = []

def parse_lidar_data(data):
    length, speed, start_angle, *pos_data, stop_angle, timestamp, crc = struct.unpack(MESSAGE_FORMAT, data)
    start_angle = float(start_angle) / 100.0
    stop_angle = float(stop_angle) / 100.0
    if stop_angle < start_angle:
        stop_angle += 360.0
    step_size = (stop_angle - start_angle) / (MEASUREMENT_LENGTH - 1)
    angle = [start_angle + step_size * i for i in range(0, MEASUREMENT_LENGTH)]
    distance = pos_data[0::2]
    confidence = pos_data[1::2]
    return list(zip(angle, distance, confidence))

def get_xyz_data(measurements, z):
    angle = np.radians([m[0] for m in measurements])
    distance = np.array([m[1] for m in measurements]) / 1000.0
    x = np.sin(angle) * distance
    y = np.cos(angle) * distance
    z = np.full_like(x, z)
    return x, y, z

running = True

while running:
    if state == State.SYNC0:
        data = b''
        measurements = []
        if lidar_serial.read() == b'\x54':
            data = b'\x54'
            state = State.SYNC1
    elif state == State.SYNC1:
        if lidar_serial.read() == b'\x2C':
            state = State.SYNC2
            data += b'\x2C'
        else:
            state = State.SYNC0
    elif state == State.SYNC2:
        data += lidar_serial.read(PACKET_LENGTH - 2)
        if len(data) != PACKET_LENGTH:
            state = State.SYNC0
            continue
        measurements += parse_lidar_data(data)
        state = State.LOCKED
    elif state == State.LOCKED:
        data = lidar_serial.read(PACKET_LENGTH)
        if data[0] != 0x54 or len(data) != PACKET_LENGTH:
            print("WARNING: Serial sync lost")
            state = State.SYNC0
            continue
        measurements += parse_lidar_data(data)
        if len(measurements) > MEASUREMENTS_PER_PLOT:
            state = State.UPDATE_PLOT
    elif state == State.UPDATE_PLOT:
        x, y, z = get_xyz_data(measurements, z_position)
        for i in range(len(x)):
            client_socket.sendall(f"v {x[i]} {y[i]} {z[i]}\n".encode())
        z_position += 0.1  # Simulation du mouvement vertical
        state = State.LOCKED
        measurements = []