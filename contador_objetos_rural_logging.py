# contador_objetos_rural - By: tatia - Fri Jul 10 2026
# Edge Impulse - OpenMV FOMO Object Detection Example

import sensor
import time
import ml
from ml.utils import NMS
import math
import image
from lora import *
from time import sleep_ms

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

min_confidence = 0.5
threshold_list = [(math.ceil(min_confidence * 255), 255)]

model = ml.Model("trained")
print(model)

colors = [
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
]

prev_img = None
contador_imagenes = 0
count = 0
counted_objects = []
cesta_vacia = False
cesta_iniciada_con_objetos = False
tolerance_counted_obj = 30
tolerance_new_obj = 70
area_blob = 100
pixels_blob = 100

lora = Lora(band=BAND_EU868, poll_ms=1000, debug=False)
appEui = "00000000000000AA"
appKey = "24D83E922BE80ECD38F85B1FAD696C77"

t0 = time.ticks_ms()

def log_event(msg):
    dt = time.ticks_diff(time.ticks_ms(), t0) / 1000.0
    print("{:.3f}s | {}".format(dt, msg))

def mostrar_estado(texto, x=10, y=10, color=(0, 0, 0), scale=2):
    act_img.draw_string(x, y, texto, color=color, scale=scale)

def enviar_total_lora(total):
    try:
        log_event("send_lora_start total={}".format(total))
        print("Enviando total por LoRa:", total)

        if not lora.get_join_status():
            log_event("lora_join_start")
            print("No unido a la red. Intentando join OTAA...")
            lora.join_OTAA(appEui, appKey, timeout=60000)
            sleep_ms(3000)

        if lora.get_join_status():
            lora.set_port(3)
            payload = "COUNT: {}".format(total)
            print("Payload:", payload, "len:", len(payload))
            log_event("lora_payload {}".format(payload))
            if lora.send_data(payload, False):
                print("Enviado a TTN:", payload)
                log_event("lora_send_ok")
                return True
            else:
                print("No se pudo enviar el total.")
                log_event("lora_send_fail")
                return False
        else:
            print("No unido a la red, no se envía.")
            log_event("lora_not_joined")
            return False
    except Exception as e:
        print("Error LoRa:", e)
        log_event("lora_error {}".format(e))
        return False

def fomo_post_process(model, inputs, outputs):
    n, oh, ow, oc = model.output_shape[0]
    nms = NMS(ow, oh, inputs[0].roi)
    for i in range(oc):
        img = image.Image(outputs[0][0, :, :, i] * 255)
        blobs = img.find_blobs(threshold_list, x_stride=1, area_threshold=1, pixels_threshold=1)
        for b in blobs:
            rect = b.rect()
            x, y, w, h = rect
            score = img.get_statistics(thresholds=threshold_list, roi=rect).l_mean() / 255.0
            nms.add_bounding_box(x, y, x + w, y + h, score, i)
    return nms.get_bounding_boxes()

def already_counted(center_x_obj, center_y_obj, counted_objects):
    for obj_x, obj_y in counted_objects:
        distance = math.sqrt((center_x_obj - obj_x) ** 2 + (center_y_obj - obj_y) ** 2)
        if distance < tolerance_counted_obj:
            print("El objeto ya está contado")
            log_event("already_counted")
            return True
    return False

def new_object(center_x_obj, center_y_obj, center_x_blob, center_y_blob):
    distance = math.sqrt((center_x_obj - center_x_blob) ** 2 + (center_y_obj - center_y_blob) ** 2)
    if distance < tolerance_new_obj:
        print("Es un nuevo objeto")
        log_event("new_object_confirmed")
        return True
    else:
        print("El centro del objeto detectado y el centro del blob NO coinciden")
        log_event("object_blob_mismatch")
        return False

