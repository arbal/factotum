from django.db import models
from .extracted_text import ExtractedText
from .extracted_list_presence import ExtractedListPresence


class ExtractedCPCat(ExtractedText):
    cat_code = models.CharField("Cat code", max_length=100, null=True, blank=True)
    description_cpcat = models.CharField(
        "CPCat cassette", max_length=200, null=True, blank=True
    )
    cpcat_code = models.CharField("ACToR snaid", max_length=50, null=True, blank=True)
    cpcat_sourcetype = models.CharField(
        "CPCat source", max_length=50, null=True, blank=True
    )

    def __str__(self):
        return str(self.prod_name)

    @property
    def qa_begun(self):
        return (
            self.rawchem.select_subclasses()
            .filter(extractedlistpresence__qa_flag=True)
            .exists()
        )

    def prep_cp_for_qa(self):
        """
        Given an ExtractedCPCat object, select a sample of its 
        ExtractedListPresence children for QA review.
        """
        QA_RECORDS_PER_DOCUMENT = 30

        elps = self.rawchem.select_subclasses()
        flagged = elps.filter(extractedlistpresence__qa_flag=True).count()
        # if less than 30 records not flagged for QA, count of ALL may be < 30
        if flagged < QA_RECORDS_PER_DOCUMENT and flagged < elps.count():
            x = QA_RECORDS_PER_DOCUMENT - flagged
            unflagged = list(
                elps.filter(extractedlistpresence__qa_flag=False)
                .order_by("?")  # this makes the selection random
                .values_list("pk", flat=True)
            )
            lps = ExtractedListPresence.objects.filter(pk__in=unflagged[:x])
            for lp in lps:
                lp.qa_flag = True
                lp.save()
        return self.rawchem.select_subclasses().filter(
            extractedlistpresence__qa_flag=True
        )
