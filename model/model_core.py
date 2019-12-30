""" Core model module.
"""
import os
from shutil import copyfile

import numpy as np
from keras.applications.mobilenet_v2 import preprocess_input
from keras.callbacks import EarlyStopping, TensorBoard, ModelCheckpoint
from keras.models import load_model
from keras.optimizers import Adam
from keras.preprocessing.image import load_img, img_to_array

from model_helpers import (load_inference_model, save_model, count_images,
                           get_generators, get_initial_model)


EPOCHS = 50
WIDTH = 128
HEIGHT = 128
BATCH_SIZE = 32

models = {}


def load_parking_model(model_path):
    """ Load a single model from the path.

    :param model_path: path to the model folder
    """
    name = os.path.basename(os.path.normpath(model_path))
    models[name] = load_inference_model(
        os.path.join(model_path, 'model.json'),
        os.path.join(model_path, 'weights.h5'))


def load_all_parking_models(models_path):
    """ Load all models from the path.

    :param models_path: path to models folder
    """
    for entry in os.scandir(models_path):
        if entry.is_dir():
            models[entry.name] = load_inference_model(
                os.path.join(models_path, entry.name, 'model.json'),
                os.path.join(models_path, entry.name, 'weights.h5'))


def train_and_save(train_data_path, dev_data_path, save_to_path):
    """
    Train and save new model.

    :param train_data_path: path to the training data folder
    :param dev_data_path: path to the validation data folder
    :param save_to_path: path to the model folder (where to save
                         model.json and weights.h5)
    """
    model = get_initial_model(WIDTH, HEIGHT)

    checkpoint_path = os.path.join(save_to_path, 'weights.h5')
    model_checkpoint = ModelCheckpoint(checkpoint_path, monitor='val_loss',
                                       verbose=1, save_best_only=True,
                                       save_weights_only=False, mode='auto',
                                       period=1)
    earlystop = EarlyStopping(monitor='val_loss', min_delta=0, patience=5,
                              verbose=0, mode='auto')
    tensorboard = TensorBoard(log_dir='./logs', histogram_freq=0,
                              write_graph=True, write_images=True)

    train_generator, validation_generator = get_generators(
        train_data_path, dev_data_path, WIDTH, HEIGHT, BATCH_SIZE)

    model.fit_generator(
        train_generator,
        steps_per_epoch=count_images(train_data_path) // BATCH_SIZE,
        epochs=EPOCHS,
        validation_data=validation_generator,
        callbacks=[earlystop,
                   tensorboard,
                   model_checkpoint],
        validation_steps=count_images(dev_data_path) // BATCH_SIZE,
        verbose=True,
        shuffle=True
    )
    best_checkpoint = load_model(checkpoint_path)
    save_model(best_checkpoint, save_to_path)


def retrain_and_save(source_model_path, train_data_path, dev_data_path,
                     save_to_path):
    """
    Retrain and save existing model.

    :param source_model_path: path to the existing model folder
    :param train_data_path: path to the training data folder
    :param dev_data_path: path to the validation data folder
    :param save_to_path: path to the new model folder (where to save
                         model.json and weights.h5)
    """
    model = load_inference_model(os.path.join(source_model_path, 'model.json'),
                                 os.path.join(source_model_path, 'weights.h5'))
    adam = Adam(1e-4)
    model.compile(loss='binary_crossentropy', optimizer=adam,
                  metrics=['accuracy'])

    for layer in model.layers[:]:
        layer.trainable = True

    checkpoint_path = os.path.join(save_to_path, 'weights.h5')
    model_checkpoint = ModelCheckpoint(checkpoint_path, monitor='val_loss',
                                       verbose=1, save_best_only=True,
                                       save_weights_only=False, mode='auto',
                                       period=1)
    earlystop = EarlyStopping(monitor='val_loss', min_delta=0, patience=5,
                              verbose=0, mode='auto')
    tensorboard = TensorBoard(log_dir='./logs', histogram_freq=0,
                              write_graph=True, write_images=True)

    train_generator, validation_generator = get_generators(
        train_data_path, dev_data_path, WIDTH, HEIGHT, BATCH_SIZE)

    class_weight = {0: 1,
                    1: count_images(os.path.join(train_data_path, 'free')) /
                       count_images(os.path.join(train_data_path, 'occupied'))}
    model.fit_generator(
        train_generator,
        steps_per_epoch=count_images(train_data_path) // BATCH_SIZE,
        epochs=EPOCHS,
        validation_data=validation_generator,
        callbacks=[earlystop,
                   tensorboard,
                   model_checkpoint],
        class_weight=class_weight,
        validation_steps=count_images(dev_data_path) // BATCH_SIZE,
        verbose=True,
        shuffle=True
    )
    best_checkpoint = load_model(checkpoint_path)
    save_model(best_checkpoint, save_to_path)


