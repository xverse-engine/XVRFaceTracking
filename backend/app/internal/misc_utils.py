import os
import platform
import cv2
import re
# Detect the operating system
is_nt = os.name == "nt"
os_type = platform.system()
 

def is_valid_float_input(value):
    # Allow empty string, negative sign, or a float number
    return bool(re.match(r"^-?\d*\.?\d*$", value))

def is_valid_int_input(value):
    # Allow empty string, negative sign, or an integer number
    return bool(re.match(r"^-?\d*$", value))

# Handle debugging virtual envs.
def EnsurePath():
    if os.path.exists(os.path.join(os.getcwd(), "BabbleApp")):
        os.chdir(os.path.join(os.getcwd(), "BabbleApp"))
