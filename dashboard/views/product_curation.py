from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.utils import safestring
from django.contrib import messages
from django.template.defaultfilters import pluralize
from django.shortcuts import redirect
from django.db.models import Count, Q, Max
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import FormView
from django_datatables_view.base_datatable_view import BaseDatatableView

from dashboard.forms.forms import BulkProductToPUCDeleteForm
from dashboard.forms.puc_forms import PredictedPucCsvFormSet
from dashboard.models import (
    DataSource,
    Product,
    ProductToPUC,
    DataGroup,
    DataDocument,
    DocumentType,
    ProductDocument,
    PUC,
    PUCTag,
    PUCToTag,
    ProductToTag,
    Script,
)
from dashboard.forms import (
    ProductPUCForm,
    ProductLinkForm,
    ProductTagForm,
    BulkProductPUCForm,
    BulkProductTagForm,
    BulkPUCForm,
    ProductForm,
)
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from dashboard.utils import gather_errors


@login_required()
def category_assignment(
    request, pk, template_name=("product_curation/" "category_assignment.html")
):
    """Deliver a datasource and its associated products"""
    ds = DataSource.objects.get(pk=pk)
    product_count = ds.source.exclude(
        id__in=(ProductToPUC.objects.values_list("product_id", flat=True))
    ).count()
    products = ds.source.exclude(
        id__in=(ProductToPUC.objects.values_list("product_id", flat=True))
    ).order_by("-created_at")[:500]
    return render(
        request,
        template_name,
        {"datasource": ds, "products": products, "product_count": product_count},
    )


@login_required()
def link_product_list(
    request, pk, template_name="product_curation/link_product_list.html"
):
    dg = DataGroup.objects.get(pk=pk)
    documents = dg.datadocument_set.filter(productdocument__document__isnull=True)
    npage = 20  # TODO: make this dynamic someday in its own ticket
    paginator = Paginator(documents, npage)  # Show npage data documents per page
    page = request.GET.get("page")
    page = 1 if page is None else page
    docs_page = paginator.page(page)
    return render(request, template_name, {"documents": docs_page, "datagroup": dg})


@login_required()
def link_product_form(request, pk):
    template_name = "product_curation/link_product_form.html"
    doc = DataDocument.objects.get(pk=pk)
    initial = {
        "upc": (
            "stub_" + str(Product.objects.all().aggregate(Max("id"))["id__max"] + 1)
        ),
        "document_type": doc.document_type,
        "return_url": request.META.get("HTTP_REFERER"),
    }
    form = ProductLinkForm(initial=initial)
    # limit document type options to those matching parent datagroup group_type
    queryset = DocumentType.objects.compatible(doc)
    form.fields["document_type"].queryset = queryset
    if request.method == "POST":
        form = ProductLinkForm(request.POST or None)
        form.fields["document_type"].queryset = queryset
        if form.is_valid():
            upc = form["upc"].value()
            title = form["title"].value()
            product, created = Product.objects.get_or_create(upc=upc)
            if created:
                product.title = title
                product.manufacturer = form["manufacturer"].value() or ""
                product.brand_name = form["brand_name"].value() or ""
                product.upc = form["upc"].value()
                product.size = form["size"].value() or ""
                product.color = form["color"].value() or ""
                product.save()
            if not ProductDocument.objects.filter(
                document=doc, product=product
            ).exists():
                p = ProductDocument(product=product, document=doc)
                p.save()
            document_type = form["document_type"].value()
            if int(document_type) != doc.document_type_id:
                doc.document_type = DocumentType.objects.get(pk=document_type)
                doc.save()
            if "datadocument" in form["return_url"].value():
                return redirect("data_document", pk=doc.pk)
            else:
                return redirect("link_product_list", pk=doc.data_group.pk)
    return render(request, template_name, {"document": doc, "form": form})


@login_required()
def detach_puc_from_product(request, pk):
    p = Product.objects.get(pk=pk)
    ProductToPUC.objects.filter(product=p, is_uber_puc=True).delete()
    # if additional PUCs are assigned to this product, a new uberpuc should be selected
    return redirect("product_detail", pk=p.pk)


