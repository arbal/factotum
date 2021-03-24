let pucSelect2 = $('#id_puc')
let puc = null
let classification_methods = null
let product_table = null

function searchPUC() {
    puc = pucSelect2.val()

    // Display block if no puc is selected
    if (puc)
        $('#products-table-wrapper').removeClass("d-none")
    else
        $('#products-table-wrapper').addClass("d-none")

    product_table.ajax.reload()
}

function filterClassificationMethod() {
    classification_methods = []
    for (let cm of $("#classification-methods :input")
        .filter((key, node) => {
            return node.checked
        })) {
        classification_methods.push(cm.value)
    }

    // Don't attempt reload if initial load isn't done.
    if (product_table)
        product_table.ajax.reload()
}

pucSelect2.ready(function () {
    pucSelect2.attr('onchange', 'searchPUC()')
});

$(document).ready(function () {
    let table_settings = JSON.parse(document.getElementById('table_settings').textContent);

    // This loads in the current checked classification methods
    filterClassificationMethod()

    product_table = $('#products').DataTable({
        "lengthMenu": [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        "bPaginate": table_settings.pagination,
        "pageLength": table_settings.pageLength,
        "autoWidth": false,
        "processing": true,
        "ajax": {
            url: table_settings.ajax,
            data: function (d) {
                // Add the filtered properties.
                return $.extend({}, d, {"puc": puc, "classification_methods": classification_methods})
            }
        },
        "serverSide": true,
        columnDefs: [
            {
                defaultContent: "",
                data: null,
                orderable: false,
                searchable: false,
                width: '3%',
                className: 'select-checkbox',
                targets: 0
            },
            {
                title: "Product Name",
                data: "product__title",
                width: '40%',
                targets: 1
            },
            {
                title: "Classification Method",
                data: "classification_method__name",
                searchable: false,
                width: '20%',
                targets: 2
            },
            {
                data: "pk",
                orderable: false,
                searchable: false,
                className: 'hide_column',
                targets: 3
            },
        ],
        select: {
            style: 'multi',
            selector: 'td:first-child'
        },
        order: [
            [1, 'asc']
        ],
        "initComplete": function (settings, json) {
            $("div#products_info").insertAfter('div#products_wrapper');
        }
    });
    product_table.on("click", "th.select-checkbox", function () {
        if ($("th.select-checkbox").hasClass("selected")) {
            product_table.rows().deselect();
            $(product_table).removeClass("selected");
        } else {
            product_table.rows().select();
            $("th.select-checkbox").addClass("selected");
        }
    }).on("select deselect", function () {
        if (product_table.rows({
            selected: true
        }).count() !== product_table.rows().count()) {
            $("th.select-checkbox").removeClass("selected");
        } else {
            $("th.select-checkbox").addClass("selected");
        }
    });
    $('#btn-assign-puc').click(function (e) {
        pk_data = product_table.rows({selected: true});
        pk = '';
        // find the (hidden) pk column in each row
        for (i = 0; i < pk_data.count(); i++) {
            pk += pk_data.data()[i][4] + ',';
        }
        pk = pk.replace(/,$/g, '');
        $('input[name="id_pks"]').val(pk);
        return true;
    });
});