def predict(folder):
    """ Predict state (free/occupied) for each image in the folder.

    :param folder: path to a folder with cropped images
                   (assumes a separate subfolder for each model)
    :return: dict in the following format:
             {<slot id>: (<state>, <probability>), ...}

             <slot id>: int
             <state>: either 0 (means free) or 1 (means occupied)
             <probability>: probability that the parking slot is occupied
                (float in range [0..1])
    """
    res = {}
    for dirpath, _, filenames in os.walk(folder):
        model_name = os.path.basename(dirpath)
        if model_name not in models:
            continue

        model = models[model_name]
        for filename in filenames:
            if not filename.endswith('.png'):
                continue

            slot_id = int(filename.split('.')[-2].split(' - ')[-1])
            filepath = os.path.join(dirpath, filename)
            img = load_img(filepath, target_size=(WIDTH, HEIGHT))
            x = img_to_array(img)
            x = np.expand_dims(x, axis=0)
            prob_occupied = model.predict(preprocess_input(x))[0][0]
            res[slot_id] = (1 if prob_occupied > 0.5 else 0,
                            str(prob_occupied))

    return res


def batch_predict(batch_input, models_to_ids):
    """ Predict state (free/occupied) for each image in a numpy tensor.

    :param batch_input: dict of a model names mapped to
           numpy tensors of parking spots to recognize
    :param models_to_ids: dict of a model names mapped to ids
    :return: dict in the following format:
             {<slot id>: (<state>, <probability>), ...}

             <slot id>: int
             <state>: either 0 (means free) or 1 (means occupied)
             <probability>: probability that the parking slot is occupied
                (float in range [0..1])
    """
    res = {}

    for model_name, ids in models_to_ids.items():
        model = models[model_name]
        predictions = model.predict(batch_input[model_name])

        for slot_id, probabilities in enumerate(predictions):
            pred_occupancy = np.argmax(probabilities)
            res[ids[slot_id]] = (pred_occupancy.item(), str(probabilities[pred_occupancy]))

    return res


def classify(input_folder, output_folder, model_name):
    """ Classify images as free or occupied and copy them to the right folders.

    :param input_folder: path to input folder with cropped images
    :param output_folder: path to output folder with classified images
    :param model_name: model name
    """
    free_folder = os.path.join(output_folder, 'free')
    occupied_folder = os.path.join(output_folder, 'occupied')
    for subdir, _, files in os.walk(input_folder):
        for filename in files:
            input_path = os.path.join(subdir, filename)

            if input_path.endswith('.png'):
                img = load_img(input_path, target_size=(WIDTH, HEIGHT))
                x = img_to_array(img)
                x = np.expand_dims(x, axis=0)
                is_occupied = (
                    models[model_name].predict(preprocess_input(x)) > 0.5)
                if is_occupied[0][0]:
                    output_path = os.path.join(occupied_folder, filename)
                else:
                    output_path = os.path.join(free_folder, filename)

                copyfile(input_path, output_path)


def test_model(model_path, test_folder, misclassified_folder):
    """
    Test how well the model performs on a new data.

    :param model_path: path to the model folder
    :param test_folder: path to the classified images
    :param misclassified_folder: path to output folder with misclassified images
    """
    model = load_inference_model(os.path.join(model_path, 'model.json'),
                                 os.path.join(model_path, 'weights.h5'))
    for subdir, _, files in os.walk(test_folder):
        for src_name in files:
            maybe_img = os.path.join(subdir, src_name)

            if maybe_img.endswith(('.png', '.jpg', '.bmp')):
                x = img_to_array(load_img(maybe_img, target_size=(WIDTH, HEIGHT)))
                x = np.expand_dims(x, axis=0)
                is_occupied = model.predict(preprocess_input(x)) > 0.5
                is_occupied_gt = "occupied" in subdir
                if is_occupied[0][0]:
                    if not is_occupied_gt:
                        dest_folder = os.path.join(misclassified_folder,
                                                   'free')
                        os.makedirs(dest_folder, exist_ok=True)
                        dest_path = os.path.join(dest_folder, src_name)
                        copyfile(maybe_img, dest_path)
                else:
                    if is_occupied_gt:
                        dest_folder = os.path.join(misclassified_folder,
                                                   'occupied')
                        os.makedirs(dest_folder, exist_ok=True)
                        dest_path = os.path.join(dest_folder, src_name)
                        copyfile(maybe_img, dest_path)
