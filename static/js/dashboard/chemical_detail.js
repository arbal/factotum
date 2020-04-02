var chemical = $('#chemical'),
    puc = chemical.data('puc'),
    sid = chemical.data('sid'),
    pid = chemical.data('pid'),
    puc_parents = chemical.data('puc-parents'),
    document_table,
    product_table;
nestedBubbleChart(500, 500, false, "/dl_pucs_json/?dtxsid=" + sid);


$(document).ready(function () {
    document_table = build_document_table().on('draw', moveText);
    product_table = build_product_table().on('draw', moveText);

    //expand accordion to default puc, if one exists
    if (puc_parents.length) {
        $('#accordion-' + puc_parents.join(', #accordion-')).collapse('show');
    }

    if (puc) {
        $('#reset-documents').prop('disabled', false);
        $('#reset-products').prop('disabled', false);

    }

    $('a[id^="filter-"]').on('click', e => {
        chemical.data('puc', $(e.currentTarget).data('pk'));
        document_table.ajax.url(get_documents_url()).load(moveText);
        product_table.ajax.url(get_products_url()).load(moveText);
        $('#reset-documents').prop('disabled', false);
        $('#reset-products').prop('disabled', false);
    });
    $('a[id^="keywords-"]').on('click', e => {
        chemical.data('pid', $(e.currentTarget).data('presence-id'));
        document_table.ajax.url(get_documents_url()).load(moveText);
        $('#reset-documents').prop('disabled', false);
    });
    $('#group_type_dropdown').on('change', e => {
        var group_type = $(e.currentTarget).children("option:selected").val();
        document_table.ajax.url(get_documents_url() + '&group_type=' + group_type).load(moveText);
        $('#reset-documents').prop('disabled', false);
    });
    $('#reset-documents').on('click', function (e) {
        chemical.data('puc', '');
        chemical.data('pid', '');
        document_table.ajax.url(get_documents_url()).load(moveText);
        $(this).prop('disabled', true);
    });
    $('#reset-products').on('click', function (e) {
        chemical.data('puc', '');
        chemical.data('pid', '');
        product_table.ajax.url(get_products_url()).load(moveText);
        $(this).prop('disabled', true);
    });
    var moveText = () => {
        $('#documents-info-text').text($('#documents-info').text());
        $('#products-info-text').text($('#products-info').text());
    };
});

function get_documents_url() {
    return '/d_json/?chem_detail=True&sid=' + chemical.data('sid') + '&category=' + chemical.data('puc') + '&pid=' + chemical.data('pid');
}

function get_products_url() {
    return '/chemical_product_json/?sid=' + chemical.data('sid') + '&category=' + chemical.data('puc');
}

function build_document_table() {
    return $('#documents').DataTable({
        columns: [
            {
                data: 0,
                orderable: true,
                searchable: true
            },
            {
                data: 1,
                orderable: true,
                searchable: true,
                className: "text-center",
                width: "30%"
            }
        ],
        dom: "<'row'<'col-6 form-inline'l><'col-6 form-inline'f>>" +
            "<'row'<'col-12 p-0'tr>>" +
            "<'row'i>" +
            "<'row'<'ml-auto'p>>",
        destroy: true,
        processing: true,
        serverSide: true,
        ordering: true,
        // stateSave: true,
        drawCallback: () => {
            // $('.paginate_button').on('click', moveText);
        },
        ajax: get_documents_url(),
        initComplete: function () {
            $('#documents-info-text').text($('#documents-info').text())
        }
    });
}

function build_product_table() {
    return $('#products').DataTable({
        columns: [
            {
                data: 0,
                orderable: true,
                searchable: true
            },
            {
                data: 1,
                orderable: true,
                searchable: true,
                className: "text-center",
                width: "30%"
            },
            {
                data: 2,
                orderable: true,
                searchable: true,
                className: "text-center",
                width: "30%"
            }

        ],
        dom: "<'row'<'col-6 form-inline'l><'col-6 form-inline'f>>" +
            "<'row'<'col-12 p-0'tr>>" +
            "<'row'i>" +
            "<'row'<'ml-auto'p>>",
        destroy: true,
        processing: true,
        serverSide: true,
        ordering: true,
        // stateSave: true,
        drawCallback: () => {
            // $('.paginate_button').on('click', moveText);
        },
        ajax: get_products_url(),
        initComplete: function () {
            $('#products-info-text').text($('#products-info').text())
        }
    });
}
