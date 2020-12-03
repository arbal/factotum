$(document).ready(function () {
    var table_url = JSON.parse(document.getElementById('table_url').textContent);
    $('#audit-log').DataTable({
        serverSide: true,
        paging: true,
        searching: false,
        ordering: false,
        ajax:  table_url,
        "columnDefs": [
            {
                "targets": 4,
                "render": function (data, type, row, meta) {
                    if (data === "I") {
                        return "Insert";
                    } else if (data === "U") {
                        return "Update";
                    } else {
                        return "Delete";
                    }
                }
            }
        ]
    });
});
