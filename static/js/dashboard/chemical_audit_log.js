$(document).ready(function () {
    var table = $('#audit-log').DataTable({
        "serverSide": false,
        "paging": false,
        "searching": false,
        "ordering": false,
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
