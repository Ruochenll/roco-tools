"""Check reference ability icon size and list abilities"""
from PIL import Image
import os

# The actual filename has quotes in it
ref_path = r'static\images\abilities\"国王"的威严.png'
img = Image.open(ref_path)
print(f'Reference: {img.size}, mode={img.mode}')

# Check what abilities folder looks like
all_files = os.listdir(r'static\images\abilities')
print(f'Total ability icons: {len(all_files)}')
print(f'Sample: {all_files[:3]}')
