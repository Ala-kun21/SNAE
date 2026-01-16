from django.contrib import admin
from .models import TelegramUser, PhoneNumber, Image, FileUpload

# تسجيل كل الموديلات لعرضها في صفحة إدارة Django
admin.site.register(TelegramUser)
admin.site.register(PhoneNumber)
admin.site.register(Image)
admin.site.register(FileUpload)
