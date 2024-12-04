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

codes = [
	'110000000000000000000011000000000000000000000000000000000000001100000000000011000000000000000000000000001100000000000000001100000000',
	'001100000000000000000000000011000000000000000011000000000000000000000000000000000000110000000011000000000000000000001100000000000000',
	'000011000000000000000000000000000000000000110000000000000000000011000000000000001100000011000000000000000000001100000000000000000000',
	'000000110000000000000000000000110000000000000000000000110000000000000011000000000000000000000000000011000000000000000000110000000000',
	'000000001100000000000000000000000000110000000000110000000000000000000000110000000000000000001100000000000000000000000000000000001100',
	'000000000011000000000000000000001100000000001100000000000000000000001100000000000000000000000000110000000000000000000000000000000011',
	'000000000000110000000000000000000000000011000000001100000000000000000000000000110000000000000000000000000000110000110000000000000000',
	'000000000000001100000000000000000011000000000000000011000000000000000000000000000000001100000000000000000011000011000000000000000000',
	'000000000000000011000000001100000000000000000000000000000011000000000000000000000011000000110000000000000000000000000011000000000000',
	'000000000000000000110000110000000000000000000000000000000000110000110000000000000000000000000000000000110000000000000000000011000000',
	'000000000000000000001100000000000000001100000000000000001100000000000000001100000000000000000000001100000000000000000000000000110000'
 ]

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

def get_codes(layout):
	if layout == "single":
		#return code[0]
		return gen_code(offset=10)
	if layout == "simple":
		#return " ".join(codes[0:5])
		return " ".join(gen_codes(5))
	if layout == "grid":
		#return " ".join(codes[0:9])
		return " ".join(gen_codes(9))
	if layout == "keyboard":
		#return " ".join(codes)
		return " ".join(gen_codes(11))

def get_codes(layout, static=False):
	if layout == "single":
		return codes[0] if static else gen_code(offset=10)
	if layout == "simple":
		return " ".join(codes[0:5]) if static else " ".join(gen_codes(5))
	if layout == "grid":
		return " ".join(codes[0:9]) if static else " ".join(gen_codes(9))
	if layout == "keyboard":
		return " ".join(codes) if static else " ".join(gen_codes(11))


# For reproducibility
seed = int(os.getenv("SEED", time.time_ns()))
logger.info(f"Random seed: {seed}")
random.seed(seed)

# Get or generate codes
static = not(int(os.getenv("DYNAMIC_CODES", "1")))
os.environ["CALIBRATION_CODES"] = get_codes(os.getenv("CALIBRATION_LAYOUT", "single"), static);
os.environ["TASK_CODES"] = get_codes(os.getenv("TASK_LAYOUT", "simple"), static);
logger.debug(os.environ["TASK_CODES"])
