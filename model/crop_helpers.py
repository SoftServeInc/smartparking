""" Module for cropping input images according to parking configuration.
"""
import os
import cv2
import shutil
import numpy as np


clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
MEANS = [0.485, 0.456, 0.406]
STDS = [0.229, 0.224, 0.225]
WIDTH = 128
HEIGHT = 128


def verify_conf(conf):
    """ Verify parking configuration.

    :param conf: parking configuration json
    :raise ValueError: in case parking configuration is incorrect
    """
    slot_ids = [a['id'] for a in conf[0]['annotations']]
    seen = set()
    duplicates = [i for i in slot_ids if i in seen or seen.add(i)]
    if duplicates:
        raise ValueError(
            'Parking configuration contains duplicate slot ID(s): {}'
            .format(', '.join(duplicates)))

    for polygon in conf[0]['annotations']:
        slot_id = int(polygon['id'])
        points = _get_points(polygon['xn'], polygon['yn'])
        if points.shape[0] != 4 or points.shape[1] != 2:
            raise ValueError(
                'Polygon shape for slot ID {} should be (4, 2), '
                'but actually is: {}'.format(slot_id, points.shape))


def create_output_folder(output_folder, conf):
    """ Create output folder including subfolders for each model.

    :param output_folder: path to the output folder
    :param conf: parking configuration json
    """
    models = {a['model'] for a in conf[0]['annotations']}
    for model in models:
        os.makedirs(os.path.join(output_folder, model.replace(' ', '_')),
                    exist_ok=True)


def remove_output_folder(output_folder):
    """ Remove output folder.

    :param output_folder: path to the output folder
    """
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)


def map_models_to_ids(conf):
    """ Links models and parking lot ids

    :param conf: parking configuration json
    :return: models_to_ids: dict of model names and appropriate ids
    """
    models_to_ids = {}

    for a in conf[0]['annotations']:
        model_name = a['model']

        if model_name not in models_to_ids:
            models_to_ids[model_name] = []

        models_to_ids[model_name].append(a['id'])

    return models_to_ids


def extract_and_save(input_file, output_folder, conf, keep_file_name=True):
    """ Extract and save cropped images.
    :param input_file: path to input image file
    :param output_folder: path to the output folder
    :param conf: parking configuration json
    :param keep_file_name: keep original file name for cropped images
    """
    img = cv2.imread(input_file)
    img = _apply_clahe(img)

    for polygon in conf[0]['annotations']:
        slot_id = int(polygon['id'])
        model = polygon['model'].replace(' ', '_')
        points = _get_points(polygon['xn'], polygon['yn'])
        warped_img = _four_points_transform(img, points)
        if keep_file_name:
            output_file = '{}_{}.png'.format(
                '.'.join(os.path.basename(input_file).split('.')[:-1]),
                slot_id)
        else:
            output_file = '{}.png'.format(slot_id)
        cv2.imwrite(
            os.path.join(
                output_folder,
                model,
                output_file),
            warped_img)


def preprocess_input(img):
    img = cv2.resize(img, (WIDTH, HEIGHT))
    img_norm = img / 255
    img_norm = (img_norm - MEANS) / STDS

    return np.expand_dims(img_norm, axis=0)


def collect_input(input_file, conf):
    """ Collects images for a specific model

    :param input_file: path to input image file
    :param conf: parking configuration json
    :param models_to_tensors: dict of model names mapped to corresponding tensors
    """
    models_to_tensors = {}
    img = cv2.imread(input_file)
    img = _apply_clahe(img)

    for polygon in conf[0]['annotations']:
        model_name = polygon['model']
        points = _get_points(polygon['xn'], polygon['yn'])
        warped_img = _four_points_transform(img, points)

        if model_name not in models_to_tensors:
            models_to_tensors[model_name] = preprocess_input(warped_img)
        else:
            models_to_tensors[model_name] = np.vstack((models_to_tensors[model_name],
                                                       preprocess_input(warped_img)))

    return models_to_tensors


def _apply_clahe(img):
    """
    Contrast Limited Adaptive Histogram Equalization is used here.
    In this, image is divided into small blocks called "tiles"
    (tileSize is 8x8 by default in OpenCV).
    Then each of these blocks are histogram equalized as usual.
    So in a small area, histogram would confine to a small region (unless there is noise).
    If noise is there, it will be amplified. To avoid this, contrast limiting is applied.
    If any histogram bin is above the specified contrast limit (by default 40 in OpenCV),
    those pixels are clipped and distributed uniformly to other bins before
    applying histogram equalization.
    After equalization, to remove artifacts in tile borders, bilinear interpolation is applied.

    :param img: original BGR image (output of opencv.imread)
    :return: normalized BGR image
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lab_planes = cv2.split(lab)
    lab_planes[0] = clahe.apply(lab_planes[0])
    lab = cv2.merge(lab_planes)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _get_points(xn, yn):
    xn = np.array(xn.split(';')).astype(np.float32)
    yn = np.array(yn.split(';')).astype(np.float32)
    points = np.stack((xn, yn), axis=-1)
    return points


def _four_points_transform(img, points):
    (tl, tr, br, bl) = points

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    if max_height > max_width:
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], np.float32)
    else:
        dst = np.array([
            [max_height - 1, 0],
            [max_height - 1, max_width - 1],
            [0, max_width - 1],
            [0, 0]], np.float32)

    matrix = cv2.getPerspectiveTransform(points, dst)
    warped = cv2.warpPerspective(img, matrix, (max_width, max_height))
    return warped
