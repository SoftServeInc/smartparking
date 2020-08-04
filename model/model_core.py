""" Core model module.
"""
import os
import yaml

import cv2
import numpy as np
import torch
from albumentations import Normalize


class ParkingInference:
    """ Parking inference.
    """

    def __init__(self, inference_config, parking_coords, model_path,
                 model_name):
        """ Initialize a parking inference object.

        :param inference_config: path to inference configuration yaml
        :param parking_coords: dict with parking configuration:
            {<slot_id>: {'xn': <X coordinate of the parking slot>,
                         'yn': <Y coordinate of the parking slot>,
                         'model': <model name>}}
        :param model_path: path to the models folder
        :param model: model name
        """
        with open(inference_config) as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)

        self.parking_slots = {
            item['id']: list(zip(map(lambda x:
                                     int(float(x)), item['xn'].split(';')),
                                 map(lambda x:
                                     int(float(x)), item['yn'].split(';'))))
                        for item in parking_coords[0]['annotations']
                        if item['model'] == model_name}
        self.image_size = (self.config['frame']['height'],
                           self.config['frame']['width'])
        self.device = 'cuda:0' if self.config['use_cuda'] else 'cpu'
        self.binary_threshold = self.config['binary_threshold']
        self.occupation_threshold = self.config['occupation_threshold']
        self.border_width = self.config['border_width']
        self.load_size = self.config['load_size']
        self.model = self.load_model(os.path.join(model_path,
                                                  '{}.zip'.format(model_name)))

    def load_model(self, model_path):
        """ Load a model.

        :param model_path: path to a model zip archive
        :return: model object
        """
        model = torch.jit.load(model_path)
        model.to(self.device)
        return model

    def load_image(self, image_path):
        """ Load an image.

        :param image_path: path to an image from a camera
        :return: image object
        """
        image = read_image(image_path)
        image = Normalize(mean=[0.485, 0.456, 0.406],
                          std=[0.229, 0.224, 0.225])(image=image)['image']

        border_width = int(self.border_width * image.shape[1] /
                           self.load_size['width'])

        cover = get_preprocessed_mask(self.image_size,
                                      parking_slots=self.parking_slots,
                                      border_width=border_width,
                                      for_metrics=False)
        image = image * cover
        image = cv2.resize(image, tuple(self.config['size']))
        image = torch.from_numpy(
            np.transpose(image, (2, 0, 1)).astype('float32')).unsqueeze(0)
        return image

    def predict(self, image_path):
        """ Predict state (free/occupied) for each parking slot.

        :param image_path: path to an image from a camera
        :return: dict in the following format:
                 {<slot id>: (<state>, <probability>), ...}

                 <slot id>: int
                 <state>: either 0 (means free) or 1 (means occupied)
                 <probability>: probability that the parking slot is occupied
                    (float in range [0..1])
        """
        with torch.no_grad():
            image = self.load_image(image_path)
            image = image.to(self.device)
            predict = self.model(image)
            predict = torch.sigmoid(
                predict).squeeze().squeeze().detach().cpu().numpy()

            if self.binary_threshold:
                predict = predict > self.binary_threshold

        border_width = int(self.border_width * self.config['frame']['width'] /
                           self.load_size['width'])
        cover = get_preprocessed_mask(self.image_size,
                                      parking_slots=self.parking_slots,
                                      border_width=border_width,
                                      for_metrics=True)

        size = self.config['size']
        cover = cv2.resize(cover, tuple(size), interpolation=cv2.INTER_NEAREST)
        result = predict * cover

        occupied_lots_dict = {}
        for key in self.parking_slots:
            prob = (np.sum(result == int(key)) / np.sum(cover == int(key)))
            occupied_lots_dict[int(key)] = (
                int(prob > self.occupation_threshold), prob)

        return occupied_lots_dict


def read_image(image_path, mask=False):
    """ Read an image.

    :param image_path: path to an image from a camera
    :param mask: whether to apply a grayscale mask or not
    :return: image object
    """
    color = cv2.COLOR_BGR2GRAY if mask else cv2.COLOR_BGR2RGB
    image = cv2.cvtColor(cv2.imread(image_path), color)
    return image


def get_preprocessed_mask(image_size, parking_slots, border_width=15,
                          for_metrics=False):
    """ Get a preprocessed mask.

    :param image_size: image size: (X, Y) tuple
    :param parking_slots: dict of parking slots coordinates
    :param border_width: border width (int)
    :param for_metrics: whether we need metrics or not
    :return: mask (array object)
    """
    mask = np.zeros(image_size).astype('uint8')

    for pklot_id, pts in parking_slots.items():
        pts = np.array(pts)
        color = int(pklot_id) if for_metrics else 1
        cv2.fillPoly(mask, [pts], color=color)
        cv2.polylines(mask, [pts], True, 0, border_width)

    if not for_metrics:
        mask = mask[:, :, np.newaxis]

    return mask
