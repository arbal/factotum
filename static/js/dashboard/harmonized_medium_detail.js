$(document).ready(function () {
    var medium = $('#documents').data('medium');

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
            ajax: "/hm_d_json/?medium=" + medium,
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
                    searchable: true
                },
                {
                    data: 2,
                    orderable: true,
                    searchable: true,
                    className: "text-center",
                    width:"25%"
                },
            ],
            destroy: true,
            processing: true,
            serverSide: true,
            ordering: true,
            stateSave: true,
            ajax: "/hm_c_json/?medium=" + medium,
        });
    });
    $("#document-tab-header").click()
});

function activateTable(tableID) {
    $(tableID).click()
}
