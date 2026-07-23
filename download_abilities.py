"""Find new pet ability icons, download and convert to 128x128 circular PNG"""
import requests, json, os, io
from PIL import Image, ImageDraw

headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://wiki.lcx.cab/lk/tujian.php'}
OUT = r'D:\homework\webHomework\期末\MD\新精灵图鉴数据整理'
ABILITIES_DIR = r'D:\homework\webHomework\期末\static\images\abilities'

# Load new pets
with open(os.path.join(OUT, 'new_pets.json'), 'r', encoding='utf-8') as f:
    new_pets = json.load(f)

# Get unique ability names
ability_names = set()
for p in new_pets:
    if p.get('ability_name'):
        ability_names.add(p['ability_name'])

print(f'Unique ability names needed: {len(ability_names)}')

# Check which already exist
existing = set()
for f in os.listdir(ABILITIES_DIR):
    name = f.rsplit('.', 1)[0]  # Remove extension
    existing.add(name)

need_download = ability_names - existing
already_have = ability_names & existing

print(f'Already exist: {len(already_have)}')
print(f'Need to download: {len(need_download)}')
for n in need_download:
    print(f'  {n}')

# Download missing ability icons from wiki
# Try the wiki's ability image URL pattern
base_url = 'https://wiki.lcx.cab/lk/imgs/abilities/'
downloaded = 0

for aname in need_download:
    # Try .webp first
    url = base_url + requests.utils.quote(aname) + '.webp'
    r = requests.get(url, headers=headers, timeout=10)
    
    if r.status_code != 200 or len(r.content) < 200:
        # Try .png
        url = base_url + requests.utils.quote(aname) + '.png'
        r = requests.get(url, headers=headers, timeout=10)
    
    if r.status_code == 200 and len(r.content) > 200:
        # Load image
        try:
            img = Image.open(io.BytesIO(r.content))
            
            # Convert to 128x128 circular PNG
            img = img.convert('RGBA')
            img = img.resize((128, 128), Image.LANCZOS)
            
            # Create circular mask
            mask = Image.new('L', (128, 128), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 128, 128), fill=255)
            
            # Apply mask
            output = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
            output.paste(img, (0, 0), mask)
            
            # Save as PNG
            save_path = os.path.join(ABILITIES_DIR, aname + '.png')
            output.save(save_path, 'PNG')
            downloaded += 1
            print(f'  Downloaded & converted: {aname} -> {os.path.getsize(save_path)} bytes')
        except Exception as e:
            print(f'  Failed to process {aname}: {e}')
    else:
        print(f'  Image not found: {aname}')
    
    import time
    time.sleep(0.3)

print(f'\nTotal downloaded & converted: {downloaded}')
