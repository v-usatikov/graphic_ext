from typing import List, Any, Callable, Optional

import PIL
import numpy as np
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QFrame, QLabel
from PyQt5.QtWidgets import QSizePolicy
from PIL import Image
from nptyping import NDArray, Bool



class GraphicField(QFrame):
    zoomed = pyqtSignal()

    def __init__(self, parent=None, x_range: float = 1000, y_range: float = 1000, margin: float = 0,
                 keep_ratio: bool = True, scale: bool = True):
        super().__init__(parent)

        self.x_range = x_range
        self.y_range = y_range
        self.margin = margin
        self.pixel_range0 = self.width()

        # Zoom Daten (in Normierte Einheiten)
        self.zoom_x = 0
        self.zoom_y = 0
        self.zoom_w = x_range

        # Mode einstellen ('navig', 'move' oder 'select')
        self.keep_ratio = keep_ratio
        self.scale = scale
        self.__modes = ['normal', 'grab', 'select']
        self.__mode = 'normal'

        self.objects: List[GraphicObject] = []
        self.zones: List[GraphicZone] = []

        self.__select = False
        self.__select_start = (0, 0)
        self.__select_end = (0, 0)

        self.__move_start = (0, 0)
        self.__zoom_x0 = 0
        self.__zoom_y0 = 0

        self.zoomed.connect(self.update)

    def zoom_reset(self):
        self.zoom_x = 0
        self.zoom_y = 0
        self.zoom_w = self.x_range
        self.zoomed.emit()

    def set_mode(self, mode: str):
        if mode not in self.__modes:
            raise ValueError(f'Unbekannter Mode: "{mode}". Mögliche Variante: {self.__modes}')
        self.__mode = mode
        if mode == 'normal':
            self.setCursor(Qt.ArrowCursor)
        elif mode == 'grab':
            self.setCursor(Qt.OpenHandCursor)
        elif mode == 'select':
            self.setCursor(Qt.CrossCursor)

    def mode(self) -> str:
        return self.__mode

    def pixel_range(self):
        if self.scale:
            return self.width()
        else:
            return self.pixel_range0

    def set_current_width_as_pixel_range(self):
        self.pixel_range0 = self.width()

    def norm_to_pixel_rel(self, value: float) -> int:
        """Transformiert ein Wert in normierte Einheiten zu Pixel."""
        return round(self.pixel_range() / (self.zoom_w + 2*self.margin) * value)

    def pixel_to_norm_rel(self, value: float) -> float:
        """Transformiert ein Wert in Pixel zu normierte Einheiten."""
        return (self.zoom_w + 2*self.margin) / self.pixel_range() * value

    def norm_to_pixel_coord(self, x: float, y: float) -> (float, float):
        """Transformiert Koordinaten in normierte Einheiten zu Pixel."""
        x = self.norm_to_pixel_rel(x - self.zoom_x + self.margin)
        y = self.norm_to_pixel_rel(y - self.zoom_y + self.margin)
        return x, y

    def pixel_to_norm_coord(self, x: float, y: float) -> (float, float):
        """Transformiert Koordinaten in Pixel zu normierte Einheiten."""
        x = self.pixel_to_norm_rel(x) + self.zoom_x - self.margin
        y = self.pixel_to_norm_rel(y) + self.zoom_y - self.margin
        return x, y

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if self.keep_ratio:
            if a0.size().width() <= a0.size().height()*self.x_range/self.y_range:
                width = a0.size().width()
                self.resize(width, round(width*self.y_range/self.x_range))
            else:
                height = a0.size().height()
                self.resize(round(height * self.x_range / self.y_range), height)
        if self.scale:
            self.zoomed.emit()
        # print(a0.size())

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super().paintEvent(a0)

        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Hintergrund malen
        pen = QPen(Qt.gray, 2, Qt.SolidLine)
        pen.setWidth(1)
        pen.setColor(Qt.gray)
        qp.setPen(pen)
        qp.setBrush(Qt.gray)
        qp.drawRect(0, 0, self.width(), self.height())

        # Sample malen
        pen = QPen(Qt.gray, 2, Qt.SolidLine)
        pen.setWidth(1)
        pen.setColor(Qt.white)
        qp.setPen(pen)
        qp.setBrush(Qt.white)
        qp.drawRect(*self.norm_to_pixel_coord(-self.margin, -self.margin),
                    self.norm_to_pixel_rel(self.x_range + 2*self.margin),
                    self.norm_to_pixel_rel(self.x_range + 2*self.margin))

        if self.__select:
            pen = QPen(Qt.gray, 1, Qt.SolidLine)

            pen.setWidth(1)
            qp.setPen(pen)
            qp.setBrush(Qt.NoBrush)
            start = self.__select_start
            end = self.__select_end
            qp.drawRect(start[0], start[1], end[0] - start[0], end[1] - start[1])
        qp.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        x, y = event.pos().x(), event.pos().y()
        if self.__mode == 'select':
            self.__select = True
            self.__select_start = (x, y)
            self.__select_end = (x, y)
        elif self.__mode == 'grab':
            self.setCursor(Qt.ClosedHandCursor)
            self.__move_start = (x, y)

            self.__zoom_x0 = self.zoom_x
            self.__zoom_y0 = self.zoom_y
        else:
            x, y = self.pixel_to_norm_coord(x, y)
            for zone in self.zones:
                if zone.coordinates_are_in_zone(x, y):
                    zone.clicked.emit()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        x, y = event.pos().x(), event.pos().y()
        if self.__mode == 'select':
            self.__select_end = (x, y)
            self.update()
        elif self.__mode == 'grab':
            end = (x, y)
            dx = end[0] - self.__move_start[0]
            dy = end[1] - self.__move_start[1]
            self.zoom_x = self.__zoom_x0 - self.pixel_to_norm_rel(dx)
            self.zoom_y = self.__zoom_y0 - self.pixel_to_norm_rel(dy)
            self.zoomed.emit()
        else:
            x, y = self.pixel_to_norm_coord(x, y)
            for zone in self.zones:
                if zone.coordinates_are_in_zone(x, y):
                    if not zone.activated:
                        zone.mouse_enter.emit()
                        zone.activated = True
                else:
                    if zone.activated:
                        zone.mouse_leave.emit()
                        zone.activated = False

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.__mode == 'select':
            self.__select_end = (event.pos().x(), event.pos().y())
            width = self.__select_end[0] - self.__select_start[0]
            height = self.__select_end[1] - self.__select_start[1]

            self.zoom_x, self.zoom_y = self.pixel_to_norm_coord(self.__select_start[0], self.__select_start[1])

            self.zoom_x += self.margin
            self.zoom_y += self.margin

            if width < 0:
                width = abs(width)
                self.zoom_x -= self.pixel_to_norm_rel(width)
            if height < 0:
                height = abs(height)
                self.zoom_y -= self.pixel_to_norm_rel(height)

            if width <= height * self.x_range / self.y_range:
                self.zoom_w = self.pixel_to_norm_rel(width)
            else:
                self.zoom_w = self.pixel_to_norm_rel(height * self.x_range / self.y_range)

            if self.zoom_w <= 2*self.margin:
                self.zoom_w = 0
            else:
                self.zoom_w -= 2*self.margin

            self.__select = False
            self.zoomed.emit()
        elif self.__mode == 'grab':
            self.setCursor(Qt.OpenHandCursor)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:

        x, y = self.pixel_to_norm_coord(event.pos().x(), event.pos().y())
        for zone in self.zones:
            if zone.coordinates_are_in_zone(x, y):
                zone.double_clicked.emit()

    def zoom_in(self, zoom_k: float = 0.2):
        # print(self.zoom_w)
        zoom_w0 = self.zoom_w
        zoom_k = 1 - zoom_k
        self.zoom_w = (self.zoom_w + 2*self.margin)*zoom_k - 2*self.margin
        if self.zoom_w < 0:
            self.zoom_w = 0

        d_z = (zoom_w0 - self.zoom_w)/2
        self.zoom_x += d_z
        self.zoom_y += d_z
        self.zoomed.emit()

        # print(self.zoom_w)

    def zoom_out(self, zoom_k: float = 0.2):
        zoom_w0 = self.zoom_w
        zoom_k = 1 - zoom_k
        self.zoom_w = (self.zoom_w + 2*self.margin)/zoom_k - 2*self.margin
        d_z = (zoom_w0 - self.zoom_w) / 2
        self.zoom_x += d_z
        self.zoom_y += d_z

        self.zoomed.emit()


