#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int


def detect_color_targets(bgr_img, hsv_lo=(40, 80, 80), hsv_hi=(80, 255, 255), min_area=200):
    """Detects bright green squares by HSV thresholding; returns list[Box]."""
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(hsv_lo, dtype=np.uint8), np.array(hsv_hi, dtype=np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w * h >= min_area:
            boxes.append(Box(x, y, w, h))
    return boxes


def draw_boxes(bgr_img, boxes, color=(0, 0, 255)):
    out = bgr_img.copy()
    for b in boxes:
        cv2.rectangle(out, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 2)
    return out