def write_count(count):
    act_img.draw_string(
        10, 210,
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
    act_img.draw_string(
        10, 150,
        "AVISO\nSe han recogido {} huevos.\nEl contador reiniciado".format(count),
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
    print("!!!AVISO!!! Se ha detectado cesta vacía. Reiniciando contador.")
    log_event("cesta_vacia_reboot")
    write_reboot(count)

    if enviar_total_lora(count):
        count = 0
        counted_objects = []
        print("!!!AVISO!!! Se ha reiniciado el contador de objetos")
        log_event("counter_reset")
    else:
        print("!!!AVISO!!! No se reinicia el contador porque LoRa no confirmó el envío")
        log_event("counter_not_reset_lora_failed")

log_event("boot")
print("Firmware:", lora.get_fw_version())
print("Device EUI:", lora.get_device_eui())

prev_img = sensor.snapshot().copy()
print("Imagen inicial capturada. Iniciando monitoreo del nido.")
log_event("initial_reference_captured")
clock = time.clock()

while True:
    detected_objects = []
    clock.tick()
    print("\n--- Nueva iteración ---")
    log_event("loop_start")

    act_img = sensor.snapshot()
    ref_img = act_img.copy()
    log_event("frame_captured")

    difference = act_img.copy().difference(prev_img.copy())
    difference.binary([(20, 255)])
    difference.erode(3)
    difference.dilate(3)
    difference.close(2)

    blobs = difference.find_blobs([(50, 255)], area_threshold=area_blob, pixels_threshold=pixels_blob, merge=True)
    print("Detectando blobs en la imagen de diferencia")
    log_event("blobs_found={}".format(len(blobs)))

    count_blobs = 0
    detections_found = False

    filename1 = f"/diferencia_{contador_imagenes}.jpg"
    filename2 = f"/objeto_{contador_imagenes}.jpg"
    filename3 = f"/imagen_{contador_imagenes}.jpg"

    # difference.save(filename1)
    # act_img.save(filename3)

    if blobs:
        print("Hay cambios en la escena, ejecutando inferencia")
        log_event("running_inference")

        for i, detection_list in enumerate(model.predict([act_img], callback=fomo_post_process)):
            if i == 0:
                continue
            if len(detection_list) == 0:
                continue

            class_name = model.labels[i]

            if class_name == "egg":
                detections_found = True
                print("Clase objetivo detectada: egg")
                log_event("egg_detected")

                for (x, y, w, h), score in detection_list:
                    if score > min_confidence:
                        center_x_obj = math.floor(x + w / 2)
                        center_y_obj = math.floor(y + h / 2)
                        detected_objects.append((center_x_obj, center_y_obj))

        if detections_found:
            cesta_vacia = False
            cesta_iniciada_con_objetos = True
        elif not detections_found and cesta_iniciada_con_objetos and not cesta_vacia:
            reboot_count()
            cesta_vacia = True

    if detected_objects:
        for blob in blobs:
            count_blobs += 1
            aspect_ratio = blob.w() / blob.h()
            if 0.3 < aspect_ratio < 1.7:
                center_x_blob = blob.cx()
                center_y_blob = blob.cy()

                for object in detected_objects:
                    center_x_obj, center_y_obj = object

                    if new_object(center_x_obj, center_y_obj, center_x_blob, center_y_blob):
                        if not already_counted(center_x_obj, center_y_obj, counted_objects):
                            counted_objects.append((center_x_obj, center_y_obj))
                            print("Objetos ya contados anteriormente:", counted_objects)

                            count += 1
                            print("Nuevo huevo detectado. Total de huevos:", count)
                            log_event("object_counted total={}".format(count))

                            write_count(count)

                            act_img.draw_circle((center_x_obj, center_y_obj, 12), color=(0, 0, 0))
                            act_img.draw_string(center_x_obj + 10, center_y_obj - 5, str(count), color=(255, 255, 255), scale=3)
                            act_img.draw_string(center_x_obj + 10 - 1, center_y_obj - 5 - 1, str(count), color=(0, 0, 0), scale=3)
                            act_img.draw_string(center_x_obj + 10 + 1, center_y_obj - 5 + 1, str(count), color=(0, 0, 0), scale=3)
                            act_img.draw_cross(center_x_blob, center_y_blob, size=12, color=(0, 0, 0))

                            # act_img.save(filename2)

                            contador_imagenes += 1

    prev_img = ref_img.copy()
    print("Actualizada la imagen de diferencia")
    log_event("reference_updated")
    time.sleep(15)
