import os
import logging
import random
import time
import subprocess

logger = logging.getLogger("timeflux")

try:
	version = subprocess.check_output(["git", "describe", "--tags"]).strip().decode()
	logger.info(f"Application version: {version}")
except:
	pass


# RB_Burst_2200_1f_150_5C_Correlation02 4 STARS DOUBLE BURST!!!!
# codes = ['110000000001100000000000011000000000000110000000001100000000011000000000110000000000011000000000110000000001100000000000011000000000',
#  '000000000110000000000110000000001100000000001100000000011000000000110000000000110000000000110000000000110000000000000110000000000011',
#  '000001100000000011000000000000001100000000011000000000001100000000011000000000110000000001100000000000110000000000011000000000110000',
#  '000000000000000001100000000011000000000110000000001100000000011000000000011000000000110000000001100000000011000000000110000000001100',
#  '000110000000000110000000001100000000011000000000011000000000011000000000000000110000000001100000000011000000000001100000000011000000']


# RB_Burst_2200_2f_175_5
# codes = [
#  '000000000001100000000001100000000001100000000001100000000000110000000000001100000000001100000000000000001100000000001100000000001100',
#  '000000011000000000000011000000000000011000000000011000000000011000000000011000000000000011000000000001100000000001100000000001100000',
#  '001100000000001100000000000001100000000001100000000001100000000000011000000000000110000000000110000000000001100000000001100000000000',
#  '000000110000000000001100000000000110000000000011000000000000110000000000110000000000110000000000001100000000001100000000000011000000',
#  '011000000000001100000000000110000000000000000110000000000011000000000001100000000001100000000001100000000000110000000000011000000000']


# Lowest
# codes = [
#  '110000000000000000000011000000000000000000000000000000000000001100000000000011000000000000000000000000001100000000000000001100000000',
#  '001100000000000000000000000011000000000000000011000000000000000000000000000000000000110000000011000000000000000000001100000000000000',
#  '000011000000000000000000000000000000000000110000000000000000000011000000000000001100000011000000000000000000001100000000000000000000',
#  '000000110000000000000000000000110000000000000000000000110000000000000011000000000000000000000000000011000000000000000000110000000000',
#  '000000001100000000000000000000000000110000000000110000000000000000000000110000000000000000001100000000000000000000000000000000001100',
#  '000000000011000000000000000000001100000000001100000000000000000000001100000000000000000000000000110000000000000000000000000000000011',
#  '000000000000110000000000000000000000000011000000001100000000000000000000000000110000000000000000000000000000110000110000000000000000',
#  '000000000000001100000000000000000011000000000000000011000000000000000000000000000000001100000000000000000011000011000000000000000000',
#  '000000000000000011000000001100000000000000000000000000000011000000000000000000000011000000110000000000000000000000000011000000000000',
#  '000000000000000000110000110000000000000000000000000000000000110000110000000000000000000000000000000000110000000000000000000011000000',
#  '000000000000000000001100000000000000001100000000000000001100000000000000001100000000000000000000001100000000000000000000000000110000'] 

#G1
# codes = [
#  '110000000000000000000011000000000000000000000000000000000000001100000000000011000000000000000000000000001100000000000000000011000000',
#  '001100000000000000000000000011000000000000000011000000000000000000000000000000000000110000000011000000000000000000001100000000000000',
#  '000000110000000000000000000000110000000000000000000000110000000000000011000000000000000000000000000011000000000000000000110000000000',
#  '000000001100000000000000000000000000110000000000001100000000000000000000110000000000000000001100000000000000000000000000000000001100',
#  '000011000000000000000000000000000000000000110000000000000000000011000000000000001100000000000000011000000000001100000000000000000000',
#  '000000000011000000000000000000001100000000001100000000000000000000001100000000000000000000000000110000000000000000000000000000000011']

#G2
codes = [
 '110000000000000000000011000000000000000000000000000000000000001100000000000011000000000000000000000000001100000000000000000011000000',
 '001100000000000000000000000011000000000000000011000000000000000000000000000000000000110000000011000000000000000000001100000000000000',
 '000000110000000000000000000000001100000000000000000000110000000000000011000000000000000000000000000011000000000000000000110000000000',
 '000000000000000110000000000000000000011000000000001100000000000000000000011000000000000000001100000000000000000000000000000000001100',
 '000011000000000000000000000000000000000000110000000000000000000001100000000000011000000000000000011000000000001100000000000000000000',
 '000000000011000000000000110000000000000000001100000000000000000000001100000000000000000011000000000000000000000000000000000000000011']
 

