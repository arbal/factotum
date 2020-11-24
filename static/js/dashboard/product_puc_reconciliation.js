$(document).ready(function () {
    var oTable = $('#assigned-pucs').dataTable({
        order: [[ 0, "asc" ]],
        language: {
            "sSearchPlaceholder": "Filter by Product",
        },
        columns: [
            {
                data: 'product_id',
                searchable: false,

            },
            {
                data: 'product__title',
                orderable: true,
                searchable: true
            },
            {
                data: 'puc',
                orderable: true,
                searchable: false,
            },
            {
                data: 'classification_method',
                orderable: true,
                searchable: false,
            },
            // {   
            //     data: 'unassign',
            //     orderable: false,
            // },
            {
                data: 'classification_confidence',
                orderable: true,
                searchable: false,
            }
        ],
        processing: true,
        serverSide: true,
        stateSave: true,
        ajax: "/p_puc_json/",
    });
});