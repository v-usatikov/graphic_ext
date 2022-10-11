from cmath import rect, pi
from typing import List, Any, Callable, Optional, Dict, Tuple, Iterable

import PIL
import numpy as np
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRect
from PyQt6.QtGui import QPainter, QPen, QPixmap, QColor, QFont
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtWidgets import QSizePolicy
from PIL import Image
from nptyping import NDArray, Bool

from graphic_ext.paint_ext import QPainter_ext
from graphic_ext.helper_functions import set_attributes, complex_to_tuple_rounded


class GraphicField(QFrame):
    zoomed = pyqtSignal()

    def __init__(self, parent=None, x_range: float = 1000, y_range: float = 1000, margin: float = 0,
                 keep_ratio: bool = True, scale: bool = True):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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

        self.__mouse_is_pressed = False

        self.zoomed.connect(self.update)

        self.background = BackgroundPicture(self)
        self.front_layer = FrontLayer(self)

    def mouse_is_pressed(self):

        return self.__mouse_is_pressed

    def set_background(self, pixmap: QPixmap, use_picture_coordinates: bool = True):

        if use_picture_coordinates:
            self.x_range = pixmap.width()
            self.y_range = pixmap.height()
            self.zoom_reset()
        self.background.set_picture(pixmap)

    def set_background_from_file(self, file_path: str, use_picture_coordinates: bool = True):

        pixmap = QPixmap(file_path)
        self.set_background(pixmap, use_picture_coordinates)

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

    def norm_to_pixel_rel(self, value: float) -> float:
        """Transformiert ein Wert in normierte Einheiten zu Pixel."""

        return self.pixel_range() / (self.zoom_w + 2*self.margin) * value

    def norm_to_pixel_rel_int(self, value: float) -> int:
        """Transformiert ein Wert in normierte Einheiten zu Pixel."""

        return round(self.norm_to_pixel_rel(value))

    def pixel_to_norm_rel(self, value: float) -> float:
        """Transformiert ein Wert in Pixel zu normierte Einheiten."""

        return (self.zoom_w + 2*self.margin) / self.pixel_range() * value

    def norm_to_pixel_coord(self, x: float, y: float) -> (float, float):
        """Transformiert Koordinaten in normierte Einheiten zu Pixel."""

        x = self.norm_to_pixel_rel(x - self.zoom_x + self.margin)
        y = self.norm_to_pixel_rel(y - self.zoom_y + self.margin)
        return x, y

    def norm_to_pixel_coord_int(self, x: float, y: float) -> (int, int):
        """Transformiert Koordinaten in normierte Einheiten zu Pixel."""

        x, y = self.norm_to_pixel_coord(x, y)
        return round(x), round(y)

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

        self.front_layer.setFixedWidth(self.width())
        self.front_layer.setFixedHeight(self.height())
        # print(a0.size())

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:

        super().paintEvent(a0)

        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund malen
        pen = QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.SolidLine)
        qp.setPen(pen)
        qp.setBrush(Qt.GlobalColor.gray)
        qp.drawRect(0, 0, self.width(), self.height())

        # Sample malen
        pen.setColor(Qt.GlobalColor.white)
        qp.setPen(pen)
        qp.setBrush(Qt.GlobalColor.white)
        qp.drawRect(*self.norm_to_pixel_coord_int(-self.margin, -self.margin),
                    self.norm_to_pixel_rel_int(self.x_range + 2*self.margin),
                    self.norm_to_pixel_rel_int(self.x_range + 2*self.margin))

        qp.end()

    def paintFrontLayer(self, painter: QPainter_ext):

        if self.__select:
            pen = QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            start = self.__select_start
            end = self.__select_end
            painter.drawRect(start[0], start[1], end[0] - start[0], end[1] - start[1])

        for zone in self.zones:
            zone.paint(painter)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        x, y = event.pos().x(), event.pos().y()
        if self.__mode == 'select':
            self.__select = True
            self.__select_start = (x, y)
            self.__select_end = (x, y)
        elif self.__mode == 'grab':
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.__move_start = (x, y)

            self.__zoom_x0 = self.zoom_x
            self.__zoom_y0 = self.zoom_y
        else:
            x, y = self.pixel_to_norm_coord(x, y)
            for zone in self.zones:
                if zone.coordinates_are_in_zone(x, y):
                    zone.clicked.emit()
        self.__mouse_is_pressed = True

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:

        x, y = event.pos().x(), event.pos().y()
        if self.__mode == 'select' and self.__mouse_is_pressed:
            self.__select_end = (x, y)
            self.update()
        elif self.__mode == 'grab' and self.__mouse_is_pressed:
            end = (x, y)
            dx = end[0] - self.__move_start[0]
            dy = end[1] - self.__move_start[1]
            self.zoom_x = self.__zoom_x0 - self.pixel_to_norm_rel(dx)
            self.zoom_y = self.__zoom_y0 - self.pixel_to_norm_rel(dy)
            self.zoomed.emit()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:

        self.__mouse_is_pressed = False
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
            self.setCursor(Qt.CursorShape.OpenHandCursor)

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

    def __init__(self, gr_field: GraphicField, x: float = 0, y: float = 0, centered: bool = False):
        super().__init__(gr_field)
        self.setText('')
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.gr_field = gr_field
        self.gr_field.objects.append(self)

        self.centered = centered

        self.x = x
        self.y = y
        self.reposition()
        # print(self.pos())

        self.gr_field.zoomed.connect(self.refresh)

    def rescale(self):
        pass

    def reposition(self):
        x, y = self.gr_field.norm_to_pixel_coord(self.x, self.y)
        if self.centered:
            self.move(round(x - self.width() / 2), round(y - self.height() / 2))
        else:
            self.move(round(x), round(y))

    def move_to(self, x, y):
        self.x = x
        self.y = y
        self.reposition()

    def refresh(self):
        self.rescale()
        self.reposition()


