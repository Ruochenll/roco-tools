"""Check reference ability icon size"""
from PIL import Image
import os

dir_path = r'D:\homework\webHomework\期末\static\images\abilities'

# List files containing 国王
for f in os.listdir(dir_path):
    if '国王' in f:
        ref_path = os.path.join(dir_path, f)
        print(f'File: {f}')
        img = Image.open(ref_path)
        print(f'Size: {img.size}, Mode: {img.mode}')
        break
