import os
import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt


def load_image(path):
	if not os.path.isabs(path):
		# make path relative to script location
		script_dir = os.path.dirname(os.path.abspath(__file__))
		path = os.path.abspath(os.path.join(script_dir, '..', path))
	img = cv.imread(path)
	if img is None:
		raise FileNotFoundError(f"无法读取图片: {path}")
	return img


def detect_and_compute(img):
	gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
	# try SIFT, fallback to ORB
	try:
		sift = cv.SIFT_create()
		kp, des = sift.detectAndCompute(gray, None)
		descriptor_type = 'SIFT'
	except Exception:
		orb = cv.ORB_create(5000)
		kp, des = orb.detectAndCompute(gray, None)
		descriptor_type = 'ORB'
	return kp, des, descriptor_type


def match_descriptors(des1, des2, descriptor_type='SIFT'):
	if descriptor_type == 'SIFT':
		bf = cv.BFMatcher(cv.NORM_L2)
	else:
		bf = cv.BFMatcher(cv.NORM_HAMMING)
	# KNN match and ratio test
	matches = bf.knnMatch(des1, des2, k=2)
	good = []
	for m, n in matches:
		if m.distance < 0.75 * n.distance:
			good.append(m)
	return good


def compute_homography(kp1, kp2, matches, reprojThresh=4.0):
	if len(matches) < 4:
		return None, None
	ptsA = np.float32([kp1[m.queryIdx].pt for m in matches])
	ptsB = np.float32([kp2[m.trainIdx].pt for m in matches])
	H, status = cv.findHomography(ptsB, ptsA, cv.RANSAC, reprojThresh)
	return H, status


def create_panorama(img1, img2, H):
	# warp img2 into img1 coordinate space
	(h1, w1) = img1.shape[:2]
	(h2, w2) = img2.shape[:2]
	# corners of img2
	corners_img2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
	warped_corners = cv.perspectiveTransform(corners_img2, H)
	all_corners = np.concatenate((np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2), warped_corners), axis=0)
	[xmin, ymin] = np.int32(all_corners.min(axis=0).ravel() - 0.5)
	[xmax, ymax] = np.int32(all_corners.max(axis=0).ravel() + 0.5)
	translation = [-xmin, -ymin]
	H_trans = np.array([[1, 0, translation[0]], [0, 1, translation[1]], [0, 0, 1]])
	result = cv.warpPerspective(img2, H_trans.dot(H), (xmax - xmin, ymax - ymin))
	result[translation[1]:h1 + translation[1], translation[0]:w1 + translation[0]] = img1
	return result


def draw_matches(img1, img2, kp1, kp2, matches, status=None, max_draw=200):
	# create a concatenated image
	h1, w1 = img1.shape[:2]
	h2, w2 = img2.shape[:2]
	height = max(h1, h2)
	vis = np.zeros((height, w1 + w2, 3), dtype=np.uint8)
	vis[:h1, :w1] = img1
	vis[:h2, w1:w1 + w2] = img2

	# draw lines
	drawn = 0
	for i, m in enumerate(matches):
		if drawn >= max_draw:
			break
		if status is not None and status[i] == 0:
			# outlier in homography estimation -> draw in red (optional)
			color = (0, 0, 255)
		else:
			color = tuple(np.random.randint(0, 255, 3).tolist())
		pt1 = (int(kp1[m.queryIdx].pt[0]), int(kp1[m.queryIdx].pt[1]))
		pt2 = (int(kp2[m.trainIdx].pt[0] + w1), int(kp2[m.trainIdx].pt[1]))
		cv.circle(vis, pt1, 4, color, 1, cv.LINE_AA)
		cv.circle(vis, pt2, 4, color, 1, cv.LINE_AA)
		cv.line(vis, pt1, pt2, color, 1, cv.LINE_AA)
		drawn += 1
	return vis


