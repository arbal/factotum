$(document).ready(function () {
    var puc = $('#products').data('puc');
    var pucname = $('#products').data('pucname');

    $("#product-tab-header").on("click", function () {
        $("div[id$='table-div']").hide();
        $("#product-table-div").show();
        var producttable = $('#products').DataTable({
            dom: "<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f><'col-md-4'>>" +
                "<'row'<'col-sm-12'tr>>" +
                "<'row'<'col-sm-5'i><'col-sm-7'p>>", // order the control divs
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
                },
                {
                    data: 2,
                    orderable: true,
                    searchable: true,
                }
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/p_json/?puc=" + puc
        });
    });

    $("#document-tab-header").on("click", function () {
        $("div[id$='table-div']").hide();
        $("#document-table-div").show();
        var documenttable = $('#documents').DataTable({
            dom: "<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f><'col-md-4'>>" +
                "<'row'<'col-sm-12'tr>>" +
                "<'row'<'col-sm-5'i><'col-sm-7'p>>", // order the control divs
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
                    className: "text-center"
                }
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/d_json/?puc=" + puc
        });
    });

    $("#chemical-tab-header").on("click", function () {
        $("div[id$='table-div']").hide();
        $("#chemical-table-div").show();
        var chemicaltable = $('#chemicals').DataTable({
            dom: "<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f><'col-md-4'B>>" +
                "<'row'<'col-sm-12'tr>>" +
                "<'row'<'col-sm-5'i><'col-sm-7'p>>", // order the control divs
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
                    width: "25%"
                },
                {
                    data: 2,
                    orderable: true,
                    searchable: true
                },
                {
                    data: 3,
                    orderable: true,
                    searchable: false
                },
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/c_json/?puc=" + puc,
            buttons: [{
               className: 'btn btn-primary btn-sm btn-dl-chemical',
                text: '<span class="fa fa-sm fa-file-csv"></span> Download All Chemicals Associated with PUC',
                title: pucname + '-chemicals',
                action: function ( e, dt, node, config ) {
                    document.location = "/puc_chemical_csv/" + puc;
                },
            }]
        });
    });
    $("#product-tab-header").click()
});

function activateTable(tableID) {
    $(tableID).click()
}
