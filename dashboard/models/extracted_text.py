from model_utils.managers import InheritanceManager

from django.db import models
from django.urls import reverse

from .extracted_functional_use import ExtractedFunctionalUse
from .common_info import CommonInfo


class ExtractedText(CommonInfo):
    """
    The ExtractedText record stores attributes that only apply to extracted
    documents.
    """

    data_document = models.OneToOneField(
        "DataDocument", on_delete=models.CASCADE, primary_key=True
    )
    prod_name = models.CharField(
        "Product name",
        max_length=500,
        blank=True,
        help_text="The name of the product according to the extracted document",
    )
    doc_date = models.CharField(
        "Document date",
        max_length=25,
        blank=True,
        help_text="Date the study document was published",
    )
    rev_num = models.CharField("Revision number", max_length=50, blank=True)
    extraction_script = models.ForeignKey(
        "Script", on_delete=models.CASCADE, limit_choices_to={"script_type": "EX"}
    )
    qa_checked = models.BooleanField(default=False, verbose_name="QA approved")
    qa_edited = models.BooleanField(default=False, verbose_name="QA edited")
    qa_approved_date = models.DateTimeField(
        null=True, blank=True, verbose_name="QA approval date"
    )
    qa_approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        verbose_name="QA approved by",
        null=True,
        blank=True,
    )
    qa_group = models.ForeignKey(
        "QAGroup",
        verbose_name="QA group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    cleaning_script = models.ForeignKey(
        "Script",
        on_delete=models.CASCADE,
        limit_choices_to={"script_type": "DC"},
        null=True,
        blank=True,
        help_text="The script used to clean the data after extraction",
        related_name="cleaned_documents",
    )
    cleaning_qa_checked = models.BooleanField(
        null=True,
        default=None,
        verbose_name="Cleaning QA status",
        help_text="The approval status of a cleaned document can be 0 (rejected), 1 (approved) or null (neither approved nor rejected).",
    )
    cleaning_qa_edited = models.BooleanField(
        default=False, verbose_name="Cleaning QA edited"
    )
    cleaning_qa_approved_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Cleaning QA approval date"
    )
    cleaning_qa_approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        verbose_name="Cleaning QA approved by",
        null=True,
        blank=True,
        related_name="cleaned_documents",
    )
    cleaning_qa_group = models.ForeignKey(
        "QAGroup",
        verbose_name="Cleaning QA group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleaned_documents",
    )
    objects = InheritanceManager()

    def __str__(self):
        return str(self.data_document)

    @property
    def group_type(self):
        return self.data_document.data_group.group_type.code

    @property
    def cleaning_qa_status(self):
        if self.cleaning_qa_checked == 1:
            return "Approved"
        elif self.cleaning_qa_checked == 0:
            return "Rejected"
        else:
            return "Not reviewed"

    def get_qa_queryset(self):
        """
        The business logic that assigns a set of composition documents 
        to a QA Group depends on whether the set of records was manually
        extracted or extracted via a script.
        Documents are only aggregated under the QAGroup model when the
        QA workflow is based on their extraction script. When composition
        documents have been manually extracted, the unit of QA aggregation
        is the data group.   
        """
        # Manually-extracted composition documents
        if self.extraction_script.title == "Manual (dummy)" and self.group_type == "CO":
            qs = ExtractedText.objects.filter(
                extraction_script=self.extraction_script,
                data_document__data_group=self.data_document.data_group,
            )

        # Script-extracted composition documents
        elif self.group_type == "CO":
            qs = ExtractedText.objects.filter(qa_group=self.qa_group)
        # CPCat and HHE documents are what remains
        else:
            qs = ExtractedText.objects.filter(
                data_document__data_group=self.data_document.data_group
            )
        return qs

    def get_approved_doc_count(self):
        """
        Returns the number of documents in the current object's
        QA set that have been approved (moved here from the QAGroup model)
        """
        qs = self.get_qa_queryset().filter(qa_checked=True)
        return qs.count()

    def next_extracted_text_in_qa_group(self):
        """
        Returns the extracted document next up in the QA cycle after
        the current object
        """
        nextid = 0
        # If the document is part of a Script-based QA Group, the
        # next document is drawn from that group. If it is a CPCat
        # or HHE record, there is no next document
        extextnext = get_next_or_prev(
            self.get_qa_queryset().filter(qa_checked=False), self, "next"
        )
        if extextnext:
            # Replace our item with the next one
            nextid = extextnext.pk
        if extextnext == self:
            nextid = 0
        return nextid

    def get_cleaning_qa_queryset(self):
        """
        The cleaning QA queryset is the collection of extractedtext
        records that share a Cleaning QA Group  
        """

        qs = ExtractedText.objects.filter(cleaning_qa_group=self.cleaning_qa_group)
        return qs

    def next_extracted_text_in_cleaning_qa_group(self):
        """
        Returns the extracted document next up in the QA cycle 
        for the current object's cleaned composition data
        """
        nextid = 0

        extextnext = get_next_or_prev(
            self.get_cleaning_qa_queryset().exclude(cleaning_qa_checked=True),
            self,
            "next",
        )
        if extextnext:
            # Replace our item with the next one
            nextid = extextnext.pk

        if extextnext == self:
            nextid = 0

        return nextid

    def get_qa_index_path(self):
        """
        The type of data group to which the extracted text object belongs
        and its extraction method determine which QA index it will use.
        """
        group_type_code = self.data_document.data_group.group_type.code

        if group_type_code in ["CP", "HH"]:
            # TODO: change HH to its own path
            return reverse("qa_chemicalpresence_index")
        elif (
            self.extraction_script.title == "Manual (dummy)" and group_type_code == "CO"
        ):
            return reverse("qa_manual_composition_index")
        else:
            return (
                reverse("qa_extractionscript_index") + f"?group_type={group_type_code}"
            )

    def one_to_one_check(self, odict):
        """
        Used in the upload of extracted text in the data_group_detail view, this
        returns a boolean to assure that there is a 1:1 relationship w/
        the Extracted{parent}, i.e. (Text/CPCat), and the DataDocument
        """
        if hasattr(self, "cat_code"):
            return self.cat_code != odict["cat_code"]
        else:
            return self.prod_name != odict["prod_name"]

    def is_approvable(self):
        """
        Returns true or false to indicate whether the ExtractedText object
        can be approved. If the object has been edited, then there must be
        some related QA Notes.

        Note that if the ExtractedText object is missing a related QANotes
        record, self.qanotes will not return None. Instead it returns an 
        ObjectDoesNotExist error.
        https://stackoverflow.com/questions/3463240/check-if-onetoonefield-is-none-in-django

        The hasattr() method is the correct way to test for the presence of 
        a related record.

        It is not enough to test for the related record, though, because an empty
        qa_notes field is functionally equivalent to a missing QANotes record.

        """

        if not self.qa_edited:
            return True
        elif self.qa_edited and not hasattr(self, "qanotes"):
            return False
        elif (
            self.qa_edited
            and hasattr(self, "qanotes")
            and not bool(self.qanotes.qa_notes)
        ):
            return False
        else:
            return True

    def prep_functional_use_for_qa(self):
        if self.data_document.data_group.is_functional_use:
            """
            QA up to 100 samples of Functional Use chemicals
            """
            QA_RECORDS_PER_DOCUMENT = 100
            chems = ExtractedFunctionalUse.objects.filter(extracted_text=self)
            flagged = chems.filter(qa_flag=True).count()
            # if less than 100 records not flagged for QA, count of ALL may be < 100
            if flagged < QA_RECORDS_PER_DOCUMENT and flagged < chems.count():
                x = QA_RECORDS_PER_DOCUMENT - flagged
                unflagged = list(
                    chems.filter(qa_flag=False)
                    .order_by("?")  # this makes the selection random
                    .values_list("pk", flat=True)
                )
                fus = ExtractedFunctionalUse.objects.filter(pk__in=unflagged[:x])
                for fu in fus:
                    fu.qa_flag = True
                    fu.save()
            return ExtractedFunctionalUse.objects.filter(
                extracted_text=self, qa_flag=True
            )
        else:
            pass


def get_next_or_prev(models, item, direction):
    """
    Returns the next or previous item of
    a query-set for 'item'.

    'models' is a query-set containing all
    items of which 'item' is a part of.

    direction is 'next' or 'prev'

    """
    getit = False
    if direction == "prev":
        models = models.reverse()
    for m in models:
        if getit:
            return m
        if item == m:
            getit = True
    if getit:
        # This would happen when the last
        # item made getit True
        return models[0]
    return False