#RB_Burst_2200_1f_116_5.npy ZERO STAR TOO FAST
# codes = ['100000001000000001000000010000000100000001000000010000000100000001000000010000000100000001000000000010000000100000001000000010000000',
#  '000010000000100000001000000010000000001000000010000000100000001000000010000000001000000010000000100000001000000010000000100000001000',
#  '010000000100000001000000010000000001000000010000000100000001000000010000000001000000010000000100000001000000010000000100000001000000',
#  '000000100000001000000010000000100000000010000000100000001000000010000000100000000010000000100000001000000010000000100000001000000010',
#  '000100000001000000001000000001000000010000000100000001000000010000000010000000010000000100000001000000010000000100000001000000010000']

# RB_Burst_2200_1f_150_5 3STARS!!!!
# codes =['010000000000100000000000100000000000100000000000100000000000010000000000001000000000001000000000001000000000001000000000001000000000',
#  '000000100000000000100000000000100000000001000000000000100000000000100000000001000000000010000000000010000000000000001000000000010000',
#  '001000000000010000000000000010000000000100000000001000000000010000000000100000000000100000000000010000000000100000000000000100000000',
#  '000000010000000000010000000000000010000000000010000000000100000000000100000000000100000000000100000000001000000000010000000000010000',
#  '000000001000000000001000000000001000000000010000000000001000000000001000000000010000000000100000000000100000000000000010000000000100']

# RB_Burst_2200_1f_150_5C_Correlation02 4STARS!!!!
# codes = ['100000000001000000000000010000000000000100000000001000000000010000000000100000000000010000000000100000000001000000000000010000000000',
#  '000000000100000000000100000000001000000000001000000000010000000000100000000000100000000000100000000000100000000000000100000000000010',
#  '000001000000000010000000000000001000000000010000000000001000000000010000000000100000000001000000000000100000000000010000000000100000',
#  '000000000000000001000000000010000000000100000000001000000000010000000000010000000000100000000001000000000010000000000100000000001000',
#  '000100000000000100000000001000000000010000000000010000000000010000000000000000100000000001000000000010000000000001000000000010000000']

# PRI_Burst2200_2f_40_5Class
# codes = ['000000001000000000000000000000000000100000001000000000000000000000000000100000000000100000000000000010000000000000000000000000000000',
#  '000000000000000010000000100000000000000000000000000010000000000000001000000000000000000000000000100000000000000010000000000000001000',
#  '000000000000100000000000000010000000000010000000000000000000000000000000000010000000000010000000000000001000000000000000100000000000',
#  '000010000000000000000000000000001000000000000000100000000000000010000000000000001000000000000000000000000000000000001000000000000000',
#  '100000000000000000001000000000000000000000000000000000001000100000000000000000000000000000001000000000000000100000000000000010000000']

# RB_Burst_2200_1f_200_5
# codes = ['000000010000000000000000100000000000001000000000000010000000000000000000100000000000000100000000000000000000000100000000000001000000',
#  '100000000000001000000000000010000000000000100000000000001000000000000010000000000000100000000000001000000000000000010000000000000000',
#  '000100000000000000000001000000000000010000000000000100000000000001000000000000010000000000000100000000000001000000000000010000000000',
#  '000000000000100000000000000000001000000000000010000000000000100000000000000010000000000000000000100000000000000000100000000000000010',
#  '100000000000001000000000000000001000000000000000100000000000001000000000000010000000000000100000000000001000000000000010000000000000']

# RB_Burst_2200_1f_150_5C_Correlation01!!!!
# codes = ['000000001000000000000000000000000000100000001000000000000000000000000000100000000000100000000000000010000000000000000000000000000000',
#  '000000000000000010000000100000000000000000000000000010000000000000001000000000000000000000000000100000000000000010000000000000001000',
#  '000000000000100000000000000010000000000010000000000000000000000000000000000010000000000010000000000000001000000000000000100000000000',
#  '000010000000000000000000000000001000000000000000100000000000000010000000000000001000000000000000000000000000000000001000000000000000',
#  '100000000000000000001000000000000000000000000000000000001000100000000000000000000000000000001000000000000000100000000000000010000000']
 

