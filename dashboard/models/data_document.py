from django.db import models
from .common_info import CommonInfo
from django.urls import reverse
from django.utils import timezone
from .document_type import DocumentType
from django.core.exceptions import ValidationError


class DataDocument(CommonInfo):
    """
    A DataDocument object is a single source of Factotum data. 

    ``filename``
        the name of the document's source file

    ``title``
        the title of the document
    
    ``url``
        an optional URL to the document's remote source

    ``raw_category``

    ``data_group``
        the DataGroup object to which the document belongs. The
        type of the data group determines which document types the
        document might be among, and determines much of the available 
        relationships and behavior associated with the document's 
        extracted data
    
    ``products``
        Products are associated with the data document in a many-to-many relationship

    ``matched``
        When a source file for the document has been uploaded to the
        file system, the document is considered "matched" to that
        source file. 
    
    ``extracted``
        When the content of a data document has been extracted by manual data entry
        or by an extraction script, a new ExtractedText record is created
        with the DataDocument's id as its primary key. 
    
    ``document_type``
        each type of data group may only contain certain types of data documents. The
        clean() method checks to make sure that the assigned document type is among the
        types allowed by the group type

    ``organization``

    ``note``

    """

    filename = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    url = models.CharField(null=True, blank=True, max_length=275)
    raw_category = models.CharField(null=True, blank=True, max_length=100)
    data_group = models.ForeignKey('DataGroup', on_delete=models.CASCADE)
    products = models.ManyToManyField('Product', through='ProductDocument')
    matched = models.BooleanField(default=False)
    #############################################################
    #  T E C H N I C A L   D E B T 
    # Storing this as a boolean field might not be a good idea. If someone 
    # deletes an ExtractedText object in the admin panel or in the database,
    # the bit will not flip, so the document will remain "extracted"
    # even in the absence of an ExtractedText object
    extracted = models.BooleanField(default=False)  
    # The is_extracted method below should replace this attribute
    #############################################################
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT,
                                                        null=True, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return str(self.title)
    
    @property
    def detail_page_editable(self):
        # this could be moved to settings
        return self.data_group.group_type.code in ['CP', 'HH', 'CO', ] 

    @property
    def is_extracted(self):
        return hasattr(self,'extractedtext')

    def get_absolute_url(self):
        return reverse('data_document', kwargs={'pk': self.pk})

    def get_abstract_filename(self):
        ext = self.filename.split('.')[-1] #maybe not all are PDF??
        return f'document_{self.pk}.{ext}'

    def pdf_url(self):
        dg = self.data_group
        fn = self.get_abstract_filename()
        return f'/media/{dg.fs_id}/pdf/{fn}'

    def clean(self):
        # the document_type must be one of the children types
        # of the datadocument's parent datagroup
        this_type = self.data_group.group_type
        doc_types = DocumentType.objects.filter(group_type=this_type)
        if not self.document_type in doc_types:
            raise ValidationError(('The document type must be allowed by '
                                                    'the parent data group.'))
