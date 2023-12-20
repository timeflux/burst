import os
import logging
import subprocess

logger = logging.getLogger("timeflux")
logger.info(subprocess.check_output(["git", "describe", "--tags"]).strip().decode())

codes = [
	"000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000",
	"001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000",
	"000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000",
	"000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000",
	"100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000",
	"000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000",
	"000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000",
	"000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000",
	"000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000",
	"000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000",
	"000000000000000000001000000000000000000000100000000000000000000010000000000000000000001000000000000000000000100000000000000000000010",
]

def get_codes(layout):
	if layout == "single":
		return codes[0]
	if layout == "simple":
		return " ".join(codes[0:5])
	if layout == "keyboard":
		return " ".join(codes[0:11])

os.environ["CALIBRATION_CODES"] = get_codes(os.getenv("CALIBRATION_LAYOUT", "single"));
os.environ["TASK_CODES"] = get_codes(os.getenv("TASK_LAYOUT", "simple"));