def select_top_matches(matches, kp1, kp2, topN=50):
	"""Select top-N matches by keypoint response (sum of responses of the pair).

	Returns a list of matches sorted by descending saliency.
	"""
	if not matches:
		return []
	scored = []
	for m in matches:
		r1 = kp1[m.queryIdx].response if kp1[m.queryIdx] is not None else 0
		r2 = kp2[m.trainIdx].response if kp2[m.trainIdx] is not None else 0
		score = (r1 + r2) / 2.0
		scored.append((score, m))
	scored.sort(key=lambda x: x[0], reverse=True)
	top = [m for _, m in scored[:topN]]
	return top

def main():
	# image paths relative to repository root (script uses parent dir)
	img1 = load_image('Image/image2.1.jpg')
	img2 = load_image('Image/image2.2.jpg')

	kp1, des1, dtype1 = detect_and_compute(img1)
	kp2, des2, dtype2 = detect_and_compute(img2)

	# prefer descriptor type of first image; if different fallback to SIFT/ORB selection
	descriptor_type = dtype1 if dtype1 == dtype2 else ('SIFT' if 'SIFT' in (dtype1, dtype2) else 'ORB')

	good_matches = match_descriptors(des1, des2, descriptor_type=descriptor_type)
	print(f"找到匹配对: {len(good_matches)}")

	if len(good_matches) < 4:
		print("匹配点太少，无法计算单应矩阵。")
		# still draw matches
		top_matches = select_top_matches(good_matches, kp1, kp2, topN=50)
		matches_img = draw_matches(img1, img2, kp1, kp2, top_matches)
		out_matches = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Image', 'matches_visualization.jpg'))
		cv.imwrite(out_matches, matches_img)
		print(f"已保存匹配可视化到: {out_matches}")
		# show
		plt.figure(figsize=(12, 6))
		plt.imshow(cv.cvtColor(matches_img, cv.COLOR_BGR2RGB))
		plt.axis('off')
		plt.title('Feature matches (insufficient for homography)')
		plt.show()
		return

	H, status = compute_homography(kp1, kp2, good_matches)
	if H is None:
		print("单应矩阵估计失败")
		return

	panorama = create_panorama(img1, img2, H)

	# draw matches with status mask (flattened) but only top-N most salient
	status_flat = status.flatten() if status is not None else None
	top_matches = select_top_matches(good_matches, kp1, kp2, topN=50)
	# If status is provided, we need to pass a status array aligned to top_matches
	if status_flat is not None and len(status_flat) == len(good_matches):
		# build a mapping from match to its original index to extract corresponding status
		match_to_idx = {id(m): i for i, m in enumerate(good_matches)}
		top_status = [status_flat[match_to_idx[id(m)]] if id(m) in match_to_idx else 0 for m in top_matches]
	else:
		top_status = None
	matches_img = draw_matches(img1, img2, kp1, kp2, top_matches, status=top_status)

	# save outputs
	out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Image'))
	os.makedirs(out_dir, exist_ok=True)
	out_panorama = os.path.join(out_dir, 'panorama_result.jpg')
	out_matches = os.path.join(out_dir, 'matches_visualization.jpg')
	cv.imwrite(out_panorama, panorama)
	cv.imwrite(out_matches, matches_img)
	print(f"已保存拼接图: {out_panorama}")
	print(f"已保存匹配可视化: {out_matches}")

	# display using matplotlib (convert BGR->RGB)
	plt.figure(figsize=(16, 8))
	plt.subplot(1, 2, 1)
	plt.imshow(cv.cvtColor(panorama, cv.COLOR_BGR2RGB))
	plt.title('Panorama')
	plt.axis('off')

	plt.subplot(1, 2, 2)
	plt.imshow(cv.cvtColor(matches_img, cv.COLOR_BGR2RGB))
	plt.title('Feature Matches')
	plt.axis('off')

	plt.tight_layout()
	plt.show()


if __name__ == '__main__':
	main()