class GraphicObject(QLabel):

    def __init__(self, gr_field: GraphicField, x: float = 0, y: float = 0):
        super().__init__(gr_field)
        self.setText('')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.gr_field = gr_field
        self.gr_field.objects.append(self)

        self.x = x
        self.y = y
        self.reposition()
        # print(self.pos())

        self.gr_field.zoomed.connect(self.refresh)

    def rescale(self):
        pass

    def reposition(self):
        # print('norm', self.x, self.y)
        x, y = self.gr_field.norm_to_pixel_coord(self.x, self.y)
        # print('pixel', x, y)
        self.move(round(x - self.width() / 2), round(y - self.height() / 2))
        # print('угол', round(x - self.width() / 2), round(y - self.height() / 2))
        # print()

    def move_to(self, x, y):
        self.x = x
        self.y = y
        self.reposition()

    def refresh(self):
        self.rescale()
        self.reposition()


class GraphicZone(QObject):

    mask: NDArray[(Any, 2), Bool]
    check_func: Optional[Callable[[float, float], bool]] = None

    activated: bool = False
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    mouse_enter = pyqtSignal()
    mouse_leave = pyqtSignal()

    def __init__(self, gr_field: GraphicField, check_func: Callable[[float, float], bool] = None,
                 mask: NDArray[(Any, 2), Bool] = None,
                 mask_file: str = None):

        super().__init__()
        self.gr_field = gr_field

        if check_func is not None:
            self.check_func = check_func
        elif mask is not None:
            self.mask = mask.copy()
        elif mask_file is not None:
            self.read_mask_from_file(mask_file)
        else:
            self.check_func = lambda x, y: False

    def read_mask_from_file(self, mask_file: str):

        image_pil = PIL.Image.open(mask_file).convert('L')
        image = np.array(image_pil)
        self.mask = image > 123
        self.check_func = None

    def coordinates_are_in_zone(self, x: float, y: float) -> bool:
        if self.check_func is not None:
            return self.check_func(x, y)
        else:
            n_y, n_x = self.mask.shape
            k = n_x/self.gr_field.x_range
            x_index = round(x*k)
            y_index = round(y*k)
            try:
                return self.mask[y_index, x_index]
            except IndexError:
                return False
