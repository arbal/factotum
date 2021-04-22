$(document).ready(function () {
    let table_settings = JSON.parse(document.getElementById('table_settings').textContent);

    let table = $('#table').DataTable({
        "lengthMenu": [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        "paginate": table_settings.pagination,
        "pageLength": table_settings.pageLength,
        "autoWidth": false,
        "resizeable": true,
        "processing": true,
        "ajax": table_settings.ajax,
        "serverSide": true,
        columnDefs: [
            {
                title: "Chemical Name",
                data: "preferred_name",
                targets: 0
            },
            {
                title: "Functional Uses",
                data: "functional_uses",
                searchable: false,
                orderable: false,
                targets: 1
            },
            {
                title: "Document Title",
                data: "extracted_text__data_document__title",
                targets: 2
            },
        ],
    });
})
