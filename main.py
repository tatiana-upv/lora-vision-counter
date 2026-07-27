# contador_objetos_rural - By: tatia - Fri Jul 10 2026
# Edge Impulse - OpenMV FOMO Object Detection Example
#
# This work is licensed under the MIT license.
# Copyright (c) 2013-2024 OpenMV LLC. All rights reserved.
# [https://github.com/openmv/openmv/blob/master/LICENSE](https://github.com/openmv/openmv/blob/master/LICENSE)

import sensor
import time
import ml
from ml.utils import NMS
import math
import image
import sys
import machine
import os
import pyb

from lora import *
from time import sleep_ms

# Inicialización de la cámara y configuración básica de captura.
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

# Umbral mínimo de confianza para aceptar una detección como válida.
# El valor se convierte a escala 0..255 porque FOMO trabaja con imágenes postprocesadas en ese rango.
min_confidence = 0.5
threshold_list = [(math.ceil(min_confidence * 255), 255)]

# Carga del modelo entrenado con Edge Impulse.
# Este modelo se usa para localizar el objeto de interés en cada captura.
model = ml.Model("trained")
print(model)

# Colores de apoyo para anotación visual sobre la imagen.
# No afectan al algoritmo; solo sirven para depuración y visualización.
colors = [
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
]

# Imagen de referencia para calcular diferencias entre capturas consecutivas.
# Esta estrategia permite detectar cambios relevantes en la escena y reduce falsas alarmas.
prev_img = None

# Contador auxiliar para generar nombres únicos de archivos cuando se guardan imágenes.
# Sirve para la depuración y el desarollo del proyecto. Se comenta después.
contador_imagenes = 0

# Contador principal de objetos detectados.
count = 0

# Lista de centros ya contabilizados.
# Evita doble conteo de un mismo objeto cuando persiste varias iteraciones.
counted_objects = []

# Condición de la cesta vacía.
# Se utiliza para reiniciar el contador y enviar datos as servidor solo cuando la cesta
# haya sido vaciada.
cesta_vacia = False

#Condición de la cesta iniciada con objetos.
#Sirve para no reiniciar el contador con la cesta vacia al inicio del conteo.
cesta_iniciada_con_objetos = False

# Tolerancias y parámetros empíricos ajustados durante la validación experimental.
# Se utilizan para robustecer el conteo frente a pequeñas variaciones de posición y segmentación.
tolerance_counted_obj = 30
tolerance_new_obj = 70
area_blob = 100
pixels_blob = 100

# Inicialización del módulo LoRa en banda europea.
# El objetivo es enviar a TTN el total acumulado cuando el sistema detecta que la cesta queda vacío.
lora = Lora(band=BAND_EU868, poll_ms=1000, debug=False)
appEui = "00000000000000AA"
appKey = "24D83E922BE80ECD38F85B1FAD696C77"

print("Firmware:", lora.get_fw_version())
print("Device EUI:", lora.get_device_eui())

def enviar_total_lora(total):
    # Envía por LoRa el total acumulado justo antes de reiniciar el contador.
    # Si el dispositivo no está unido, intenta el join OTAA de nuevo.
    try:
        if not lora.get_join_status():
            lora.join_OTAA(appEui, appKey, timeout=60000)
            # Pequeña espera para dar margen a la estabilización del enlace tras el join.
            sleep_ms(3000)

        if lora.get_join_status():
            # FPort 3 se usa como puerto de aplicación para transportar el payload.
            lora.set_port(3)
            payload = "COUNT: " + str(total)
            print("Payload:", payload, "len:", len(payload))
            if lora.send_data(payload, False):
                print("Enviado a TTN:", payload)
            else:
                print("No se pudo enviar el total.")
        else:
            print("No unido a la red, no se envía.")
    except Exception as e:
        print("Error LoRa:", e)