@login_required()
def bulk_assign_tag_to_products(request):
    template_name = "product_curation/bulk_product_tag.html"
    has_products = False
    msg = ""
    puc_form = BulkPUCForm(request.POST or None)
    table_url = (
        reverse("bulk_product_tag_table", args=[puc_form["puc"].value()])
        if puc_form["puc"].value()
        else ""
    )
    form = BulkProductTagForm()
    if puc_form["puc"].value():
        # Build taglist for dropdown.
        puc = PUC.objects.get(pk=puc_form["puc"].value())
        assumed_tags = puc.get_assumed_tags()
        puc2tags = PUCToTag.objects.filter(
            content_object=puc, assumed=False
        ).values_list("tag", flat=True)
        form.fields["tag"].queryset = PUCTag.objects.filter(id__in=puc2tags)
        # Determine if any products matching criteria exist.
        has_products = Product.objects.filter(
            producttopuc__puc=puc_form["puc"].value(), producttopuc__is_uber_puc=True
        ).exists()
    if request.method == "POST" and "save" in request.POST:
        form = BulkProductTagForm(request.POST or None)
        form.fields["tag"].queryset = PUCTag.objects.filter(id__in=puc2tags)
        if form.is_valid():
            assign_tag = PUCTag.objects.filter(id=form["tag"].value())
            tags = assumed_tags | assign_tag
            product_ids = form["id_pks"].value().split(",")
            for id in product_ids:
                product = Product.objects.get(id=id)
                # add the assumed tags to the update
                for tag in tags:
                    ProductToTag.objects.update_or_create(
                        tag=tag, content_object=product
                    )
            puc_form = BulkPUCForm()
            form = BulkProductTagForm()
            tag = assign_tag[0]
            msg = f'The "{tag.name}" Attribute was assigned to {len(product_ids)} Product(s).'
            if assumed_tags:
                msg += (
                    " Along with the assumed tags: "
                    f'{" | ".join(x.name for x in assumed_tags)}'
                )
            has_products = False
    return render(
        request,
        template_name,
        {
            "has_products": has_products,
            "table_url": table_url,
            "puc_form": puc_form,
            "form": form,
            "msg": msg,
        },
    )


class ProductTableByPUC(BaseDatatableView):
    """Table showing all Products associated with a specific PUC.
    """

    columns = ["checkbox", "title", "brand_name", "get_tag_list", "pk"]

    model = apps.get_model("dashboard", "Product")

    def get_filter_method(self):
        """ Returns preferred filter method """
        return self.FILTER_ICONTAINS

    def render_column(self, row, column):
        if column == "checkbox":
            return ""
        elif column == "title":
            return f"<a href='{reverse('product_detail', args=[row.id])}' target='_blank'>{row.title}</a>"
        elif column == "get_tag_list":
            return row.get_tag_list()
        elif column == "pk":
            return row.pk
        return super().render_column(row, column)

    def get_initial_queryset(self):
        """Returns the initial queryset.

        Set of products that match the provided puc_pk as their uberPUC

        :return: QuerySet of all valid Product rows
        """
        qs = self.model.objects.filter(
            producttopuc__puc=self.kwargs.get("puc_pk"), producttopuc__is_uber_puc=True
        ).all()

        return qs


