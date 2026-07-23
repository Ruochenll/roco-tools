"""Find ability icon references in detail page"""
import requests, re

url = 'https://wiki.lcx.cab/lk/detail.php?name=' + requests.utils.quote('钨丝贝贝')
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
html = r.text

# Find abilities section
idx = html.find('abilities-section')
if idx > 0:
    section = html[idx:idx+800]
    print('=== Abilities section HTML ===')
    print(section)

# Find all img tags in abilities context  
matches = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', html)
print(f'\n=== All unique image sources ===')
ability_related = [m for m in matches if 'abilit' in m.lower() or 'trait' in m.lower() or 'skill' in m.lower()]
for a in ability_related:
    print(f'  {a}')

# Check the API return data for ability_icon
print('\n=== Checking API data ===')
import requests as req2
r2 = req2.get('https://wiki.lcx.cab/lk/get_pokemon_data.php?page=53&exclude_details=1&hide_not_released=0', 
              headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
data = r2.json()
for p in data:
    tid = int(p['t_id'])
    if tid == 348:
        print(f'API has fields: {list(p.keys())}')
        break
