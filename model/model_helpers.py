""" Various helper functions for models.
"""
import os

import numpy as np
from keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from keras.backend import image_data_format
from keras.layers import Dense, Dropout, Flatten
from keras.models import Sequential, model_from_json
from keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from weather_augmentations import augment_random


def load_inference_model(structure_path, weights_path):
    """ Load inference model.

    :param structure_path: path to architecture of the neural network (.json)
    :param weights_path: path to weights (.h5)
    :return: Keras model
    """
    json_file = open(structure_path, 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    loaded_model.load_weights(weights_path)
    return loaded_model

def save_model(model, path):
    """ Save the model.

    :param model: Keras model
    :param path: path to the model folder
    """
    model_json = model.to_json()
    structure_path = os.path.join(path, "model.json")
    weights_path = os.path.join(path, "weights.h5")
    with open(structure_path, "w") as json_file:
        json_file.write(model_json)
    model.save_weights(weights_path)

def count_images(folder):
    """ Return total number of images in the folder and all its subfolders.

    :param folder: path to a folder
    """
    total = 0
    for _, _, files in os.walk(folder):
        total += len([f for f in files if f.endswith(('.png', '.jpg',
                                                      '.bmp'))])

    return total

def weather_augment(image):
    """ Apply weather augmentation.

    :param image: original image
    :return: augmented image
    """
    rand = np.random.randint(5)
    if rand == 4:
        image = augment_random(image.astype(np.uint8),
                               aug_types=['add_snow', 'add_rain', 'add_fog',
                                          'add_shadow'])
    return preprocess_input(image.astype(np.float32))

def get_generators(train_data_path, val_data_path, width, height, batch_size):
    """ Get training and validation generators.

    :param train_data_path: path to training dataset
    :param val_data_path: path to validation dataset
    :param width: width of images in pixels
    :param height: height of images in pixels
    :param batch_size: batch size
    :return: (training generator, validation generator)
    """
    train_datagen = ImageDataGenerator(
        rotation_range=20,
        shear_range=0.2,
        zoom_range=0.2,
        brightness_range=(0.5, 1.5),
        horizontal_flip=True,
        vertical_flip=True,
        preprocessing_function=weather_augment
    )

    test_datagen = ImageDataGenerator(
        preprocessing_function=preprocess_input
    )

    train_generator = train_datagen.flow_from_directory(
        train_data_path,
        target_size=(width, height),
        batch_size=batch_size,
        class_mode='binary'
    )

    validation_generator = test_datagen.flow_from_directory(
        val_data_path,
        target_size=(width, height),
        batch_size=batch_size,
        class_mode='binary'
    )

    return train_generator, validation_generator

def get_initial_model(width, height):
    """ Get initial model.

    :param width: width of images in pixels
    :param height: height of images in pixels
    :return: Keras model
    """
    if image_data_format() == 'channels_first':
        input_shape = (3, width, height)
    else:
        input_shape = (width, height, 3)

    mobilenet = MobileNetV2(weights='imagenet', include_top=False,
                            input_shape=input_shape)
    for layer in mobilenet.layers[:]:
        layer.trainable = True
    model = Sequential()
    model.add(mobilenet)
    model.add(Flatten())
    model.add(Dense(512, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(1, activation='sigmoid'))

    adam = Adam(1e-4)

    model.compile(loss='binary_crossentropy', optimizer=adam,
                  metrics=['accuracy'])

    return model