# class GraphicObject_FixSize(GraphicObject):
#
#     def __init__(self, gr_field: GraphicField,
#                  x: float = 0,
#                  y: float = 0,
#                  width: float = 0,
#                  height: float = 0,
#                  centered: bool = False):
#
#         super().__init__(gr_field, x, y, centered)
#
#         self.width_norm = width
#         self.height_norm = height
#         self.refresh()
#
#     def rescale(self):
#
#         self.setFixedWidth(self.gr_field.norm_to_pixel_rel(self.width_norm))
#         self.setFixedHeight(self.gr_field.norm_to_pixel_rel(self.height_norm))
#         self.update()


class BackgroundPicture(GraphicObject):

    def __init__(self, gr_field: GraphicField, pixmap: Optional[QPixmap] = None, file_path: Optional[str] = None):

        super().__init__(gr_field, 0, 0, False)
        if pixmap is not None:
            self.set_picture(pixmap)
        elif file_path is not None:
            self.set_picture_from_file(file_path)

        self.rescale()

    def set_picture(self, pixmap: QPixmap):

        self.setPixmap(pixmap)
        self.setScaledContents(True)

    def set_picture_from_file(self, file_path: str):

        pixmap = QPixmap(file_path)
        self.set_picture(pixmap)

    def rescale(self):

        self.setFixedWidth(self.gr_field.norm_to_pixel_rel_int(self.gr_field.x_range))
        self.setFixedHeight(self.gr_field.norm_to_pixel_rel_int(self.gr_field.y_range))
        self.update()