#HOMEMADE 1!!!!
# codes = ['000000000000100000000000100000000000100000000000100000000000010000000000001000000000001000000000001000000000001000000000000000000001',
#  '000000100000000000100000000000100000000001000000000000100000000000100000000001000000000010000000000010000000000000001000000000010000',
#  '000000010000000000010000000000000010000000000010000000000100000000000100000000000100000000000100000000001000000000010000000000010000',
#  '000000000100000000000100000000001000000000001000000000010000000000100000000000100000000000100000000000100000000000000100000000000010',
#  '100000000001000000000000010000000000000100000000001000000000010000000000100000000000010000000000100000000001000000000000010000000000']

#HOMEMADE 2 4-STARS!!!!
# codes = ['000000000100000000000001000000000010000000001000000000010000000000100000000000100000000000100000000000000100000000000100000000000010',
# '000000000000100000000010000000010000000000000000100000000000010000000000100000000000000100000000001000000000000000100000000000000001',
# '100000000001000000000000010000000000000100000000001000000000010000000000100000000000010000000001000000000000010000000000010000000000',
# '000000100000000000100000000000100000000001000000000000100000000000100000000001000000000010000000000010000000000000001000000001000000',
# '100000000000000100000000000000000010000000000000100000000100000000000100000000000100000000000100000000001000000001000000000000001000',]


#HOMEMADE 2BIS!!!!
# codes = [
# '000000000100000000000001000000000010000000001000000000010000000000100000000000100000000000100000000000000100000000000100000000000010',
# '000000000000100000000010000000010000000000000000100000000000010000000000100000000000000100000000001000000000000000100000000000000001',
# '100000000001000000000000010000000000000100000000001000000000010000000000100000000000010000000001000000000000010000000000010000000000',
# '000000100000000000100000000000100000000001000000000000100000000000100000000001000000000010000000000010000000000100000000000001000000',
# '100000000000000100000000000000000010000000000000100000000100000000000100000000000100000000000100000000001000000001000000000000001000']


# PRI 1 40 5
# codes = ['100000000000000000000000100000000000000010000000000000000000000010000000000000000000000010000000000010000000000000000000000010000000',
#  '000000000000000010000000000010000000000000000000100000000000100000000000000000001000000000000000000000000000100000000000000000001000',
#  '000000000000100000001000000000000000000000000000000000001000000000000000100000000000000000000000100000001000000000000000100000000000',
#  '000000001000000000000000000000000000100000000000000010000000000000001000000000000000100000000000000000000000000000001000000000000000',
#  '000010000000000000000000000000001000000000001000000000000000000000000000000010000000000000001000000000000000000010000000000000000000']

# # RB 200 5
# codes = ['000000010000000000000000100000000000001000000000000010000000000000000000100000000000000100000000000000000000000100000000000001000000',
#  '100000000000001000000000000010000000000000100000000000001000000000000010000000000000100000000000001000000000000000010000000000000000',
#  '000100000000000000000001000000000000010000000000000100000000000001000000000000010000000000000100000000000001000000000000010000000000',
#  '000000000000100000000000000000001000000000000010000000000000100000000000000010000000000000000000100000000000000000100000000000000010',
#  '100000000000001000000000000000001000000000000000100000000000001000000000000010000000000000100000000000001000000000000010000000000000']

#RB 150 5 PAS MAL!! 
# codes = ['001000000000001000000000010000000000001000000000010000000000010000000000100000000000010000000000100000000000001000000000010000000000',
#  '001000000000010000000000010000000000010000000000001000000000001000000000000100000000001000000000000010000000000100000000000100000000',
#  '010000000000010000000000010000000000100000000001000000000010000000000010000000000100000000000000000010000000000100000000001000000000',
#  '000000000100000000001000000000000100000000001000000000010000000000100000000001000000000000100000000000100000000000000100000000000010',
#  '000000100000000000010000000000001000000000010000000000000000100000000001000000000001000000000010000000000100000000001000000000010000']



# # PRI_Burst2200_1f_40_5Class 
# codes = ['000000001000000000000000000000000000100000001000000000000000000000000000100000000000100000000000000010000000000000000000000000000000',
#  '000000000000000010000000100000000000000000000000000010000000000000001000000000000000000000000000100000000000000010000000000000001000',
#  '000000000000100000000000000010000000000010000000000000000000000000000000000010000000000010000000000000001000000000000000100000000000',
#  '000010000000000000000000000000001000000000000000100000000000000010000000000000001000000000000000000000000000000000001000000000000000',
#  '100000000000000000001000000000000000000000000000000000001000100000000000000000000000000000001000000000000000100000000000000010000000']

