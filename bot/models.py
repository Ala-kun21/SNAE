from django.db import models

# ==========================
# مستخدم تيليجرام
# ==========================
class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username or str(self.telegram_id)

# ==========================
# أرقام الهاتف
# ==========================
class PhoneNumber(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="phones")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} : {self.phone}"

# ==========================
# الصور المرسلة
# ==========================
class Image(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="images/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image {self.id} by {self.user}"

# ==========================
# الملفات المرسلة
# ==========================
class FileUpload(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="files/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File {self.id} by {self.user}"
