var chemical = $('#chemical'),
    puc = chemical.data('puc'),
    sid = chemical.data('sid'),
    pid = chemical.data('pid'),
    puc_parents = chemical.data('puc-parents'),
    document_table,
    product_table;

fobc = new nestedBubbleChart(500, 500, false, "/dl_pucs_json/?kind=FO&dtxsid=" + sid, "nestedcircles_FO");
arbc = new nestedBubbleChart(500, 500, false, "/dl_pucs_json/?kind=AR&dtxsid=" + sid, "nestedcircles_AR");
ocbc = new nestedBubbleChart(500, 500, false, "/dl_pucs_json/?kind=OC&dtxsid=" + sid, "nestedcircles_OC");

$( window ).on( "load", function() {
    if (puc) {
        // which chart does the specified PUC appear on?
        bubble_el = document.getElementById("bubble-" + puc);
        console.log(bubble_el);
        chart_el = bubble_el.closest(".nestedcircles");
        nbc = (chart_el.id == "nestedcircles_FO" ? fobc : (chart_el.id == "nestedcircles_AR" ? arbc : ocbc))
        fobc.zoomToNode(puc);
    }

});

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
        if ($(e.currentTarget).find(".icon-primary").length > 0) {
            // filter already applied, reset it
            chemical.data('puc', '');
            $(e.currentTarget).attr('data-original-title', 'Filter table by PUC');
            $(e.currentTarget).find('.icon-primary').removeClass('icon-primary').addClass('icon-secondary');
        } else {
            // apply new filter
            chemical.data('puc', $(e.currentTarget).data('pk'));
            $('a[id^="filter-"]').attr('data-original-title', 'Filter table by PUC');
            $('a[id^="filter-"]').find('.icon-primary').removeClass('icon-primary').addClass('icon-secondary');
            $(e.currentTarget).attr('data-original-title', 'Clear filter table by PUC');
            $(e.currentTarget).find('.icon-secondary').removeClass('icon-secondary').addClass('icon-primary');
        }
        let hasFilter = chemical.data('puc') || chemical.data('pid');
        $('#reset-documents').prop('disabled', !hasFilter);
        $('#reset-products').prop('disabled', !hasFilter);
        document_table.ajax.url(get_documents_url()).load(moveText);
        product_table.ajax.url(get_products_url()).load(moveText);
    });
    $('a[id^="keywords-"]').on('click', e => {
        if ($(e.currentTarget).find(".icon-primary").length > 0) {
            // filter already applied, reset it
            chemical.data('pid', '');
            $(e.currentTarget).attr('data-original-title', 'Filter table by Keyword Set');
            $(e.currentTarget).find('.icon-primary').removeClass('icon-primary').addClass('icon-secondary');
        } else {
            // apply new filter
            chemical.data('pid', $(e.currentTarget).data('presence-id'));
            // removing existing filter primary class and change this filter to primary
            $('a[id^="keywords-"]').attr('data-original-title', 'Filter table by Keyword Set');
            $('a[id^="keywords-"]').find(".icon-primary").removeClass("icon-primary").addClass("icon-secondary");
            $(e.currentTarget).attr('data-original-title', 'Clear filter table by Keyword Set');
            $(e.currentTarget).find(".icon-secondary").removeClass("icon-secondary").addClass("icon-primary");
        }
        document_table.ajax.url(get_documents_url()).load(moveText);
        let hasFilter = chemical.data('puc') || chemical.data('pid');
        $('#reset-documents').prop('disabled', !hasFilter);
    });
    $('#group_type_dropdown').on('change', e => {
        var group_type = $(e.currentTarget).children("option:selected").val();
        document_table.ajax.url(get_documents_url() + '&group_type=' + group_type).load(moveText);
        $('#reset-documents').prop('disabled', false);
    });
    $('#puc_kinds_dropdown').on('change', e => {
        var puc_kind = $(e.currentTarget).children("option:selected").val();
        product_table.ajax.url(get_products_url() + '&puc_kind=' + puc_kind).load(moveText);
        $('#reset-products').prop('disabled', false);
    });
    $('#reset-documents').on('click', function (e) {
        chemical.data('puc', '');
        chemical.data('pid', '');
        document_table.ajax.url(get_documents_url()).load(moveText);
        $(this).prop('disabled', true);
        // document is not filtered now, reset the keyword filter class/tooltip
        $('a[id^="keywords-"]').attr('data-original-title', 'Filter table by Keyword Set');
        $('a[id^="keywords-"]').find(".icon-primary").removeClass("icon-primary").addClass("icon-secondary");
        // if both document and product are not filtered, remove puc filter indicator
        if ($("#reset-products").is(":disabled")) {
            $('a[id^="filter-"]').find(".icon-primary").removeClass("icon-primary").addClass("icon-secondary");
        }
    });
    $('#reset-products').on('click', function (e) {
        chemical.data('puc', '');
        chemical.data('pid', '');
        product_table.ajax.url(get_products_url()).load(moveText);
        $(this).prop('disabled', true);
        // if both document and product are not filtered, remove puc filter indicator
        if ($("#reset-documents").is(":disabled")) {
            $('a[id^="filter-"]').attr('data-original-title', 'Filter table by PUC');
            $('a[id^="filter-"]').find(".icon-primary").removeClass("icon-primary").addClass("icon-secondary");
        }
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
        language: {
            "infoFiltered": "_FILTER_ (filtered from _MAX_ total documents)"
        },
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
            let infoText = $('#documents_info').text();
            if (infoText.indexOf('_FILTER_') > 0) {
                // customized the filter message
                let filter = '';
                let pucId = chemical.data('puc');
                let pid = chemical.data('pid');
                // puc filter
                if (pucId) {
                    let pucName = $('#puc-' + pucId).text();
                    filter += ' related to PUC <b>' + pucName + '</b>';
                }
                // keyword filter
                if (pid) {
                    let keywords = $('#keyset-' + pid).text();
                    let charsToKeep = 30;
                    // truncate keywords if too long
                    if (keywords.length > charsToKeep) {
                        keywords = keywords.substr(0, charsToKeep - 5).concat('... }');
                    }
                    if (filter) {
                        filter += ' and ';
                    } else {
                        filter += ' related to ';
                    }
                    filter += ' Keyword <b>' + keywords + '</b>';
                }
                infoText = infoText.replace('_FILTER_', filter);
                $("#documents_info").html(infoText);
            }
        },
        ajax: get_documents_url(),
        initComplete: function () {
            $('#documents-info-text').text($('#documents-info').text())
        }
    });
}

function build_product_table() {
    return $('#products').DataTable({
        language: {
            "infoFiltered": "_FILTER_ (filtered from _MAX_ total products)"
        },
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
            },
            {
                data: 3,
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
            let infoText = $('#products_info').text();
            if (infoText.indexOf('_FILTER_') > 0) {
                // customized the filter message
                let filter = '';
                let pucId = chemical.data('puc');
                if (pucId) {
                    let pucName = $('#puc-' + pucId).text();
                    filter += ' related to PUC <b>' + pucName + '</b>';
                }
                infoText = infoText.replace('_FILTER_', filter);
                $("#products_info").html(infoText);
            }
        },
        ajax: get_products_url(),
        initComplete: function () {
            $('#products-info-text').text($('#products-info').text())
        }
    });
}
