from cmath import pi, rect
from typing import Tuple

from PyQt5.QtCore import QObject, QRect, Qt
from PyQt5.QtGui import QPainter, QPainterPath

from graphic_ext.helper_functions import set_attributes, complex_to_tuple_rounded


def start_painter(parent: QObject):

    painter = QPainter_ext()
    painter.begin(parent)
    painter.setRenderHint(QPainter.Antialiasing)
    return painter


def draw_arrow_p(start: Tuple[int, int],
                 end: Tuple[int, int],
                 arrow_head1: Tuple[int, int],
                 arrow_head2: Tuple[int, int],
                 painter: QPainter,
                 filled_arrow_head: bool = False):

    # painter.setPen(color)

    painter.drawLine(*start, *end)
    if not filled_arrow_head:
        painter.drawLine(*end, *arrow_head1)
        painter.drawLine(*end, *arrow_head2)
    else:
        # brush0 = painter.pen().brush()
        # painter.setBrush(painter.pen().color())
        path = QPainterPath()
        path.moveTo(*end)
        path.lineTo(*arrow_head1)
        path.lineTo(*arrow_head2)
        path.lineTo(*end)
        painter.drawPath(path)
        # painter.setBrush(brush0)


def compute_arrow_head(start: Tuple[int, int],
                       end: Tuple[int, int],
                       fix_arrow_head: bool = False,
                       arrow_head_fix_width: int = 4,
                       arrow_head_rel_width: float = 0.1,
                       arrow_head_angle: float = 33) -> (Tuple[int, int], Tuple[int, int]):

    start = complex(*start)
    end = complex(*end)
    arrow = end - start
    arrow_length = abs(arrow)
    arrow /= arrow_length
    rotation = rect(1, arrow_head_angle*pi/180)

    arrow_head1 = (-arrow) * rotation
    arrow_head2 = (-arrow) / rotation

    if fix_arrow_head:
        length = arrow_head_fix_width
    else:
        length = (arrow_length * arrow_head_rel_width)

    arrow_head1 = arrow_head1 * length + end
    arrow_head2 = arrow_head2 * length + end

    arrow_head1 = complex_to_tuple_rounded(arrow_head1)
    arrow_head2 = complex_to_tuple_rounded(arrow_head2)

    return arrow_head1, arrow_head2


def draw_arrow(start: Tuple[int, int],
               end: Tuple[int, int],
               painter: QPainter,
               fix_arrow_head: bool = False,
               arrow_head_fix_width: int = 4,
               arrow_head_rel_width: float = 0.1,
               arrow_head_angle: float = 33,
               filled_arrow_head: bool = False):

    arrow_head1, arrow_head2 = compute_arrow_head(start, end, fix_arrow_head, arrow_head_fix_width,
                                                  arrow_head_rel_width, arrow_head_angle)

    draw_arrow_p(start, end, arrow_head1, arrow_head2, painter, filled_arrow_head)


def draw_round_arrow(center: Tuple[int, int],
                     width: int,
                     painter: QPainter,
                     start_angle: int = -150,
                     end_angle: int = 150,
                     fix_arrow_head: bool = False,
                     arrow_head_fix_width: int = 4,
                     arrow_head_rel_width: float = 0.2,
                     arrow_head_angle: float = 45,
                     arrow_head_rotation: float = 10,
                     filled_arrow_head: bool = False):

    painter.drawArc(round(center[0] - width/2), round(center[1] - width/2), width, width,
                    start_angle*16, (end_angle-start_angle)*16)

    end = complex(*center) + rect(width/2, -end_angle*pi/180)

    if fix_arrow_head:
        arrow_head_width = arrow_head_fix_width
    else:
        arrow_head_width = arrow_head_rel_width * width

    direction = (end_angle - start_angle)
    direction /= abs(direction)

    arrow_head1 = end - direction * rect(arrow_head_width, -(end_angle - direction * arrow_head_rotation + 90 + arrow_head_angle)*pi/180)
    arrow_head2 = end - direction * rect(arrow_head_width, -(end_angle - direction * arrow_head_rotation + 90 - arrow_head_angle)*pi/180)

    end = complex_to_tuple_rounded(end)
    arrow_head1 = complex_to_tuple_rounded(arrow_head1)
    arrow_head2 = complex_to_tuple_rounded(arrow_head2)

    draw_arrow_p(end, end, arrow_head1, arrow_head2, painter, filled_arrow_head)


class QPainter_ext(QPainter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fix_arrow_head: bool = False
        self.arrow_head_fix_width: int = 4
        self.arrow_head_rel_width: float = 0.1
        self.arrow_head_angle: float = 33
        self.filled_arrow_head: bool = False

        self.round_arrow_head_rel_width: float = 0.2
        self.round_arrow_head_fix_width: int = 4
        self.round_arrow_head_angle: float = 45
        self.round_arrow_head_rotation: float = 10
        self.round_arrow_start_angle: int = -150
        self.round_arrow_end_angle: int = 150

    def set_parameters(self, parameters: dict):

        set_attributes(self, parameters)

    def drawArrow(self, start: Tuple[int, int], end: Tuple[int, int]):

        draw_arrow(start, end, self, self.fix_arrow_head, self.arrow_head_fix_width, self.arrow_head_rel_width,
                   self.arrow_head_angle, self.filled_arrow_head)

    def drawRoundArrow(self, center: Tuple[int, int], width: int, invert: bool = False):

        if invert:
            round_arrow_start_angle = self.round_arrow_end_angle
            round_arrow_end_angle = self.round_arrow_start_angle
        else:
            round_arrow_start_angle = self.round_arrow_start_angle
            round_arrow_end_angle = self.round_arrow_end_angle

        draw_round_arrow(center, width, self, round_arrow_start_angle, round_arrow_end_angle,
                         self.fix_arrow_head, self.round_arrow_head_fix_width, self.round_arrow_head_rel_width,
                         self.round_arrow_head_angle, self.round_arrow_head_rotation, self.filled_arrow_head)

    def drawText_centered(self, center_point: Tuple[int, int], text: str):

        rect_height = 2 * self.font().pointSize()
        rect_width = rect_height * len(text)
        rect_position = complex(*center_point) - complex(rect_width, rect_height) / 2
        rect_position = complex_to_tuple_rounded(rect_position)
        text_rect = QRect(*rect_position, rect_width, rect_height)

        self.drawText(text_rect, Qt.AlignCenter, text)



