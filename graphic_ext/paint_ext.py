from cmath import pi, rect
from typing import Tuple

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QPainter, QPainterPath


def start_painter(parent: QObject):

    painter = QPainter()
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

    arrow_head1 = (round(arrow_head1.real), round(arrow_head1.imag))
    arrow_head2 = (round(arrow_head2.real), round(arrow_head2.imag))

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


class QPainter_ext(QPainter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fix_arrow_head: bool = False
        self.arrow_head_fix_width: int = 4
        self.arrow_head_rel_width: float = 0.1
        self.arrow_head_angle: float = 33
        self.filled_arrow_head: bool = False

    def drawArrow(self, start: Tuple[int, int], end: Tuple[int, int]):

        draw_arrow(start, end, self, self.fix_arrow_head, self.arrow_head_fix_width, self.arrow_head_rel_width,
                   self.arrow_head_angle, self.filled_arrow_head)
