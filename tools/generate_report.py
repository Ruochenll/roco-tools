"""
S1 vs S2 差异报告HTML生成器
读取 diff_report.json 生成可视化对比报告页面
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
S2_DIR = BASE_DIR / 'MD' / 's2_data'


def load_report():
    with open(S2_DIR / 'diff_report.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_pet_section(report):
    """生成精灵差异HTML"""
    pet_diff = report['pets']
    summary = report['summary']
    
    # 汇总卡片
    html = '''
    <div class="section" id="pets">
        <h2>🐾 精灵图鉴变更</h2>
        <div class="info-banner">
            S1: {s1_total} 总数 ({s1_valid} 有效 + {s1_empty} 空壳) → 
            S2: {s2_total} 总数 ({s2_valid} 有效 + {s2_empty} 空壳)
        </div>
        <div class="summary-cards">
            <div class="card card-total">
                <div class="card-num">{s2_valid}</div>
                <div class="card-label">S2 有效精灵</div>
            </div>
            <div class="card card-new">
                <div class="card-num">+{n_added}</div>
                <div class="card-label">新增精灵</div>
            </div>
            <div class="card card-changed">
                <div class="card-num">{n_changed}</div>
                <div class="card-label">数值变更</div>
            </div>
            <div class="card card-removed">
                <div class="card-num">-{n_removed}</div>
                <div class="card-label">S2移除</div>
            </div>
        </div>
    '''.format(
        s1_total=summary['s1_total_pets'],
        s1_valid=summary['s1_valid_pets'],
        s1_empty=summary['s1_empty_pets'],
        s2_total=summary['s2_total_pets'],
        s2_valid=summary['s2_valid_pets'],
        s2_empty=summary['s2_empty_pets'],
        n_added=summary['pet_added'],
        n_changed=summary['pet_changed'],
        n_removed=summary['pet_removed'],
    )
    
    # 新增精灵列表
    if pet_diff['added']:
        html += '<div class="sub-section"><h3>🟢 新增精灵（有效）</h3><div class="pet-grid">'
        for entry in pet_diff['added']:
            name = entry['name'] if isinstance(entry, dict) else entry
            html += f'<span class="tag tag-new">{name}</span>'
        html += '</div></div>'
    
    # 空壳新增
    if pet_diff.get('added_empty'):
        html += '<div class="sub-section"><h3>⚪ 新增（空壳/无数据）</h3><div class="pet-grid">'
        for entry in pet_diff['added_empty']:
            name = entry['name'] if isinstance(entry, dict) else entry
            html += f'<span class="tag tag-empty">{name}</span>'
        html += '</div></div>'
    
    # 变更精灵（重要！）
    if pet_diff['changed']:
        html += '<div class="sub-section"><h3>🟡 数值变更</h3>'
        html += '<input type="text" class="search-box" placeholder="搜索精灵名称..." oninput="filterTable(this, \'pet-changes\')">'
        html += '<div class="table-wrapper"><table id="pet-changes"><thead><tr>'
        html += '<th>精灵名称</th><th>变更字段</th><th>S1值</th><th>S2值</th><th>变化</th>'
        html += '</tr></thead><tbody>'
        
        for pet in pet_diff['changed']:
            name = pet['name']
            for i, change in enumerate(pet['changes']):
                field_label = f'{change["label"]}'
                old_val = str(change['old'])
                new_val = str(change['new'])
                
                # 数值变化带颜色
                delta_html = ''
                if 'delta' in change:
                    delta = change['delta']
                    if isinstance(delta, (int, float)):
                        if delta > 0:
                            delta_html = f'<span class="delta-up">+{delta}</span>'
                        elif delta < 0:
                            delta_html = f'<span class="delta-down">{delta}</span>'
                        else:
                            delta_html = f'<span class="delta-same">0</span>'
                
                # 只用一行
                rowspan = f' rowspan="{len(pet["changes"])}"' if i == 0 else ''
                name_cell = f'<td{rowspan} class="pet-name-cell"><strong>{name}</strong></td>' if i == 0 else ''
                
                html += f'<tr>{name_cell}<td>{field_label}</td><td class="old">{old_val}</td><td class="new">{new_val}</td><td>{delta_html}</td></tr>'
        
        html += '</tbody></table></div></div>'
    
    # 移除精灵
    if pet_diff['removed']:
        html += '<div class="sub-section"><h3>🔴 S2中移除（有效）</h3><div class="pet-grid">'
        for entry in pet_diff['removed'][:100]:
            name = entry['name'] if isinstance(entry, dict) else entry
            html += f'<span class="tag tag-removed">{name}</span>'
        if len(pet_diff['removed']) > 100:
            html += f'<span class="tag tag-more">...还有{len(pet_diff["removed"]) - 100}个</span>'
        html += '</div></div>'
    
    html += '</div>'
    return html


def generate_skill_section(report):
    """生成技能差异HTML"""
    skill_diff = report['skills']
    
    html = '''
    <div class="section" id="skills">
        <h2>⚔️ 技能变更</h2>
        <div class="summary-cards">
            <div class="card card-total">
                <div class="card-num">{s2_total}</div>
                <div class="card-label">S2 技能总数</div>
            </div>
            <div class="card card-new">
                <div class="card-num">+{n_added}</div>
                <div class="card-label">新增技能</div>
            </div>
            <div class="card card-changed">
                <div class="card-num">{n_changed}</div>
                <div class="card-label">数值变更</div>
            </div>
            <div class="card card-removed">
                <div class="card-num">-{n_removed}</div>
                <div class="card-label">S2移除</div>
            </div>
        </div>
    '''.format(
        s2_total=report['summary']['s2_skills'],
        n_added=report['summary']['skill_added'],
        n_changed=report['summary']['skill_changed'],
        n_removed=report['summary']['skill_removed'],
    )
    
    if skill_diff['added']:
        html += '<div class="sub-section"><h3>🟢 新增技能</h3><div class="pet-grid">'
        for name in skill_diff['added']:
            html += f'<span class="tag tag-new">{name}</span>'
        html += '</div></div>'
    
    if skill_diff['changed']:
        html += '<div class="sub-section"><h3>🟡 技能数值变更</h3>'
        html += '<input type="text" class="search-box" placeholder="搜索技能名称..." oninput="filterTable(this, \'skill-changes\')">'
        html += '<div class="table-wrapper"><table id="skill-changes"><thead><tr>'
        html += '<th>技能名称</th><th>变更字段</th><th>S1值</th><th>S2值</th><th>变化</th>'
        html += '</tr></thead><tbody>'
        
        for skill in skill_diff['changed']:
            name = skill['name']
            for i, change in enumerate(skill['changes']):
                field_label = change['label']
                old_val = str(change['old'])
                new_val = str(change['new'])
                
                delta_html = ''
                if 'delta' in change:
                    delta = change['delta']
                    if isinstance(delta, (int, float)):
                        if delta > 0:
                            delta_html = f'<span class="delta-up">+{delta}</span>'
                        elif delta < 0:
                            delta_html = f'<span class="delta-down">{delta}</span>'
                
                rowspan = f' rowspan="{len(skill["changes"])}"' if i == 0 else ''
                name_cell = f'<td{rowspan} class="pet-name-cell"><strong>{name}</strong></td>' if i == 0 else ''
                
                html += f'<tr>{name_cell}<td>{field_label}</td><td class="old">{old_val}</td><td class="new">{new_val}</td><td>{delta_html}</td></tr>'
        
        html += '</tbody></table></div></div>'
    
    if skill_diff['removed']:
        html += '<div class="sub-section"><h3>🔴 S2中移除</h3><div class="pet-grid">'
        for name in skill_diff['removed'][:50]:
            html += f'<span class="tag tag-removed">{name}</span>'
        if len(skill_diff['removed']) > 50:
            html += f'<span class="tag tag-more">...还有{len(skill_diff["removed"]) - 50}个</span>'
        html += '</div></div>'
    
    html += '</div>'
    return html


def generate_evo_section(report):
    """生成进化链差异HTML"""
    evo_diff = report['evolutions']
    
    html = '''
    <div class="section" id="evolutions">
        <h2>🔗 进化链变更</h2>
        <div class="summary-cards">
            <div class="card card-new">
                <div class="card-num">+{n_added}</div>
                <div class="card-label">新增进化</div>
            </div>
            <div class="card card-removed">
                <div class="card-num">-{n_removed}</div>
                <div class="card-label">移除进化</div>
            </div>
        </div>
    '''.format(
        n_added=report['summary']['evo_added'],
        n_removed=report['summary']['evo_removed'],
    )
    
    if evo_diff['added']:
        html += '<div class="sub-section"><h3>🟢 新增进化关系</h3><div class="evo-list">'
        for pair in evo_diff['added'][:200]:
            html += f'<div class="evo-item"><span class="evo-from">{pair[0]}</span> <span class="evo-arrow">→</span> <span class="evo-to">{pair[1]}</span></div>'
        if len(evo_diff['added']) > 200:
            html += f'<div class="evo-more">...还有 {len(evo_diff["added"]) - 200} 条</div>'
        html += '</div></div>'
    
    if evo_diff['removed']:
        html += '<div class="sub-section"><h3>🔴 移除进化关系</h3><div class="evo-list">'
        for pair in evo_diff['removed'][:200]:
            html += f'<div class="evo-item removed-evo"><span class="evo-from">{pair[0]}</span> <span class="evo-arrow">→</span> <span class="evo-to">{pair[1]}</span></div>'
        if len(evo_diff['removed']) > 200:
            html += f'<div class="evo-more">...还有 {len(evo_diff["removed"]) - 200} 条</div>'
        html += '</div></div>'
    
    html += '</div>'
    return html


def generate_ps_section(report):
    """生成技能关联差异HTML"""
    ps_diff = report['pet_skills']
    
    html = '''
    <div class="section" id="pet-skills">
        <h2>📋 精灵技能关联变更</h2>
        <div class="summary-cards">
            <div class="card card-new">
                <div class="card-num">+{n_added}</div>
                <div class="card-label">新增关联</div>
            </div>
            <div class="card card-removed">
                <div class="card-num">-{n_removed}</div>
                <div class="card-label">移除关联</div>
            </div>
        </div>
    '''.format(
        n_added=report['summary']['ps_added'],
        n_removed=report['summary']['ps_removed'],
    )
    
    # 按精灵汇总
    from collections import defaultdict
    added_by_pet = defaultdict(list)
    removed_by_pet = defaultdict(list)
    
    for ps in ps_diff['added'][:500]:
        added_by_pet[ps[0]].append(ps[1])
    for ps in ps_diff['removed'][:500]:
        removed_by_pet[ps[0]].append(ps[1])
    
    html += '<div class="sub-section"><h3>🟢 新增技能关联（前500条，按精灵分组）</h3>'
    html += '<div class="ps-grid">'
    for pet_name, skill_names in sorted(added_by_pet.items()):
        skill_tags = ''.join(f'<span class="tag tag-skill">{s}</span>' for s in skill_names[:20])
        more = f' +{len(skill_names) - 20}个' if len(skill_names) > 20 else ''
        html += f'<div class="ps-card"><div class="ps-pet">{pet_name}</div><div class="ps-skills">{skill_tags}{more}</div></div>'
    html += '</div></div>'
    
    html += '<div class="sub-section"><h3>🔴 移除技能关联（前500条，按精灵分组）</h3>'
    html += '<div class="ps-grid">'
    for pet_name, skill_names in sorted(removed_by_pet.items()):
        skill_tags = ''.join(f'<span class="tag tag-skill-removed">{s}</span>' for s in skill_names[:20])
        more = f' +{len(skill_names) - 20}个' if len(skill_names) > 20 else ''
        html += f'<div class="ps-card"><div class="ps-pet">{pet_name}</div><div class="ps-skills">{skill_tags}{more}</div></div>'
    html += '</div></div>'
    
    html += '</div>'
    return html


def generate_html(report):
    """生成完整HTML页面"""
    summary = report['summary']
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>洛克王国世界 S1 → S2 数据差异报告</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --bg: #f8f9fa;
    --text: #2c3e50;
    --card-bg: #fff;
    --border: #e0e0e0;
    --new: #27ae60;
    --new-bg: #e8f8f0;
    --changed: #f39c12;
    --changed-bg: #fef9e7;
    --removed: #e74c3c;
    --removed-bg: #fdecea;
    --shadow: 0 2px 8px rgba(0,0,0,0.08);
    --primary: #3498db;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

.header {
    background: linear-gradient(135deg, #2c3e50, #3498db);
    color: white;
    padding: 40px 20px;
    text-align: center;
}
.header h1 { font-size: 2em; margin-bottom: 10px; }
.header .subtitle { opacity: 0.85; font-size: 1em; }

.container { max-width: 1400px; margin: 0 auto; padding: 20px; }

/* 信息横幅 */
.info-banner {
    background: #eaf2f8;
    border-radius: 8px;
    padding: 12px 20px;
    margin-bottom: 20px;
    font-size: 0.95em;
    color: #2c3e50;
}

/* 导航标签 */
.nav-tabs {
    display: flex;
    gap: 10px;
    background: var(--card-bg);
    padding: 15px 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
    flex-wrap: wrap;
    position: sticky;
    top: 0;
    z-index: 100;
}
.nav-tab {
    padding: 10px 24px;
    border-radius: 8px;
    cursor: pointer;
    border: 2px solid transparent;
    font-weight: 600;
    transition: all 0.2s;
    background: var(--bg);
    text-decoration: none;
    color: var(--text);
}
.nav-tab:hover { border-color: var(--primary); color: var(--primary); }
.nav-tab.active { background: var(--primary); color: white; border-color: var(--primary); }

/* 汇总卡片 */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin: 20px 0 30px;
}

.card {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: var(--shadow);
    border-left: 4px solid var(--primary);
}
.card-new { border-left-color: var(--new); }
.card-changed { border-left-color: var(--changed); }
.card-removed { border-left-color: var(--removed); }
.card-total { border-left-color: var(--primary); }

.card-num {
    font-size: 2em;
    font-weight: 700;
    margin-bottom: 5px;
}
.card-new .card-num { color: var(--new); }
.card-changed .card-num { color: var(--changed); }
.card-removed .card-num { color: var(--removed); }
.card-label { color: #777; font-size: 0.9em; }

/* 分区 */
.section {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: var(--shadow);
    display: none;
}
.section.active { display: block; }
.section h2 { margin-bottom: 10px; color: #2c3e50; }

.sub-section { margin-top: 25px; }
.sub-section h3 { margin-bottom: 15px; color: #555; font-size: 1.1em; }

/* 标签 */
.pet-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.tag {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.9em;
    font-weight: 500;
}
.tag-new { background: var(--new-bg); color: var(--new); border: 1px solid var(--new); }
.tag-removed { background: var(--removed-bg); color: var(--removed); border: 1px solid var(--removed); }
.tag-empty { background: #eee; color: #999; border: 1px solid #ccc; }
.tag-more { background: #eee; color: #888; }
.tag-skill { background: #eaf2f8; color: #2c3e50; font-size: 0.8em; padding: 3px 10px; }
.tag-skill-removed { background: var(--removed-bg); color: var(--removed); font-size: 0.8em; padding: 3px 10px; text-decoration: line-through; }

/* 搜索框 */
.search-box {
    width: 100%;
    padding: 10px 16px;
    border: 2px solid var(--border);
    border-radius: 8px;
    font-size: 1em;
    margin-bottom: 15px;
}
.search-box:focus { border-color: var(--primary); outline: none; }

/* 表格 */
.table-wrapper { overflow-x: auto; }
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    font-size: 0.9em;
}
th {
    background: #f1f3f5;
    font-weight: 600;
    position: sticky;
    top: 0;
}
tr:hover { background: #f8f9fa; }
.old { color: var(--removed); text-decoration: line-through; }
.new { color: var(--new); font-weight: 500; }
.pet-name-cell { min-width: 120px; }

.delta-up { color: var(--new); font-weight: 700; }
.delta-down { color: var(--removed); font-weight: 700; }
.delta-same { color: #999; }

/* 进化列表 */
.evo-list { display: flex; flex-wrap: wrap; gap: 8px; }
.evo-item {
    padding: 6px 14px;
    border-radius: 20px;
    background: #f0f0f0;
    font-size: 0.9em;
}
.evo-arrow { color: var(--primary); margin: 0 4px; font-weight: 700; }
.evo-from { color: #555; }
.evo-to { color: var(--primary); font-weight: 600; }
.removed-evo { background: var(--removed-bg); text-decoration: line-through; }
.evo-more { width: 100%; color: #999; font-style: italic; padding: 10px; }

/* 技能关联卡片 */
.ps-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 12px; }
.ps-card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 15px;
    border: 1px solid var(--border);
}
.ps-pet { font-weight: 700; margin-bottom: 8px; color: var(--primary); }
.ps-skills { display: flex; flex-wrap: wrap; gap: 4px; }

.footer {
    text-align: center;
    padding: 30px;
    color: #999;
    font-size: 0.85em;
}

@media (max-width: 768px) {
    .container { padding: 10px; }
    .section { padding: 15px; }
    .ps-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="header">
    <h1>洛克王国世界 S1 → S2 数据差异报告</h1>
    <p class="subtitle">基于 BWIKI S2「狂欢怪谈」版本数据 · 生成时间: ''' + now + '''</p>
</div>

<div class="container">
    <div class="nav-tabs">
        <a class="nav-tab active" href="#pets" onclick="showSection('pets', this)">🐾 精灵变更 · {n_added_pets}新增 {n_changed_pets}变更</a>
        <a class="nav-tab" href="#skills" onclick="showSection('skills', this)">⚔️ 技能变更 · {n_added_skills}新增 {n_changed_skills}变更</a>
        <a class="nav-tab" href="#evolutions" onclick="showSection('evolutions', this)">🔗 进化链 · +{n_added_evo}/-{n_removed_evo}</a>
        <a class="nav-tab" href="#pet-skills" onclick="showSection('pet-skills', this)">📋 技能关联 · +{n_added_ps}/-{n_removed_ps}</a>
    </div>
'''.format(
        n_added_pets=summary['pet_added'],
        n_changed_pets=summary['pet_changed'],
        n_added_skills=summary['skill_added'],
        n_changed_skills=summary['skill_changed'],
        n_added_evo=summary['evo_added'],
        n_removed_evo=summary['evo_removed'],
        n_added_ps=summary['ps_added'],
        n_removed_ps=summary['ps_removed'],
    )
    
    # 各个分区
    html += generate_pet_section(report)
    html += generate_skill_section(report)
    html += generate_evo_section(report)
    html += generate_ps_section(report)
    
    # JavaScript
    html += '''
</div>

<div class="footer">
    <p>数据来源: <a href="https://wiki.biligame.com/rocom/" target="_blank">洛克王国世界 BWIKI</a> · S1数据为网站当前数据库 · S2数据为Wiki「狂欢怪谈」版本</p>
    <p>生成工具: wiki_fetcher.py + compare_data.py + generate_report.py</p>
</div>

<script>
// 分区切换
function showSection(sectionId, tab) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    if (tab) tab.classList.add('active');
    window.location.hash = sectionId;
}

// 页面加载时显示对应分区
window.onload = function() {
    var hash = window.location.hash.substring(1);
    if (hash) {
        var section = document.getElementById(hash);
        var tab = document.querySelector('[href="#' + hash + '"]');
        if (section && tab) showSection(hash, tab);
    }
};

// 表格搜索过滤
function filterTable(input, tableId) {
    var filter = input.value.toUpperCase();
    var table = document.getElementById(tableId);
    var rows = table.getElementsByTagName('tr');
    var currentGroup = null;
    var groupVisible = false;
    
    for (var i = 1; i < rows.length; i++) {
        var row = rows[i];
        var nameCell = row.querySelector('.pet-name-cell');
        
        if (nameCell) {
            // 新的精灵分组 - 检查之前的分组是否需要隐藏
            if (currentGroup) {
                currentGroup.style.display = groupVisible ? '' : 'none';
            }
            currentGroup = row;
            var nameText = nameCell.textContent || nameCell.innerText;
            groupVisible = nameText.toUpperCase().indexOf(filter) > -1;
        } else {
            // 同一分组内的其他行
        }
    }
    // 最后一个分组
    if (currentGroup) {
        currentGroup.style.display = groupVisible ? '' : 'none';
    }
    
    // 第二遍：隐藏不属于可见分组的行
    var visibleGroup = false;
    for (var i = 1; i < rows.length; i++) {
        var row = rows[i];
        if (row.querySelector('.pet-name-cell')) {
            visibleGroup = row.style.display !== 'none';
        }
        if (!row.querySelector('.pet-name-cell')) {
            row.style.display = visibleGroup ? '' : 'none';
        }
    }
}
</script>
</body>
</html>'''
    
    return html


def main():
    report = load_report()
    html = generate_html(report)
    
    output_path = S2_DIR / 'diff_report.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'差异报告HTML已生成: {output_path}')
    print(f'文件大小: {output_path.stat().st_size / 1024:.1f} KB')


if __name__ == '__main__':
    main()
