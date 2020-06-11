""" Core model module.
"""
import yaml

import torch
import numpy as np
import cv2
from albumentations import Normalize


class ParkingInference:

    def __init__(self, inference_config, parking_coords, model_path):
        super(ParkingInference, self).__init__()

        with open(inference_config) as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)

        self.parking_lots = {'parking_lot_coords': {item['id']:
                                list(zip(map(lambda x: int(float(x)), item['xn'].split(';')),
                                         map(lambda x: int(float(x)), item['yn'].split(';'))))
                                            for item in parking_coords[0]['annotations']}}
        self.image_size = (self.config['frame']['height'], self.config['frame']['width'])
        self.device = 'cuda:0' if self.config['use_cuda'] else 'cpu'
        self.model = self.load_model(model_path)
        self.binary_threshold = self.config['binary_threshold']
        self.occupation_threshold = self.config['occupation_threshold']
        self.border_width = self.config['border_width']
        self.load_size = self.config['load_size']

    def load_model(self, model_path):

        model = torch.jit.load(model_path)
        model.to(self.device)

        return model

    def load_image(self, image_path, size):

        image = read_img(image_path)
        image = Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])(image=image)['image']

        border_width = int(self.border_width * image.shape[1] / self.load_size['width'])

        cover = get_preprocessed_mask(self.image_size,
                                      parking_lots=self.parking_lots,
                                      border_width=border_width,
                                      for_metrics=False)
        image = image * cover
        image = cv2.resize(image, tuple(size))
        image = torch.from_numpy(np.transpose(image, (2, 0, 1)).astype('float32')).unsqueeze(0)

        return image

    def predict(self, image_path):

        with torch.no_grad():
            image = self.load_image(image_path,
                                    size=self.config['size'])
            image = image.to(self.device)
            predict = self.model(image)
            predict = torch.sigmoid(predict).squeeze().squeeze().detach().cpu().numpy()

            if self.binary_threshold:
                predict = predict > self.binary_threshold

        border_width = int(self.border_width * self.config['frame']['width'] / self.load_size['width'])
        cover = get_preprocessed_mask(self.image_size,
                                      parking_lots=self.parking_lots,
                                      border_width=border_width,
                                      for_metrics=True)

        size = self.config['size']
        cover = cv2.resize(cover, tuple(size), interpolation=cv2.INTER_NEAREST)
        result = predict * cover

        occupied_lots_dict = {}
        for key in self.parking_lots['parking_lot_coords']:
            prob = (np.sum(result == int(key)) / np.sum(cover == int(key)))
            occupied_lots_dict[int(key)] = (int(prob > self.occupation_threshold), prob)

        return occupied_lots_dict


def read_img(path, mask=False):
    color = cv2.COLOR_BGR2GRAY if mask else cv2.COLOR_BGR2RGB
    image = cv2.cvtColor(cv2.imread(path), color)

    return image


def get_preprocessed_mask(image_size, parking_lots, border_width=15, for_metrics=False):
    mask = np.zeros(image_size).astype('uint8')

    parking_lots_coords = parking_lots['parking_lot_coords']
    for pklot_id, pts in parking_lots_coords.items():
        pts = np.array(pts)
        color = int(pklot_id) if for_metrics else 1
        cv2.fillPoly(mask, [pts], color=color)
        cv2.polylines(mask, [pts], True, 0, border_width)

    if not for_metrics:
        mask = mask[:, :, np.newaxis]

    return mask
