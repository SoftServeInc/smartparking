""" Custom SmartParking configuration and some patches.
"""
from PyQt4.Qt import QPointF, QRectF, QPolygonF
from sloth import items
from sloth.core import labeltool


LABELS = (
    {'attributes': {'id': [str(i) for i in range(1, 501)],
                    'model': ['main', 'behind_trees'],
                    'class': 'polygon'},
     'item': 'smartparking.ParkingPolygonItem',
     'inserter': 'smartparking.ParkingPolygonItemInserter',
     'text': 'Parking Slot'
    },
)


def save_annotations(self, fname):
    """ Custom implementation of labeltool.LabelTool.saveAnnotations method.
    """
    success = False
    try:
        if fname != self._container.filename():
            self._container = self._container_factory.create(fname)

        duplicates = []
        anns = self._model.root().getAnnotations()
        for ann in anns:
            ann['annotations'] = [a for a in ann['annotations']
                                  if a and a.get('id') is not None]
            ann_ids = [a['id'] for a in ann['annotations']]
            for ann_id in set(ann_ids):
                ann_ids.remove(ann_id)

            ann_ids = [int(ann_id) if ann_id.isdigit() else ann_id
                       for ann_id in ann_ids]
            ann_ids = sorted(ann_ids)
            ann_ids = [str(ann_id) for ann_id in ann_ids]
            duplicates.extend(ann_ids)

        num_files = len(anns)
        num_anns = sum(len(ann['annotations']) for ann in anns)
        self._container.save(anns, fname)
        if duplicates:
            msg = 'Successfully saved %s (%d files, %d annotations). ' \
                  'WARNING: Found duplicate ids: %s.' % (
                      fname, num_files, num_anns, ', '.join(duplicates))
        else:
            msg = 'Successfully saved %s (%d files, %d annotations)' % (
                fname, num_files, num_anns)
        success = True
        self._model.setDirty(False)
    except Exception as exc:
        msg = "Error: Saving failed (%s)" % str(exc)

    self.statusMessage.emit(msg)
    return success

labeltool.LabelTool.saveAnnotations = save_annotations


class ParkingPolygonItem(items.PolygonItem):
    """ PolygonItem class with displayed ID value and some behavior changes.
    """
    defaultAutoTextKeys = ['id', 'model']

    def _compile_text(self):
        text_lines = []
        if self._text:
            text_lines.append(self._text)

        if self._model_item.get('model') is None:
            self._model_item['model'] = LABELS[0]['attributes']['model'][0]

        for key in self._auto_text_keys:
            text_lines.append(self._model_item.get(key, '') or '')

        return ' '.join(text_lines)

    def _updatePolygon(self, polygon):
        if polygon == self._polygon:
            return

        if len([p for p in polygon]) != 4 or self._model_item.get('id') is None:
            self.setValid(False)
            self._polygon = QPolygonF()
            self._text_item.setHtml('')
            for key in self._model_item:
                del self._model_item[key]

            return

        if self._model_item.get('model') is None:
            self._model_item['model'] = LABELS[0]['attributes']['model'][0]

        self.prepareGeometryChange()
        self._polygon = polygon
        self.setPos(QPointF(0, 0))
        rect = self.boundingRect()
        pos_x = (rect.topLeft().x() + rect.topRight().x()) / 2 - 30
        pos_y = (rect.topLeft().y() + rect.bottomLeft().y()) / 2 - 10
        self._text_item.setPos(pos_x, pos_y)

    def boundingRect(self):
        if self.isValid():
            return items.PolygonItem.boundingRect(self)

        return QRectF()


class ParkingPolygonItemInserter(items.PolygonItemInserter):
    """ PolygonItemInserter class with some behavior changes.
    """
    def _removeLastPointAndFinish(self, image_item):
        polygon = self._item.polygon()
        polygon.remove(polygon.size() - 1)
        assert polygon.size() > 0
        self._item.setPolygon(polygon)

        self._updateAnnotation()
        if self._commit:
            image_item.addAnnotation(self._ann)

        self._scene.removeItem(self._item)
        self.annotationFinished.emit()
        self._item = None
        self._scene.clearMessage()