@login_required()
def bulk_assign_puc_to_product(
    request, template_name=("product_curation/bulk_product_puc.html")
):
    max_products_returned = 200
    table_settings = {"pagination": True, "pageLength": 50}
    context = {}
    q = safestring.mark_safe(request.GET.get("q", "")).lstrip()
    datagroup_pk = safestring.mark_safe(request.GET.get("dg", "")).lstrip()
    rawcategory = safestring.mark_safe(request.GET.get("rc", "")).lstrip()

    form = BulkProductPUCForm(request.POST or None)
    if form.is_valid():
        puc = PUC.objects.get(id=form["puc"].value())
        product_ids = form["id_pks"].value().split(",")
        for id in product_ids:
            product = Product.objects.get(id=id)
            ProductToPUC.objects.update_or_create(
                puc=puc,
                product=product,
                classification_method_id="MB",
                puc_assigned_usr=request.user,
            )
        messages.success(request, f"{len(product_ids)} products added to PUC - {puc}")
        queryparams = f"?q={q}" if q else f"?dg={datagroup_pk}&rc={rawcategory}"
        return HttpResponseRedirect(reverse("bulk_product_puc") + queryparams)

    if q > "":
        p = Product.objects.filter(
            Q(title__icontains=q)
            | Q(brand_name__icontains=q)
            | Q(manufacturer__icontains=q)
        ).exclude(
            id__in=(
                ProductToPUC.objects.filter(
                    ~Q(classification_method_id="AU")
                ).values_list("product_id", flat=True)
            )
        )[
            :max_products_returned
        ]
        full_p_count = Product.objects.filter(
            Q(title__icontains=q) | Q(brand_name__icontains=q)
        ).count()
    elif datagroup_pk > "" and rawcategory > "":
        p = Product.objects.filter(
            Q(
                datadocument__data_group__pk=datagroup_pk,
                datadocument__raw_category=rawcategory,
            )
        ).exclude(
            id__in=(
                ProductToPUC.objects.filter(
                    ~Q(classification_method_id="AU")
                ).values_list("product_id", flat=True)
            )
        )
        datagroup = DataGroup.objects.get(pk=datagroup_pk)
        context.update({"datagroup": datagroup, "rawcategory": rawcategory})
        full_p_count = Product.objects.filter(
            Q(
                datadocument__data_group__pk=datagroup_pk,
                datadocument__raw_category=rawcategory,
            )
        ).count()
    else:
        p = {}
        full_p_count = 0
    form["puc"].label = "PUC to Assign to Selected Products"
    context.update(
        {
            "products": p,
            "q": q,
            "form": form,
            "full_p_count": full_p_count,
            "table_settings": table_settings,
        }
    )
    return render(request, template_name, context)


class RemoveProductToPUC(LoginRequiredMixin, FormView):
    form_class = BulkProductToPUCDeleteForm
    template_name = "product_curation/bulk_remove_product_puc.html"
    success_url = reverse_lazy("bulk_remove_product_puc")
    table_settings = {
        "pagination": True,
        "pageLength": 50,
        "ajax": reverse_lazy("bulk_remove_product_puc_table"),
    }
    puc_form = ProductPUCForm()  # This form is only needed for the puc select2 widget

    def get_context_data(self, **kwargs):
        # Set width of the puc widget to 100% so the entire puc is visible.
        self.puc_form.fields["puc"].widget.attrs["style"] = "width: 100%"
        self.puc_form.fields["puc"].required = False

        context = super().get_context_data(**kwargs)
        context["table_settings"] = self.table_settings
        context["puc_form"] = self.puc_form
        context["classification_methods"] = apps.get_model(
            "dashboard", "ProductToPUCClassificationMethod"
        ).objects
        return context

    def form_invalid(self, form):
        for non_field_error in form.non_field_errors():
            messages.error(self.request, non_field_error)
        return super().form_invalid(form)

    def form_valid(self, form):
        success_message = form.save()
        messages.success(self.request, success_message)
        return super().form_valid(form)


class RemoveProductToPUCTable(BaseDatatableView):
    """Table showing all Products associated with a specific PUC.
    """

    model = apps.get_model("dashboard", "ProductToPUC")

    def get_filter_method(self):
        """ Returns preferred filter method """
        return self.FILTER_ICONTAINS

    def render_column(self, row, column):
        if column == "classification_method__name":
            return row.classification_method.name
        elif column == "product__manufacturer":
            return row.product.manufacturer
        elif column == "product__brand_name":
            return row.product.brand_name
        elif column == "product__title":
            return f"<a href='{reverse('product_detail', args=[row.product.id])}' target='_blank'>{row.product.title}</a>"
        elif column == "pk":
            return row.pk
        return super().render_column(row, column)

    def filter_queryset(self, qs):
        puc_id = self.request.GET.get("puc", None)
        classification_methods = self.request.GET.getlist(
            "classification_methods[]", None
        )

        if puc_id:
            qs = qs.filter(puc=puc_id)
        if classification_methods:
            qs = qs.filter(classification_method__pk__in=classification_methods)

        return super().filter_queryset(qs)

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        return qs.prefetch_related("classification_method", "product").filter(
            is_uber_puc=True
        )


