# Claude Code 计划修正点 — 直接粘贴给 Claude Code

以下是对你实施计划的 6 处修正，按优先级排列。

## 🔴 必须修

### 1. Pet 模型补上 ability_icon
pets.json 中有此字段，模型漏了：

```python
ability_icon = CharField(100, blank=True)
```

### 2. ElementType 去掉 color 字段
elements.json 只有 name 和 icon，没有 color。前端用属性图标展示，不需要 color：

```python
class ElementType(models.Model):
    name = CharField(50, unique=True)
    icon = CharField(100, blank=True)
```

### 3. EggData 不可从 Pet 身高体重推导
孵蛋的蛋尺寸和精灵体型是两套独立数据。请从 import_data 阶段 H 中删除"从 Pet 自动生成"的逻辑，孵蛋查询的数据我已经给出在MD\egg_data.json中

## 🟡 建议修

### 4. 明确 3 条跳过进化的原因
3 条引用缺失是因为樱桃饰品香草甜甜被 BWIKI 反爬挡住没爬到。跳过时打印 WARNING 日志。

### 5. PetSkill 的 unique_together
建议不加 unique_together，查询时用 .distinct() 去重，更安全避免边界情况：

```python
class Meta:
    # 不设 unique_together，查询时用 distinct()
    pass
```

### 6. 首页"热门精灵"定义
建议明确规则：按种族值总和降序取前 6 只，或者手动指定 6 只代表性精灵（如迪莫、火花、水蓝蓝、喵喵、魔力猫、烈火战神）。
