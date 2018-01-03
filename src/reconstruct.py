# ================================================
# Skeleton codes for HW5
# Read the skeleton codes carefully and put all your
# codes into function "reconstruct_from_binary_patterns"
# ================================================
import sys
import cv2
import pickle
import numpy as np
import matplotlib.pyplot as plt
from math import log, ceil, floor

color = []

def help_message():
	# Note: it is assumed that "binary_codes_ids_codebook.pckl", "stereo_calibration.pckl",
	# and images folder are in the same root folder as your "generate_data.py" source file.
	# Same folder structure will be used when we test your program
	print("Usage: [Output_Directory]")
	print("[Output_Directory]")
	print("Where to put your output.xyz")
	print("Example usages:")
	print(sys.argv[0] + " ./")

def reconstruct_from_binary_patterns():
	debug = False
	showInit = False
	showProjMask = False
	showOnMask = False

	scale_factor = 1.0
	ref_white = cv2.resize(cv2.imread("images/pattern000.jpg", cv2.IMREAD_GRAYSCALE) / 255.0, (0,0), fx=scale_factor,fy=scale_factor)
	ref_black = cv2.resize(cv2.imread("images/pattern001.jpg", cv2.IMREAD_GRAYSCALE) / 255.0, (0,0), fx=scale_factor,fy=scale_factor)
	ref_color = cv2.resize(cv2.imread("images/pattern001.jpg"), (0,0), fx=scale_factor,fy=scale_factor)
	ref_avg   = (ref_white + ref_black) / 2.0
	ref_on    = ref_avg + 0.05 # a threshold for ON pixels
	ref_off   = ref_avg - 0.05 # add a small buffer region
	h,w = ref_white.shape
	# debug block to visualize
	if debug and showInit:
		cv2.imshow("ref_white", ref_white)
		cv2.imshow("ref_black", ref_black)
		cv2.imshow("ref_avg", ref_avg)
		cv2.imshow("ref_on", ref_on)
		cv2.imshow("ref_off", ref_off)
		cv2.waitKey(0)

	# mask of pixels where there is projection
	proj_mask = (ref_white > (ref_black + 0.05)) # this is True/False array
	scan_bits = np.zeros((h,w), dtype=np.uint16)
	# debug block to visualize
	if debug and showProjMask:
		cv2.imshow("proj_mask", proj_mask.astype('uint8')*255)
		cv2.waitKey(0)

	# analyze the binary patterns from the camera
	for i in range(0,15):
		# read the file
		patt_gray = cv2.resize(cv2.imread("images/pattern%03d.jpg"%(i+2), cv2.IMREAD_GRAYSCALE) / 255.0, (0,0), fx=scale_factor,fy=scale_factor)

		# mask where the pixels are ON
		on_mask = (patt_gray > ref_on) & proj_mask
		if debug and showOnMask:
			cv2.imshow("patt_gray", patt_gray)
			cv2.imshow("on_mask", on_mask.astype('uint8')*255)
			cv2.waitKey(0)

		# this code corresponds with the binary pattern code
		bit_code = np.uint16(1 << i)

		# TODO: populate scan_bits by putting the bit_code according to on_mask
		on_mask_curr_bit = on_mask.astype('uint16')*bit_code
		scan_bits += on_mask_curr_bit

	print("load codebook")
	# the codebook translates from <binary code> to (x,y) in projector screen space
	with open("binary_codes_ids_codebook.pckl","r") as f:
		binary_codes_ids_codebook = pickle.load(f)

	# print( binary_codes_ids_codebook.keys() )
	camera_points = []
	projector_points = []
	corr_image = np.zeros((h,w,3), np.float32)
	for x in range(w):
		for y in range(h):
			if not proj_mask[y,x]:
				continue # no projection here
			if scan_bits[y,x] not in binary_codes_ids_codebook:
				continue # bad binary code

			# TODO: use binary_codes_ids_codebook[...] and scan_bits[y,x] to
			# TODO: find for the camera (x,y) the projector (p_x, p_y).
			# TODO: store your points in camera_points and projector_points
			# IMPORTANT!!! : due to differences in calibration and acquisition - divide the camera points by 2
			proj_x, proj_y = binary_codes_ids_codebook[scan_bits[y,x]]
			if proj_x>=1279 or proj_y>=799:
				continue
			projector_points.append( (proj_x, proj_y) )
			camera_points.append( (x/2.0, y/2.0) )
			color.append( (ref_color[y,x]) )
			corr_image[y,x] = (proj_x/1280.0, proj_y/800.0, 0)

	# save correspondence image
	plt.figure()
	plt.imshow(corr_image)
	plt.savefig('correspondence.jpg')

	# now that we have 2D-2D correspondances, we can triangulate 3D points!
	# load the prepared stereo calibration between projector and camera
	with open("stereo_calibration.pckl","r") as f:
		d = pickle.load(f)
		camera_K    = d['camera_K']
		camera_d    = d['camera_d']
		projector_K = d['projector_K']
		projector_d = d['projector_d']
		projector_R = d['projector_R']
		projector_t = d['projector_t']

	# convert to numpy array first
	camera_points = np.array(camera_points)[np.newaxis,:,:].astype(np.float32)
	projector_points = np.array(projector_points)[np.newaxis,:,:].astype(np.float32)

	# TODO: use cv2.undistortPoints to get normalized points for camera/projector
	camera_points = cv2.undistortPoints(camera_points, camera_K, camera_d)
	projector_points = cv2.undistortPoints(projector_points, projector_K, projector_d)

	# TODO: use cv2.triangulatePoints to triangulate the normalized points
	cam_mat = np.eye(3,4)
	proj_mat = np.hstack([projector_R,projector_t])
	homogenous_points = cv2.triangulatePoints(cam_mat, proj_mat, camera_points, projector_points)

	# TODO: use cv2.convertPointsFromHomogeneous to get real 3D points
	# TODO: name the resulted 3D points as "points_3d"
	points_3d = cv2.convertPointsFromHomogeneous(homogenous_points.T)
	return points_3d
	
def write_3d_points(points_3d):
	# ===== DO NOT CHANGE THIS FUNCTION =====
	print("write output point cloud")
	print(points_3d.shape)
	output_name = sys.argv[1] + "output.xyz"
	with open(output_name,"w") as f:
		for p in points_3d:
			if(p[0,2]>200 and p[0,2]<1400):
				f.write("%d %d %d\n"%(p[0,0],p[0,1],p[0,2]))

	index = 0
	output_name = sys.argv[1] + "output_color.xyz"
	with open(output_name,"w") as f:
		for p in points_3d:
			if(p[0,2]>150 and p[0,2]<1550):
				f.write("%d %d %d %d %d %d\n"%(p[0,0],p[0,1],p[0,2],color[index][2],color[index][1],color[index][0]))
			index += 1

	return points_3d

if __name__ == '__main__':
	# ===== DO NOT CHANGE THIS FUNCTION =====
	# validate the input arguments
	if (len(sys.argv) != 2):
		help_message()
		sys.exit()
	points_3d = reconstruct_from_binary_patterns()
	write_3d_points(points_3d)
