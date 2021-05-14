$(document).ready(function () {
    var functional_use_category = $('#products').data('functional_use_category');

    $("#product-tab-header").on("click", function(){
        $("div[id$='table-div']").hide();
        $("#product-table-div").show();
        var producttable = $('#products').DataTable({
            columns: [
                {
                    data: 0,
                    orderable: true,
                    searchable: true
                },
                {
                    data: 1,
                    orderable: false,
                    searchable: false,
                },
                {
                    data: 2,
                    orderable: false,
                    searchable: false,
                },
                {
                    data: 3,
                    orderable: true,
                    searchable: true,
                }
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/fuc_p_json/?functional_use_category=" + functional_use_category,
        });
    });

    $("#document-tab-header").on("click", function(){
        $("div[id$='table-div']").hide();
        $("#document-table-div").show();
        var documenttable = $('#documents').DataTable({
            columns: [
                {
                    data: 0,
                    orderable: true,
                    searchable: true,
                    className: "text-center"
                },
                {
                    data: 1,
                    orderable: true,
                    searchable: true
                    
                },
                {
                    data: 2,
                    orderable: true,
                    searchable: true
                },
                {
                    data: 3,
                    orderable: true,
                    searchable: true
                }
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/fuc_d_json/?functional_use_category=" + functional_use_category,
        });
    });

    $("#chemical-tab-header").on("click", function(){
        $("div[id$='table-div']").hide();
        $("#chemical-table-div").show();
        var chemicaltable = $('#chemicals').DataTable({
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
                    width:"25%"
                },
                {
                    data: 2,
                    orderable: true,
                    searchable: true
                },
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/fuc_c_json/?functional_use_category=" + functional_use_category,
        });
    });
    $("#product-tab-header").click()
});

function activateTable(tableID) {
    $(tableID).click()
}