class FrontLayer(QLabel):

    def __init__(self, gr_field: GraphicField):
        super().__init__(gr_field)
        self.gr_field = gr_field
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.move(0, 0)
        self.show()
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:

        x, y = event.pos().x(), event.pos().y()
        x, y = self.gr_field.pixel_to_norm_coord(x, y)
        for zone in self.gr_field.zones:
            if zone.coordinates_are_in_zone(x, y):
                if not zone.activated:
                    zone.mouse_enter.emit()
                    zone.activated = True
            else:
                if zone.activated:
                    zone.mouse_leave.emit()
                    zone.activated = False
        self.gr_field.mouseMoveEvent(event)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super().paintEvent(a0)
        self.raise_()

        painter = QPainter_ext()
        painter.begin(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.gr_field.paintFrontLayer(painter)
        painter.end()


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
        self.mask = image > 10
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

    def paint(self, painter: QPainter_ext):
        pass


AXES_PARAMETERS: Dict[Tuple[int, int, int], dict] = {}
AXES_DEFINER = np.array([-rect(1, -pi/6), rect(1, pi/6), rect(1, -pi/2)])


class Axes(GraphicObject):

    def __init__(self, gr_field: GraphicField,
                 x: float,
                 y: float,
                 arrow_length: float,
                 font_size_rel: Optional[float] = 0.15,
                 font_size: Optional[int] = None,
                 pen_width: int = 1,
                 pen_color: QColor = Qt.GlobalColor.black,
                 pen_width_activated: int = 2,
                 pen_color_activated: QColor = Qt.GlobalColor.red,
                 arrow_parameters: Optional[dict] = None,
                 axis_parameters: Optional[dict] = None,
                 round_axis_parameters: Optional[dict] = None,):

        super().__init__(gr_field, x, y, True)
        if arrow_parameters is None:
            self.arrow_parameters = {}
        else:
            self.arrow_parameters = arrow_parameters
        if axis_parameters is None:
            self.axis_parameters = {}
        else:
            self.axis_parameters = axis_parameters
        if round_axis_parameters is None:
            self.round_axis_parameters = {}
        else:
            self.round_axis_parameters = round_axis_parameters

        self.font_size_rel = font_size_rel
        self.font_size = font_size
        self.pen_width = pen_width
        self.pen_color = pen_color
        self.pen_width_activated = pen_width_activated
        self.pen_color_activated = pen_color_activated
        self.activated = False
        self.rel_width = 3
        self.clockwise = False  # False, wenn positive Richtung ist gegen den Uhrzeigersinn

        self.arrow_length = arrow_length
        self.rescale()

        self.axes: Dict[str, Axis] = {}

    def set_activated(self, activated: bool):
        self.activated = activated
        self.update()

    def rescale(self):
        self.setFixedWidth(self.gr_field.norm_to_pixel_rel_int(self.rel_width * self.arrow_length))
        self.setFixedHeight(self.gr_field.norm_to_pixel_rel_int(self.rel_width * self.arrow_length))
        self.update()

    def def_axes(self, declaration: Iterable[Tuple[str, Tuple[int, int, int], bool]]):

        self.axes = {}
        for axis_def in declaration:
            name, definition, add_rotation = axis_def
            axis = Axis(self, name, definition, self.axis_parameters)
            self.axes[name] = axis
            if add_rotation:
                self.axes['R' + name]= RoundAxis(axis, parameters=self.round_axis_parameters)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:

        super().paintEvent(a0)

        painter = QPainter_ext()
        painter.begin(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.set_parameters(self.arrow_parameters)

        pen = QPen()
        font = painter.font()
        if self.font_size is None:
            font_size = round(self.font_size_rel*self.gr_field.norm_to_pixel_rel(self.arrow_length))
        else:
            font_size = self.font_size
        font.setPointSize(font_size)

        center = complex(self.width()/2, self.height()/2)

        for axis in self.axes.values():
            if axis.activated or self.activated:
                pen.setColor(self.pen_color_activated)
                pen.setWidth(self.pen_width_activated)
                font.setBold(True)
            else:
                pen.setColor(self.pen_color)
                pen.setWidth(self.pen_width)
                font.setBold(False)
            painter.setPen(pen)
            painter.setFont(font)

            axis.paint(painter, center)


class Axis:

    notation_shift: Tuple[float, float] = (0.7, 0.7)  # Verschiebung der Achsenbeschriftung
    # in relative Einheiten von jetzigen font-pt-size ([Entlang der Pfeile], [quer der Pfeile nach rechts])

    def __init__(self, axes_obj: Axes, name: str, definition: Tuple[int, int, int], parameters: Optional[dict] = None):

        self.axes_obj = axes_obj
        self.name = name
        self.definition = definition

        self.activated = False

        if parameters is None:
            parameters = {}
        else:
            self.set_parameters(parameters)

    def set_parameters(self, parameters: dict):

        set_attributes(self, parameters)

    def paint(self, painter: QPainter_ext, center: complex):

        # die Pfeile zeichnen
        arrow_length_p = self.axes_obj.gr_field.norm_to_pixel_rel(self.axes_obj.arrow_length)
        arrow_direction = np.dot(self.definition, AXES_DEFINER)
        arrow_from_center = arrow_length_p * arrow_direction
        arrow_end = center + arrow_from_center

        start = complex_to_tuple_rounded(center)
        end = complex_to_tuple_rounded(arrow_end)
        painter.drawArrow(start, end)

        # beschriftung der Achse
        font_size = painter.font().pointSize()
        along, across = self.notation_shift
        notation_shift = along * arrow_direction + across * arrow_direction * rect(1, -pi / 2)
        notation_shift *= font_size

        notation_center = arrow_end + notation_shift
        notation_center = complex_to_tuple_rounded(notation_center)

        painter.drawText_centered(notation_center, self.name)


class RoundAxis(Axis):

    rel_width: float = 0.3  # Breite der runden Pfeile relativ der Pfeillänge
    axis_notation_shift: Tuple[float, float] = (0, 0.9)  # dieser Wert ersetzt notation_shift im dazugehörigen Axis Objekt
    shift: float = 0.15  # Abstand zwischen dem Ende der Pfeile und dem Körper der runden Pfeile (Einh: Pfeillänge)
    notation_shift: Tuple[float, float] = (0.72, 0.72)  # Abstand zwischen der runden Pfeile und deren Beschriftung
    # in relative Einheiten von jetzigen font-pt-size ([Entlang der Pfeile], [quer der Pfeile nach rechts])

    def __init__(self, axis: Axis, name: Optional[str] = None, parameters: Optional[dict] = None):

        if name is None:
            name = 'R' + axis.name

        self.axis = axis

        super().__init__(axis.axes_obj, name, axis.definition, parameters)

        if sum(self.definition) > 0:
            self._invert = False
        else:
            self._invert = True
        if self.axis.axes_obj.clockwise:
            self._invert = not self._invert

        self.axis.notation_shift = self.axis_notation_shift
        self.axis.axes_obj.rel_width += 2*(self.rel_width + self.shift +
                                           2*len(name)*max(self.notation_shift)*self.axis.axes_obj.font_size_rel)

    def paint(self, painter: QPainter_ext, center: complex):

        # die Pfeile zeichnen
        arrow_length_p = self.axes_obj.gr_field.norm_to_pixel_rel(self.axes_obj.arrow_length)
        arrow_direction = np.dot(self.definition, AXES_DEFINER)
        from_coord_center_to_round_center = (1 + self.shift + self.rel_width/2) * arrow_length_p * arrow_direction
        round_center = center + from_coord_center_to_round_center

        width = self.rel_width * arrow_length_p
        painter.drawRoundArrow(complex_to_tuple_rounded(round_center), round(width), self._invert)

        # beschriftung der Achse
        font_size = painter.font().pointSize()
        along, across = self.notation_shift
        notation_shift = along * arrow_direction + across * arrow_direction * rect(1, -pi / 2)
        notation_shift *= font_size
        notation_shift *= (1 + width/(2*abs(notation_shift)))

        notation_center = round_center + notation_shift
        notation_center = complex_to_tuple_rounded(notation_center)

        font0 = painter.font()
        font = painter.font()
        font.setPointSize(round(0.9 * font_size))
        painter.setFont(font)
        painter.drawText_centered(notation_center, self.name)
        painter.setFont(font0)
