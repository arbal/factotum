from django.db import models
from .common_info import CommonInfo


class DocumentTypeGroupTypeCompatibilty(CommonInfo):
    document_type = models.ForeignKey("DocumentType", on_delete=models.CASCADE)
    group_type = models.ForeignKey("GroupType", on_delete=models.CASCADE)

    def __str__(self):
        return ""

    class Meta:
        unique_together = ["document_type", "group_type"]
        verbose_name = "Document type/Group type compatibilty"
        verbose_name_plural = "Document type/Group type compatibilties"