#OIR 1 10 11
# codes = [
# 	"000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000",
# 	"001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000",
# 	"000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000",
# 	"000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000",
# 	"100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000",
# 	"000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000",
# 	"000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000",
# 	"000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000",
# 	"000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000",
# 	"000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000",
# 	"000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010",
# ]

# PRI2200 2frames 20ms Ratio=1 5classes
# codes = ['110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000',
#  '000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000',
#  '000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000',
#  '000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110',
#  '000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000000000110000000']

# PRI2200 2frames 40ms Ratio=1 5classes
# codes = ['000011000000000000000000110000000000000000001100000000000000000011000000000000000000110000000000000000001100000000000000000011000000',
#  '110000000000000000001100000000000000000011000000000000000000110000000000000000001100000000000000000011000000000000000000110000000000',
#  '000000000000110000000000000000001100000000000000000011000000000000000000110000000000000000001100000000000000000011000000000000000000',
#  '000000001100000000000000000011000000000000000000110000000000000000001100000000000000000011000000000000000000110000000000000000001100',
#  '000000000000000011000000000000000000110000000000000000001100000000000000000011000000000000000000110000000000000000001100000000000000']

# PRI2200 2frames 20ms Ratio=0.5 5classes
# codes = ['000000011000000000000000000000110000000000000001100000000000000110000000000000000001100000000000000000000110000000000000000000000110',
#  '110000000000000000001100000000000000000001100000000000000110000000000000000001100000000000000001100000000000000000000000001100000000',
#  '000011000000000000000000000110000000000000001100000000000000110000000000000000001100000000000000001100000000000000000000000001100000',
#  '000000000011000000000000000000000110000000000000000110000000000000011000000000000000000001100000000000000000011000000000000000000000',
#  '000000000000000001100000000000000000001100000000000000110000000000000011000000000000000000001100000000000000000000000011000000000000']

# PRI2200 2frames 40ms Ratio=0.5 5classes
# codes =['000000000000000011000000000000000000000011000000000000000000001100000000000000000001100000000000000000000000000000000110000000000000',
#  '000000000000000000001100000000000000000000001100000000000000000000110000000000000000000000000000001100000000000000000000011000000000',
#  '000000000001100000000000000000001100000000000000000000001100000000000000000000110000000000000000000000000000000001100000000000000000',
#  '110000000000000000000000110000000000000000000000110000000000000000000011000000000000000000000000000000000110000000000000000000000000',
#  '000000110000000000000000000011000000000000000000000011000000000000000000001100000000000000000000000000000000011000000000000000000000']


def gen_code(length=132, bursts=6, jitter=3, offset=0):
	code = ["0"] * length
	for frame in range(offset, length, int(length / bursts)):
		frame += random.randint(-jitter, jitter)
		if frame < 0: frame = 0
		if frame > length - 1: frame = length - 1
		code[frame] = "1"
	code = "".join(code)
	return code

def gen_codes(n, length=132, bursts=6, jitter=3):
	codes = []
	offset = length / bursts / n
	for i in range(n):
		codes.append(gen_code(length, bursts, jitter, round(offset * i)))
	random.shuffle(codes)
	return codes

def get_codes(layout, style):
	if layout == "single":
		return codes[0] if style == "static" else gen_code(offset=10)
	if layout == "simple":
		return " ".join(codes[0:5]) if style == "static" else " ".join(gen_codes(5))
	if layout == "grid":
		return " ".join(codes[0:9])if style == "static" else " ".join(gen_codes(9))
	if layout == "keyboard":
		return " ".join(codes) if style == "static" else " ".join(gen_codes(11))

# For reproducibility
seed = int(os.getenv("SEED", time.time_ns()))
logger.info(f"Random seed: {seed}")
random.seed(seed)

codestyle = os.getenv("CODE_STYLE", "gen")
os.environ["CALIBRATION_CODES"] = get_codes(os.getenv("CALIBRATION_LAYOUT", "single"), codestyle);
os.environ["TASK_CODES"] = get_codes(os.getenv("TASK_LAYOUT", "simple"), codestyle);
logger.debug(os.environ["TASK_CODES"])
