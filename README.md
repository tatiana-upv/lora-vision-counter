# lora-vision-counter
Sistema de visión artificial para detección de cambios, reconocimiento de objetos y conteo progresivo con comunicación LoRa.

# LoRa Vision Counter
Embedded vision system for change detection, object recognition, progressive counting, and LoRa communication.

This project detects changes in a scene, recognizes new objects, and counts them progressively. The final count is transmitted remotely using LoRa.

## Features
- Change detection.
- Object recognition.
- Progressive counting.
- LoRa communication.

## How it works
1. The system captures a reference image.
2. New frames are compared against it.
3. A new object increases the counter.
4. The final value is sent through LoRa.
