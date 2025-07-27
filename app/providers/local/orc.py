import io
import logging
import os
import time

import cv2
import numpy as np
import pytesseract
from PIL import Image

log = logging.getLogger(__name__)

DEBUG = False
OCR_DEBUG_DIR = "./ocr_debug"
if DEBUG:
	os.makedirs(OCR_DEBUG_DIR, exist_ok=True)

MAX_EDGE = 2500
CLAHE_CLIP = 2.0
TESS_CONFIG = (
	"--oem 3 --psm 6 "
	"-c tessedit_char_whitelist="
	"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	"abcdefghijklmnopqrstuvwxyz:/.%-$"
)
DESKEW_MAX_ANG = 15.0


def _debug_save(img, step):
	if not DEBUG:
		return
	filename = f"{step.replace(' ', '_')}.png"
	path = os.path.join(OCR_DEBUG_DIR, filename)
	cv2.imwrite(path, img)
	log.info("wrote debug image: %s", path)


def _order_pts(pts):
	rect = np.zeros((4, 2), dtype="float32")
	s = pts.sum(axis=1)
	diff = np.diff(pts, axis=1)
	rect[0] = pts[np.argmin(s)]
	rect[2] = pts[np.argmax(s)]
	rect[1] = pts[np.argmin(diff)]
	rect[3] = pts[np.argmax(diff)]
	return rect


def _four_point_transform(image, pts):
	rect = _order_pts(pts)
	tl, tr, br, bl = rect
	widthA = np.linalg.norm(br - bl)
	widthB = np.linalg.norm(tr - tl)
	maxW = int(max(widthA, widthB))
	heightA = np.linalg.norm(tr - br)
	heightB = np.linalg.norm(tl - bl)
	maxH = int(max(heightA, heightB))

	dst = np.array(
		[[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]], dtype="float32"
	)

	M = cv2.getPerspectiveTransform(rect, dst)
	warped = cv2.warpPerspective(
		image, M, (maxW, maxH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
	)
	return warped


def _detect_receipt_contour(gray):
	blur = cv2.GaussianBlur(gray, (5, 5), 0)
	edges = cv2.Canny(blur, 50, 150)
	cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
	cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
	for c in cnts:
		peri = cv2.arcLength(c, True)
		approx = cv2.approxPolyDP(c, 0.02 * peri, True)
		if len(approx) == 4:
			return approx.reshape(4, 2)
	return None


def _smart_deskew(gray):
	coords = np.column_stack(np.where(gray < 255))
	if coords.size == 0:
		return gray

	angle = cv2.minAreaRect(coords)[-1]
	if angle < -45:
		angle += 90

	if abs(angle) <= DESKEW_MAX_ANG:
		h, w = gray.shape
		M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
		return cv2.warpAffine(
			gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
		)
	else:
		log.debug("skip deskew: %.1f° outside ±%.1f°", angle, DESKEW_MAX_ANG)
		return gray


def extract_text(image_bytes: bytes) -> str:
	t0 = time.perf_counter()

	pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
	bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
	_debug_save(bgr, "1_original")

	small_gray = cv2.cvtColor(
		cv2.resize(bgr, (0, 0), fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY
	)
	quad = _detect_receipt_contour(small_gray)
	warped = _four_point_transform(bgr, quad * 2) if quad is not None else bgr.copy()
	_debug_save(warped, "2_warped")

	h, w = warped.shape[:2]
	if max(h, w) > MAX_EDGE:
		scale = MAX_EDGE / max(h, w)
		warped = cv2.resize(
			warped, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
		)
	_debug_save(warped, "3_resized")

	gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
	clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=(8, 8))
	gray = clahe.apply(gray)
	_debug_save(gray, "4_clahe")

	gray = _smart_deskew(gray)
	_debug_save(gray, "5_deskew")

	text = pytesseract.image_to_string(gray, lang="eng", config=TESS_CONFIG).strip()

	log.info("ocr time: %.2fs | %d chars", time.perf_counter() - t0, len(text))
	return text
