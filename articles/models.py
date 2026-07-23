from ckeditor.fields import RichTextField
from django.conf import settings
from django.db import models


class Article(models.Model):
    CATEGORY_CHOICES = [
        ('攻略', '攻略'),
        ('公告', '公告'),
        ('活动', '活动'),
        ('更新', '更新'),
    ]

    title = models.CharField(max_length=200, verbose_name='标题')
    content = RichTextField(verbose_name='正文')
    summary = models.TextField(blank=True, verbose_name='摘要')
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        default='攻略', verbose_name='分类'
    )
    cover_image = models.ImageField(
        upload_to='articles/covers/', blank=True, null=True, verbose_name='封面图'
    )
    is_published = models.BooleanField(default=False, verbose_name='发布状态')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='articles', verbose_name='作者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