# contador_objetos_rural - By: tatia - Fri Jul 10 2026
# Edge Impulse - OpenMV FOMO Object Detection Example
#
# This work is licensed under the MIT license.
# Copyright (c) 2013-2024 OpenMV LLC. All rights reserved.
# [https://github.com/openmv/openmv/blob/master/LICENSE](https://github.com/openmv/openmv/blob/master/LICENSE)

import sensor
import time
import ml
from ml.utils import NMS
import math
import image
import sys
import machine
import os
import pyb

from lora import *
from time import sleep_ms

# Inicialización de la cámara y configuración básica de captura.
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

# Umbral mínimo de confianza para aceptar una detección como válida.
# El valor se convierte a escala 0..255 porque FOMO trabaja con imágenes postprocesadas en ese rango.
min_confidence = 0.5
threshold_list = [(math.ceil(min_confidence * 255), 255)]

# Carga del modelo entrenado con Edge Impulse.
# Este modelo se usa para localizar el objeto de interés en cada captura.
model = ml.Model("trained")
print(model)

# Colores de apoyo para anotación visual sobre la imagen.
# No afectan al algoritmo; solo sirven para depuración y visualización.
colors = [
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
]

# Imagen de referencia para calcular diferencias entre capturas consecutivas.
# Esta estrategia permite detectar cambios relevantes en la escena y reduce falsas alarmas.
prev_img = None

# Contador auxiliar para generar nombres únicos de archivos cuando se guardan imágenes.
# Sirve para la depuración y el desarollo del proyecto. Se comenta después.
contador_imagenes = 0

# Contador principal de objetos detectados.
count = 0

# Lista de centros ya contabilizados.
# Evita doble conteo de un mismo objeto cuando persiste varias iteraciones.
counted_objects = []

# Condición de la cesta vacía.
# Se utiliza para reiniciar el contador y enviar datos as servidor solo cuando la cesta
# haya sido vaciada.
cesta_vacia = False

#Condición de la cesta iniciada con objetos.
#Sirve para no reiniciar el contador con la cesta vacia al inicio del conteo.
cesta_iniciada_con_objetos = False

# Tolerancias y parámetros empíricos ajustados durante la validación experimental.
# Se utilizan para robustecer el conteo frente a pequeñas variaciones de posición y segmentación.
tolerance_counted_obj = 30
tolerance_new_obj = 70
area_blob = 100
pixels_blob = 100

# Inicialización del módulo LoRa en banda europea.
# El objetivo es enviar a TTN el total acumulado cuando el sistema detecta que la cesta queda vacío.
lora = Lora(band=BAND_EU868, poll_ms=1000, debug=False)
appEui = "00000000000000AA"
appKey = "24D83E922BE80ECD38F85B1FAD696C77"

print("Firmware:", lora.get_fw_version())
print("Device EUI:", lora.get_device_eui())

def enviar_total_lora(total):
    # Envía por LoRa el total acumulado justo antes de reiniciar el contador.
    # Si el dispositivo no está unido, intenta el join OTAA de nuevo.
    # Devuelve True si el envío fue exitoso, False en caso contrario.
    try:
        if not lora.get_join_status():
            lora.join_OTAA(appEui, appKey, timeout=60000)
            # Pequeña espera para dar margen a la estabilización del enlace tras el join.
            sleep_ms(3000)

        if lora.get_join_status():
            # FPort 3 se usa como puerto de aplicación para transportar el payload.
            lora.set_port(3)
            payload = "COUNT: " + str(total)
            print("Payload:", payload, "len:", len(payload))
            if lora.send_data(payload, False):
                print("Enviado a TTN:", payload)
                return True
            else:
                print("No se pudo enviar el total.")
                return False
        else:
            print("No unido a la red, no se envía.")
            return False
    except Exception as e:
        print("Error LoRa:", e)
        return False