@login_required()
def category_assign_puc_to_product(
    request, ds_pk, pk, template_name=("product_curation/" "product_puc.html")
):
    p = Product.objects.get(pk=pk)
    p2p = ProductToPUC.objects.filter(classification_method_id="MA", product=p).first()
    form = ProductPUCForm(request.POST or None, instance=p2p)
    if form.is_valid():
        if p2p:
            p2p.save()
        else:
            puc = PUC.objects.get(id=form["puc"].value())
            p2p = ProductToPUC.objects.create(
                puc=puc,
                product=p,
                classification_method_id="MA",
                puc_assigned_usr=request.user,
            )
        return redirect("category_assignment", pk=ds_pk)
    form.return_url = reverse("category_assignment", kwargs={"pk": ds_pk})
    return render(request, template_name, {"product": p, "form": form})


@login_required()
def product_assign_puc_to_product(
    request, pk, template_name=("product_curation/" "product_puc.html")
):
    p = Product.objects.get(pk=pk)
    p2p = ProductToPUC.objects.filter(classification_method_id="MA", product=p).first()
    form = ProductPUCForm(request.POST or None, instance=p2p)
    if form.is_valid():
        if p2p:
            p2p.save()
        else:
            puc = PUC.objects.get(id=form["puc"].value())
            p2p = ProductToPUC.objects.create(
                puc=puc,
                product=p,
                classification_method_id="MA",
                puc_assigned_usr=request.user,
            )
        return redirect("product_detail", pk=pk)
    form.return_url = reverse("product_detail", kwargs={"pk": pk})
    return render(request, template_name, {"product": p, "form": form})


def product_detail(request, pk):
    template_name = "product_curation/product_detail.html"
    p = get_object_or_404(Product, pk=pk)
    tagform = ProductTagForm(request.POST or None, instance=p)
    tagform["tags"].label = ""
    puc = p.uber_puc
    classification_method = p.get_classification_method
    assumed_tags = puc.get_assumed_tags() if puc else PUCTag.objects.none()
    if request.user.is_authenticated and tagform.is_valid():
        tagform.save()
    docs = p.datadocument_set.order_by("-created_at")
    return render(
        request,
        template_name,
        {
            "product": p,
            "puc": puc,
            "tagform": tagform,
            "docs": docs,
            "assumed_tags": assumed_tags,
            "classification_method": classification_method,
        },
    )


@login_required()
def product_update(
    request, pk, template_name=("product_curation/" "product_edit.html")
):
    p = Product.objects.get(pk=pk)
    form = ProductForm(request.POST or None, instance=p)
    if form.is_valid():
        form.save()
        return redirect("product_detail", pk=p.pk)
    return render(request, template_name, {"product": p, "form": form})


@login_required()
def product_delete(request, pk):
    p = Product.objects.get(pk=pk)
    messages.success(request, f"Product: {p} successfully deleted.")
    doc = p.datadocument_set.first()
    p.delete()
    return redirect("data_document", pk=doc.pk) if doc else redirect("index")


def product_list(request):
    template_name = "product_curation/products.html"
    data = {}
    data["products"] = {}
    return render(request, template_name, data)


@login_required()
def product_puc_reconciliation(
    request, template_name="product_curation/product_puc_reconciliation.html"
):
    data = {}
    data["products"] = {}
    return render(request, template_name, data)


@login_required()
def upload_predicted_pucs(
    request, template_name="product_curation/upload_predicted_pucs.html"
):
    data = {}
    puc_formset = PredictedPucCsvFormSet()
    puc_formset.script_choices = [
        (str(s.pk), str(s))
        for s in Script.objects.filter(script_type="PC").filter(qa_begun=False)
    ]

    if "POST" == request.method:
        puc_formset = PredictedPucCsvFormSet(request.POST, request.FILES)
        puc_formset.user = request.user
        if request.POST["predicted-prediction_script_id"]:
            puc_formset.script_id = request.POST["predicted-prediction_script_id"]
        if puc_formset.is_valid():
            num_created, num_updated = puc_formset.save()
            messages.success(
                request,
                "%d Product-to-PUC assignment%s created, %d updated."
                % (num_created, pluralize(num_created), num_updated),
            )
        else:
            errors = gather_errors(puc_formset)
            for e in errors:
                messages.error(request, e)
        return redirect("upload_predicted_pucs")

    data["puc_formset"] = puc_formset
    return render(request, template_name, data)
