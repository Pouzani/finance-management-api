import re
from django.contrib import admin
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import Goal

_SAFE_COLOR_RE = re.compile(
    r'^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$|^rgb\([\d\s,]+\)$'
)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('label', 'current', 'target', 'progress_pct', 'icon', 'color_preview')
    search_fields = ('label',)
    readonly_fields = ('id', 'progress_pct', 'color_preview')

    @admin.display(description='Progress')
    def progress_pct(self, obj):
        if not obj.target:
            return '0%'
        pct = (obj.current / obj.target) * 100
        return f'{pct:.1f}%'

    @admin.display(description='Color')
    def color_preview(self, obj):
        color = obj.color if _SAFE_COLOR_RE.match(obj.color or '') else '#cccccc'
        return mark_safe(
            f'<span style="display:inline-block;width:16px;height:16px;'
            f'background:{color};border-radius:3px;border:1px solid #ccc;"></span>'
            f' {escape(obj.color)}'
        )