def fomo_post_process(model, inputs, outputs):
    # Postprocesado específico de FOMO:
    # convierte la salida de la red en candidatos geométricos y aplica NMS
    # para suprimir solapamientos entre detecciones.
    n, oh, ow, oc = model.output_shape[0]
    nms = NMS(ow, oh, inputs[0].roi)
    for i in range(oc):
        img = image.Image(outputs[0][0, :, :, i] * 255)
        blobs = img.find_blobs(
            threshold_list, x_stride=1, area_threshold=1, pixels_threshold=1
        )
        for b in blobs:
            rect = b.rect()
            x, y, w, h = rect
            score = (
                img.get_statistics(thresholds=threshold_list, roi=rect).l_mean() / 255.0
            )
            nms.add_bounding_box(x, y, x + w, y + h, score, i)
    return nms.get_bounding_boxes()

def already_counted(center_x_obj, center_y_obj, counted_objects):
    # Filtrado espacial para evitar volver a contar un objeto ya registrado.
    # Se compara la distancia al resto de centros previamente contabilizados.
    for obj_x, obj_y in counted_objects:
        distance = math.sqrt((center_x_obj - obj_x) ** 2 + (center_y_obj - obj_y) ** 2)
        if distance < tolerance_counted_obj:
            print("El objeto ya está contado")
            return True
    return False

def new_object(center_x_obj, center_y_obj, center_x_blob, center_y_blob):
    # Verifica coherencia geométrica entre la detección de la red neuronal
    # y el blob extraído por diferencia de imágenes.
    distance = math.sqrt((center_x_obj - center_x_blob) ** 2 + (center_y_obj - center_y_blob) ** 2)
    if distance < tolerance_new_obj:
        print("Es un nuevo objeto")
        return True
    else:
        print("El centro del objeto detectado y el centro del blob NO coinciden")
        return False

def write_count(count):
    # Superpone el contador actual sobre la imagen capturada.
    # Útil para depuración y demostración del funcionamiento.
    act_img.draw_string(
        10,
        210,
        "Cantidad de objetos es " + str(count),
        color=(0, 0, 0),
        scale=3,
        mono_space=False,
        char_rotation=0,
        char_hmirror=False,
        char_vflip=False,
        string_rotation=0,
        string_hmirror=False,
        string_vflip=False,
    )

def write_reboot(count):
    # Mensaje visual de aviso cuando se detecta que la escena queda vacía
    # y el contador va a reiniciarse tras reportar el total.
    act_img.draw_string(
        10,
        150,
        f"AVISO\nSe han recogido {count} huevos.\nEl contador reiniciado",
        color=(0, 0, 0),
        scale=3,
        mono_space=False,
        char_rotation=0,
        char_hmirror=False,
        char_vflip=False,
        string_rotation=0,
        string_hmirror=False,
        string_vflip=False,
    )

def reboot_count():
    global count, counted_objects
    # El total se transmite antes de poner el contador a cero.
    # Esto conserva el valor real acumulado en la iteración anterior.
    write_reboot(count)
    # Solo se reinicia el contador si el envío LoRa fue exitoso.
    if enviar_total_lora(count):
        count = 0
        counted_objects = []
        print("!!!AVISO!!! Se ha reiniciado el contador de objetos")
    else:
        print("!!!AVISO!!! No se reinicia el contador porque LoRa falló")

# Captura inicial usada como referencia para la primera resta de imágenes.
# A partir de aquí, el sistema compara cada frame con el anterior.
prev_img = sensor.snapshot().copy()
print("Imagen inicial capturada. Iniciando monitoreo del nido.")
clock = time.clock()

