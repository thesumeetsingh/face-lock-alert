import base64
import binascii
import os
import tempfile

import cv2
import numpy as np

from db import get_face_model, save_face_data

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def decode_image(data_url):
    if not data_url or "," not in data_url:
        raise ValueError("Invalid image data.")

    try:
        encoded = data_url.split(",", 1)[1]
        raw = base64.b64decode(encoded)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Could not decode image.") from exc

    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not read captured image.")

    return image


def extract_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        return None

    x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
    face = gray[y : y + height, x : x + width]

    if face.size == 0:
        return None

    return cv2.resize(face, (200, 200), interpolation=cv2.INTER_AREA)


def _encode_face(face):
    ok, encoded = cv2.imencode(".jpg", face, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise ValueError("Could not encode a captured face image.")
    return encoded.tobytes()


def _model_to_blob(model):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as temp_file:
            temp_path = temp_file.name
        model.write(temp_path)
        with open(temp_path, "rb") as model_file:
            return model_file.read()
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def _model_from_blob(model_blob):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(model_blob)
        model = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8,
        )
        model.read(temp_path)
        return model
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def train_user_model(user_id, images, saved_at):
    valid_faces = []
    face_blobs = []

    for image in images:
        face = extract_face(image)
        if face is None:
            continue
        valid_faces.append(face)
        face_blobs.append(_encode_face(face))

    if len(valid_faces) < 10:
        return 0

    model = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=8,
        grid_y=8,
    )
    labels = np.ones(len(valid_faces), dtype=np.int32)
    model.train(valid_faces, labels)
    model_blob = _model_to_blob(model)

    save_face_data(user_id, face_blobs, model_blob, saved_at)
    return len(valid_faces)


def verify_face(user_id, image, threshold):
    model_blob = get_face_model(user_id)
    if not model_blob:
        return False, None

    face = extract_face(image)
    if face is None:
        return False, None

    model = _model_from_blob(model_blob)
    _, confidence = model.predict(face)
    return confidence <= threshold, float(confidence)
