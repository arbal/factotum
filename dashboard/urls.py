from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static

import dashboard.views.data_group
import dashboard.views.qa
import dashboard.views.functional_use_category
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("grouptype/stats/", views.grouptype_stats, name="grouptype_stats"),
    path("datasources/", views.data_source_list, name="data_source_list"),
    path("datasource/<int:pk>/", views.data_source_detail, name="data_source_detail"),
    path("datasource/new/", views.data_source_create, name="data_source_new"),
    path(
        "datasource/edit/<int:pk>/", views.data_source_update, name="data_source_edit"
    ),
    path(
        "datasource/delete/<int:pk>/",
        views.data_source_delete,
        name="data_source_delete",
    ),
    path(
        "datasource/<int:pk>/datagroup_new/",
        views.data_group_create,
        name="data_group_new",
    ),
    path("datagroups/", views.data_group_list, name="data_group_list"),
    re_path(
        r"datagroups/(?P<code>[A-Z]{2})/$",
        views.data_group_list,
        name="data_group_list",
    ),
    path("datagroup/<int:pk>/", views.data_group_detail, name="data_group_detail"),
    path(
        "datagroup/<int:pk>/download_documents/",
        views.download_datadocuments,
        name="download_datadocuments",
    ),
    path(
        "datagroup/<int:pk>/documents_table/",
        views.data_group_documents_table,
        name="documents_table",
    ),
    path(
        "datagroup/<int:pk>/download_document_zip/",
        views.download_datadocument_zip_file,
        name="download_datadocument_zip_file",
    ),
    path(
        "datagroup/<int:pk>/download_raw_extracted_records/",
        views.download_raw_extracted_records,
        name="download_raw_extracted_records",
    ),
    path(
        "datagroup/<int:pk>/download_raw_functional_use_records/",
        views.download_raw_functional_use_records,
        name="download_raw_functional_use_records",
    ),
    path(
        "datagroup/<int:pk>/download_registered_documents/",
        views.download_registered_datadocuments,
        name="download_registered_datadocuments",
    ),
    path(
        "datagroup/<int:pk>/download_unextracted_documents/",
        views.download_unextracted_datadocuments,
        name="download_unextracted_datadocuments",
    ),
    path("datagroup/edit/<int:pk>/", views.data_group_update, name="data_group_edit"),
    path(
        "datagroup/delete/<int:pk>/", views.data_group_delete, name="data_group_delete"
    ),
    path(
        "datagroup/<int:pk>/delete_products",
        views.data_group_delete_products,
        name="data_group_delete_products",
    ),
    path(
        "datagroup/<int:pk>/datadocument_new/",
        views.data_document_create,
        name="data_document_new",
    ),
    path("datadocument/<int:pk>/", views.data_document_detail, name="data_document"),
    path(
        "datadocument/<int:pk>/cards",
        views.data_document_cards,
        name="data_document_cards",
    ),
    path(
        "save_datadocument_note/<int:pk>/",
        views.save_data_document_note,
        name="save_data_document_note",
    ),
    path(
        "save_datadocument_type/<int:pk>/",
        views.save_data_document_type,
        name="save_data_document_type",
    ),
    path(
        "save_datadocument_extext/<int:pk>/",
        views.save_data_document_extext,
        name="save_data_document_extext",
    ),
    path(
        "datadocument/delete/<int:pk>/",
        views.data_document_delete,
        name="data_document_delete",
    ),
    path(
        "datadocument/<int:pk>/tags/delete/",
        views.data_document_delete_tags,
        name="data_document_delete_tags",
    ),
    path(
        "datadocument/detected/<int:doc_pk>/",
        views.detected_flag,
        name="detected_flag_toggle_yes",
    ),
    path(
        "datadocument/non_detected/<int:doc_pk>/",
        views.detected_flag,
        name="detected_flag_toggle_no",
    ),
    path(
        "datadocument/clear_flag/<int:doc_pk>/",
        views.detected_flag,
        name="detected_flag_reset",
    ),
    path(
        "list_presence_tag_curation/",
        views.list_presence_tag_curation,
        name="list_presence_tag_curation",
    ),
    path("save_tags/<int:pk>/", views.SaveTagForm.as_view(), name="save_tag_form"),
    path(
        "list_presence_tags_autocomplete/",
        views.ListPresenceTagAutocomplete.as_view(),
        name="list_presence_tags_autocomplete",
    ),
    path(
        "habits_and_practices_tags_autocomplete/",
        views.HabitsAndPracticesTagAutocomplete.as_view(),
        name="habits_and_practices_tags_autocomplete",
    ),
    path(
        "chemical_autocomplete/",
        views.ChemicalAutocomplete.as_view(),
        name="chemical_autocomplete",
    ),
    path(
        "functional_use_autocomplete/",
        views.FunctionalUseAutocomplete.as_view(),
        name="functional_use_autocomplete",
    ),
    path(
        "product_puc_reconciliation/",
        views.product_puc_reconciliation,
        name="product_puc_reconciliation",
    ),
    path("chemical_curation/", views.chemical_curation_index, name="chemical_curation"),
    path(
        "curated_chemical_removal/",
        views.curated_chemical_removal_index.as_view(),
        name="curated_chemical_removal",
    ),
    path(
        "curated_chemical_detail/<str:sid>",
        views.curated_chemical_detail,
        name="curated_chemical_detail",
    ),
    path(
        "category_assignment/<int:pk>/",
        views.category_assignment,
        name="category_assignment",
    ),
    path(
        "functional_use_cleanup/",
        views.functional_use_cleanup,
        name="functional_use_cleanup",
    ),
    path(
        "functional_use_curation/",
        views.functional_use_curation,
        name="functional_use_curation",
    ),
    path(
        "functional_use_curation/<functional_use_pk>/",
        views.FunctionalUseCurationChemicals.as_view(),
        name="functional_use_curation_chemicals",
    ),
    path(
        "functional_use_curation/<functional_use_pk>/table",
        views.FunctionalUseCurationChemicalsTable.as_view(),
        name="functional_use_curation_chemicals_table",
    ),
    path(
        "link_product_list/<int:pk>/", views.link_product_list, name="link_product_list"
    ),
    path(
        "link_product_form/<int:pk>/", views.link_product_form, name="link_product_form"
    ),
    path(
        "qa/extractionscript/",
        views.qa_extractionscript_index,
        name="qa_extractionscript_index",
    ),
    path(
        "qa/manualcomposition/",
        views.qa_manual_composition_index,
        name="qa_manual_composition_index",
    ),
    path(
        "qa/manualcomposition/<int:pk>/summary",
        views.qa_manual_composition_summary,
        name="qa_manual_composition_summary",
    ),
    path(
        "qa/manualcomposition/<int:pk>/summary/table",
        dashboard.views.qa.ManualCompositionDataGroupSummaryTable.as_view(),
        name="qa_manual_composition_summary_table",
    ),
    path(
        "qa/extractionscript/<int:pk>/",
        dashboard.views.qa.qa_extraction_script,
        name="qa_extraction_script",
    ),
    path(
        "qa/extractionscript/<int:pk>/summary",
        dashboard.views.qa.qa_extraction_script_summary,
        name="qa_extraction_script_summary",
    ),
    path(
        "qa/extractionscript/<int:pk>/summary/table",
        dashboard.views.qa.ScriptSummaryTable.as_view(),
        name="qa_extraction_script_summary_table",
    ),
    path(
        "extractionscripts/delete/",
        dashboard.views.extraction_script_delete_list,
        name="extraction_script_delete_list",
    ),
    path(
        "duplicate_chemicals/",
        dashboard.views.duplicate_chemical_records,
        name="duplicate_chemicals",
    ),
    path(
        "duplicate_chemicals_json/",
        dashboard.views.DuplicateChemicalsJson.as_view(),
        name="duplicate_chemicals_ajax_url",
    ),
    path(
        "qa/extractedtext/<int:pk>/",
        dashboard.views.qa.extracted_text_qa,
        name="extracted_text_qa",
    ),
    path(
        "extractionscript/<int:pk>/",
        views.extraction_script_detail,
        name="extraction_script_detail",
    ),
    path(
        "qa/chemicalpresence/",
        views.qa_chemicalpresence_index,
        name="qa_chemicalpresence_index",
    ),
    path(
        "qa/chemicalpresencegroup/<int:pk>/",
        views.qa_chemicalpresence_group,
        name="qa_chemical_presence_group",
    ),
    path(
        "qa/chemicalpresencegroup/<int:pk>/summary/",
        views.qa_chemicalpresence_summary,
        name="qa_chemical_presence_summary",
    ),
    path(
        "qa/chemicalpresencegroup/<int:pk>/summary/table",
        dashboard.views.qa.ChemicalPresenceSummaryTable.as_view(),
        name="qa_chemical_presence_summary_table",
    ),
    path(
        "bulk_remove_product_puc/",
        views.RemoveProductToPUC.as_view(),
        name="bulk_remove_product_puc",
    ),
    path(
        "bulk_remove_product_puc/table",
        views.RemoveProductToPUCTable.as_view(),
        name="bulk_remove_product_puc_table",
    ),
    path(
        "bulk_product_puc/", views.bulk_assign_puc_to_product, name="bulk_product_puc"
    ),
    path(
        "bulk_product_tag/", views.bulk_assign_tag_to_products, name="bulk_product_tag"
    ),
    path(
        "bulk_product_tag/<int:puc_pk>/table",
        views.ProductTableByPUC.as_view(),
        name="bulk_product_tag_table",
    ),
    path(
        "category_assignment/<int:ds_pk>/product_puc/<int:pk>",
        views.category_assign_puc_to_product,
        name="category_assignment_product_puc",
    ),
    path(
        "product_puc/<int:pk>/", views.product_assign_puc_to_product, name="product_puc"
    ),
    path(
        "product_puc_delete/<int:pk>/",
        views.detach_puc_from_product,
        name="product_puc_delete",
    ),
    path(
        "puc-autocomplete/",
        views.puc_autocomplete.PUCAutocomplete.as_view(),
        name="puc-autocomplete",
    ),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("product/edit/<int:pk>/", views.product_update, name="product_edit"),
    path("product/delete/<int:pk>/", views.product_delete, name="product_delete"),
    path("products/", views.product_list, name="product_list"),
    path("d_json/", views.DocumentListJson.as_view(), name="d_ajax_url"),
    path("p_json/", views.ProductListJson.as_view(), name="p_ajax_url"),
    path(
        "p_puc_json/",
        views.ProductPUCReconciliationJson.as_view(),
        name="p_puc_ajax_url",
    ),
    path(
        "fu_puc_json/", views.PucFunctionalUseListJson.as_view(), name="fu_puc_ajax_url"
    ),
    path("c_json/", views.ChemicalListJson.as_view(), name="c_ajax_url"),
    path("fuc_p_json/", views.FUCProductListJson.as_view(), name="fuc_p_ajax_url"),
    path("fuc_d_json/", views.FUCDocumentListJson.as_view(), name="fuc_d_ajax_url"),
    path("fuc_c_json/", views.FUCChemicalListJson.as_view(), name="fuc_c_ajax_url"),
    path(
        "hp_json/", views.HabitsAndPracticesDocumentsJson.as_view(), name="hp_ajax_url"
    ),
    path(
        "curated_chem_json/",
        views.CuratedChemicalsListJson.as_view(),
        name="curated_chem_ajax_url",
    ),
    path(
        "curated_chem_detail_json/",
        views.CuratedChemicalDetailJson.as_view(),
        name="curated_chem_detail_ajax_url",
    ),
    path("sid_gt_json", views.sids_by_grouptype_ajax, name="sid_gt_json_url"),
    path("pucs/", views.puc_list, name="puc_list"),
    path("puc/<int:pk>/", views.puc_detail, name="puc_detail"),
    path(
        "puc_chemical_csv/<int:pk>/",
        views.download_puc_chemicals,
        name="puc_chemical_csv",
    ),
    path(
        "download_puc_products_weight_fractions/<int:pk>/",
        views.download_puc_products_weight_fractions,
        name="download_puc_products_weight_fractions",
    ),
    path("dl_pucs_json/", views.bubble_PUCs, name="bubble_PUCs"),
    path(
        "dl_pucs_json/tree/", views.collapsible_tree_PUCs, name="collapsible_tree_PUCs"
    ),
    path("dl_pucs/", views.download_PUCs, name="download_PUCs"),
    path(
        "dl_lp_chemicals/",
        views.download_list_presence_chemicals,
        name="download_LP_chemicals",
    ),
    path("dl_puctags/", views.download_PUCTags, name="download_PUCTags"),
    path("dl_lpkeywords/", views.download_LPKeywords, name="download_LPKeywords"),
    path(
        "dl_functionalusecategories/",
        views.download_FunctionalUseCategories,
        name="download_FunctionalUseCategories",
    ),
    path(
        "dl_functional_uses/",
        views.download_functional_uses,
        name="download_functional_uses",
    ),
    path(
        "functional_use_categories/",
        views.functional_use_category_list,
        name="functional_use_category_list",
    ),
    path(
        "functional_use_category/<int:pk>/",
        views.functional_use_category_detail,
        name="functional_use_category_detail",
    ),
    path(
        "dl_raw_chems_dg/<int:pk>/",
        views.download_raw_chems_dg,
        name="download_raw_chems_dg",
    ),
    path("chemical/<str:sid>/", views.chemical_detail, name="chemical"),
    path(
        "dl_composition_chemical/<str:sid>/",
        views.download_composition_chemical,
        name="download_composition_chemical",
    ),
    path(
        "dl_functional_uses_chemical/<str:sid>/",
        views.download_functional_uses_chemical,
        name="download_functional_uses_chemical",
    ),
    path(
        "chemical/<str:sid>/puc/<int:puc_id>/",
        views.chemical_detail,
        name="chemical_puc",
    ),
    path(
        "chemical_product_json/",
        views.ChemicalProductListJson.as_view(),
        name="chemical_product_ajax_url",
    ),
    path(
        "chemical_functional_use_json/",
        views.ChemicalFunctionalUseListJson.as_view(),
        name="chemical_functional_use_ajax_url",
    ),
    path(
        "habitsandpractices/<int:pk>/",
        views.habitsandpractices,
        name="habitsandpractices",
    ),
    path(
        "link_habitandpractice_to_puc/<int:pk>/",
        views.link_habitsandpractices,
        name="link_habitsandpractices",
    ),
    path("get_data/", views.get_data, name="get_data"),
    path("statistics/", views.Statistics.as_view(), name="statistics"),
    path("visualizations/", views.Visualizations.as_view(), name="visualizations"),
    path("bulk_documents/", views.BulkDocuments.as_view(), name="bulk_documents"),
    path(
        "bulk_rawcategory/",
        views.RawCategoryToPUCList.as_view(),
        name="rawcategory_to_puc",
    ),
    path("dl_chem_summary/", views.download_chem_stats, name="download_chem_stats"),
    path("upload/dtxsid_csv/", views.upload_dtxsid_csv, name="upload_dtxsid_csv"),
    path(
        "get_data/get_dsstox_csv_template/",
        views.get_data_dsstox_csv_template,
        name="get_data_dsstox_csv_template",
    ),
    path(
        "product_csv_template/<int:pk>/",
        views.get_product_csv_template,
        name="get_product_csv_template",
    ),
    path(
        "extractedtext/edit/<int:pk>/",
        views.extracted_text_edit,
        name="extracted_text_edit",
    ),
    path(
        "datadocument/edit/<int:pk>/",
        views.data_document_edit,
        name="data_document_edit",
    ),
    path(
        "datadocument/<int:pk>/download_chemicals/",
        views.download_document_chemicals,
        name="download_document_chemicals",
    ),
    path("qanotes/save/<int:pk>/", views.save_qa_notes, name="save_qa_notes"),
    path(
        "qasummarynote/edit/<str:model>/<int:pk>/",
        views.edit_qa_summary_note,
        name="edit_qa_summary_note",
    ),
    path(
        "extractedtext/approve/<int:pk>/",
        views.approve_extracted_text,
        name="approve_extracted_text",
    ),
    path(
        "extractedtext/delete/<int:pk>/",
        views.delete_extracted_text,
        name="delete_extracted_text",
    ),
    path(
        "chemical/delete/<int:doc_pk>/<int:chem_pk>/",
        views.chemical_delete,
        name="chemical_delete",
    ),
    path(
        "chemical/<int:doc>/create/",
        views.ChemCreateView.as_view(),
        name="chemical_create",
    ),
    path("chemical/<pk>/edit/", views.ChemUpdateView.as_view(), name="chemical_update"),
    path(
        "habitspractices/<int:doc>/create/",
        views.EHPCreateView.as_view(),
        name="ehp_create",
    ),
    path(
        "habitspractices/<pk>/edit/", views.EHPUpdateView.as_view(), name="ehp_update"
    ),
    path(
        "datadocument/<int:doc>/habitspractices/<pk>/delete/",
        views.EHPDeleteView.as_view(),
        name="ehp_delete",
    ),
    path(
        "chemical/<pk>/auditlog/", views.chemical_audit_log, name="chemical_audit_log"
    ),
    path(
        "document/<pk>/auditlog/", views.document_audit_log, name="document_audit_log"
    ),
    path(
        "document/<pk>/auditlog/table",
        views.DocumentAuditLog.as_view(),
        name="document_audit_log_table",
    ),
    path(
        "list_presence_tag/delete/<int:doc_pk>/<int:chem_pk>/<int:tag_pk>/",
        views.list_presence_tag_delete,
        name="list_presence_tag_delete",
    ),
    path(
        "habits_and_practices_tag/delete/<int:doc_pk>/<int:chem_pk>/<int:tag_pk>/",
        views.habits_and_practices_tag_delete,
        name="habits_and_practices_tag_delete",
    ),
    path("search/<str:model>/", views.search_model, name="search-model"),
    path(
        "list_presence_tags/",
        views.list_presence_tag_list,
        name="list_presence_tag_list",
    ),
    path(
        "list_presence_tag/<int:pk>/",
        views.ListPresenceTagView.as_view(),
        name="lp_tag_detail",
    ),
    path(
        "list_presence_tag/<int:pk>/tagsets/",
        views.ListPresenceTagSetsJson.as_view(),
        name="lp_tagsets",
    ),
    path(
        "list_presence_tag/<int:tag_pk>/documents/",
        views.ListPresenceDocumentsJson.as_view(),
        name="lp_documents",
    ),
    path(
        "data_group_tracking/",
        dashboard.views.data_group_tracking,
        name="data_group_tracking",
    ),
    path(
        "data_group_tracking/edit/<int:dg_pk>/",
        dashboard.views.edit_data_group_tracking,
        name="data_group_tracking_edit",
    ),
    path("", include("django_prometheus.urls")),
]
if settings.DEBUG is True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