while True:
    # Lista temporal con las detecciones válidas de la iteración actual.
    detected_objects = []
    clock.tick()

    # Captura de la imagen actual y copia auxiliar para anotaciones.
    act_img = sensor.snapshot()
    ref_img = act_img.copy()

    # Diferencia entre el frame actual y el de referencia.
    # Esta operación resalta cambios en la escena que pueden indicar movimiento o aparición de un objeto.
    difference = act_img.copy().difference(prev_img.copy())

    # Binarización y filtrado morfológico para eliminar ruido y unir regiones relevantes.
    difference.binary([(20, 255)])
    difference.erode(3)
    difference.dilate(3)
    difference.close(2)

    # Segmentación de blobs en la imagen de diferencia.
    # Los parámetros de área y píxeles minimizan detecciones erroneas.
    blobs = difference.find_blobs([(50, 255)], area_threshold=area_blob, pixels_threshold=pixels_blob, merge=True)
    print("Detectando blobs en la imagen de diferencia")

    count_blobs = 0
    detections_found = False

    # Nombres de archivo usados para guardar evidencias durante la fase de pruebas.
    # Se comentan en la versión final.
    filename1 = f"/diferencia_{contador_imagenes}.jpg"
    filename2 = f"/objeto_{contador_imagenes}.jpg"
    filename3 = f"/imagen_{contador_imagenes}.jpg"

    #difference.save(filename1)
    #act_img.save(filename3)

    # Si existen cambios en la escena, se ejecuta la inferencia para confirmar la clase detectada.
    if blobs:
        for i, detection_list in enumerate(model.predict([act_img], callback=fomo_post_process)):
            if i == 0:
                continue
            if len(detection_list) == 0:
                continue

            class_name = model.labels[i]

            # Solo interesa la clase objetivo del proyecto.
            # Esto reduce la complejidad de la lógica posterior y evita contar objetos no relevantes.
            if class_name == "egg":
                detections_found = True
                for (x, y, w, h), score in detection_list:
                    if score > min_confidence:
                        center_x_obj = math.floor(x + w / 2)
                        center_y_obj = math.floor(y + h / 2)
                        detected_objects.append((center_x_obj, center_y_obj))

        # Si hay cambio pero no se confirma ninguna detección válida, se interpreta como escena vacía.
        if detections_found:
            cesta_vacia = False
            cesta_iniciada_con_objetos = True
        elif not detections_found and cesta_iniciada_con_objetos and not cesta_vacia:
            reboot_count()
            cesta_vacia = True

    # La comparación blob/detección se usa como validación cruzada para reducir falsos positivos.
    if detected_objects:
        for blob in blobs:
            count_blobs += 1
            aspect_ratio = blob.w() / blob.h()
            if 0.3 < aspect_ratio < 1.7:
                center_x_blob = blob.cx()
                center_y_blob = blob.cy()

                for object in detected_objects:
                    center_x_obj, center_y_obj = object

                    # Se exige coherencia espacial entre ambos métodos de detección:
                    # red neuronal y análisis por diferencia de imágenes.
                    if new_object(center_x_obj, center_y_obj, center_x_blob, center_y_blob):
                        if not already_counted(center_x_obj, center_y_obj, counted_objects):
                            counted_objects.append((center_x_obj, center_y_obj))
                            print("Objetos ya contados anteriormente:", counted_objects)

                            # Conteo efectivo del nuevo objeto.
                            count += 1
                            print(f"Nuevo huevo detectado. Total de huevos: {count}")
                            write_count(count)
                            act_img.draw_circle((center_x_obj, center_y_obj, 12), color=(0, 0, 0))
                            act_img.draw_string(center_x_obj + 10, center_y_obj - 5, str(count), color=(255, 255, 255), scale=3)
                            act_img.draw_string(center_x_obj + 10 - 1, center_y_obj - 5 - 1, str(count), color=(0, 0, 0), scale=3)
                            act_img.draw_string(center_x_obj + 10 + 1, center_y_obj - 5 + 1, str(count), color=(0, 0, 0), scale=3)
                            act_img.draw_cross(center_x_blob, center_y_blob, size=12, color=(0, 0, 0))

                            # Guardado de la imagen ya anotada para trazabilidad de pruebas.
                            # Se comenta en la versión final.
                            #act_img.save(filename2)

                            contador_imagenes += 1

    # La imagen de referencia para la siguiente iteración se actualiza sin anotaciones.
    # Así se evita que el texto o dibujos superpuestos interfieran en la diferencia de frames.
    prev_img = ref_img.copy()
    print("Actualizada la imagen de diferencia")
    time.sleep(5)
