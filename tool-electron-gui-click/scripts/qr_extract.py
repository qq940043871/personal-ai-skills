# -*- coding: utf-8 -*-
"""Extract text/URL from a QR code inside a screenshot or image.

Usage:
  python qr_extract.py <image.png> [x1 y1 x2 y2]

If a crop box is given, only that region is decoded (faster & more reliable
when the screenshot has many UI elements). Prints the decoded string.

Requires: opencv-python (anaconda 自带), pillow.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import cv2


def try_decode(img):
    det = cv2.QRCodeDetector()
    data, pts, _ = det.detectAndDecode(img)
    return data or ""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    img = cv2.imread(path)
    if img is None:
        print("cannot read image:", path)
        sys.exit(2)

    # 1) try full image
    data = try_decode(img)
    if data:
        print(data)
        return

    # 2) optional crop box
    if len(sys.argv) >= 6:
        x1, y1, x2, y2 = map(int, sys.argv[2:6])
        crop = img[max(0, y1):y2, max(0, x1):x2]
        for scale in (1, 2, 3, 4):
            if crop.size == 0:
                break
            resized = cv2.resize(crop, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_LANCZOS4)
            data = try_decode(resized)
            if data:
                print(data)
                return
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            data = try_decode(gray)
            if data:
                print(data)
                return

    print("NO_QR_DECODED")


if __name__ == "__main__":
    main()
